"""What the ISP owes a dealer for a month: one place for every screen and report.

Three ways to pay a dealer (Dealer.commission_type):
- PERCENTAGE: a share of what was collected from their customers.
- FLAT_PER_USER: a fixed rate for each active customer.
- MONTHLY_SLAB: a fixed monthly amount picked from the dealer's own slab table
  by how many active users they have, sub dealers' users included.

A sub dealer is paid by their parent dealer, never by the ISP, so their
payout here is always zero.
"""
from decimal import Decimal

from customers.models import Dealer, DealerPayoutSlab, ServiceAccount

ZERO = Decimal("0.00")


def network_active_users(dealer: Dealer) -> int:
    """Active connections of the dealer and of all their sub dealers."""
    return (
        ServiceAccount.objects.for_organization(dealer.organization_id)
        .filter(status=ServiceAccount.Status.ACTIVE)
        .filter(customer__dealer__in=[dealer.id, *dealer.sub_dealers.values_list("id", flat=True)])
        .count()
    )


def slab_rows(dealer: Dealer) -> list[dict]:
    return [
        {"min_active_users": slab.min_active_users, "monthly_amount": str(slab.monthly_amount)}
        for slab in DealerPayoutSlab.objects.for_organization(dealer.organization_id).filter(dealer=dealer)
    ]


def pick_slab(slabs: list[dict], active_users: int) -> tuple[dict | None, dict | None]:
    """The slab reached (highest min the users meet) and the next one to aim for."""
    reached, upcoming = None, None
    for slab in sorted(slabs, key=lambda row: row["min_active_users"]):
        if active_users >= slab["min_active_users"]:
            reached = slab
        elif upcoming is None:
            upcoming = slab
    return reached, upcoming


def dealer_payout(dealer: Dealer, *, collected: Decimal, own_active: int) -> dict:
    """amount plus what it was based on, so screens can explain the number."""
    if dealer.parent_dealer_id:
        return {"amount": ZERO, "basis": "PAID_BY_PARENT", "active_users": own_active, "slab": None, "next_slab": None}

    rate = dealer.commission_rate_percentage or ZERO
    if dealer.commission_type == Dealer.CommissionType.PERCENTAGE:
        amount = (collected * rate / Decimal("100")).quantize(Decimal("0.01"))
        return {"amount": amount, "basis": dealer.commission_type, "active_users": own_active, "slab": None, "next_slab": None}
    if dealer.commission_type == Dealer.CommissionType.FLAT_PER_USER:
        amount = (Decimal(own_active) * rate).quantize(Decimal("0.01"))
        return {"amount": amount, "basis": dealer.commission_type, "active_users": own_active, "slab": None, "next_slab": None}

    active_users = network_active_users(dealer)
    reached, upcoming = pick_slab(slab_rows(dealer), active_users)
    amount = Decimal(reached["monthly_amount"]) if reached else ZERO
    return {
        "amount": amount,
        "basis": dealer.commission_type,
        "active_users": active_users,
        "slab": reached,
        "next_slab": upcoming,
    }


def payout_json(payout: dict) -> dict:
    return {**payout, "amount": str(payout["amount"])}


def replace_payout_slabs(dealer: Dealer, slabs: list[dict]) -> None:
    DealerPayoutSlab.objects.filter(dealer=dealer).delete()
    DealerPayoutSlab.objects.bulk_create(
        DealerPayoutSlab(
            organization_id=dealer.organization_id,
            dealer=dealer,
            min_active_users=slab["min_active_users"],
            monthly_amount=slab["monthly_amount"],
        )
        for slab in slabs
    )
