import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounting.models import (
    Account,
    DealerSettlement,
    FinancialPeriod,
    JournalEntry,
    JournalLine,
)
from accounting.services import (
    create_journal_entry,
    get_or_create_default_chart_of_accounts,
)
from billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
    PromiseToPay,
    RecoveryAllocation,
)
from customers.models import (
    Area,
    BillingProfile,
    City,
    Customer,
    Dealer,
    Inquiry,
    InternetPackage,
    ServiceAccount,
)
from inventory.models import DeviceAssignment, InventoryDevice
from support.models import Complaint
from tenancy.models import Organization, OrganizationMembership

User = get_user_model()


class Batch11ReportingEngineTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Organizations (Main Tenant & Other Tenant)
        self.org = Organization.objects.create(
            name="Nexora Fiber Lahore",
            code="NX-LHR-RPT",
            currency="PKR",
            is_active=True,
        )

        self.other_org = Organization.objects.create(
            name="Alpha Telecom Karachi",
            code="NX-KHI-RPT",
            currency="PKR",
            is_active=True,
        )

        # 2. Users & Memberships
        self.owner = User.objects.create_user(
            username="owner_rpt",
            email="owner@nexora.test",
            password="Password123!",
            first_name="Owner",
            last_name="Admin",
        )
        self.owner_membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        self.staff_user = User.objects.create_user(
            username="staff_rpt",
            email="staff@nexora.test",
            password="Password123!",
            first_name="Staff",
            last_name="Accountant",
        )
        self.staff_membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.staff_user,
            role=OrganizationMembership.Role.STAFF,
            is_active=True,
        )

        self.other_user = User.objects.create_user(
            username="other_rpt",
            email="other@nexora.test",
            password="Password123!",
            first_name="Other",
            last_name="User",
        )
        self.other_membership = OrganizationMembership.objects.create(
            organization=self.other_org,
            user=self.other_user,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        )

        # 3. JWT Auth Headers
        token_owner = RefreshToken.for_user(self.owner)
        token_owner["organization_id"] = str(self.org.id)
        self.owner_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {str(token_owner.access_token)}",
        }

        token_staff = RefreshToken.for_user(self.staff_user)
        token_staff["organization_id"] = str(self.org.id)
        self.staff_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {str(token_staff.access_token)}",
        }

        token_other = RefreshToken.for_user(self.other_user)
        token_other["organization_id"] = str(self.other_org.id)
        self.other_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {str(token_other.access_token)}",
        }

        # 4. Base Domain Seed
        self.city = City.objects.create(
            organization=self.org,
            name="Lahore",
            code="LHR",
        )
        self.area = Area.objects.create(
            organization=self.org,
            city=self.city,
            name="Gulberg III",
        )
        self.pkg = InternetPackage.objects.create(
            organization=self.org,
            name="Super Fiber 50",
            code="SF-50",
            download_speed_mbps=50,
            upload_speed_mbps=50,
            monthly_price=Decimal("4000.00"),
            is_active=True,
        )
        self.dealer = Dealer.objects.create(
            organization=self.org,
            dealer_code="DLR-101",
            name="Gulberg Net Partner",
            commission_rate_percentage=Decimal("10.00"),
            commission_type=Dealer.CommissionType.PERCENTAGE,
            joining_date=date(2026, 1, 1),
            status=Dealer.Status.ACTIVE,
            phone="03001234567",
        )
        self.customer = Customer.objects.create(
            organization=self.org,
            customer_number="NX-CUST-501",
            first_name="Ahmed",
            last_name="Raza",
            phone="03001112233",
            area="Gulberg III",
            city="Lahore",
            dealer=self.dealer,
            is_active=True,
        )
        self.service = ServiceAccount.objects.create(
            organization=self.org,
            service_number="NX-SRV-501",
            customer=self.customer,
            internet_package=self.pkg,
            status=ServiceAccount.Status.ACTIVE,
        )
        self.billing_profile = BillingProfile.objects.create(
            organization=self.org,
            service_account=self.service,
            billing_day=1,
            due_day=10,
        )

    # -------------------------------------------------------------------------
    # 1. COLLECTIONS REGISTER & CASHIER SHIFT REPORT TESTS
    # -------------------------------------------------------------------------
    def test_customer_collections_report(self):
        # Create payments
        p1 = Payment.objects.create(
            organization=self.org,
            payment_number="NX-PAY-001",
            service_account=self.service,
            amount=Decimal("4000.00"),
            payment_method=Payment.Method.CASH,
            received_by=self.staff_user,
            paid_at=timezone.now(),
        )
        p2 = Payment.objects.create(
            organization=self.org,
            payment_number="NX-PAY-002",
            service_account=self.service,
            amount=Decimal("2000.00"),
            payment_method=Payment.Method.BANK_TRANSFER,
            received_by=self.staff_user,
            paid_at=timezone.now(),
        )
        # Reversed payment must be excluded
        Payment.objects.create(
            organization=self.org,
            payment_number="NX-PAY-REV",
            service_account=self.service,
            amount=Decimal("5000.00"),
            payment_method=Payment.Method.CASH,
            is_reversed=True,
            paid_at=timezone.now(),
        )

        url = "/api/v1/reports/collections/register/"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["total_collected"], "6000.00")
        self.assertEqual(resp.data["summary"]["payment_count"], 2)

    def test_cashier_shift_close_report(self):
        Payment.objects.create(
            organization=self.org,
            payment_number="NX-PAY-SHIFT-1",
            service_account=self.service,
            amount=Decimal("3500.00"),
            payment_method=Payment.Method.CASH,
            received_by=self.staff_user,
            paid_at=timezone.now(),
        )

        url = f"/api/v1/reports/collections/cashier-shift/?collector_id={self.staff_user.id}"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_intake"], "3500.00")
        self.assertEqual(resp.data["transaction_count"], 1)

    # -------------------------------------------------------------------------
    # 2. DEFAULTERS AGING REPORT TESTS
    # -------------------------------------------------------------------------
    def test_defaulters_aging_report(self):
        # Invoice 1: 15 days overdue -> 0-30 bucket
        inv1 = Invoice.objects.create(
            organization=self.org,
            invoice_number="NX-INV-001",
            service_account=self.service,
            billing_profile=self.billing_profile,
            billing_period_start=date(2026, 8, 1),
            billing_period_end=date(2026, 8, 31),
            issue_date=date(2026, 8, 1),
            due_date=date(2026, 8, 10),
            status=Invoice.Status.UNPAID,
        )
        InvoiceLine.objects.create(
            organization=self.org,
            invoice=inv1,
            description="August Internet",
            amount=Decimal("4000.00"),
        )

        url = "/api/v1/reports/collections/defaulters-aging/?as_of_date=2026-08-25"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["total_exposure"], "4000.00")
        self.assertEqual(resp.data["summary"]["aging_buckets"]["0-30"], "4000.00")

    # -------------------------------------------------------------------------
    # 3. SUBSCRIBER DIRECTORY & GROWTH CHURN TESTS
    # -------------------------------------------------------------------------
    def test_customer_master_report(self):
        url = "/api/v1/reports/customers/master/"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["total_subscribers"], 1)
        self.assertEqual(resp.data["records"][0]["customer_number"], "NX-CUST-501")

    def test_customer_growth_churn_report(self):
        url = "/api/v1/reports/customers/growth-churn/"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("intervals", resp.data)

    # -------------------------------------------------------------------------
    # 4. DEALER 360 PERFORMANCE REPORT TESTS
    # -------------------------------------------------------------------------
    def test_dealer_360_performance_report(self):
        inv = Invoice.objects.create(
            organization=self.org,
            invoice_number="NX-INV-DLR-1",
            service_account=self.service,
            billing_profile=self.billing_profile,
            billing_period_start=date(2026, 9, 1),
            billing_period_end=date(2026, 9, 30),
            issue_date=date(2026, 9, 1),
            due_date=date(2026, 9, 10),
            status=Invoice.Status.PAID,
        )
        InvoiceLine.objects.create(
            organization=self.org,
            invoice=inv,
            description="Fiber Monthly",
            amount=Decimal("10000.00"),
        )
        Payment.objects.create(
            organization=self.org,
            payment_number="NX-PAY-DLR-1",
            service_account=self.service,
            amount=Decimal("10000.00"),
            payment_method=Payment.Method.CASH,
            paid_at=timezone.now(),
        )

        url = "/api/v1/reports/dealers/performance-360/"
        resp = self.client.get(url, **self.owner_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        row = resp.data[0]
        self.assertEqual(row["dealer_code"], "DLR-101")
        self.assertEqual(row["invoiced_amount"], "10000.00")
        self.assertEqual(row["collected_amount"], "10000.00")
        # 10% commission on 10,000 = 1,000
        self.assertEqual(row["commission_accrued"], "1000.00")
        # Net ISP Margin = 10,000 - 1,000 = 9,000
        self.assertEqual(row["net_isp_margin"], "9000.00")

    # -------------------------------------------------------------------------
    # 5. FORMAL FINANCIAL STATEMENTS (BATCH 10 GL INTEGRATION)
    # -------------------------------------------------------------------------
    def test_profit_and_loss_statement(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = date(2026, 9, 15)

        # Revenue: 20,000
        create_journal_entry(
            organization=self.org,
            actor=self.staff_user,
            txn_date=today,
            narration="Subscriber Revenue",
            lines=[
                {"account": coa["1010"], "debit": Decimal("20000.00"), "credit": Decimal("0.00")},
                {"account": coa["4000"], "debit": Decimal("0.00"), "credit": Decimal("20000.00")},
            ],
        )

        # Expense: 5,000
        create_journal_entry(
            organization=self.org,
            actor=self.staff_user,
            txn_date=today,
            narration="Bandwidth Transit Cost",
            lines=[
                {"account": coa["5000"], "debit": Decimal("5000.00"), "credit": Decimal("0.00")},
                {"account": coa["1010"], "debit": Decimal("0.00"), "credit": Decimal("5000.00")},
            ],
        )

        url = f"/api/v1/reports/financial/profit-and-loss/?start_date=2026-09-01&end_date=2026-09-30"
        resp = self.client.get(url, **self.owner_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["revenue_statement"]["total_revenue"], "20000.00")
        self.assertEqual(resp.data["expense_statement"]["total_expenses"], "5000.00")
        self.assertEqual(resp.data["net_income"]["net_profit_amount"], "15000.00")
        self.assertTrue(resp.data["net_income"]["is_profitable"])

    def test_balance_sheet_statement(self):
        coa = get_or_create_default_chart_of_accounts(self.org)
        today = date(2026, 9, 20)

        # Seed capital: 50,000 to Bank from Equity
        create_journal_entry(
            organization=self.org,
            actor=self.staff_user,
            txn_date=today,
            narration="Capital Seed",
            lines=[
                {"account": coa["1010"], "debit": Decimal("50000.00"), "credit": Decimal("0.00")},
                {"account": coa["3000"], "debit": Decimal("0.00"), "credit": Decimal("50000.00")},
            ],
        )

        url = f"/api/v1/reports/financial/balance-sheet/?as_of_date=2026-09-30"
        resp = self.client.get(url, **self.owner_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_balanced"])
        self.assertEqual(resp.data["assets"]["total_assets"], "50000.00")

    # -------------------------------------------------------------------------
    # 6. RECOVERY & PROMISES TESTS
    # -------------------------------------------------------------------------
    def test_promise_to_pay_report(self):
        PromiseToPay.objects.create(
            organization=self.org,
            promise_number="NX-PTP-001",
            customer=self.customer,
            service_account=self.service,
            outstanding_amount=Decimal("4000.00"),
            promised_amount=Decimal("4000.00"),
            promise_date=date(2026, 9, 1),
            deadline=date(2026, 9, 5),
            status=PromiseToPay.Status.FULFILLED,
        )

        url = "/api/v1/reports/recovery/ptp-performance/"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["fulfilled_count"], 1)
        self.assertEqual(resp.data["summary"]["fulfillment_rate_percent"], 100.0)

    # -------------------------------------------------------------------------
    # 7. SUPPORT, INQUIRIES & INVENTORY REPORTS
    # -------------------------------------------------------------------------
    def test_support_sla_mttr_report(self):
        Complaint.objects.create(
            organization=self.org,
            complaint_number="CMP-001",
            customer=self.customer,
            service_account=self.service,
            category=Complaint.Category.SPEED,
            priority=Complaint.Priority.HIGH,
            status=Complaint.Status.RESOLVED,
            sla_status=Complaint.SLAStatus.ON_TRACK,
            created_by=self.staff_user,
        )

        url = "/api/v1/reports/support/sla-mttr/"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["total_complaints"], 1)
        self.assertEqual(resp.data["summary"]["sla_compliance_rate_percent"], 100.0)

    def test_lead_conversion_funnel_report(self):
        Inquiry.objects.create(
            organization=self.org,
            inquiry_number="INQ-001",
            full_name="Usman Ali",
            phone="03009988776",
            address_line="Model Town",
            city="Lahore",
            status=Inquiry.Status.CONVERTED,
            source=Inquiry.Source.PHONE_CALL,
        )

        url = "/api/v1/reports/inquiries/conversion-funnel/"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["total_inquiries"], 1)
        self.assertEqual(resp.data["summary"]["converted_count"], 1)
        self.assertEqual(resp.data["summary"]["conversion_rate_percent"], 100.0)

    def test_device_custody_report(self):
        InventoryDevice.objects.create(
            organization=self.org,
            asset_tag="DEV-ONU-99",
            device_type=InventoryDevice.DeviceType.ONU,
            serial_number="SN998877",
            status=InventoryDevice.Status.AVAILABLE,
        )

        url = "/api/v1/reports/inventory/device-custody/"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["total_devices"], 1)
        self.assertEqual(resp.data["summary"]["available_count"], 1)

    # -------------------------------------------------------------------------
    # 8. CSV EXPORT & TENANT ISOLATION TESTS
    # -------------------------------------------------------------------------
    def test_csv_export_format(self):
        url = "/api/v1/reports/collections/register/?format=csv"
        resp = self.client.get(url, **self.staff_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("Payment #,Paid Date", resp.content.decode())

    def test_tenant_isolation_in_reports(self):
        # Org 2 request must NOT see Org 1 records
        url = "/api/v1/reports/customers/master/"
        resp = self.client.get(url, **self.other_headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["total_subscribers"], 0)
        self.assertEqual(len(resp.data["records"]), 0)
