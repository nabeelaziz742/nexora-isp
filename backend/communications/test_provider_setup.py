from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from communications.models import CommunicationProvider, CommunicationTemplate
from communications.notification_engine import NotificationEvent, dispatch_notification_event
from customers.models import Customer, NotificationPreference
from tenancy.models import Organization, OrganizationMembership


User = get_user_model()


class ProviderSetupAPITests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Provider ISP",
            code="PROVIDER-ISP",
            city="Lahore",
            currency="PKR",
        )
        self.owner = User.objects.create_user(
            username="provider-owner",
            email="provider-owner@nexora.local",
            password="StrongTestPassword123!",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=OrganizationMembership.Role.OWNER,
        )
        response = self.client.post(
            reverse("tenant-login"),
            {
                "email": self.owner.email,
                "password": "StrongTestPassword123!",
                "organization_code": self.organization.code,
            },
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def create_whatsapp(self, **extra):
        return self.client.post(
            "/api/v1/communications/providers/",
            {
                "name": "Main WhatsApp",
                "provider_type": "WHATSAPP",
                "phone_number_id": "123456",
                "access_token": "secret-token",
                **extra,
            },
            format="json",
        )

    def test_new_isp_can_add_whatsapp_provider(self):
        response = self.create_whatsapp()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("access_token", response.data)
        self.assertTrue(response.data["has_access_token"])
        self.assertFalse(response.data["is_connected"])
        provider = CommunicationProvider.objects.get(id=response.data["id"])
        self.assertEqual(provider.organization, self.organization)
        self.assertEqual(provider.access_token, "secret-token")

    def test_blank_token_on_update_keeps_saved_token(self):
        provider_id = self.create_whatsapp().data["id"]

        response = self.client.patch(
            f"/api/v1/communications/providers/{provider_id}/settings/",
            {"name": "Renamed", "access_token": ""},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        provider = CommunicationProvider.objects.get(id=provider_id)
        self.assertEqual(provider.name, "Renamed")
        self.assertEqual(provider.access_token, "secret-token")

    def test_changing_credentials_requires_a_new_connection_test(self):
        provider_id = self.create_whatsapp().data["id"]
        CommunicationProvider.objects.filter(id=provider_id).update(is_connected=True)

        self.client.patch(
            f"/api/v1/communications/providers/{provider_id}/settings/",
            {"name": "Renamed only"},
            format="json",
        )
        self.assertTrue(CommunicationProvider.objects.get(id=provider_id).is_connected)

        self.client.patch(
            f"/api/v1/communications/providers/{provider_id}/settings/",
            {"phone_number_id": "999999"},
            format="json",
        )
        self.assertFalse(CommunicationProvider.objects.get(id=provider_id).is_connected)

    @patch("communications.views.requests.get")
    def test_connection_test_marks_provider_connected(self, mock_get):
        mock_get.return_value = Mock(
            ok=True,
            content=b"{}",
            json=Mock(return_value={"display_phone_number": "+92 300 0000000"}),
        )
        provider_id = self.create_whatsapp().data["id"]

        response = self.client.post(f"/api/v1/communications/providers/{provider_id}/test_connection/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CommunicationProvider.objects.get(id=provider_id).is_connected)

    def test_provider_in_use_cannot_be_deleted(self):
        provider = CommunicationProvider.objects.get(id=self.create_whatsapp().data["id"])
        CommunicationTemplate.objects.create(
            organization=self.organization,
            name="In use",
            body="Hello",
            communication_provider=provider,
        )

        response = self.client.delete(f"/api/v1/communications/providers/{provider.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("used by templates", response.data["detail"])
        self.assertTrue(CommunicationProvider.objects.filter(id=provider.id).exists())

    def test_unused_provider_can_be_deleted(self):
        provider_id = self.create_whatsapp().data["id"]

        response = self.client.delete(f"/api/v1/communications/providers/{provider_id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ProviderSelectionTests(APITestCase):
    @patch("communications.providers.whatsapp.requests.post")
    def test_connected_provider_is_preferred_over_placeholder(self, mock_post):
        mock_post.return_value = Mock(
            ok=True,
            status_code=200,
            json=Mock(return_value={"messages": [{"id": "wamid.x"}]}),
        )
        organization = Organization.objects.create(name="Pick ISP", code="PICK-ISP", city="Lahore")
        customer = Customer.objects.create(
            organization=organization,
            customer_number="PICK-1",
            first_name="Ali",
            phone="03001231234",
            address_line="Street",
            city="Lahore",
        )
        NotificationPreference.objects.create(
            organization=organization,
            customer=customer,
            whatsapp_enabled=True,
            sms_enabled=False,
        )
        # Placeholder created earlier by the notification engine.
        CommunicationProvider.objects.create(
            organization=organization,
            name="Pick ISP - WHATSAPP Provider",
            provider_type=CommunicationProvider.ProviderType.WHATSAPP,
            is_connected=False,
        )
        real = CommunicationProvider.objects.create(
            organization=organization,
            name="Main WhatsApp",
            provider_type=CommunicationProvider.ProviderType.WHATSAPP,
            phone_number_id="123456",
            access_token="token",
            is_connected=True,
        )

        result = dispatch_notification_event(
            organization=organization,
            customer=customer,
            event_type=NotificationEvent.SERVICE_RESTORED,
            context={"service_number": "PICK-SRV"},
        )

        mock_post.assert_called_once()
        self.assertEqual(result["queued_items"][0]["status"], "SENT")
        self.assertIn(real.phone_number_id, mock_post.call_args.args[0])
