import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounting.models import Account, JournalEntry
from billing.models import Invoice, InvoiceLine, Payment, PaymentAllocation, PromiseToPay
from billing.services import generate_service_invoice, record_invoice_payment
from billing.tasks import (
    generate_monthly_invoices_task,
    scan_overdue_invoices_task,
    scan_ptp_breaches_task,
)
from communications.models import (
    CommunicationLog,
    CommunicationProvider,
    CommunicationQueue,
    CommunicationTemplate,
)
from communications.tasks import (
    dispatch_communication_queue_task,
    recover_stale_processing_task,
)
from customers.models import BillingProfile, Customer, InternetPackage, ServiceAccount
from tenancy.cache_utils import (
    get_or_set_tenant_cached,
    get_tenant_cached,
    invalidate_tenant_cached,
    make_tenant_cache_key,
    set_tenant_cached,
)
from tenancy.models import Organization, OrganizationMembership, StaffProfile

User = get_user_model()


class Batch15ComprehensiveSecurityAndPerformanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create Tenant A
        self.org_a = Organization.objects.create(
            name="Alpha Telecom",
            code="ALPHA",
            is_active=True,
        )
        self.user_a = User.objects.create_user(
            username="alpha_admin",
            email="admin@alpha.local",
            password="StrongPassword123!",
            first_name="Alpha",
            last_name="Admin",
            is_active=True,
        )
        self.membership_a = OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )
        self.profile_a = StaffProfile.objects.create(
            organization=self.org_a,
            membership=self.membership_a,
            user=self.user_a,
            role=StaffProfile.Role.OWNER,
            staff_code="ALPHA-001",
        )

        # Create Tenant B
        self.org_b = Organization.objects.create(
            name="Beta Networks",
            code="BETA",
            is_active=True,
        )
        self.user_b = User.objects.create_user(
            username="beta_admin",
            email="admin@beta.local",
            password="StrongPassword123!",
            first_name="Beta",
            last_name="Admin",
            is_active=True,
        )
        self.membership_b = OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        # Create Customer & Package for Tenant A
        self.package_a = InternetPackage.objects.create(
            organization=self.org_a,
            name="Alpha Fiber 50M",
            code="AF50",
            download_speed_mbps=50,
            upload_speed_mbps=50,
            monthly_price=Decimal("3500.00"),
            is_active=True,
        )
        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            customer_number="CUST-A-001",
            first_name="John",
            last_name="Doe",
            phone="+923001112233",
            email="john@alpha.local",
            city="Lahore",
            area="Gulberg",
            is_active=True,
        )
        self.service_a = ServiceAccount.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            service_number="SRV-A-001",
            internet_package=self.package_a,
            status=ServiceAccount.Status.ACTIVE,
        )
        self.billing_profile_a = BillingProfile.objects.create(
            organization=self.org_a,
            service_account=self.service_a,
            billing_day=1,
            due_day=10,
            is_active=True,
        )

    def _get_token_pair(self, user, membership, role="OWNER"):
        refresh = RefreshToken.for_user(user)
        refresh["organization_id"] = str(membership.organization_id)
        refresh["organization_code"] = membership.organization.code
        refresh["role"] = role
        return str(refresh.access_token), str(refresh)

    # --------------------------------------------------------------------------
    # 1. JWT REFRESH ACTIVE-MEMBERSHIP REVALIDATION & ROLE UPDATES
    # --------------------------------------------------------------------------
    def test_jwt_refresh_active_membership_succeeds(self):
        _, refresh_str = self._get_token_pair(self.user_a, self.membership_a)

        res = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_str})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["role"], "OWNER")
        self.assertEqual(res.data["organization"]["code"], "ALPHA")

    def test_jwt_refresh_inactive_membership_rejected(self):
        _, refresh_str = self._get_token_pair(self.user_a, self.membership_a)

        # Deactivate membership in database
        self.membership_a.is_active = False
        self.membership_a.save(update_fields=["is_active"])

        res = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_str})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    def test_jwt_refresh_inactive_organization_rejected(self):
        _, refresh_str = self._get_token_pair(self.user_a, self.membership_a)

        # Deactivate organization
        self.org_a.is_active = False
        self.org_a.save(update_fields=["is_active"])

        res = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_str})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_jwt_refresh_dynamic_role_recalculation(self):
        # User starts as STAFF in DB
        staff_user = User.objects.create_user(
            username="staff_alpha",
            email="staff@alpha.local",
            password="Password123!",
            is_active=True,
        )
        membership = OrganizationMembership.objects.create(
            organization=self.org_a,
            user=staff_user,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )
        profile = StaffProfile.objects.create(
            organization=self.org_a,
            membership=membership,
            user=staff_user,
            role=StaffProfile.Role.STAFF,
            staff_code="ALPHA-STAFF-1",
        )

        _, refresh_str = self._get_token_pair(staff_user, membership, role="STAFF")

        # Promote staff profile to ACCOUNTANT in database
        profile.role = StaffProfile.Role.ACCOUNTANT
        profile.save(update_fields=["role"])

        res = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_str})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Token refresh must reflect dynamic DB role promotion
        self.assertEqual(res.data["role"], StaffProfile.Role.ACCOUNTANT)

    # --------------------------------------------------------------------------
    # 2. JWT LOGOUT / REVOCATION & BLACKLISTING
    # --------------------------------------------------------------------------
    def test_jwt_logout_and_revocation(self):
        access_token, refresh_str = self._get_token_pair(self.user_a, self.membership_a)

        # Logout with refresh token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_res = self.client.post("/api/v1/auth/logout/", {"refresh": refresh_str})
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)
        self.assertEqual(logout_res.data["detail"], "Successfully logged out.")

        # Attempting to refresh with the blacklisted token must fail
        refresh_res = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_str})
        self.assertEqual(refresh_res.status_code, status.HTTP_400_BAD_REQUEST)

    # --------------------------------------------------------------------------
    # 3. GLOBAL API PAGINATION
    # --------------------------------------------------------------------------
    def test_pagination_standard_response(self):
        access_token, _ = self._get_token_pair(self.user_a, self.membership_a)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Create multiple invoices
        for i in range(5):
            Invoice.objects.create(
                organization=self.org_a,
                service_account=self.service_a,
                billing_profile=self.billing_profile_a,
                invoice_number=f"INV-TEST-{i:03d}",
                billing_period_start=date(2026, 1 + i, 1),
                billing_period_end=date(2026, 1 + i, 28),
                issue_date=date(2026, 1 + i, 1),
                due_date=date(2026, 1 + i, 10),
                status=Invoice.Status.UNPAID,
            )

        res = self.client.get("/api/v1/billing/invoices/?page_size=2")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("count", res.data)
        self.assertIn("results", res.data)
        self.assertIn("next", res.data)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertEqual(res.data["count"], 5)

    # --------------------------------------------------------------------------
    # 4. INVOICE N+1 QUERY OPTIMIZATION & MATHEMATICAL PARITY
    # --------------------------------------------------------------------------
    def test_invoice_n_plus_one_query_optimization(self):
        access_token, _ = self._get_token_pair(self.user_a, self.membership_a)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Create 10 invoices each with 2 lines and 1 allocation
        for i in range(10):
            svc = ServiceAccount.objects.create(
                organization=self.org_a,
                customer=self.customer_a,
                service_number=f"SRV-PERF-{i:03d}",
                internet_package=self.package_a,
                status=ServiceAccount.Status.ACTIVE,
            )
            bp = BillingProfile.objects.create(
                organization=self.org_a,
                service_account=svc,
                billing_day=1,
                due_day=10,
                is_active=True,
            )
            inv = Invoice.objects.create(
                organization=self.org_a,
                service_account=svc,
                billing_profile=bp,
                invoice_number=f"INV-PERF-{i:03d}",
                billing_period_start=date(2026, 2, 1),
                billing_period_end=date(2026, 2, 28),
                issue_date=date(2026, 2, 1),
                due_date=date(2026, 2, 10),
                status=Invoice.Status.PARTIALLY_PAID,
            )
            InvoiceLine.objects.create(
                organization=self.org_a,
                invoice=inv,
                description="Line 1",
                quantity=1,
                unit_price=Decimal("2000.00"),
                amount=Decimal("2000.00"),
            )
            InvoiceLine.objects.create(
                organization=self.org_a,
                invoice=inv,
                description="Line 2",
                quantity=1,
                unit_price=Decimal("1500.00"),
                amount=Decimal("1500.00"),
            )
            pmt = Payment.objects.create(
                organization=self.org_a,
                service_account=svc,
                payment_number=f"PMT-PERF-{i:03d}",
                amount=Decimal("1000.00"),
                payment_method=Payment.Method.CASH,
                paid_at=timezone.now(),
            )
            PaymentAllocation.objects.create(
                organization=self.org_a,
                invoice=inv,
                payment=pmt,
                amount=Decimal("1000.00"),
            )

        # The query count must be fixed regardless of 10 items (O(1) constant queries)
        with self.assertNumQueries(4):  # auth user, auth membership, count, annotated query
            res = self.client.get("/api/v1/billing/invoices/?page_size=10")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data["results"]), 10)
            # Verify mathematical totals are exactly 3500.00 total, 1000.00 paid, 2500.00 outstanding
            first_inv = res.data["results"][0]
            self.assertEqual(Decimal(str(first_inv["total_amount"])), Decimal("3500.00"))
            self.assertEqual(Decimal(str(first_inv["paid_amount"])), Decimal("1000.00"))
            self.assertEqual(Decimal(str(first_inv["outstanding_amount"])), Decimal("2500.00"))

    # --------------------------------------------------------------------------
    # 5. BACKGROUND TASK IDEMPOTENCY & TENANT ISOLATION
    # --------------------------------------------------------------------------
    def test_monthly_billing_task_idempotency_and_tenant_isolation(self):
        # Run 1: Generates invoice for Tenant A
        res1 = generate_monthly_invoices_task(
            organization_id=str(self.org_a.id),
            billing_year=2026,
            billing_month=5,
        )
        self.assertEqual(res1["generated_invoices"], 1)
        self.assertEqual(res1["skipped_existing_invoices"], 0)

        # Run 2: Executing same month again must be strictly idempotent (0 generated, 1 skipped)
        res2 = generate_monthly_invoices_task(
            organization_id=str(self.org_a.id),
            billing_year=2026,
            billing_month=5,
        )
        self.assertEqual(res2["generated_invoices"], 0)
        self.assertEqual(res2["skipped_existing_invoices"], 1)

        # Tenant B must have 0 invoices created by Tenant A's task
        invoices_b = Invoice.objects.filter(organization=self.org_b).count()
        self.assertEqual(invoices_b, 0)

    def test_ptp_breach_scanner_task(self):
        # Create an expired Promise to Pay
        res_inv = generate_service_invoice(
            organization=self.org_a,
            actor=self.user_a,
            service_account_id=self.service_a.id,
            billing_period_start=date(2026, 6, 1),
            billing_period_end=date(2026, 6, 30),
            issue_date=date(2026, 6, 1),
            due_date=date(2026, 6, 10),
        )
        inv = res_inv.invoice
        expired_ptp = PromiseToPay.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            service_account=self.service_a,
            invoice=inv,
            promise_number="PTP-EXP-001",
            promised_amount=Decimal("3500.00"),
            outstanding_amount=Decimal("3500.00"),
            promise_date=date.today() - timedelta(days=5),
            deadline=date.today() - timedelta(days=2),
            status=PromiseToPay.Status.PENDING,
        )

        res = scan_ptp_breaches_task(organization_id=str(self.org_a.id))
        self.assertEqual(res["broken_count"], 1)

        expired_ptp.refresh_from_db()
        self.assertEqual(expired_ptp.status, PromiseToPay.Status.BROKEN)

        # Running scan a second time must be idempotent
        res_idempotent = scan_ptp_breaches_task(organization_id=str(self.org_a.id))
        self.assertEqual(res_idempotent["broken_count"], 0)

    # --------------------------------------------------------------------------
    # 6. COMMUNICATION QUEUE & STALE PROCESSING RECOVERY
    # --------------------------------------------------------------------------
    def test_communication_stale_recovery(self):
        provider = CommunicationProvider.objects.create(
            organization=self.org_a,
            name="Alpha SMS",
            provider_type=CommunicationProvider.ProviderType.SMS,
            status=CommunicationProvider.Status.ACTIVE,
        )
        template = CommunicationTemplate.objects.create(
            organization=self.org_a,
            name="Reminder",
            body="Hello {{name}}",
            communication_provider=provider,
        )
        stale_item = CommunicationQueue.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            provider=provider,
            template=template,
            recipient="+923001112233",
            rendered_body="Hello John",
            status=CommunicationQueue.Status.PROCESSING,
            scheduled_at=timezone.now() - timedelta(minutes=30),
            processing_started_at=timezone.now() - timedelta(minutes=25),
        )

        recover_stale_processing_task(timeout_minutes=10)

        stale_item.refresh_from_db()
        self.assertEqual(stale_item.status, CommunicationQueue.Status.PENDING)

    # --------------------------------------------------------------------------
    # 7. TENANT-SAFE CACHING ISOLATION
    # --------------------------------------------------------------------------
    def test_tenant_cache_isolation(self):
        set_tenant_cached(self.org_a.id, "kpi_summary", {"active_subs": 150}, timeout=60)
        set_tenant_cached(self.org_b.id, "kpi_summary", {"active_subs": 42}, timeout=60)

        cached_a = get_tenant_cached(self.org_a.id, "kpi_summary")
        cached_b = get_tenant_cached(self.org_b.id, "kpi_summary")

        self.assertEqual(cached_a["active_subs"], 150)
        self.assertEqual(cached_b["active_subs"], 42)

        # Invalidate Org A cache
        invalidate_tenant_cached(self.org_a.id, "kpi_summary")
        self.assertIsNone(get_tenant_cached(self.org_a.id, "kpi_summary"))
        # Org B cache must remain unaffected
        self.assertIsNotNone(get_tenant_cached(self.org_b.id, "kpi_summary"))

    # --------------------------------------------------------------------------
    # 8. REQUEST ID OBSERVED IN RESPONSE HEADERS
    # --------------------------------------------------------------------------
    def test_request_id_middleware_header(self):
        res = self.client.get("/api/v1/auth/login/")
        self.assertIn("X-Request-ID", res.headers)
        self.assertTrue(len(res.headers["X-Request-ID"]) > 0)
