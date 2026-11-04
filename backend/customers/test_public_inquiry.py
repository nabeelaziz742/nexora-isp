from datetime import timedelta

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from customers.models import Inquiry, InternetPackage
from tenancy.models import AuditLog, Organization


class PublicInquiryTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.organization = Organization.objects.create(
            name="Smart Broadband",
            code="SMART-BB",
            city="Lahore",
            phone="0421234567",
        )
        self.package = InternetPackage.objects.create(
            organization=self.organization,
            name="Fiber 20",
            code="SB-20",
            download_speed_mbps=20,
            upload_speed_mbps=10,
            monthly_price="2500.00",
        )
        InternetPackage.objects.create(
            organization=self.organization,
            name="Old Plan",
            code="SB-OLD",
            download_speed_mbps=5,
            upload_speed_mbps=1,
            monthly_price="1000.00",
            is_active=False,
        )
        self.url = reverse("public-inquiry", kwargs={"organization_code": "smart-bb"})

    def payload(self, **extra):
        return {
            "full_name": "Ayesha Khan",
            "phone": "03001234567",
            "address_line": "House 12, Street 4",
            "city": "Lahore",
            "area": "Johar Town",
            "preferred_package": str(self.package.id),
            **extra,
        }

    def test_form_shows_isp_and_active_packages_without_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["organization"]["name"], "Smart Broadband")
        self.assertEqual([p["name"] for p in response.data["packages"]], ["Fiber 20"])

    def test_unknown_or_inactive_isp_returns_404(self):
        response = self.client.get(reverse("public-inquiry", kwargs={"organization_code": "nope"}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.organization.is_active = False
        self.organization.save()
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_404_NOT_FOUND)

    def test_submission_creates_website_lead(self):
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inquiry = Inquiry.objects.get()
        self.assertEqual(inquiry.organization, self.organization)
        self.assertEqual(inquiry.source, Inquiry.Source.WEBSITE)
        self.assertEqual(inquiry.status, Inquiry.Status.NEW)
        self.assertEqual(inquiry.preferred_package, self.package)
        self.assertEqual(response.data["reference"], inquiry.inquiry_number)
        self.assertTrue(AuditLog.objects.filter(action="INQUIRY_SUBMITTED_ONLINE").exists())

    def test_repeat_submission_from_same_phone_is_not_duplicated(self):
        first = self.client.post(self.url, self.payload(), format="json")
        second = self.client.post(self.url, self.payload(full_name="Ayesha K"), format="json")

        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["reference"], second.data["reference"])
        self.assertEqual(Inquiry.objects.count(), 1)

    def test_same_phone_can_apply_again_after_window(self):
        self.client.post(self.url, self.payload(), format="json")
        Inquiry.objects.update(created_at=timezone.now() - timedelta(days=2))

        self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(Inquiry.objects.count(), 2)

    def test_honeypot_submission_is_silently_dropped(self):
        response = self.client.post(self.url, self.payload(website="http://spam.example"), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(Inquiry.objects.exists())

    def test_inactive_or_foreign_package_is_rejected(self):
        other = Organization.objects.create(name="Other", code="OTHER-BB", city="Lahore")
        foreign = InternetPackage.objects.create(
            organization=other,
            name="Foreign",
            code="OT-1",
            download_speed_mbps=10,
            upload_speed_mbps=5,
            monthly_price="1500.00",
        )

        response = self.client.post(self.url, self.payload(preferred_package=str(foreign.id)), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Inquiry.objects.exists())

    def test_invalid_phone_is_rejected(self):
        response = self.client.post(self.url, self.payload(phone="abc"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data)

    def test_submissions_are_rate_limited_per_ip(self):
        for index in range(5):
            response = self.client.post(
                self.url,
                self.payload(phone=f"0300123450{index}"),
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        blocked = self.client.post(self.url, self.payload(phone="03001234599"), format="json")

        self.assertEqual(blocked.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        # Reading the form is never limited.
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_200_OK)
