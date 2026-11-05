import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook, load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Invoice, Payment
from billing.services import get_service_advance_balance
from communications.models import CommunicationQueue
from customers.import_services import COLUMN_KEYS
from customers.models import (
    BillingProfile,
    Customer,
    CustomerImportBatch,
    Dealer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from network.credentials import decrypt_secret
from network.models import NetworkAssignment, NetworkNode, ProvisioningRequest
from notifications.models import NotificationJob
from tenancy.models import Organization, OrganizationMembership, StaffProfile


User = get_user_model()

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def base_row(**overrides):
    row = {
        "first_name": "Ali",
        "last_name": "Khan",
        "phone": "03001234567",
        "address": "House 12, Street 4",
        "city": "Lahore",
        "package_code": "F-20",
        "billing_mode": "MONTHLY",
    }
    row.update(overrides)
    return row


def make_xlsx(rows, headers=COLUMN_KEYS):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Customers"
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(key, "") for key in headers])
    output = io.BytesIO()
    workbook.save(output)
    return SimpleUploadedFile("customers.xlsx", output.getvalue(), content_type=XLSX)


class CustomerImportTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Import ISP", code="IMPORT-ISP", city="Lahore")
        self.owner = self.make_user("import-owner", OrganizationMembership.Role.OWNER)
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 20",
            code="F-20",
            download_speed_mbps=20,
            upload_speed_mbps=10,
            monthly_price="2500.00",
        )
        self.node = NetworkNode.objects.create(
            organization=self.organization,
            name="Johar Router",
            code="RTR-01",
            node_type=NetworkNode.NodeType.ROUTER,
            management_ip="10.50.0.1",
        )
        self.dealer = Dealer.objects.create(
            organization=self.organization,
            dealer_code="DLR-001",
            name="Usman",
            phone="03009990000",
            joining_date="2025-01-01",
        )
        self.login(self.owner)

    def make_user(self, username, role, staff_role=None):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@nexora.local",
            password="StrongTestPassword123!",
        )
        membership = OrganizationMembership.objects.create(organization=self.organization, user=user, role=role)
        if staff_role:
            StaffProfile.objects.create(
                organization=self.organization,
                membership=membership,
                user=user,
                staff_code=f"IMP-{username}",
                role=staff_role,
            )
        return user

    def login(self, user):
        response = self.client.post(
            reverse("tenant-login"),
            {"email": user.email, "password": "StrongTestPassword123!", "organization_code": self.organization.code},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def preview(self, upload):
        return self.client.post(reverse("customer-import-preview"), {"file": upload}, format="multipart")

    def run_import(self, upload, **extra):
        return self.client.post(reverse("customer-import"), {"file": upload, **extra}, format="multipart")

    # Template -------------------------------------------------------------

    def test_template_lists_columns_and_tenant_codes(self):
        response = self.client.get(reverse("customer-import-template"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], XLSX)
        workbook = load_workbook(io.BytesIO(response.content))
        self.assertEqual(workbook.sheetnames, ["Customers", "Instructions", "Codes"])
        headers = [cell.value for cell in workbook["Customers"][1]]
        self.assertEqual(headers, COLUMN_KEYS)
        codes = [cell.value for row in workbook["Codes"].iter_rows() for cell in row]
        self.assertIn("F-20", codes)
        self.assertIn("RTR-01", codes)
        self.assertIn("DLR-001", codes)

    # Preview --------------------------------------------------------------

    def test_preview_reports_rows_without_saving(self):
        upload = make_xlsx([
            base_row(),
            base_row(phone="03007654321", package_code="NOPE"),
        ])

        response = self.preview(upload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["valid_count"], 1)
        self.assertEqual(response.data["invalid_count"], 1)
        bad = response.data["rows"][1]
        self.assertEqual(bad["row"], 3)
        self.assertIn("Package code 'NOPE' was not found or is inactive.", bad["errors"])
        self.assertFalse(Customer.objects.exists())

    def test_missing_required_column_is_rejected(self):
        upload = make_xlsx([base_row()], headers=["first_name", "phone"])

        response = self.preview(upload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Missing required columns", response.data["detail"])

    # Import ---------------------------------------------------------------

    def test_monthly_customer_is_imported_without_bill_router_or_messages(self):
        upload = make_xlsx([base_row(
            cnic="3520212345671",
            legacy_id="WAS-1043",
            dealer_code="dlr-001",
            node_code="RTR-01",
            pppoe_username="ali-johar",
            pppoe_password="secret123",
            ip_address="10.50.0.25",
            billing_day="5",
            due_day="15",
        )])

        response = self.run_import(upload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["imported_count"], 1)
        customer = Customer.objects.get()
        self.assertEqual(customer.cnic, "35202-1234567-1")
        self.assertEqual(customer.legacy_id, "WAS-1043")
        self.assertEqual(customer.dealer, self.dealer)
        service = ServiceAccount.objects.get(customer=customer)
        self.assertEqual(service.status, ServiceAccount.Status.ACTIVE)
        profile = BillingProfile.objects.get(service_account=service)
        self.assertEqual((profile.billing_cycle, profile.billing_day, profile.due_day), ("MONTHLY", 5, 15))
        assignment = NetworkAssignment.objects.get(service_account=service)
        self.assertEqual(assignment.username, "ali-johar")
        self.assertEqual(decrypt_secret(assignment.network_password_encrypted), "secret123")
        self.assertTrue(NotificationPreference.objects.get(customer=customer).whatsapp_enabled)

        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(ProvisioningRequest.objects.exists())
        self.assertFalse(CommunicationQueue.objects.exists())
        self.assertFalse(NotificationJob.objects.exists())

    def test_prepaid_customer_keeps_expiry_and_needs_one(self):
        upload = make_xlsx([
            base_row(billing_mode="prepaid", expiry_date="30-11-2026"),
            base_row(phone="03007654321", billing_mode="PREPAID"),
        ])

        response = self.run_import(upload)

        self.assertEqual(response.data["imported_count"], 1)
        self.assertEqual(str(ServiceAccount.objects.get().expiry_date), "2026-11-30")
        self.assertIn("expiry_date is required for PREPAID customers.", response.data["errors"][0]["errors"])

    def test_opening_balance_becomes_one_invoice(self):
        self.run_import(make_xlsx([base_row(opening_balance="2,500")]))

        invoice = Invoice.objects.get()
        self.assertEqual(invoice.total_amount, Decimal("2500.00"))
        self.assertEqual(invoice.lines.get().description, "Opening balance (imported)")

    def test_advance_becomes_credit_without_a_message(self):
        self.run_import(make_xlsx([base_row(advance="800")]))

        service = ServiceAccount.objects.get()
        payment = Payment.objects.get()
        self.assertEqual(payment.reference, "OPENING-ADVANCE")
        self.assertEqual(get_service_advance_balance(service_account=service), Decimal("800.00"))
        self.assertFalse(CommunicationQueue.objects.exists())

    def test_opening_balance_and_advance_together_is_an_error(self):
        response = self.run_import(make_xlsx([base_row(opening_balance="100", advance="100")]))

        self.assertEqual(response.data["imported_count"], 0)
        self.assertIn("Give either opening_balance or advance, not both.", response.data["errors"][0]["errors"])

    def test_suspended_status_is_kept(self):
        self.run_import(make_xlsx([base_row(status="suspended", advance="500")]))

        self.assertEqual(ServiceAccount.objects.get().status, ServiceAccount.Status.SUSPENDED_NON_PAYMENT)
        self.assertFalse(ProvisioningRequest.objects.exists())

    def test_create_on_router_queues_activation(self):
        self.run_import(
            make_xlsx([base_row(node_code="RTR-01", pppoe_username="ali-johar")]),
            create_on_router="true",
        )

        request = ProvisioningRequest.objects.get()
        self.assertEqual(request.action, ProvisioningRequest.Action.ACTIVATE)

    def test_duplicates_are_reported(self):
        Customer.objects.create(
            organization=self.organization,
            customer_number="OLD-1",
            first_name="Existing",
            phone="03001111111",
            address_line="Street",
            city="Lahore",
            legacy_id="WAS-1",
        )
        upload = make_xlsx([
            base_row(phone="03001111111"),
            base_row(phone="03002222222", node_code="RTR-01", pppoe_username="same", legacy_id="WAS-2"),
            base_row(phone="03002222222"),
            base_row(phone="03003333333", node_code="RTR-01", pppoe_username="SAME"),
            base_row(phone="03004444444", legacy_id="was-1"),
        ])

        rows = self.preview(upload).data["rows"]

        self.assertIn("A customer with this phone already exists.", rows[0]["errors"])
        self.assertTrue(rows[1]["valid"])
        self.assertIn("This phone appears twice in the file.", rows[2]["errors"])
        self.assertIn("PPPoE username 'SAME' appears twice for RTR-01.", rows[3]["errors"])
        self.assertIn("A customer with this legacy_id was already imported.", rows[4]["errors"])

    def test_phone_saved_as_number_gets_its_zero_back(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(COLUMN_KEYS)
        row = base_row()
        row["phone"] = 3001234567
        sheet.append([row.get(key, "") for key in COLUMN_KEYS])
        output = io.BytesIO()
        workbook.save(output)

        self.run_import(SimpleUploadedFile("numbers.xlsx", output.getvalue(), content_type=XLSX))

        self.assertEqual(Customer.objects.get().phone, "03001234567")

    def test_csv_upload_is_accepted(self):
        header = ",".join(COLUMN_KEYS)
        row = base_row()
        line = ",".join(f'"{row.get(key, "")}"' for key in COLUMN_KEYS)
        upload = SimpleUploadedFile("customers.csv", f"{header}\n{line}\n".encode(), content_type="text/csv")

        response = self.run_import(upload)

        self.assertEqual(response.data["imported_count"], 1)

    def test_history_lists_batches(self):
        self.run_import(make_xlsx([base_row(), base_row(phone="bad")]))

        response = self.client.get(reverse("customer-import-history"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        batch = response.data[0]
        self.assertEqual((batch["total_rows"], batch["imported_count"], batch["skipped_count"]), (2, 1, 1))
        self.assertEqual(CustomerImportBatch.objects.count(), 1)

    def test_operator_cannot_import(self):
        operator = self.make_user("import-operator", OrganizationMembership.Role.STAFF, StaffProfile.Role.OPERATOR)
        self.login(operator)

        response = self.run_import(make_xlsx([base_row()]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Customer.objects.exists())
