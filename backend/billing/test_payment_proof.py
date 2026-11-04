import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Payment
from customers.models import Customer, InternetPackage, ServiceAccount
from tenancy.models import AuditLog, Organization, OrganizationMembership, StaffProfile


User = get_user_model()

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64
MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PaymentProofTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.organization = Organization.objects.create(name="Proof ISP", code="PROOF-ISP", city="Lahore")
        self.owner = self.make_user("proof-owner", OrganizationMembership.Role.OWNER)
        customer = Customer.objects.create(
            organization=self.organization,
            customer_number="PRF-CUST-1",
            first_name="Zain",
            phone="03004441111",
            address_line="Street 1",
            city="Lahore",
        )
        package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 10",
            code="PRF-10",
            download_speed_mbps=10,
            upload_speed_mbps=5,
            monthly_price="1500.00",
        )
        service = ServiceAccount.objects.create(
            organization=self.organization,
            service_number="PRF-SRV-1",
            customer=customer,
            internet_package=package,
        )
        self.payment = Payment.objects.create(
            organization=self.organization,
            payment_number="PROOF-ISP-PAY-00001",
            service_account=service,
            amount="1500.00",
            payment_method=Payment.Method.MOBILE_WALLET,
            reference="JC-123",
            paid_at=timezone.now(),
        )
        self.url = reverse("billing-payment-proof", kwargs={"payment_id": self.payment.id})
        self.login(self.owner)

    def make_user(self, username, role, staff_role=None):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@nexora.local",
            password="StrongTestPassword123!",
        )
        membership = OrganizationMembership.objects.create(
            organization=self.organization,
            user=user,
            role=role,
        )
        if staff_role:
            StaffProfile.objects.create(
                organization=self.organization,
                membership=membership,
                user=user,
                staff_code=f"PROOF-{username}",
                role=staff_role,
            )
        return user

    def login(self, user):
        response = self.client.post(
            reverse("tenant-login"),
            {
                "email": user.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def upload(self, content, name="proof.png"):
        return self.client.post(
            self.url,
            {"proof_file": SimpleUploadedFile(name, content)},
            format="multipart",
        )

    def test_upload_image_and_view_it(self):
        response = self.upload(PNG)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["has_proof"])
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.proof_uploaded_by, self.owner)
        self.assertTrue(AuditLog.objects.filter(action="PAYMENT_PROOF_UPLOADED").exists())

        download = self.client.get(self.url)
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        self.assertEqual(download["Content-Type"], "image/png")
        self.assertEqual(b"".join(download.streaming_content), PNG)

    def test_pdf_and_jpeg_are_accepted(self):
        self.assertEqual(self.upload(PDF, "slip.pdf").status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.get(self.url)["Content-Type"], "application/pdf")

        self.assertEqual(self.upload(JPEG, "slip.jpg").status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.get(self.url)["Content-Type"], "image/jpeg")

    def test_file_type_is_checked_by_content_not_name(self):
        response = self.upload(b"MZ\x90\x00 not an image", "proof.png")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.payment.refresh_from_db()
        self.assertFalse(self.payment.proof_file)

    def test_oversized_file_is_rejected(self):
        response = self.upload(PNG + b"\x00" * (5 * 1024 * 1024))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("5 MB", response.data["detail"])

    def test_missing_file_is_rejected(self):
        response = self.client.post(self.url, {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_viewing_without_proof_returns_404(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_404_NOT_FOUND)

    def test_other_tenant_cannot_see_or_upload(self):
        self.upload(PNG)
        other_org = Organization.objects.create(name="Other ISP", code="OTHER-PRF", city="Lahore")
        intruder = User.objects.create_user(
            username="intruder",
            email="intruder@nexora.local",
            password="StrongTestPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=other_org,
            user=intruder,
            role=OrganizationMembership.Role.OWNER,
        )
        response = self.client.post(
            reverse("tenant-login"),
            {"email": intruder.email, "password": "StrongTestPassword123!", "organization_code": other_org.code},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.upload(PNG).status_code, status.HTTP_400_BAD_REQUEST)

    def test_technician_cannot_upload_but_can_view(self):
        self.upload(PNG)
        technician = self.make_user(
            "proof-tech",
            OrganizationMembership.Role.STAFF,
            staff_role=StaffProfile.Role.TECHNICIAN,
        )
        self.login(technician)

        self.assertEqual(self.upload(PNG).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_200_OK)

    def test_payment_list_reports_proof(self):
        self.upload(PNG)

        response = self.client.get(reverse("billing-payment-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertTrue(items[0]["has_proof"])
