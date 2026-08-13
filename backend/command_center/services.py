from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from billing.models import (
    Invoice,
    InvoiceLine,
    PaymentAllocation,
)
from customers.models import Customer, ServiceAccount
from field_operations.models import WorkOrder
from inventory.models import InventoryDevice
from network.models import NetworkNode, ProvisioningRequest
from notifications.models import NotificationJob
from support.models import Complaint, Incident
from tenancy.models import AuditLog, Organization


@dataclass(frozen=True)
class CommandCenterSummary:
    total_customers: int
    active_customers: int

    total_services: int
    active_services: int
    grace_period_services: int
    suspension_pending_services: int
    suspended_services: int
    restore_pending_services: int

    total_network_nodes: int
    active_network_nodes: int

    pending_provisioning_requests: int
    processing_provisioning_requests: int
    failed_provisioning_requests: int

    total_inventory_devices: int
    available_devices: int
    assigned_devices: int
    faulty_devices: int
    in_repair_devices: int

    total_invoices: int
    unpaid_invoices: int
    partially_paid_invoices: int
    paid_invoices: int

    invoiced_amount: Decimal
    collected_amount: Decimal
    outstanding_amount: Decimal

    open_complaints: int
    in_progress_complaints: int
    critical_complaints: int

    active_incidents: int
    critical_incidents: int

    open_work_orders: int
    critical_work_orders: int

    pending_notifications: int
    processing_notifications: int
    failed_notifications: int

    operational_health_score: int


def _count_by_status(queryset, status):
    return queryset.filter(status=status).count()


def _calculate_operational_health_score(
    *,
    total_network_nodes: int,
    active_network_nodes: int,
    failed_provisioning_requests: int,
    critical_complaints: int,
    critical_incidents: int,
    critical_work_orders: int,
    faulty_devices: int,
    in_repair_devices: int,
    failed_notifications: int,
) -> int:
    score = 100

    if total_network_nodes > 0:
        inactive_network_nodes = (
            total_network_nodes - active_network_nodes
        )

        network_penalty = min(
            30,
            round(
                (
                    inactive_network_nodes
                    / total_network_nodes
                )
                * 30
            ),
        )

        score -= network_penalty

    score -= min(
        failed_provisioning_requests * 5,
        15,
    )

    score -= min(
        critical_incidents * 10,
        25,
    )

    score -= min(
        critical_complaints * 5,
        15,
    )

    score -= min(
        critical_work_orders * 5,
        15,
    )

    score -= min(
        faulty_devices * 2,
        10,
    )

    score -= min(
        in_repair_devices,
        5,
    )

    score -= min(
        failed_notifications,
        5,
    )

    return max(0, min(100, score))


def get_command_center_summary(
    *,
    organization: Organization,
) -> CommandCenterSummary:
    customers = Customer.objects.for_organization(
        organization
    )

    services = ServiceAccount.objects.for_organization(
        organization
    )

    network_nodes = NetworkNode.objects.for_organization(
        organization
    )

    provisioning_requests = (
        ProvisioningRequest.objects.for_organization(
            organization
        )
    )

    devices = InventoryDevice.objects.for_organization(
        organization
    )

    invoices = Invoice.objects.for_organization(
        organization
    )

    complaints = Complaint.objects.for_organization(
        organization
    )

    incidents = Incident.objects.for_organization(
        organization
    )

    work_orders = WorkOrder.objects.for_organization(
        organization
    )

    notification_jobs = (
        NotificationJob.objects.for_organization(
            organization
        )
    )

    invoice_line_total = (
        InvoiceLine.objects
        .for_organization(organization)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    collected_total = (
        PaymentAllocation.objects
        .for_organization(organization)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    total_network_nodes = network_nodes.count()

    active_network_nodes = network_nodes.filter(
        is_active=True,
    ).count()

    failed_provisioning_requests = _count_by_status(
        provisioning_requests,
        ProvisioningRequest.Status.FAILED,
    )

    faulty_devices = _count_by_status(
        devices,
        InventoryDevice.Status.FAULTY,
    )

    in_repair_devices = _count_by_status(
        devices,
        InventoryDevice.Status.IN_REPAIR,
    )

    critical_complaints = complaints.filter(
        priority=Complaint.Priority.CRITICAL,
        status__in=[
            Complaint.Status.OPEN,
            Complaint.Status.IN_PROGRESS,
        ],
    ).count()

    critical_incidents = incidents.filter(
        severity=Incident.Severity.CRITICAL,
    ).exclude(
        status=Incident.Status.RESOLVED,
    ).count()

    critical_work_orders = work_orders.filter(
        priority=WorkOrder.Priority.CRITICAL,
    ).exclude(
        status=WorkOrder.Status.COMPLETED,
    ).count()

    failed_notifications = _count_by_status(
        notification_jobs,
        NotificationJob.Status.FAILED,
    )

    operational_health_score = (
        _calculate_operational_health_score(
            total_network_nodes=total_network_nodes,
            active_network_nodes=active_network_nodes,
            failed_provisioning_requests=(
                failed_provisioning_requests
            ),
            critical_complaints=critical_complaints,
            critical_incidents=critical_incidents,
            critical_work_orders=critical_work_orders,
            faulty_devices=faulty_devices,
            in_repair_devices=in_repair_devices,
            failed_notifications=failed_notifications,
        )
    )

    return CommandCenterSummary(
        total_customers=customers.count(),
        active_customers=customers.filter(
            is_active=True,
        ).count(),

        total_services=services.count(),
        active_services=_count_by_status(
            services,
            ServiceAccount.Status.ACTIVE,
        ),
        grace_period_services=_count_by_status(
            services,
            ServiceAccount.Status.GRACE_PERIOD,
        ),
        suspension_pending_services=_count_by_status(
            services,
            ServiceAccount.Status.SUSPENSION_PENDING,
        ),
        suspended_services=_count_by_status(
            services,
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT,
        ),
        restore_pending_services=_count_by_status(
            services,
            ServiceAccount.Status.RESTORE_PENDING,
        ),

        total_network_nodes=total_network_nodes,
        active_network_nodes=active_network_nodes,

        pending_provisioning_requests=_count_by_status(
            provisioning_requests,
            ProvisioningRequest.Status.PENDING,
        ),
        processing_provisioning_requests=_count_by_status(
            provisioning_requests,
            ProvisioningRequest.Status.PROCESSING,
        ),
        failed_provisioning_requests=(
            failed_provisioning_requests
        ),

        total_inventory_devices=devices.count(),
        available_devices=_count_by_status(
            devices,
            InventoryDevice.Status.AVAILABLE,
        ),
        assigned_devices=_count_by_status(
            devices,
            InventoryDevice.Status.ASSIGNED,
        ),
        faulty_devices=faulty_devices,
        in_repair_devices=in_repair_devices,

        total_invoices=invoices.count(),
        unpaid_invoices=_count_by_status(
            invoices,
            Invoice.Status.UNPAID,
        ),
        partially_paid_invoices=_count_by_status(
            invoices,
            Invoice.Status.PARTIALLY_PAID,
        ),
        paid_invoices=_count_by_status(
            invoices,
            Invoice.Status.PAID,
        ),

        invoiced_amount=invoice_line_total,
        collected_amount=collected_total,
        outstanding_amount=(
            invoice_line_total - collected_total
        ),

        open_complaints=_count_by_status(
            complaints,
            Complaint.Status.OPEN,
        ),
        in_progress_complaints=_count_by_status(
            complaints,
            Complaint.Status.IN_PROGRESS,
        ),
        critical_complaints=critical_complaints,

        active_incidents=incidents.exclude(
            status=Incident.Status.RESOLVED,
        ).count(),
        critical_incidents=critical_incidents,

        open_work_orders=work_orders.exclude(
            status=WorkOrder.Status.COMPLETED,
        ).count(),
        critical_work_orders=critical_work_orders,

        pending_notifications=_count_by_status(
            notification_jobs,
            NotificationJob.Status.PENDING,
        ),
        processing_notifications=_count_by_status(
            notification_jobs,
            NotificationJob.Status.PROCESSING,
        ),
        failed_notifications=failed_notifications,

        operational_health_score=(
            operational_health_score
        ),
    )


def get_operational_alerts(
    *,
    organization: Organization,
):
    alerts = []

    failed_provisioning_requests = (
        ProvisioningRequest.objects
        .for_organization(organization)
        .filter(
            status=ProvisioningRequest.Status.FAILED
        )
    )

    for provisioning_request in (
        failed_provisioning_requests
    ):
        alerts.append(
            {
                "alert_type": "PROVISIONING_FAILED",
                "severity": "CRITICAL",
                "title": "Provisioning request failed",
                "description": (
                    "A network provisioning request "
                    "requires operational review."
                ),
                "resource_type": "ProvisioningRequest",
                "resource_id": str(
                    provisioning_request.id
                ),
                "occurred_at": (
                    provisioning_request.updated_at
                ),
                "context": {
                    "status": provisioning_request.status,
                    "action": provisioning_request.action,
                },
            }
        )

    critical_incidents = (
        Incident.objects
        .for_organization(organization)
        .filter(
            severity=Incident.Severity.CRITICAL
        )
        .exclude(
            status=Incident.Status.RESOLVED
        )
    )

    for incident in critical_incidents:
        alerts.append(
            {
                "alert_type": "CRITICAL_INCIDENT",
                "severity": "CRITICAL",
                "title": "Critical incident active",
                "description": (
                    "A critical operational incident "
                    "remains active."
                ),
                "resource_type": "Incident",
                "resource_id": str(incident.id),
                "occurred_at": incident.created_at,
                "context": {
                    "status": incident.status,
                    "severity": incident.severity,
                },
            }
        )

    critical_complaints = (
        Complaint.objects
        .for_organization(organization)
        .filter(
            priority=Complaint.Priority.CRITICAL,
            status__in=[
                Complaint.Status.OPEN,
                Complaint.Status.IN_PROGRESS,
            ],
        )
    )

    for complaint in critical_complaints:
        alerts.append(
            {
                "alert_type": "CRITICAL_COMPLAINT",
                "severity": "CRITICAL",
                "title": (
                    "Critical complaint requires attention"
                ),
                "description": (
                    "A critical customer complaint "
                    "remains active."
                ),
                "resource_type": "Complaint",
                "resource_id": str(complaint.id),
                "occurred_at": complaint.created_at,
                "context": {
                    "status": complaint.status,
                    "priority": complaint.priority,
                },
            }
        )

    critical_work_orders = (
        WorkOrder.objects
        .for_organization(organization)
        .filter(
            priority=WorkOrder.Priority.CRITICAL
        )
        .exclude(
            status=WorkOrder.Status.COMPLETED
        )
    )

    for work_order in critical_work_orders:
        alerts.append(
            {
                "alert_type": "CRITICAL_WORK_ORDER",
                "severity": "CRITICAL",
                "title": "Critical field work pending",
                "description": (
                    "A critical work order has not "
                    "been completed."
                ),
                "resource_type": "WorkOrder",
                "resource_id": str(work_order.id),
                "occurred_at": work_order.created_at,
                "context": {
                    "status": work_order.status,
                    "priority": work_order.priority,
                    "work_order_type": (
                        work_order.work_order_type
                    ),
                },
            }
        )

    inventory_devices = (
        InventoryDevice.objects
        .for_organization(organization)
        .filter(
            status__in=[
                InventoryDevice.Status.FAULTY,
                InventoryDevice.Status.IN_REPAIR,
            ]
        )
    )

    for device in inventory_devices:
        severity = (
            "HIGH"
            if device.status
            == InventoryDevice.Status.FAULTY
            else "MEDIUM"
        )

        alerts.append(
            {
                "alert_type": (
                    "INVENTORY_DEVICE_ATTENTION"
                ),
                "severity": severity,
                "title": (
                    "Inventory device requires attention"
                ),
                "description": (
                    "An ISP asset is faulty or currently "
                    "in repair."
                ),
                "resource_type": "InventoryDevice",
                "resource_id": str(device.id),
                "occurred_at": device.updated_at,
                "context": {
                    "asset_tag": device.asset_tag,
                    "device_type": device.device_type,
                    "status": device.status,
                },
            }
        )

    failed_notifications = (
        NotificationJob.objects
        .for_organization(organization)
        .filter(
            status=NotificationJob.Status.FAILED
        )
    )

    for notification_job in failed_notifications:
        alerts.append(
            {
                "alert_type": "NOTIFICATION_FAILED",
                "severity": "HIGH",
                "title": "Customer notification failed",
                "description": (
                    "A queued customer notification "
                    "failed delivery."
                ),
                "resource_type": "NotificationJob",
                "resource_id": str(
                    notification_job.id
                ),
                "occurred_at": (
                    notification_job.failed_at
                    or notification_job.updated_at
                ),
                "context": {
                    "channel": notification_job.channel,
                    "event_type": (
                        notification_job.event_type
                    ),
                    "recipient": (
                        notification_job.recipient
                    ),
                },
            }
        )

    return sorted(
        alerts,
        key=lambda alert: alert["occurred_at"],
        reverse=True,
    )


def get_priority_queues(
    *,
    organization: Organization,
):
    pending_provisioning = (
        ProvisioningRequest.objects
        .for_organization(organization)
        .filter(
            status=ProvisioningRequest.Status.PENDING
        )
        .order_by("requested_at")
    )

    critical_complaints = (
        Complaint.objects
        .for_organization(organization)
        .filter(
            priority=Complaint.Priority.CRITICAL,
            status__in=[
                Complaint.Status.OPEN,
                Complaint.Status.IN_PROGRESS,
            ],
        )
        .order_by("created_at")
    )

    critical_incidents = (
        Incident.objects
        .for_organization(organization)
        .filter(
            severity=Incident.Severity.CRITICAL
        )
        .exclude(
            status=Incident.Status.RESOLVED
        )
        .order_by("created_at")
    )

    critical_work_orders = (
        WorkOrder.objects
        .for_organization(organization)
        .filter(
            priority=WorkOrder.Priority.CRITICAL
        )
        .exclude(
            status=WorkOrder.Status.COMPLETED
        )
        .order_by("created_at")
    )

    failed_notifications = (
        NotificationJob.objects
        .for_organization(organization)
        .filter(
            status=NotificationJob.Status.FAILED
        )
        .order_by("created_at")
    )

    inventory_attention = (
        InventoryDevice.objects
        .for_organization(organization)
        .filter(
            status__in=[
                InventoryDevice.Status.FAULTY,
                InventoryDevice.Status.IN_REPAIR,
            ]
        )
        .order_by("updated_at")
    )

    return {
        "pending_provisioning": [
            {
                "resource_id": str(item.id),
                "status": item.status,
                "action": item.action,
                "queued_at": item.requested_at,
            }
            for item in pending_provisioning
        ],
        "critical_complaints": [
            {
                "resource_id": str(item.id),
                "status": item.status,
                "priority": item.priority,
                "queued_at": item.created_at,
            }
            for item in critical_complaints
        ],
        "critical_incidents": [
            {
                "resource_id": str(item.id),
                "status": item.status,
                "severity": item.severity,
                "queued_at": item.created_at,
            }
            for item in critical_incidents
        ],
        "critical_work_orders": [
            {
                "resource_id": str(item.id),
                "status": item.status,
                "priority": item.priority,
                "work_order_type": (
                    item.work_order_type
                ),
                "queued_at": item.created_at,
            }
            for item in critical_work_orders
        ],
        "failed_notifications": [
            {
                "resource_id": str(item.id),
                "status": item.status,
                "channel": item.channel,
                "event_type": item.event_type,
                "queued_at": item.created_at,
            }
            for item in failed_notifications
        ],
        "inventory_attention": [
            {
                "resource_id": str(item.id),
                "asset_tag": item.asset_tag,
                "device_type": item.device_type,
                "status": item.status,
                "queued_at": item.updated_at,
            }
            for item in inventory_attention
        ],
    }


def get_recent_operational_activity(
    *,
    organization: Organization,
    limit: int = 50,
):
    audit_logs = (
        AuditLog.objects
        .filter(organization=organization)
        .select_related("actor")
        .order_by("-created_at")[:limit]
    )

    return [
        {
            "id": audit_log.id,
            "action": audit_log.action,
            "resource_type": (
                audit_log.resource_type
            ),
            "resource_id": audit_log.resource_id,
            "actor": (
                {
                    "id": audit_log.actor.id,
                    "email": audit_log.actor.email,
                    "first_name": (
                        audit_log.actor.first_name
                    ),
                    "last_name": (
                        audit_log.actor.last_name
                    ),
                }
                if audit_log.actor
                else None
            ),
            "metadata": audit_log.metadata,
            "created_at": audit_log.created_at,
        }
        for audit_log in audit_logs
    ]