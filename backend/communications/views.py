import hashlib
import hmac
import logging
import re

from django.conf import settings
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import Customer
from tenancy.models import AuditLog
from tenancy.permissions import HasActiveTenantContext, IsOrganizationStaffOrOwner

from .models import (
    CommunicationAutomation,
    CommunicationLog,
    CommunicationProvider,
    CommunicationQueue,
    CommunicationSchedule,
    CommunicationTemplate,
)
from .serializers import (
    BroadcastSerializer,
    CommunicationAutomationSerializer,
    CommunicationLogSerializer,
    CommunicationProviderSerializer,
    CommunicationQueueSerializer,
    CommunicationScheduleSerializer,
    CommunicationTemplateSerializer,
)

logger = logging.getLogger(__name__)


class CommunicationBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]

    def get_queryset(self):
        return self.queryset.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)


class CommunicationProviderViewSet(CommunicationBaseViewSet):
    queryset = CommunicationProvider.objects.all()
    serializer_class = CommunicationProviderSerializer

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        provider = self.get_object()
        connected = bool(provider.api_url and provider.access_token)
        provider.is_connected = connected
        provider.save(update_fields=["is_connected", "updated_at"])
        return Response(
            {
                "success": True,
                "connected": provider.is_connected,
                "message": "Connection successful." if connected else "Connection failed.",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def toggle_connection(self, request, pk=None):
        provider = self.get_object()
        provider.is_connected = not provider.is_connected
        provider.save(update_fields=["is_connected", "updated_at"])
        return Response({"success": True, "is_connected": provider.is_connected})

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        provider = self.get_object()
        CommunicationProvider.objects.filter(organization=request.organization).update(is_default=False)
        provider.is_default = True
        provider.save(update_fields=["is_default", "updated_at"])
        return Response({"success": True})

    @action(detail=False, methods=["get"], url_path="settings")
    def settings_list(self, request):
        queryset = self.get_queryset().order_by("provider_type")
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["patch"], url_path="settings")
    def settings_detail(self, request, pk=None):
        provider = self.get_object()
        serializer = self.get_serializer(provider, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CommunicationAutomationViewSet(CommunicationBaseViewSet):
    queryset = CommunicationAutomation.objects.select_related("template", "template__communication_provider")
    serializer_class = CommunicationAutomationSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related("template", "template__communication_provider")
        search = self.request.query_params.get("search")
        trigger = self.request.query_params.get("trigger")
        enabled = self.request.query_params.get("enabled")
        ordering = self.request.query_params.get("ordering", "execution_order")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if trigger:
            queryset = queryset.filter(trigger=trigger)
        if enabled is not None:
            queryset = queryset.filter(is_enabled=enabled.lower() == "true")
        return queryset.order_by(ordering)

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        automation = self.get_object()
        automation.is_enabled = True
        automation.save(update_fields=["is_enabled", "updated_at"])
        AuditLog.objects.create(
            organization=request.organization,
            actor=request.user,
            action="COMMUNICATION_AUTOMATION_ENABLED",
            resource_type="CommunicationAutomation",
            resource_id=str(automation.id),
        )
        return Response({"success": True, "enabled": True})

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        automation = self.get_object()
        automation.is_enabled = False
        automation.save(update_fields=["is_enabled", "updated_at"])
        AuditLog.objects.create(
            organization=request.organization,
            actor=request.user,
            action="COMMUNICATION_AUTOMATION_DISABLED",
            resource_type="CommunicationAutomation",
            resource_id=str(automation.id),
        )
        return Response({"success": True, "enabled": False})

    @action(detail=True, methods=["post"], url_path="execute-now")
    def execute_now(self, request, pk=None):
        automation = self.get_object()
        customer_id = request.data.get("customer_id")
        if not customer_id:
            return Response({"success": False, "message": "customer_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        customer = get_object_or_404(Customer, pk=customer_id, organization=request.organization)
        from .automation_service import CommunicationAutomationService
        CommunicationAutomationService.execute_automation(automation=automation, customer=customer)
        AuditLog.objects.create(
            organization=request.organization,
            actor=request.user,
            action="COMMUNICATION_AUTOMATION_EXECUTED",
            resource_type="CommunicationAutomation",
            resource_id=str(automation.id),
        )
        return Response({"success": True, "message": "Automation executed successfully."})

    def perform_create(self, serializer):
        automation = serializer.save(organization=self.request.organization)
        AuditLog.objects.create(
            organization=self.request.organization,
            actor=self.request.user,
            action="COMMUNICATION_AUTOMATION_CREATED",
            resource_type="CommunicationAutomation",
            resource_id=str(automation.id),
        )

    def perform_update(self, serializer):
        automation = serializer.save()
        AuditLog.objects.create(
            organization=self.request.organization,
            actor=self.request.user,
            action="COMMUNICATION_AUTOMATION_UPDATED",
            resource_type="CommunicationAutomation",
            resource_id=str(automation.id),
        )

    def perform_destroy(self, instance):
        AuditLog.objects.create(
            organization=self.request.organization,
            actor=self.request.user,
            action="COMMUNICATION_AUTOMATION_DELETED",
            resource_type="CommunicationAutomation",
            resource_id=str(instance.id),
        )
        instance.delete()


class CommunicationScheduleViewSet(CommunicationBaseViewSet):
    queryset = CommunicationSchedule.objects.select_related("automation")
    serializer_class = CommunicationScheduleSerializer


class CommunicationQueueViewSet(CommunicationBaseViewSet):
    queryset = CommunicationQueue.objects.all()
    serializer_class = CommunicationQueueSerializer


class CommunicationLogViewSet(CommunicationBaseViewSet):
    queryset = CommunicationLog.objects.all()
    serializer_class = CommunicationLogSerializer


class BroadcastAPIView(APIView):
    permission_classes = [HasActiveTenantContext, IsOrganizationStaffOrOwner]

    def post(self, request):
        serializer = BroadcastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = get_object_or_404(
            CommunicationProvider,
            id=serializer.validated_data["provider_id"],
            organization=request.organization,
        )
        template = get_object_or_404(
            CommunicationTemplate,
            id=serializer.validated_data["template_id"],
            organization=request.organization,
        )
        if not provider.is_connected:
            return Response({"success": False, "message": "Provider is disconnected."}, status=status.HTTP_400_BAD_REQUEST)
        customers = Customer.objects.filter(organization=request.organization).exclude(phone="")
        queued = 0
        for customer in customers:
            queue = CommunicationQueue.objects.create(
                organization=request.organization,
                customer=customer,
                template=template,
                provider=provider,
                recipient=customer.phone,
                payload={"title": serializer.validated_data["title"], "message": serializer.validated_data["message"]},
                status=CommunicationLog.Status.PENDING,
                scheduled_at=serializer.validated_data.get("schedule_at") or timezone.now(),
            )
            CommunicationLog.objects.create(
                organization=request.organization,
                queue=queue,
                recipient=customer.phone,
                subject=serializer.validated_data["title"],
                message=serializer.validated_data["message"],
                status=CommunicationQueue.Status.PENDING,
                provider_response="Queued Successfully",
            )
            queued += 1
        return Response({"success": True, "queued": queued, "message": "Broadcast queued successfully."}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([HasActiveTenantContext, IsOrganizationStaffOrOwner])
def broadcast_options(request):
    providers = CommunicationProviderSerializer(
        CommunicationProvider.objects.filter(organization=request.organization, is_connected=True),
        many=True,
    ).data
    templates = CommunicationTemplateSerializer(
        CommunicationTemplate.objects.filter(organization=request.organization),
        many=True,
    ).data
    return Response(
        {
            "providers": providers,
            "templates": templates,
            "audience": [
                {"value": "ALL_CUSTOMERS", "label": "All Customers"},
                {"value": "AREA", "label": "Area Wise"},
                {"value": "PACKAGE", "label": "Package Wise"},
                {"value": "SELECTED_CUSTOMERS", "label": "Selected Customers"},
            ],
        }
    )


class RetryCommunicationAPIView(APIView):
    permission_classes = [HasActiveTenantContext, IsOrganizationStaffOrOwner]

    def post(self, request, pk):
        log = get_object_or_404(
            CommunicationLog.objects.select_related("queue"),
            pk=pk,
            organization=request.organization,
        )
        if not log.queue:
            return Response({"success": False, "message": "Queue record not found."}, status=status.HTTP_404_NOT_FOUND)
        queue = log.queue
        queue.status = CommunicationQueue.Status.PENDING
        queue.scheduled_at = timezone.now()
        queue.retry_count += 1
        queue.save(update_fields=["status", "scheduled_at", "retry_count", "updated_at"])
        log.status = CommunicationLog.Status.PENDING
        log.provider_response = "Queued for retry"
        log.retry_count = F("retry_count") + 1
        log.last_retry_at = timezone.now()
        log.save(update_fields=["status", "provider_response", "retry_count", "last_retry_at", "updated_at"])
        return Response({"success": True, "message": "Communication queued for retry."})


class CommunicationTemplateViewSet(CommunicationBaseViewSet):
    queryset = CommunicationTemplate.objects.select_related("communication_provider")
    serializer_class = CommunicationTemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related("communication_provider")
        search = self.request.query_params.get("search")
        status_filter = self.request.query_params.get("status")
        provider = self.request.query_params.get("provider")
        ordering = self.request.query_params.get("ordering", "name")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(subject__icontains=search) | Q(body__icontains=search))
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if provider:
            queryset = queryset.filter(communication_provider_id=provider)
        return queryset.order_by(ordering)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        template = self.get_object()
        copy = CommunicationTemplate.objects.create(
            organization=request.organization,
            name=f"{template.name} Copy",
            subject=template.subject,
            body=template.body,
            variables=template.variables,
            status=CommunicationTemplate.Status.DRAFT,
            communication_provider=template.communication_provider,
        )
        AuditLog.objects.create(
            organization=request.organization,
            actor=request.user,
            action="COMMUNICATION_TEMPLATE_DUPLICATED",
            resource_type="CommunicationTemplate",
            resource_id=str(copy.id),
            metadata={"source_template": str(template.id), "new_template": str(copy.id)},
        )
        return Response(self.get_serializer(copy).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        template = self.get_object()
        template.status = CommunicationTemplate.Status.ACTIVE
        template.save(update_fields=["status", "updated_at"])
        AuditLog.objects.create(
            organization=request.organization,
            actor=request.user,
            action="COMMUNICATION_TEMPLATE_ENABLED",
            resource_type="CommunicationTemplate",
            resource_id=str(template.id),
        )
        return Response({"success": True, "status": template.status})

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        template = self.get_object()
        template.status = CommunicationTemplate.Status.ARCHIVED
        template.save(update_fields=["status", "updated_at"])
        AuditLog.objects.create(
            organization=request.organization,
            actor=request.user,
            action="COMMUNICATION_TEMPLATE_DISABLED",
            resource_type="CommunicationTemplate",
            resource_id=str(template.id),
        )
        return Response({"success": True, "status": template.status})

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        template = self.get_object()
        sample_data = request.data.get("variables", {})
        rendered_subject = template.subject or ""
        rendered_body = template.body
        for key, value in sample_data.items():
            placeholder = "{{" + str(key) + "}}"
            rendered_subject = rendered_subject.replace(placeholder, str(value))
            rendered_body = rendered_body.replace(placeholder, str(value))
        AuditLog.objects.create(
            organization=request.organization,
            actor=request.user,
            action="COMMUNICATION_TEMPLATE_PREVIEWED",
            resource_type="CommunicationTemplate",
            resource_id=str(template.id),
        )
        return Response({"subject": rendered_subject, "body": rendered_body})

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        template = self.get_object()
        variables = sorted(set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", template.body)))
        return Response({"valid": True, "variables": variables, "count": len(variables)})

    def perform_create(self, serializer):
        template = serializer.save(organization=self.request.organization)
        AuditLog.objects.create(
            organization=self.request.organization,
            actor=self.request.user,
            action="COMMUNICATION_TEMPLATE_CREATED",
            resource_type="CommunicationTemplate",
            resource_id=str(template.id),
            metadata={"template": template.name},
        )

    def perform_update(self, serializer):
        template = serializer.save()
        AuditLog.objects.create(
            organization=self.request.organization,
            actor=self.request.user,
            action="COMMUNICATION_TEMPLATE_UPDATED",
            resource_type="CommunicationTemplate",
            resource_id=str(template.id),
            metadata={"template": template.name},
        )

    def perform_destroy(self, instance):
        AuditLog.objects.create(
            organization=self.request.organization,
            actor=self.request.user,
            action="COMMUNICATION_TEMPLATE_DELETED",
            resource_type="CommunicationTemplate",
            resource_id=str(instance.id),
            metadata={"template": instance.name},
        )
        instance.delete()


class WhatsAppWebhookAPIView(APIView):
    """Meta WhatsApp Cloud API Webhook."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        mode = request.GET.get("hub.mode")
        challenge = request.GET.get("hub.challenge")
        verify_token = request.GET.get("hub.verify_token")
        if mode == "subscribe" and verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("WhatsApp webhook verified.")
            return HttpResponse(challenge, status=200)
        logger.warning("WhatsApp webhook verification failed.")
        return HttpResponse("Verification failed.", status=403)

    @staticmethod
    def _valid_signature(request):
        app_secret = settings.WHATSAPP_APP_SECRET
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not app_secret or not signature.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(
            app_secret.encode("utf-8"),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def post(self, request):
        if not self._valid_signature(request):
            logger.warning("Rejected WhatsApp webhook with invalid signature.")
            return Response({"success": False}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data
        logger.info("Received WhatsApp webhook event.")

        try:
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    metadata = value.get("metadata", {})
                    phone_number_id = metadata.get("phone_number_id")
                    if not phone_number_id:
                        logger.warning("WhatsApp webhook missing phone_number_id.")
                        continue

                    provider = CommunicationProvider.objects.filter(
                        phone_number_id=phone_number_id,
                        provider_type=CommunicationProvider.ProviderType.WHATSAPP,
                        status=CommunicationProvider.Status.ACTIVE,
                    ).first()
                    if not provider:
                        logger.warning("No active WhatsApp provider for phone_number_id %s.", phone_number_id)
                        continue

                    for item in value.get("statuses", []):
                        message_id = item.get("id")
                        status_name = item.get("status")
                        if not message_id:
                            continue

                        try:
                            log = CommunicationLog.objects.select_related("queue").get(
                                provider_message_id=message_id,
                                queue__provider=provider,
                            )
                        except CommunicationLog.DoesNotExist:
                            logger.warning("CommunicationLog not found for provider message %s.", message_id)
                            continue

                        if status_name == "sent":
                            log.status = CommunicationLog.Status.SENT
                            log.queue.status = CommunicationQueue.Status.SENT
                        elif status_name == "delivered":
                            log.status = CommunicationLog.Status.DELIVERED
                            log.delivered_at = timezone.now()
                            log.queue.status = CommunicationQueue.Status.SENT
                        elif status_name == "read":
                            log.status = CommunicationLog.Status.READ
                        elif status_name == "failed":
                            log.status = CommunicationLog.Status.FAILED
                            log.queue.status = CommunicationQueue.Status.FAILED
                        else:
                            continue

                        log.provider_response = status_name
                        log.save(update_fields=["status", "provider_response", "delivered_at", "updated_at"])
                        log.queue.save(update_fields=["status", "updated_at"])

            return Response({"success": True}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("WhatsApp webhook processing failed.")
            return Response({"success": False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
