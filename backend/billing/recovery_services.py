import re
from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import Invoice, PaymentAllocation, PromiseToPay, RecoveryAllocation
from customers.models import Customer, ServiceAccount
from tenancy.models import AuditLog, OrganizationMembership, StaffProfile


def generate_allocation_number(organization):
    """Generate sequential recovery allocation number {ORG}-REC-XXXXX."""
    prefix = f"{organization.code.upper()}-REC-"
    last_rec = (
        RecoveryAllocation.objects.for_organization(organization)
        .filter(allocation_number__startswith=prefix)
        .order_by("-allocation_number")
        .first()
    )

    if not last_rec:
        return f"{prefix}00001"

    match = re.search(r"(\d+)$", last_rec.allocation_number)
    if match:
        next_seq = int(match.group(1)) + 1
        return f"{prefix}{next_seq:05d}"

    count = RecoveryAllocation.objects.for_organization(organization).count() + 1
    return f"{prefix}{count:05d}"


def get_defaulters_data(
    organization,
    *,
    search=None,
    city=None,
    area=None,
    aging_bucket=None,
    min_amount=None,
    has_active_allocation=None,
):
    """
    Query real overdue accounts from unpaid/partially paid invoices.
    Calculates authentic outstanding amounts and aging without mock data.
    """
    today = timezone.now().date()

    overdue_invoices = (
        Invoice.objects.for_organization(organization)
        .filter(
            status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID],
            due_date__lt=today,
        )
        .select_related("service_account__customer", "billing_profile")
    )

    if city:
        overdue_invoices = overdue_invoices.filter(service_account__customer__city__iexact=city.strip())
    if area:
        overdue_invoices = overdue_invoices.filter(service_account__customer__area__iexact=area.strip())
    if search:
        search_term = search.strip()
        overdue_invoices = overdue_invoices.filter(
            Q(service_account__customer__full_name__icontains=search_term)
            | Q(service_account__customer__customer_number__icontains=search_term)
            | Q(service_account__customer__phone__icontains=search_term)
            | Q(service_account__service_number__icontains=search_term)
            | Q(invoice_number__icontains=search_term)
        )

    # Group overdue invoices by customer
    customer_map = {}
    for inv in overdue_invoices:
        cust = inv.service_account.customer
        cust_id = str(cust.id)
        balance = inv.total_amount - inv.paid_amount
        if balance <= 0:
            continue

        days_overdue = (today - inv.due_date).days

        if cust_id not in customer_map:
            customer_map[cust_id] = {
                "customer_id": str(cust.id),
                "customer_number": cust.customer_number,
                "full_name": cust.full_name,
                "phone": cust.phone,
                "city": cust.city,
                "area": cust.area,
                "service_account_id": str(inv.service_account_id),
                "internet_id": inv.service_account.service_number,
                "total_overdue": Decimal("0.00"),
                "overdue_invoices_count": 0,
                "oldest_due_date": inv.due_date,
                "max_days_overdue": days_overdue,
                "invoices": [],
            }

        customer_map[cust_id]["total_overdue"] += balance
        customer_map[cust_id]["overdue_invoices_count"] += 1
        customer_map[cust_id]["invoices"].append(
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "due_date": inv.due_date.isoformat(),
                "total_amount": str(inv.total_amount),
                "paid_amount": str(inv.paid_amount),
                "balance": str(balance),
                "days_overdue": days_overdue,
            }
        )

        if inv.due_date < customer_map[cust_id]["oldest_due_date"]:
            customer_map[cust_id]["oldest_due_date"] = inv.due_date
        if days_overdue > customer_map[cust_id]["max_days_overdue"]:
            customer_map[cust_id]["max_days_overdue"] = days_overdue

    # Fetch active allocations and promises for these customers
    cust_ids = list(customer_map.keys())
    active_allocations = (
        RecoveryAllocation.objects.for_organization(organization)
        .filter(
            customer_id__in=cust_ids,
            status__in=[
                RecoveryAllocation.Status.ALLOCATED,
                RecoveryAllocation.Status.IN_PROGRESS,
                RecoveryAllocation.Status.CONTACTED,
                RecoveryAllocation.Status.PROMISE_RECEIVED,
            ],
        )
        .select_related("assigned_staff")
    )
    alloc_map = {str(a.customer_id): a for a in active_allocations}

    active_promises = (
        PromiseToPay.objects.for_organization(organization)
        .filter(
            customer_id__in=cust_ids,
            status__in=[PromiseToPay.Status.PENDING, PromiseToPay.Status.ACTIVE],
        )
    )
    promise_map = {str(p.customer_id): p for p in active_promises}

    defaulters_list = []
    for cust_id, data in customer_map.items():
        max_days = data["max_days_overdue"]
        if max_days <= 30:
            bucket = "0-30"
        elif max_days <= 60:
            bucket = "31-60"
        elif max_days <= 90:
            bucket = "61-90"
        else:
            bucket = "90+"

        data["aging_bucket"] = bucket
        data["oldest_due_date"] = data["oldest_due_date"].isoformat()

        alloc = alloc_map.get(cust_id)
        if alloc:
            data["active_allocation"] = {
                "id": str(alloc.id),
                "allocation_number": alloc.allocation_number,
                "assigned_staff_id": str(alloc.assigned_staff_id),
                "assigned_staff_name": alloc.assigned_staff.get_full_name() or alloc.assigned_staff.email,
                "status": alloc.status,
                "priority": alloc.priority,
                "due_date": alloc.due_date.isoformat() if alloc.due_date else None,
            }
        else:
            data["active_allocation"] = None

        prom = promise_map.get(cust_id)
        if prom:
            data["active_promise"] = {
                "id": str(prom.id),
                "promise_number": prom.promise_number,
                "promised_amount": str(prom.promised_amount),
                "deadline": prom.deadline.isoformat(),
                "status": prom.status,
            }
        else:
            data["active_promise"] = None

        # Filter applications
        if aging_bucket and bucket != aging_bucket:
            continue
        if min_amount and data["total_overdue"] < Decimal(str(min_amount)):
            continue
        if has_active_allocation is True and not data["active_allocation"]:
            continue
        if has_active_allocation is False and data["active_allocation"]:
            continue

        defaulters_list.append(data)

    # Sort by total overdue descending
    defaulters_list.sort(key=lambda x: x["total_overdue"], reverse=True)
    return defaulters_list


@transaction.atomic
def allocate_defaulter(
    *,
    organization,
    actor,
    customer,
    assigned_staff,
    service_account=None,
    invoice=None,
    outstanding_amount=None,
    due_date=None,
    priority=RecoveryAllocation.Priority.NORMAL,
    notes="",
):
    """
    Create a recovery allocation for an overdue customer account.
    Enforces duplicate active allocation protection.
    """
    if customer.organization_id != organization.id:
        raise ValidationError({"customer": "Customer does not belong to organization."})

    if not OrganizationMembership.objects.filter(
        organization=organization,
        user=assigned_staff,
        is_active=True,
    ).exists():
        raise ValidationError({"assigned_staff": "Assigned staff does not belong to organization or is inactive."})

    # Check for existing active allocation
    active_qs = RecoveryAllocation.objects.for_organization(organization).filter(
        customer=customer,
        status__in=[
            RecoveryAllocation.Status.ALLOCATED,
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.PROMISE_RECEIVED,
        ],
    )
    if service_account:
        active_qs = active_qs.filter(Q(service_account=service_account) | Q(service_account__isnull=True))

    if active_qs.exists():
        existing = active_qs.first()
        raise ValidationError(
            {
                "non_field_errors": (
                    f"Customer already has an active allocation ({existing.allocation_number}) assigned to "
                    f"{existing.assigned_staff.get_full_name() or existing.assigned_staff.email}. "
                    "Reassign the existing allocation instead."
                )
            }
        )

    # Compute or validate outstanding amount
    if outstanding_amount is None or Decimal(str(outstanding_amount)) <= 0:
        # Calculate from real overdue invoices
        unpaid = Invoice.objects.for_organization(organization).filter(
            service_account__customer=customer,
            status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID],
        )
        calculated = sum((inv.total_amount - inv.paid_amount for inv in unpaid), Decimal("0.00"))
        if calculated <= 0:
            raise ValidationError({"outstanding_amount": "Customer has no outstanding overdue balance to allocate."})
        outstanding_amount = calculated
    else:
        outstanding_amount = Decimal(str(outstanding_amount))

    allocation_number = generate_allocation_number(organization)

    allocation = RecoveryAllocation.objects.create(
        organization=organization,
        allocation_number=allocation_number,
        customer=customer,
        service_account=service_account,
        invoice=invoice,
        outstanding_amount=outstanding_amount,
        assigned_staff=assigned_staff,
        assigned_by=actor,
        assigned_date=timezone.now().date(),
        due_date=due_date,
        priority=priority,
        status=RecoveryAllocation.Status.ALLOCATED,
        notes=notes.strip() if notes else "",
    )

    AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action="RECOVERY_ALLOCATION_CREATED",
        resource_type="RecoveryAllocation",
        resource_id=str(allocation.id),
        metadata={
            "allocation_number": allocation.allocation_number,
            "customer_id": str(customer.id),
            "customer_name": customer.full_name,
            "assigned_staff_id": str(assigned_staff.id),
            "assigned_staff_email": assigned_staff.email,
            "outstanding_amount": str(allocation.outstanding_amount),
            "priority": allocation.priority,
        },
    )

    return allocation


@transaction.atomic
def reassign_recovery_allocation(
    *,
    organization,
    actor,
    allocation,
    new_assigned_staff,
    reassignment_reason,
    due_date=None,
    priority=None,
    notes=None,
):
    """
    Reassign an active recovery allocation to a new operator.
    Preserves full audit history by cancelling old allocation and linking reassigned_from.
    """
    if allocation.organization_id != organization.id:
        raise ValidationError({"detail": "Allocation does not belong to organization."})

    if allocation.status in [RecoveryAllocation.Status.COMPLETED, RecoveryAllocation.Status.CANCELLED]:
        raise ValidationError({"detail": f"Cannot reassign a {allocation.status.lower()} allocation."})

    if not OrganizationMembership.objects.filter(
        organization=organization,
        user=new_assigned_staff,
        is_active=True,
    ).exists():
        raise ValidationError({"new_assigned_staff": "New assigned staff does not belong to organization."})

    if not reassignment_reason or not reassignment_reason.strip():
        raise ValidationError({"reassignment_reason": "Reassignment reason is required."})

    old_staff = allocation.assigned_staff

    # Mark old allocation as CANCELLED with reassignment reason
    allocation.status = RecoveryAllocation.Status.CANCELLED
    allocation.reassignment_reason = reassignment_reason.strip()
    allocation.save(update_fields=["status", "reassignment_reason", "updated_at"])

    # Create new allocation chained to old
    new_allocation_number = generate_allocation_number(organization)
    new_allocation = RecoveryAllocation.objects.create(
        organization=organization,
        allocation_number=new_allocation_number,
        customer=allocation.customer,
        service_account=allocation.service_account,
        invoice=allocation.invoice,
        outstanding_amount=allocation.outstanding_amount,
        assigned_staff=new_assigned_staff,
        assigned_by=actor,
        assigned_date=timezone.now().date(),
        due_date=due_date or allocation.due_date,
        priority=priority or allocation.priority,
        status=RecoveryAllocation.Status.ALLOCATED,
        notes=notes.strip() if notes is not None else allocation.notes,
        reassigned_from=allocation,
        reassignment_reason=reassignment_reason.strip(),
        linked_promise=allocation.linked_promise,
    )

    AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action="RECOVERY_ALLOCATION_REASSIGNED",
        resource_type="RecoveryAllocation",
        resource_id=str(new_allocation.id),
        metadata={
            "old_allocation_id": str(allocation.id),
            "old_allocation_number": allocation.allocation_number,
            "new_allocation_number": new_allocation.allocation_number,
            "old_assigned_staff_id": str(old_staff.id),
            "new_assigned_staff_id": str(new_assigned_staff.id),
            "reason": reassignment_reason.strip(),
        },
    )

    return new_allocation


@transaction.atomic
def transition_recovery_status(
    *,
    organization,
    actor,
    allocation,
    new_status,
    notes=None,
    linked_promise=None,
):
    """
    Transition recovery allocation status.
    Guarantees no fake payments and prevents mutation of terminal states.
    """
    if allocation.organization_id != organization.id:
        raise ValidationError({"detail": "Allocation does not belong to organization."})

    if allocation.status in [RecoveryAllocation.Status.COMPLETED, RecoveryAllocation.Status.CANCELLED]:
        raise ValidationError(
            {"detail": f"Allocation is {allocation.status} and cannot be modified."}
        )

    if new_status not in RecoveryAllocation.Status.values:
        raise ValidationError(
            {"new_status": f"Invalid status. Must be one of: {', '.join(RecoveryAllocation.Status.values)}"}
        )

    # Valid transitions map
    allowed_transitions = {
        RecoveryAllocation.Status.ALLOCATED: [
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.NO_RESPONSE,
            RecoveryAllocation.Status.FAILED,
            RecoveryAllocation.Status.CANCELLED,
        ],
        RecoveryAllocation.Status.IN_PROGRESS: [
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.PROMISE_RECEIVED,
            RecoveryAllocation.Status.PAYMENT_COLLECTED,
            RecoveryAllocation.Status.NO_RESPONSE,
            RecoveryAllocation.Status.FAILED,
            RecoveryAllocation.Status.ESCALATED,
            RecoveryAllocation.Status.CANCELLED,
        ],
        RecoveryAllocation.Status.CONTACTED: [
            RecoveryAllocation.Status.PROMISE_RECEIVED,
            RecoveryAllocation.Status.PAYMENT_COLLECTED,
            RecoveryAllocation.Status.COMPLETED,
            RecoveryAllocation.Status.NO_RESPONSE,
            RecoveryAllocation.Status.FAILED,
            RecoveryAllocation.Status.ESCALATED,
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CANCELLED,
        ],
        RecoveryAllocation.Status.PROMISE_RECEIVED: [
            RecoveryAllocation.Status.PAYMENT_COLLECTED,
            RecoveryAllocation.Status.COMPLETED,
            RecoveryAllocation.Status.FAILED,
            RecoveryAllocation.Status.ESCALATED,
            RecoveryAllocation.Status.CANCELLED,
        ],
        RecoveryAllocation.Status.PAYMENT_COLLECTED: [
            RecoveryAllocation.Status.COMPLETED,
            RecoveryAllocation.Status.CANCELLED,
        ],
        RecoveryAllocation.Status.NO_RESPONSE: [
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.FAILED,
            RecoveryAllocation.Status.ESCALATED,
            RecoveryAllocation.Status.CANCELLED,
        ],
        RecoveryAllocation.Status.FAILED: [
            RecoveryAllocation.Status.ESCALATED,
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CANCELLED,
        ],
        RecoveryAllocation.Status.ESCALATED: [
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.CANCELLED,
            RecoveryAllocation.Status.COMPLETED,
        ],
    }

    if new_status not in allowed_transitions.get(allocation.status, []):
        raise ValidationError(
            {
                "new_status": f"Cannot transition allocation from {allocation.status} to {new_status}."
            }
        )

    # Business rule validations
    if new_status == RecoveryAllocation.Status.PROMISE_RECEIVED:
        if linked_promise:
            if linked_promise.organization_id != organization.id:
                raise ValidationError({"linked_promise": "Promise does not belong to organization."})
            allocation.linked_promise = linked_promise
        else:
            # Check if customer has an active promise in Batch 5
            active_p = PromiseToPay.objects.for_organization(organization).filter(
                customer=allocation.customer,
                status__in=[PromiseToPay.Status.PENDING, PromiseToPay.Status.ACTIVE],
            ).first()
            if active_p:
                allocation.linked_promise = active_p

    if new_status in [RecoveryAllocation.Status.PAYMENT_COLLECTED, RecoveryAllocation.Status.COMPLETED]:
        # Verify genuine payment exists since allocation date or outstanding balance is 0
        payments_exist = PaymentAllocation.objects.for_organization(organization).filter(
            invoice__service_account__customer=allocation.customer,
            created_at__date__gte=allocation.assigned_date,
        ).exists()

        if not payments_exist:
            # Also check if invoices are marked paid
            unpaid_count = Invoice.objects.for_organization(organization).filter(
                service_account__customer=allocation.customer,
                status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID],
            ).count()
            if unpaid_count > 0:
                raise ValidationError(
                    {
                        "non_field_errors": (
                            "Cannot mark as payment collected or completed without recorded payment receipts. "
                            "Please record the payment in Billing first."
                        )
                    }
                )

        allocation.completed_date = timezone.now()

    allocation.status = new_status
    if notes is not None:
        allocation.notes = notes.strip()

    allocation.save(
        update_fields=[
            "status",
            "notes",
            "linked_promise",
            "completed_date",
            "updated_at",
        ]
    )

    AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action="RECOVERY_STATUS_TRANSITIONED",
        resource_type="RecoveryAllocation",
        resource_id=str(allocation.id),
        metadata={
            "allocation_number": allocation.allocation_number,
            "new_status": new_status,
            "notes": allocation.notes,
        },
    )

    return allocation


def get_recovery_dashboard_metrics(organization, user=None, is_manager=False):
    """
    Get operational metrics for Recovery Dashboard.
    If is_manager is False and user is provided, filters for that specific operator.
    """
    today = timezone.now().date()
    allocations = RecoveryAllocation.objects.for_organization(organization)

    if not is_manager and user:
        allocations = allocations.filter(assigned_staff=user)

    total_assigned = allocations.count()
    active_count = allocations.filter(
        status__in=[
            RecoveryAllocation.Status.ALLOCATED,
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.PROMISE_RECEIVED,
        ]
    ).count()

    today_followups = allocations.filter(
        due_date=today,
        status__in=[
            RecoveryAllocation.Status.ALLOCATED,
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.PROMISE_RECEIVED,
        ],
    ).count()

    promises_count = allocations.filter(status=RecoveryAllocation.Status.PROMISE_RECEIVED).count()
    completed_count = allocations.filter(status=RecoveryAllocation.Status.COMPLETED).count()

    active_allocs = allocations.filter(
        status__in=[
            RecoveryAllocation.Status.ALLOCATED,
            RecoveryAllocation.Status.IN_PROGRESS,
            RecoveryAllocation.Status.CONTACTED,
            RecoveryAllocation.Status.PROMISE_RECEIVED,
        ]
    )
    total_outstanding = active_allocs.aggregate(total=Sum("outstanding_amount"))["total"] or Decimal("0.00")

    # Overdue Defaulters count across organization
    unpaid_customers_count = (
        Invoice.objects.for_organization(organization)
        .filter(
            status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID],
            due_date__lt=today,
        )
        .values("service_account__customer")
        .distinct()
        .count()
    )

    return {
        "total_assigned": total_assigned,
        "active_count": active_count,
        "today_followups": today_followups,
        "promises_count": promises_count,
        "completed_count": completed_count,
        "total_outstanding_assigned": total_outstanding,
        "total_defaulters_in_system": unpaid_customers_count,
    }
