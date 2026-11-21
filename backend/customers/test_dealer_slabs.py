from decimal import Decimal

from django.test import TestCase

from customers import test_dealer_portal as portal_tests
from customers.dealer_payout import dealer_payout, pick_slab
from customers.models import Dealer, DealerPayoutSlab, ServiceAccount

SLABS = [
    {"min_active_users": 200, "monthly_amount": "20000"},
    {"min_active_users": 500, "monthly_amount": "45000"},
    {"min_active_users": 1000, "monthly_amount": "80000"},
]


class PickSlabTests(TestCase):
    def test_highest_slab_reached_and_next_one(self):
        rows = [{"min_active_users": s["min_active_users"], "monthly_amount": s["monthly_amount"]} for s in SLABS]
        self.assertEqual(pick_slab(rows, 150), (None, rows[0]))
        self.assertEqual(pick_slab(rows, 200), (rows[0], rows[1]))
        self.assertEqual(pick_slab(rows, 999), (rows[1], rows[2]))
        self.assertEqual(pick_slab(rows, 5000), (rows[2], None))


class DealerSlabAndSubDealerTests(TestCase):
    # ALPHA ISP: dealer DL-1 (Ahmed, Sana) and DL-2 (Imran), as in the portal tests.
    setUp = portal_tests.DealerPortalTests.setUp

    def edit(self, dealer, **body):
        if not getattr(self, "_signed_in", False):
            login = self.client.post("/api/v1/auth/login/", {
                "organization_code": "ALPHA", "email": self.owner.email, "password": "OwnerPass!2345",
            }, format="json")
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
            self._signed_in = True
        return self.client.put(f"/api/v1/customers/dealers/{dealer.id}/", body, format="json")

    def small_slabs(self):
        # Small numbers so the three test customers can reach them.
        return [
            {"min_active_users": 2, "monthly_amount": "5000"},
            {"min_active_users": 3, "monthly_amount": "9000"},
        ]

    def test_owner_sets_monthly_slabs_and_payout_follows_active_users(self):
        ServiceAccount.objects.update(status=ServiceAccount.Status.ACTIVE)
        response = self.edit(self.dealer, commission_type="MONTHLY_SLAB", payout_slabs=self.small_slabs())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [(s["min_active_users"], s["monthly_amount"]) for s in response.data["payout_slabs"]],
            [(2, "5000.00"), (3, "9000.00")],
        )
        self.dealer.refresh_from_db()
        payout = dealer_payout(self.dealer, collected=Decimal("0"), own_active=2)
        self.assertEqual(payout["amount"], Decimal("5000.00"))
        self.assertEqual(payout["active_users"], 2)
        self.assertEqual(payout["next_slab"]["min_active_users"], 3)

        # Suspended users are not counted.
        self.sana.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        self.sana.save(update_fields=["status"])
        self.assertEqual(dealer_payout(self.dealer, collected=Decimal("0"), own_active=1)["amount"], Decimal("0.00"))

    def test_sub_dealer_users_count_for_parent_and_sub_dealer_gets_nothing_from_isp(self):
        ServiceAccount.objects.update(status=ServiceAccount.Status.ACTIVE)
        self.edit(self.dealer, commission_type="MONTHLY_SLAB", payout_slabs=self.small_slabs())
        response = self.edit(self.other_dealer, parent_dealer=str(self.dealer.id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["parent_dealer_code"], "DL-1")

        self.dealer.refresh_from_db()
        self.other_dealer.refresh_from_db()
        # 2 own + 1 from the sub dealer = 3 -> the 9000 slab.
        self.assertEqual(dealer_payout(self.dealer, collected=Decimal("0"), own_active=2)["amount"], Decimal("9000.00"))
        sub = dealer_payout(self.other_dealer, collected=Decimal("5000"), own_active=1)
        self.assertEqual(sub["amount"], Decimal("0.00"))
        self.assertEqual(sub["basis"], "PAID_BY_PARENT")

        detail = self.client.get(f"/api/v1/customers/dealers/{self.dealer.id}/360/").data
        self.assertEqual(detail["metrics"]["payout"]["amount"], "9000.00")
        self.assertEqual([row["dealer_code"] for row in detail["sub_dealers"]], ["DL-2"])
        self.assertEqual(detail["dealer"]["sub_dealers_count"], 1)

    def test_monthly_dealer_needs_slabs_and_slabs_must_differ(self):
        self.assertEqual(self.edit(self.dealer, commission_type="MONTHLY_SLAB").status_code, 400)
        same = [{"min_active_users": 200, "monthly_amount": "1"}, {"min_active_users": 200, "monthly_amount": "2"}]
        self.assertEqual(self.edit(self.dealer, commission_type="MONTHLY_SLAB", payout_slabs=same).status_code, 400)
        self.assertEqual(self.edit(self.dealer, commission_type="MONTHLY_SLAB", payout_slabs=SLABS).status_code, 200)
        # Sending a new table replaces the old one.
        self.edit(self.dealer, payout_slabs=SLABS[:1])
        self.assertEqual(DealerPayoutSlab.objects.filter(dealer=self.dealer).count(), 1)

    def test_sub_dealer_rules(self):
        self.assertEqual(self.edit(self.dealer, parent_dealer=str(self.dealer.id)).status_code, 400)
        self.assertEqual(self.edit(self.other_dealer, parent_dealer=str(self.dealer.id)).status_code, 200)
        # One level only: DL-1 has a sub dealer, so it cannot become one; and DL-2 cannot be a parent.
        third = Dealer.objects.create(
            organization=self.org, dealer_code="DL-3", name="Zahid", phone="03000000003",
            joining_date=self.dealer.joining_date,
        )
        self.assertEqual(self.edit(self.dealer, parent_dealer=str(third.id)).status_code, 400)
        self.assertEqual(self.edit(third, parent_dealer=str(self.other_dealer.id)).status_code, 400)
        # Removing the parent makes them a normal dealer again.
        response = self.edit(self.other_dealer, parent_dealer=None)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["parent_dealer"])

    def test_owner_edits_dealer_details(self):
        response = self.edit(self.dealer, name="Bilal Traders", phone="03009999999", email="bilal@new.test")
        self.assertEqual(response.status_code, 200, response.data)
        self.dealer.refresh_from_db()
        self.assertEqual((self.dealer.name, self.dealer.phone, self.dealer.email),
                         ("Bilal Traders", "03009999999", "bilal@new.test"))

    def test_dealer_360_shows_outstanding_and_skips_reversed_payments(self):
        from billing.services import record_payment_with_allocations, reverse_payment

        self.edit(self.dealer, name="Bilal")  # signs the owner in
        before = self.client.get(f"/api/v1/customers/dealers/{self.dealer.id}/360/").data["metrics"]
        # Ahmed was imported with 2800 owed.
        self.assertEqual(Decimal(before["total_outstanding"]), Decimal("2800.00"))

        payment = record_payment_with_allocations(
            organization=self.org, actor=self.owner, service_account_id=self.ahmed.id,
            amount=Decimal("500"), payment_method="CASH", reference="", notes="",
        )
        reverse_payment(organization=self.org, actor=self.owner, payment_id=payment.id, reversal_reason="Test")
        after = self.client.get(f"/api/v1/customers/dealers/{self.dealer.id}/360/").data["metrics"]
        self.assertEqual(Decimal(after["total_collected"]), Decimal(before["total_collected"]))
