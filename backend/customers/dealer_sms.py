"""Dealer portal SMS templates, single SMS, broadcast queue, log & cancellation."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from communications.models import CommunicationProvider, CommunicationQueue
from customers.dealer_portal import DealerPortalView, _dealer_services
from customers.models import Customer, DealerSmsTemplate, ServiceAccount
from customers.suspension_services import calculate_service_outstanding
from tenancy.services import record_audit_log

MAX_BROADCAST_RECIPIENTS = 500
NO_GATEWAY_BANNER = "SMS will be delivered once the ISP connects an SMS gateway"


def _active_sms_provider(organization) -> CommunicationProvider | None:
    return (
        CommunicationProvider.objects.filter(
            organization=organization,
            provider_type=CommunicationProvider.ProviderType.SMS,
            status=CommunicationProvider.Status.ACTIVE,
            is_connected=True,
        )
        .order_by("-is_default", "name")
        .first()
    )


def _render_sms_body(template_body: str, service: ServiceAccount, outstanding: Decimal | None = None) -> str:
    customer = service.customer
    text = template_body
    replacements = {
        "{name}": customer.full_name,
        "{phone}": customer.phone or "",
        "{package}": service.internet_package.name if service.internet_package_id else "",
        "{amount}": str(service.internet_package.monthly_price) if service.internet_package_id else "",
        "{expiry}": service.expiry_date.isoformat() if service.expiry_date else "",
        "{due}": str(outstanding) if outstanding is not None else "",
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text.strip()


def _template_row(tpl: DealerSmsTemplate) -> dict:
    return {
        "id": str(tpl.id),
        "name": tpl.name,
        "body": tpl.body,
        "is_active": tpl.is_active,
        "created_at": tpl.created_at.isoformat(),
        "updated_at": tpl.updated_at.isoformat(),
    }


def _queue_row(item: CommunicationQueue, can_cancel_right: bool) -> dict:
    return {
        "id": str(item.id),
        "customer_id": str(item.customer_id),
        "customer_name": item.customer.full_name,
        "recipient": item.recipient,
        "template_name": item.dealer_template.name if item.dealer_template_id else item.rendered_subject or "Custom SMS",
        "message": item.rendered_body,
        "status": item.status,
        "can_cancel": bool(can_cancel_right and item.status == CommunicationQueue.Status.PENDING),
        "error_message": item.last_error or item.error_message,
        "created_at": item.created_at.isoformat(),
        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
    }


# ---------------------------------------------------------------------------
# SMS Templates
# ---------------------------------------------------------------------------

class DealerSmsTemplateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    body = serializers.CharField(max_length=1000)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Template name is required.")
        return cleaned

    def validate_body(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Message body is required.")
        return cleaned


class DealerSmsTemplateListCreateView(DealerPortalView):
    required_rights = ("can_manage_sms_templates",)

    def get(self, request):
        templates = DealerSmsTemplate.objects.for_organization(request.organization).filter(dealer=request.dealer)
        return Response({"results": [_template_row(tpl) for tpl in templates]})

    @transaction.atomic
    def post(self, request):
        serializer = DealerSmsTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if DealerSmsTemplate.objects.for_organization(request.organization).filter(
            dealer=request.dealer, name__iexact=data["name"],
        ).exists():
            raise ValidationError({"name": "An SMS template with this name already exists."})
        tpl = DealerSmsTemplate.objects.create(
            organization=request.organization,
            dealer=request.dealer,
            name=data["name"],
            body=data["body"],
            is_active=data["is_active"],
            created_by=request.user,
        )
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_SMS_TEMPLATE_CREATED",
            resource_type="DealerSmsTemplate",
            resource_id=str(tpl.id),
            metadata={"dealer_code": request.dealer.dealer_code, "name": tpl.name},
        )
        return Response(_template_row(tpl), status=status.HTTP_201_CREATED)


class DealerSmsTemplateDetailView(DealerPortalView):
    required_rights = ("can_manage_sms_templates",)

    def _get(self, request, template_id) -> DealerSmsTemplate:
        tpl = (
            DealerSmsTemplate.objects.for_organization(request.organization)
            .filter(id=template_id, dealer=request.dealer)
            .first()
        )
        if tpl is None:
            raise NotFound("SMS template was not found.")
        return tpl

    def patch(self, request, template_id):
        tpl = self._get(request, template_id)
        serializer = DealerSmsTemplateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "name" in data:
            if (
                DealerSmsTemplate.objects.for_organization(request.organization)
                .filter(dealer=request.dealer, name__iexact=data["name"])
                .exclude(pk=tpl.pk)
                .exists()
            ):
                raise ValidationError({"name": "An SMS template with this name already exists."})
            tpl.name = data["name"]
        if "body" in data:
            tpl.body = data["body"]
        if "is_active" in data:
            tpl.is_active = data["is_active"]
        tpl.save()
        return Response(_template_row(tpl))

    def delete(self, request, template_id):
        # Soft-deactivate rather than hard deleting so queue history stays intact.
        tpl = self._get(request, template_id)
        tpl.is_active = False
        tpl.save(update_fields=["is_active", "updated_at"])
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_SMS_TEMPLATE_DEACTIVATED",
            resource_type="DealerSmsTemplate",
            resource_id=str(tpl.id),
            metadata={"dealer_code": request.dealer.dealer_code, "name": tpl.name},
        )
        return Response(_template_row(tpl))


# ---------------------------------------------------------------------------
# Send 1 SMS / Broadcast / Log / Cancel
# ---------------------------------------------------------------------------

def _resolve_template_and_text(request, template_id, message: str) -> tuple[DealerSmsTemplate | None, str]:
    template = None
    if template_id is not None:
        template = (
            DealerSmsTemplate.objects.for_organization(request.organization)
            .filter(id=template_id, dealer=request.dealer, is_active=True)
            .first()
        )
        if template is None:
            raise NotFound("Active SMS template was not found.")
    text = (message or "").strip()
    if not text and template is not None:
        text = template.body.strip()
    if not text:
        raise ValidationError({"message": "Enter a message or pick a template."})
    return template, text


class DealerSmsOptionsView(DealerPortalView):
    required_rights = ("can_send_sms", "can_broadcast_sms", "can_view_sms_log")

    def get(self, request):
        provider = _active_sms_provider(request.organization)
        templates = (
            DealerSmsTemplate.objects.for_organization(request.organization)
            .filter(dealer=request.dealer, is_active=True)
            .order_by("name")
        )
        services = list(_dealer_services(request).order_by("customer__first_name", "service_number")[:500])
        return Response({
            "gateway_connected": provider is not None,
            "banner": "" if provider is not None else NO_GATEWAY_BANNER,
            "templates": [_template_row(t) for t in templates],
            "customers": [
                {
                    "customer_id": str(svc.customer_id),
                    "service_id": str(svc.id),
                    "customer_name": svc.customer.full_name,
                    "service_number": svc.service_number,
                    "phone": svc.customer.phone,
                }
                for svc in services
                if svc.customer.phone
            ],
        })


class DealerSmsSendSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    template_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    message = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class DealerSmsSendView(DealerPortalView):
    required_rights = ("can_send_sms",)

    @transaction.atomic
    def post(self, request):
        serializer = DealerSmsSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        svc_qs = _dealer_services(request).filter(customer_id=data["customer_id"]).order_by("service_number")
        service = svc_qs.first()
        if service is None:
            raise NotFound("Customer was not found for your account.")
        customer = service.customer
        if not customer.phone:
            raise ValidationError({"detail": "This customer does not have a phone number."})

        template, raw_body = _resolve_template_and_text(request, data.get("template_id"), data["message"])
        outstanding = calculate_service_outstanding(service)[0]
        rendered = _render_sms_body(raw_body, service, outstanding=outstanding)
        provider = _active_sms_provider(request.organization)

        queue = CommunicationQueue.objects.create(
            organization=request.organization,
            customer=customer,
            dealer=request.dealer,
            template=None,
            dealer_template=template,
            provider=provider,
            recipient=customer.phone,
            payload={
                "channel": "SMS",
                "dealer_id": str(request.dealer.id),
                "sent_by_id": str(request.user.id),
                "gateway_connected": provider is not None,
            },
            rendered_subject=template.name if template else "Dealer SMS",
            rendered_body=rendered,
            status=CommunicationQueue.Status.PENDING,
            scheduled_at=timezone.now(),
        )
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_SMS_QUEUED",
            resource_type="CommunicationQueue",
            resource_id=str(queue.id),
            metadata={
                "dealer_code": request.dealer.dealer_code,
                "customer_number": customer.customer_number,
                "recipient": customer.phone,
                "gateway_connected": provider is not None,
            },
        )
        can_cancel = request.dealer_employee is None or request.dealer_employee.can_cancel_sms
        return Response(
            {
                "queued": 1,
                "gateway_connected": provider is not None,
                "banner": "" if provider is not None else NO_GATEWAY_BANNER,
                "entry": _queue_row(queue, can_cancel),
            },
            status=status.HTTP_201_CREATED,
        )


class DealerSmsBroadcastSerializer(serializers.Serializer):
    audience = serializers.ChoiceField(choices=["ALL", "DUE", "EXPIRING"])
    template_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    message = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class DealerSmsBroadcastView(DealerPortalView):
    required_rights = ("can_broadcast_sms",)

    @transaction.atomic
    def post(self, request):
        serializer = DealerSmsBroadcastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template, raw_body = _resolve_template_and_text(request, data.get("template_id"), data["message"])
        audience = data["audience"]
        today = timezone.localdate()

        services = list(_dealer_services(request).order_by("customer__first_name", "service_number"))
        matched: list[tuple[ServiceAccount, Decimal]] = []
        seen_customer_ids = set()
        for svc in services:
            cust = svc.customer
            if not cust.phone or cust.id in seen_customer_ids:
                continue
            outstanding = calculate_service_outstanding(svc)[0]
            if audience == "DUE" and outstanding <= Decimal("0.00"):
                continue
            if audience == "EXPIRING" and not (svc.expiry_date and (svc.expiry_date - today).days <= 3):
                continue
            seen_customer_ids.add(cust.id)
            matched.append((svc, outstanding))

        if not matched:
            raise ValidationError({"detail": "No customers with phone numbers matched this filter."})
        if len(matched) > MAX_BROADCAST_RECIPIENTS:
            raise ValidationError({
                "detail": f"Broadcast is limited to {MAX_BROADCAST_RECIPIENTS} customers at a time ({len(matched)} matched).",
            })

        provider = _active_sms_provider(request.organization)
        now = timezone.now()
        for svc, outstanding in matched:
            rendered = _render_sms_body(raw_body, svc, outstanding=outstanding)
            CommunicationQueue.objects.create(
                organization=request.organization,
                customer=svc.customer,
                dealer=request.dealer,
                template=None,
                dealer_template=template,
                provider=provider,
                recipient=svc.customer.phone,
                payload={
                    "channel": "SMS",
                    "audience": audience,
                    "dealer_id": str(request.dealer.id),
                    "sent_by_id": str(request.user.id),
                    "gateway_connected": provider is not None,
                },
                rendered_subject=template.name if template else f"Broadcast ({audience})",
                rendered_body=rendered,
                status=CommunicationQueue.Status.PENDING,
                scheduled_at=now,
            )

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_SMS_BROADCAST",
            resource_type="Dealer",
            resource_id=str(request.dealer.id),
            metadata={
                "dealer_code": request.dealer.dealer_code,
                "audience": audience,
                "queued": len(matched),
                "gateway_connected": provider is not None,
            },
        )
        return Response(
            {
                "queued": len(matched),
                "audience": audience,
                "gateway_connected": provider is not None,
                "banner": "" if provider is not None else NO_GATEWAY_BANNER,
            },
            status=status.HTTP_201_CREATED,
        )


class DealerSmsLogView(DealerPortalView):
    required_rights = ("can_view_sms_log",)

    def get(self, request):
        employee = request.dealer_employee
        qs = (
            CommunicationQueue.objects.filter(
                organization=request.organization,
                dealer=request.dealer,
            )
            .select_related("customer", "dealer_template")
            .order_by("-created_at")
        )
        if employee is not None and not employee.can_view_all_customers:
            qs = qs.filter(customer__assigned_dealer_employee=employee)

        status_filter = request.query_params.get("status", "").strip().upper()
        if status_filter:
            qs = qs.filter(status=status_filter)

        provider = _active_sms_provider(request.organization)
        can_cancel = employee is None or employee.can_cancel_sms
        return Response({
            "gateway_connected": provider is not None,
            "banner": "" if provider is not None else NO_GATEWAY_BANNER,
            "results": [_queue_row(item, can_cancel) for item in qs[:300]],
        })


class DealerSmsCancelView(DealerPortalView):
    required_rights = ("can_cancel_sms",)

    @transaction.atomic
    def post(self, request, queue_id):
        qs = CommunicationQueue.objects.filter(
            id=queue_id,
            organization=request.organization,
            dealer=request.dealer,
        ).select_related("customer", "dealer_template")
        employee = request.dealer_employee
        if employee is not None and not employee.can_view_all_customers:
            qs = qs.filter(customer__assigned_dealer_employee=employee)
        item = qs.first()
        if item is None:
            raise NotFound("SMS queue item was not found.")
        if item.status != CommunicationQueue.Status.PENDING:
            raise ValidationError({"detail": "Only pending SMS messages can be cancelled."})

        item.status = CommunicationQueue.Status.CANCELLED
        item.save(update_fields=["status", "updated_at"])
        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_SMS_CANCELLED",
            resource_type="CommunicationQueue",
            resource_id=str(item.id),
            metadata={"dealer_code": request.dealer.dealer_code, "recipient": item.recipient},
        )
        return Response(_queue_row(item, can_cancel_right=True))
