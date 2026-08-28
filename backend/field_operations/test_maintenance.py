from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from field_operations.maintenance import (
    MaintenanceDomainError,
    complete_maintenance,
    restore_maintenance,
    schedule_maintenance,
    start_maintenance,
)
from field_operations.models import WorkOrder
from field_operations.services import create_work_order
from tenancy.models import AuditLog, Organization


class MaintenanceLifecycleTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Maintenance ISP",
            code="MAINT-ISP",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

        self.work_order = create_work_order(
            organization=self.organization,
            work_type=WorkOrder.WorkType.NETWORK_MAINTENANCE,
            priority=WorkOrder.Priority.HIGH,
            title="Core router maintenance",
            description="Planned maintenance for the core router.",
        ).work_order

    def test_full_scheduled_started_completed_restored_lifecycle(self):
        scheduled_at = timezone.now() + timedelta(hours=2)

        schedule_maintenance(
            organization=self.organization,
            work_order_id=self.work_order.id,
            scheduled_at=scheduled_at,
            maintenance_notes="Customers will be notified before maintenance.",
        )
        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.status, WorkOrder.Status.SCHEDULED)
        self.assertEqual(self.work_order.scheduled_at, scheduled_at)

        start_maintenance(
            organization=self.organization,
            work_order_id=self.work_order.id,
        )
        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.status, WorkOrder.Status.STARTED)
        self.assertIsNotNone(self.work_order.started_at)

        complete_maintenance(
            organization=self.organization,
            work_order_id=self.work_order.id,
            completion_notes="Maintenance completed successfully.",
        )
        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.status, WorkOrder.Status.COMPLETED)
        self.assertIsNotNone(self.work_order.completed_at)

        restore_maintenance(
            organization=self.organization,
            work_order_id=self.work_order.id,
        )
        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.status, WorkOrder.Status.RESTORED)
        self.assertIsNotNone(self.work_order.restored_at)

        self.assertEqual(
            AuditLog.objects.filter(
                organization=self.organization,
                resource_type="WorkOrder",
                resource_id=self.work_order.id,
            ).count(),
            5,
        )

    def test_invalid_order_is_rejected(self):
        with self.assertRaisesMessage(MaintenanceDomainError, "Only scheduled maintenance can be started."):
            start_maintenance(
                organization=self.organization,
                work_order_id=self.work_order.id,
            )

        with self.assertRaisesMessage(MaintenanceDomainError, "Only completed maintenance can be restored."):
            restore_maintenance(
                organization=self.organization,
                work_order_id=self.work_order.id,
            )

    def test_schedule_requires_future_time(self):
        with self.assertRaisesMessage(MaintenanceDomainError, "Maintenance must be scheduled for a future time."):
            schedule_maintenance(
                organization=self.organization,
                work_order_id=self.work_order.id,
                scheduled_at=timezone.now() - timedelta(minutes=1),
            )

    def test_only_network_maintenance_can_use_lifecycle(self):
        repair = create_work_order(
            organization=self.organization,
            work_type=WorkOrder.WorkType.REPAIR,
            priority=WorkOrder.Priority.MEDIUM,
            title="Repair",
            description="Normal repair.",
        ).work_order

        with self.assertRaisesMessage(
            MaintenanceDomainError,
            "Maintenance lifecycle is only available for network maintenance work orders.",
        ):
            schedule_maintenance(
                organization=self.organization,
                work_order_id=repair.id,
                scheduled_at=timezone.now() + timedelta(hours=1),
            )

    def test_completion_notes_required(self):
        schedule_maintenance(
            organization=self.organization,
            work_order_id=self.work_order.id,
            scheduled_at=timezone.now() + timedelta(hours=1),
        )
        start_maintenance(
            organization=self.organization,
            work_order_id=self.work_order.id,
        )

        with self.assertRaisesMessage(
            MaintenanceDomainError,
            "Completion notes are required to complete maintenance.",
        ):
            complete_maintenance(
                organization=self.organization,
                work_order_id=self.work_order.id,
                completion_notes="   ",
            )
