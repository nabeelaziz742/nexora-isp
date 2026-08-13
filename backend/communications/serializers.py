from rest_framework import serializers
import re


from .models import (
    CommunicationAutomation,
    CommunicationLog,
    CommunicationProvider,
    CommunicationQueue,
    CommunicationSchedule,
    CommunicationTemplate,
)


class CommunicationProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationProvider
        fields = [
            "id",
            "name",
            "provider_type",
            "status",
            "business_id",
            "phone_number_id",
            "access_token",
            "webhook_verify_token",
            "api_url",
            "sender_id",
            "is_default",
            "is_connected",
            "last_health_check",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "is_connected",
            "last_health_check",
            "created_at",
            "updated_at",
        ]


class CommunicationTemplateSerializer(serializers.ModelSerializer):
    communication_provider_name = serializers.CharField(
        source="communication_provider.name",
        read_only=True,
    )

    communication_provider_type = serializers.CharField(
        source="communication_provider.provider_type",
        read_only=True,
    )

    VARIABLE_REGEX = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

    class Meta:
        model = CommunicationTemplate
        fields = [
            "id",
            "organization",
            "name",
            "subject",
            "body",
            "variables",
            "status",
            "communication_provider",
            "communication_provider_name",
            "communication_provider_type",
            "created_at",
            "updated_at",
        ]

        read_only_fields = (
            "organization",
            "variables",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        organization = self.context["request"].organization

        queryset = CommunicationTemplate.objects.filter(
            organization=organization,
            name__iexact=value.strip(),
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A template with this name already exists."
            )

        return value.strip()

    def validate(self, attrs):
        body = attrs.get(
            "body",
            getattr(self.instance, "body", ""),
        )

        variables = sorted(
            set(self.VARIABLE_REGEX.findall(body))
        )

        attrs["variables"] = variables

        return attrs


class CommunicationAutomationSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(
        source="template.name",
        read_only=True,
    )

    provider_name = serializers.CharField(
        source="template.communication_provider.name",
        read_only=True,
    )

    class Meta:
        model = CommunicationAutomation
        fields = [
            "id",
            "organization",
            "name",
            "description",
            "trigger",
            "template",
            "template_name",
            "provider_name",
            "execution_order",
            "delay_minutes",
            "max_retry_attempts",
            "is_enabled",
            "last_executed_at",
            "last_execution_status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "organization",
            "last_executed_at",
            "last_execution_status",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        organization = self.context["request"].organization

        queryset = CommunicationAutomation.objects.filter(
            organization=organization,
            name__iexact=value.strip(),
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "An automation with this name already exists."
            )

        return value.strip()

    def validate_template(self, value):
        organization = self.context["request"].organization

        if value.organization_id != organization.id:
            raise serializers.ValidationError(
                "Invalid template."
            )

        return value

    def validate_delay_minutes(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Delay cannot be negative."
            )

        return value

    def validate_max_retry_attempts(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Retry count cannot be negative."
            )

        if value > 10:
            raise serializers.ValidationError(
                "Maximum retry attempts is 10."
            )

        return value


class CommunicationScheduleSerializer(serializers.ModelSerializer):
    automation_name = serializers.CharField(
        source="automation.name",
        read_only=True,
    )

    trigger = serializers.CharField(
        source="automation.trigger",
        read_only=True,
    )

    provider_name = serializers.CharField(
        source="automation.template.communication_provider.name",
        read_only=True,
    )

    class Meta:
        model = CommunicationSchedule
        fields = [
            "id",
            "organization",
            "automation",
            "automation_name",
            "trigger",
            "provider_name",
            "frequency",
            "next_run",
            "last_run",
            "is_enabled",
            "created_at",
            "updated_at",
        ]


class CommunicationQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationQueue
        fields = "__all__"


class CommunicationLogSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="queue.customer.full_name",
        read_only=True,
    )

    template_name = serializers.CharField(
        source="queue.template.name",
        read_only=True,
    )

    communication_provider_name = serializers.CharField(
        source="queue.provider.name",
        read_only=True,
    )

    is_connected = serializers.BooleanField(
        source="queue.provider.is_connected",
        read_only=True,
    )
    
    subject = serializers.CharField(
    read_only=True,
    )

    message = serializers.CharField(
    read_only=True,
    )

    retry_count = serializers.IntegerField(
    read_only=True,
    )

    last_retry_at = serializers.DateTimeField(
    read_only=True,
    )

    class Meta:
        model = CommunicationLog
        fields = [
            "id",
            "customer_name",
            "template_name",
            "communication_provider_name",
            "is_connected",
            "recipient",
            "subject",
            "message",
            "status",
            "provider_response",
            "provider_response_code",
            "error_message",
            "retry_count",
            "delivered_at",
            "created_at",
        ]


class BroadcastSerializer(serializers.Serializer):
    provider_id = serializers.UUIDField()

    template_id = serializers.UUIDField()

    audience = serializers.ChoiceField(
        choices=[
            "ALL_CUSTOMERS",
            "AREA",
            "PACKAGE",
            "SELECTED_CUSTOMERS",
        ]
    )

    area_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    package_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    customer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )

    title = serializers.CharField()

    message = serializers.CharField()

    schedule_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )