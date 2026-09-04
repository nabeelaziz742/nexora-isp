import hashlib
import hmac
import logging
import re

import requests
from django.conf import settings
from django.core.mail import get_connection
from django.db import transaction
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
    permission_classes = [HasActiveTenantContext, IsOrganizationStaffOrOwner]

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
        connected = False
        message = "Provider connection failed."
        health = {}

        try:
            if provider.provider_type == CommunicationProvider.ProviderType.WHATSAPP:
                if not provider.phone_number_id or not provider.access_token:
                    raise ValueError("WhatsApp phone number ID and access token are required.")
                url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{provider.phone_number_id}"
                response = requests.get(
                    url,
                    headers={"Authorization": f"Bearer {provider.access_token}"},
                    timeout=15,
                )
                data = response.json() if response.content else {}
                if not response.ok:
                    error = data.get("error", {}) if isinstance(data, dict) else {}
                    raise ValueError(
                        error.get("message", "WhatsApp credentials were rejected.")
                        if isinstance(error, dict)
                        else "WhatsApp credentials were rejected."
                    )
                connected = True
                message = "WhatsApp Cloud API connection is healthy."
                health = {
                    "phone_number_id": provider.phone_number_id,
                    "display_phone_number": data.get("display_phone_number", ""),
                    "verified_name": data.get("verified_name", ""),
                }
            elif provider.provider_type == CommunicationProvider.ProviderType.EMAIL:
                connection = get_connection(fail_silently=False)
                connection.open()
                connection.close()
                connected = True
                message = "Email provider connection is healthy."
            else:
                raise ValueError("SMS provider is not configured.")
        except Exception as exc:
            logger.warning("Communication provider %s health check failed: %s", provider.id, exc)
            message = str(exc)

        provider.is_connected = connected
        provider.last_health_check = timezone.now()
        provider.save(update_fields=["is_connected", "last_health_check", "updated_at"])
        return Response(
            {
                "success": connected,
                "connected": connected,
                "message": message,
                "health": health,
                "checked_at": provider.last_health_check,
            },
            status=status.HTTP_200_OK if connected else status.HTTP_400_BAD_REQUEST,
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
        return Response({"success": True, "enabled": True})

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        automation = self.get_object()
        automation.is_enabled = False
        automation.save(update_fields=["is_enabled", "updated_at"])
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
        return Response({"success": True, "message": "Automation executed successfully."})

    def perform_create(self, serializer):
        automation = serializer.save(organization=self.request.organization)
        AuditLog.objects.create(organization=self.request.organization, actor=self.request.user, action="COMMUNICATION_AUTOMATION_CREATED", resource_type="CommunicationAutomation", resource_id=str(automation.id))

    def perform_update(self, serializer):
        automation = serializer.save()
        AuditLog.objects.create(organization=self.request.organization, actor=self.request.user, action="COMMUNICATION_AUTOMATION_UPDATED", resource_type="CommunicationAutomation", resource_id=str(automation.id))

    def perform_destroy(self, instance):
        AuditLog.objects.create(organization=self.request.organization, actor=self.request.user, action="COMMUNICATION_AUTOMATION_DELETED", resource_type="CommunicationAutomation", resource_id=str(instance.id))
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
        data = serializer.validated_data

        provider = get_object_or_404(CommunicationProvider, id=data["provider_id"], organization=request.organization)
        template = get_object_or_404(CommunicationTemplate, id=data["template_id"], organization=request.organization)

        if provider.status != CommunicationProvider.Status.ACTIVE or not provider.is_connected:
            return Response({"success": False, "message": "Provider is inactive or disconnected."}, status=status.HTTP_400_BAD_REQUEST)
        if template.status != CommunicationTemplate.Status.ACTIVE:
            return Response({"success": False, "message": "Template is not active."}, status=status.HTTP_400_BAD_REQUEST)

        audience = data["audience"]
        customers = Customer.objects.filter(organization=request.organization, is_active=True).exclude(phone="")

        if audience == "SELECTED_CUSTOMERS":
            customer_ids = data.get("customer_ids", [])
            if not customer_ids:
                return Response({"success": False, "message": "customer_ids is required for selected customers."}, status=status.HTTP_400_BAD_REQUEST)
            customers = customers.filter(id__in=customer_ids)
        elif audience == "PACKAGE":
            package_id = data.get("package_id")
            if not package_id:
                return Response({"success": False, "message": "package_id is required for package-wise broadcast."}, status=status.HTTP_400_BAD_REQUEST)
            customers = customers.filter(service_accounts__internet_package_id=package_id, service_accounts__organization=request.organization).distinct()
        elif audience == "AREA":
            return Response({"success": False, "message": "Area-wise broadcast is not available because this project currently has no Area model."}, status=status.HTTP_400_BAD_REQUEST)

        title = data.get("title") or template.subject or ""
        message = data.get("message") or template.body
        schedule_at = data.get("schedule_at") or timezone.now()
        queued = 0

        with transaction.atomic():
            for customer in customers.iterator(chunk_size=500):
                queue = CommunicationQueue.objects.create(
                    organization=request.organization,
                    customer=customer,
                    template=template,
                    provider=provider,
                    recipient=customer.phone,
                    payload={"audience": audience},
                    rendered_subject=title,
                    rendered_body=message,
                    status=CommunicationQueue.Status.PENDING,
                    scheduled_at=schedule_at,
                )
                CommunicationLog.objects.create(
                    organization=request.organization,
                    queue=queue,
                    recipient=customer.phone,
                    subject=title,
                    message=message,
                    status=CommunicationLog.Status.PENDING,
                    provider_response="Queued successfully",
                )
                queued += 1

        return Response({"success": True, "queued": queued, "audience": audience, "scheduled_at": schedule_at, "message": "Broadcast queued successfully."}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([HasActiveTenantContext, IsOrganizationStaffOrOwner])
def broadcast_options(request):
    providers = CommunicationProviderSerializer(CommunicationProvider.objects.filter(organization=request.organization, status=CommunicationProvider.Status.ACTIVE, is_connected=True), many=True).data
    templates = CommunicationTemplateSerializer(CommunicationTemplate.objects.filter(organization=request.organization, status=CommunicationTemplate.Status.ACTIVE), many=True).data
    return Response({
        "providers": providers,
        "templates": templates,
        "audience": [
            {"value": "ALL_CUSTOMERS", "label": "All Customers"},
            {"value": "AREA", "label": "Area Wise"},
            {"value": "PACKAGE", "label": "Package Wise"},
            {"value": "SELECTED_CUSTOMERS", "label": "Selected Customers"},
        ],
    })


class RetryCommunicationAPIView(APIView):
    permission_classes = [HasActiveTenantContext, IsOrganizationStaffOrOwner]

    def post(self, request, pk):
        log = get_object_or_404(CommunicationLog.objects.select_related("queue"), pk=pk, organization=request.organization)
        queue = log.queue
        if queue.status == CommunicationQueue.Status.SENT:
            return Response({"success": False, "message": "Communication has already been sent."}, status=status.HTTP_400_BAD_REQUEST)
        queue.status = CommunicationQueue.Status.PENDING
        queue.scheduled_at = timezone.now()
        queue.next_retry_at = None
        queue.processing_started_at = None
        queue.retry_count += 1
        queue.save(update_fields=["status", "scheduled_at", "next_retry_at", "processing_started_at", "retry_count", "updated_at"])
        log.status = CommunicationLog.Status.PENDING
        log.provider_response = "Queued for manual retry"
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
        copy = CommunicationTemplate.objects.create(organization=request.organization, name=f"{template.name} Copy", subject=template.subject, body=template.body, variables=template.variables, status=CommunicationTemplate.Status.DRAFT, communication_provider=template.communication_provider)
        return Response(self.get_serializer(copy).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        template = self.get_object()
        template.status = CommunicationTemplate.Status.ACTIVE
        template.save(update_fields=["status", "updated_at"])
        return Response({"success": True, "status": template.status})

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        template = self.get_object()
        template.status = CommunicationTemplate.Status.ARCHIVED
        template.save(update_fields=["status", "updated_at"])
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
        return Response({"subject": rendered_subject, "body": rendered_body})

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        template = self.get_object()
        variables = sorted(set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", template.body)))
        return Response({"valid": True, "variables": variables, "count": len(variables)})

    def perform_create(self, serializer):
        template = serializer.save(organization=self.request.organization)
        AuditLog.objects.create(organization=self.request.organization, actor=self.request.user, action="COMMUNICATION_TEMPLATE_CREATED", resource_type="CommunicationTemplate", resource_id=str(template.id), metadata={"template": template.name})

    def perform_update(self, serializer):
        template = serializer.save()
        AuditLog.objects.create(organization=self.request.organization, actor=self.request.user, action="COMMUNICATION_TEMPLATE_UPDATED", resource_type="CommunicationTemplate", resource_id=str(template.id), metadata={"template": template.name})

    def perform_destroy(self, instance):
        AuditLog.objects.create(organization=self.request.organization, actor=self.request.user, action="COMMUNICATION_TEMPLATE_DELETED", resource_type="CommunicationTemplate", resource_id=str(instance.id), metadata={"template": instance.name})
        instance.delete()


class WhatsAppWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if request.GET.get("hub.mode") == "subscribe" and request.GET.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(request.GET.get("hub.challenge"), status=200)
        return HttpResponse("Verification failed.", status=403)

    @staticmethod
    def _valid_signature(request):
        app_secret = settings.WHATSAPP_APP_SECRET
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not app_secret or not signature.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(app_secret.encode("utf-8"), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    def post(self, request):
        if not self._valid_signature(request):
            return Response({"success": False}, status=status.HTTP_403_FORBIDDEN)
        try:
            for entry in request.data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    phone_number_id = value.get("metadata", {}).get("phone_number_id")
                    if not phone_number_id:
                        continue
                    providers = CommunicationProvider.objects.filter(
                        phone_number_id=phone_number_id,
                        provider_type=CommunicationProvider.ProviderType.WHATSAPP,
                        status=CommunicationProvider.Status.ACTIVE,
                    )
                    if providers.count() > 1:
                        logger.error(
                            "Ambiguous webhook routing rejected: multiple active providers match phone_number_id %s",
                            phone_number_id,
                        )
                        continue
                    provider = providers.first()
                    if not provider:
                        continue
                    for item in value.get("statuses", []):
                        message_id = item.get("id")
                        status_name = item.get("status")
                        if not message_id:
                            continue
                        try:
                            log = CommunicationLog.objects.select_related("queue").get(
                                provider_message_id=message_id,
                                organization=provider.organization,
                                queue__provider=provider,
                            )
                        except CommunicationLog.DoesNotExist:
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


class CustomerCommunicationHistoryView(APIView):
    permission_classes = [HasActiveTenantContext]

    def get(self, request, customer_id):
        items = (
            CommunicationQueue.objects.filter(
                organization=request.organization,
                customer_id=customer_id,
            )
            .select_related("provider", "template", "log")
            .order_by("-created_at")[:50]
        )

        results = []
        for q in items:
            log_status = q.log.status if hasattr(q, "log") and q.log else q.status
            results.append({
                "id": str(q.id),
                "channel": q.provider.provider_type if q.provider else "UNKNOWN",
                "provider_name": q.provider.name if q.provider else "Default",
                "template_name": q.template.name if q.template else "Direct",
                "recipient": q.recipient,
                "subject": q.rendered_subject,
                "body": q.rendered_body,
                "status": log_status,
                "error_message": q.last_error or (q.log.error_message if hasattr(q, "log") and q.log else ""),
                "sent_at": q.sent_at.isoformat() if q.sent_at else None,
                "created_at": q.created_at.isoformat(),
            })

        return Response({"results": results}, status=status.HTTP_200_OK)

