import secrets
import string

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from onboarding.models import ISPRegistration, PaymentSettings
from tenancy.models import Organization, OrganizationMembership


User = get_user_model()


def generate_organization_code(company_name):
    prefix = "".join(ch for ch in company_name.upper() if ch.isalnum())[:6] or "ISP"
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        suffix = "".join(secrets.choice(alphabet) for _ in range(4))
        code = f"{prefix}-{suffix}"
        if not Organization.objects.filter(code=code).exists():
            return code
    raise ValidationError({"detail": "Could not generate a unique organization code."})


def get_or_create_payment_settings():
    settings = PaymentSettings.objects.filter(is_active=True).order_by("-updated_at").first()
    if settings is None:
        settings = PaymentSettings.objects.create(
            bank_name="HBL",
            account_title="Muhammad Nabeel",
            account_number="17877900894403",
            iban="",
            amount=5000.00,
            instructions="Please deposit the ISP registration setup fee to the designated account and upload your payment receipt.",
            is_active=True,
        )
    return settings


@transaction.atomic
def create_registration(*, validated_data):
    settings = get_or_create_payment_settings()

    company_name = validated_data["company_name"].strip()
    email = validated_data["email"].lower()

    organization = Organization.objects.create(
        name=company_name,
        code=generate_organization_code(company_name),
        city=validated_data.get("city", "").strip(),
        is_active=False,
    )

    owner = User.objects.create_user(
        username=email,
        email=email,
        password=validated_data["password"],
        first_name=validated_data["first_name"].strip(),
        last_name=validated_data.get("last_name", "").strip(),
        is_active=False,
        email_verified=False,
    )

    OrganizationMembership.objects.create(
        organization=organization,
        user=owner,
        role=OrganizationMembership.Role.OWNER,
        is_active=False,
    )

    registration = ISPRegistration.objects.create(
        organization=organization,
        owner=owner,
        amount_due=settings.amount,
        status=ISPRegistration.Status.PENDING_PAYMENT,
    )

    return registration, settings


@transaction.atomic
def submit_receipt(*, registration, receipt):
    if registration.status not in {
        ISPRegistration.Status.PENDING_PAYMENT,
        ISPRegistration.Status.REJECTED,
    }:
        raise ValidationError({"detail": "This registration is not accepting a payment receipt."})

    registration.receipt = receipt
    registration.status = ISPRegistration.Status.PENDING_VERIFICATION
    registration.submitted_at = timezone.now()
    registration.rejection_reason = ""
    registration.save(update_fields=["receipt", "status", "submitted_at", "rejection_reason", "updated_at"])
    return registration


@transaction.atomic
def approve_registration(*, registration, admin_user):
    if registration.status != ISPRegistration.Status.PENDING_VERIFICATION:
        raise ValidationError({"detail": "Only pending payment verifications can be approved."})

    registration.status = ISPRegistration.Status.ACTIVE
    registration.verified_at = timezone.now()
    registration.verified_by = admin_user
    registration.save(update_fields=["status", "verified_at", "verified_by", "updated_at"])

    registration.organization.is_active = True
    registration.organization.save(update_fields=["is_active", "updated_at"])

    registration.owner.is_active = True
    registration.owner.email_verified = True
    registration.owner.save(update_fields=["is_active", "email_verified", "updated_at"])

    OrganizationMembership.objects.filter(
        organization=registration.organization,
        user=registration.owner,
        role=OrganizationMembership.Role.OWNER,
    ).update(is_active=True)

    return registration


@transaction.atomic
def reject_registration(*, registration, reason=""):
    if registration.status != ISPRegistration.Status.PENDING_VERIFICATION:
        raise ValidationError({"detail": "Only pending payment verifications can be rejected."})

    registration.status = ISPRegistration.Status.REJECTED
    registration.rejection_reason = reason.strip()
    registration.save(update_fields=["status", "rejection_reason", "updated_at"])
    return registration
