from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from customers.models import Customer

from .models import CommunicationAutomation, CommunicationSchedule
from .automation_service import CommunicationAutomationService


class CommunicationScheduleService:
    """Execute due communication schedules with tenant-safe locking."""

    @classmethod
    def process_due(cls, *, limit=100):
        processed = 0
        for schedule_id in cls._due_schedule_ids(limit=limit):
            if cls.process_schedule(schedule_id):
                processed += 1
        return processed

    @staticmethod
    def _due_schedule_ids(*, limit):
        now = timezone.now()
        return list(
            CommunicationSchedule.objects.filter(
                is_enabled=True,
                next_run__lte=now,
                automation__is_enabled=True,
            )
            .order_by("next_run", "created_at")
            .values_list("id", flat=True)[:limit]
        )

    @classmethod
    def process_schedule(cls, schedule_id):
        now = timezone.now()
        with transaction.atomic():
            schedule = (
                CommunicationSchedule.objects
                .select_for_update()
                .select_related(
                    "automation",
                    "automation__template",
                    "automation__template__communication_provider",
                )
                .filter(id=schedule_id, is_enabled=True)
                .first()
            )
            if schedule is None or schedule.next_run > now:
                return False

            automation = schedule.automation
            if not automation.is_enabled:
                schedule.is_enabled = False
                schedule.save(update_fields=["is_enabled", "updated_at"])
                return False

            customers = Customer.objects.filter(
                organization=schedule.organization,
                is_active=True,
            ).order_by("id")

            queued = 0
            for customer in customers.iterator(chunk_size=500):
                if CommunicationAutomationService.execute_automation(
                    automation=automation,
                    customer=customer,
                    lifecycle_event=f"SCHEDULE:{schedule.frequency}",
                ) is not None:
                    queued += 1

            schedule.last_run = now
            if schedule.frequency == CommunicationSchedule.Frequency.ONCE:
                schedule.is_enabled = False
            elif schedule.frequency == CommunicationSchedule.Frequency.DAILY:
                schedule.next_run = schedule.next_run + timedelta(days=1)
            elif schedule.frequency == CommunicationSchedule.Frequency.WEEKLY:
                schedule.next_run = schedule.next_run + timedelta(weeks=1)
            elif schedule.frequency == CommunicationSchedule.Frequency.MONTHLY:
                schedule.next_run = cls._add_month(schedule.next_run)
            else:
                schedule.is_enabled = False

            schedule.save(
                update_fields=[
                    "last_run",
                    "next_run",
                    "is_enabled",
                    "updated_at",
                ]
            )
            return queued > 0

    @staticmethod
    def _add_month(value):
        year = value.year + (1 if value.month == 12 else 0)
        month = 1 if value.month == 12 else value.month + 1
        import calendar
        day = min(value.day, calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)
