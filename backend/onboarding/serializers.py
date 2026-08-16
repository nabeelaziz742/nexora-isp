from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from onboarding.models import ISPRegistration, PaymentSettings


User = get_user_model()


class ISPRegistrationSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=150, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value


class ReceiptUploadSerializer(serializers.Serializer):
    receipt = serializers.ImageField()


class RejectRegistrationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class PaymentSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSettings
        fields = (
            "id",
            "bank_name",
            "account_title",
            "account_number",
            "iban",
            "amount",
            "instructions",
            "is_active",
        )
        read_only_fields = ("id",)


class RegistrationListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="organization.name", read_only=True)
    organization_code = serializers.CharField(source="organization.code", read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_name = serializers.SerializerMethodField()
    receipt_url = serializers.SerializerMethodField()

    class Meta:
        model = ISPRegistration
        fields = (
            "id",
            "company_name",
            "organization_code",
            "owner_email",
            "owner_name",
            "amount_due",
            "status",
            "receipt_url",
            "rejection_reason",
            "submitted_at",
            "verified_at",
            "created_at",
        )

    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}".strip()

    def get_receipt_url(self, obj):
        if not obj.receipt:
            return None
        request = self.context.get("request")
        url = obj.receipt.url
        return request.build_absolute_uri(url) if request else url
