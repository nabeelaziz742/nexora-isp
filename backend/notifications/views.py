from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import NotificationJob
from notifications.serializers import (
    MarkNotificationFailedSerializer,
    MarkNotificationSentSerializer,
    NotificationJobQueueSerializer,
    NotificationJobSerializer,
    NotificationSummarySerializer,
    StartNotificationProcessingSerializer,
)
from notifications.services import (
    NotificationDomainError,
    mark_notification_failed,
    mark_notification_sent,
    queue_customer_notification,
    start_notification_processing,
)
from tenancy.permissions import (
    HasActiveTenantContext,
    IsOrganizationStaffOrOwner,
)


class NotificationPermissionAPIView(APIView):
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]


class NotificationJobListCreateAPIView(
    NotificationPermissionAPIView
):
    def get_queryset(self):
        return (
            NotificationJob.objects
            .for_organization(self.request.organization)
            .select_related(
                "customer",
                "service_account",
            )
        )

    def get(self, request):
        queryset = self.get_queryset()

        notification_status = request.query_params.get(
            "status",
            "",
        ).strip()

        channel = request.query_params.get(
            "channel",
            "",
        ).strip()

        event_type = request.query_params.get(
            "event_type",
            "",
        ).strip()

        customer_id = request.query_params.get(
            "customer_id",
            "",
        ).strip()

        service_account_id = request.query_params.get(
            "service_account_id",
            "",
        ).strip()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if notification_status:
            queryset = queryset.filter(
                status=notification_status,
            )

        if channel:
            queryset = queryset.filter(
                channel=channel,
            )

        if event_type:
            queryset = queryset.filter(
                event_type=event_type,
            )

        if customer_id:
            queryset = queryset.filter(
                customer_id=customer_id,
            )

        if service_account_id:
            queryset = queryset.filter(
                service_account_id=service_account_id,
            )

        if search:
            queryset = queryset.filter(
                Q(recipient__icontains=search)
                | Q(event_type__icontains=search)
                | Q(
                    customer__customer_number__icontains=search
                )
                | Q(
                    customer__first_name__icontains=search
                )
                | Q(
                    customer__last_name__icontains=search
                )
                | Q(
                    service_account__service_number__icontains=search
                )
                | Q(provider_name__icontains=search)
                | Q(provider_message_id__icontains=search)
            )

        serializer = NotificationJobSerializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = NotificationJobQueueSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        try:
            result = queue_customer_notification(
                organization=request.organization,
                customer_id=validated_data["customer_id"],
                service_account_id=validated_data.get(
                    "service_account_id"
                ),
                channel=validated_data["channel"],
                event_type=validated_data["event_type"],
                subject=validated_data.get("subject", ""),
                message=validated_data["message"],
                context=validated_data.get("context", {}),
                actor=request.user,
            )
        except NotificationDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_serializer = NotificationJobSerializer(
            result.notification_job,
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class NotificationJobDetailAPIView(
    NotificationPermissionAPIView
):
    def get(self, request, notification_job_id):
        try:
            notification_job = (
                NotificationJob.objects
                .for_organization(request.organization)
                .select_related(
                    "customer",
                    "service_account",
                )
                .get(id=notification_job_id)
            )
        except NotificationJob.DoesNotExist:
            return Response(
                {
                    "detail": "Notification job not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = NotificationJobSerializer(
            notification_job,
        )

        return Response(serializer.data)


class NotificationJobStartProcessingAPIView(
    NotificationPermissionAPIView
):
    def post(self, request, notification_job_id):
        serializer = StartNotificationProcessingSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = start_notification_processing(
                organization=request.organization,
                notification_job_id=notification_job_id,
                provider_name=serializer.validated_data[
                    "provider_name"
                ],
                actor=request.user,
            )
        except NotificationDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            NotificationJobSerializer(
                result.notification_job
            ).data
        )


class NotificationJobMarkSentAPIView(
    NotificationPermissionAPIView
):
    def post(self, request, notification_job_id):
        serializer = MarkNotificationSentSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = mark_notification_sent(
                organization=request.organization,
                notification_job_id=notification_job_id,
                provider_message_id=serializer.validated_data[
                    "provider_message_id"
                ],
                actor=request.user,
            )
        except NotificationDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            NotificationJobSerializer(
                result.notification_job
            ).data
        )


class NotificationJobMarkFailedAPIView(
    NotificationPermissionAPIView
):
    def post(self, request, notification_job_id):
        serializer = MarkNotificationFailedSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = mark_notification_failed(
                organization=request.organization,
                notification_job_id=notification_job_id,
                failure_reason=serializer.validated_data[
                    "failure_reason"
                ],
                actor=request.user,
            )
        except NotificationDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            NotificationJobSerializer(
                result.notification_job
            ).data
        )


class NotificationSummaryAPIView(
    NotificationPermissionAPIView
):
    def get(self, request):
        queryset = NotificationJob.objects.for_organization(
            request.organization
        )

        summary = queryset.aggregate(
            total=Count("id"),
            pending=Count(
                "id",
                filter=Q(
                    status=NotificationJob.Status.PENDING,
                ),
            ),
            processing=Count(
                "id",
                filter=Q(
                    status=NotificationJob.Status.PROCESSING,
                ),
            ),
            sent=Count(
                "id",
                filter=Q(
                    status=NotificationJob.Status.SENT,
                ),
            ),
            failed=Count(
                "id",
                filter=Q(
                    status=NotificationJob.Status.FAILED,
                ),
            ),
            cancelled=Count(
                "id",
                filter=Q(
                    status=NotificationJob.Status.CANCELLED,
                ),
            ),
            sms=Count(
                "id",
                filter=Q(
                    channel=NotificationJob.Channel.SMS,
                ),
            ),
            whatsapp=Count(
                "id",
                filter=Q(
                    channel=NotificationJob.Channel.WHATSAPP,
                ),
            ),
        )

        serializer = NotificationSummarySerializer(summary)

        return Response(serializer.data)