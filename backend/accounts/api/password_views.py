"""Password management: change your own, and reset a forgotten one by email.

Forgot-password always answers the same way whether or not the email exists,
so it cannot be used to discover accounts.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from tenancy.models import OrganizationMembership
from tenancy.services import record_audit_log

User = get_user_model()
logger = logging.getLogger(__name__)

RESET_REQUEST_MESSAGE = (
    "If an account exists for this email, a password reset link has been sent. "
    "Check your inbox and spam folder."
)


def check_new_password(password: str, user=None) -> None:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False, min_length=8, max_length=128)


class ChangePasswordAPIView(APIView):
    """Any signed-in ISP user (owner, staff, dealer) changes their own password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            raise serializers.ValidationError({"current_password": ["Current password is incorrect."]})
        new_password = serializer.validated_data["new_password"]
        if new_password == serializer.validated_data["current_password"]:
            raise serializers.ValidationError({"new_password": ["Choose a password different from the current one."]})
        check_new_password(new_password, user)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        organization = getattr(request, "organization", None)
        if organization is not None:
            record_audit_log(
                organization=organization,
                actor=user,
                action="USER_PASSWORD_CHANGED",
                resource_type="User",
                resource_id=str(user.id),
                metadata={"email": user.email},
            )
        return Response({"detail": "Password changed."}, status=status.HTTP_200_OK)


def build_reset_link(user) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_BASE_URL}/reset-password?uid={uid}&token={token}"


def send_reset_email(user) -> None:
    link = build_reset_link(user)
    hours = max(1, settings.PASSWORD_RESET_TIMEOUT // 3600)
    send_mail(
        subject="Reset your Nexora ISP password",
        message=(
            f"Hello {user.first_name or ''},\n\n"
            "We received a request to reset your Nexora ISP password. Open this link to choose a new one:\n\n"
            f"{link}\n\n"
            f"The link works once and expires in {hours} hour{'s' if hours != 1 else ''}. "
            "If you did not ask for this, ignore this email; your password stays the same.\n"
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        has_access = user is not None and (
            user.is_superuser
            or OrganizationMembership.objects.filter(
                user=user, is_active=True, organization__is_active=True
            ).exists()
        )
        if has_access:
            try:
                send_reset_email(user)
            except Exception:  # noqa: BLE001 - never reveal delivery problems to the caller
                logger.exception("Password reset email could not be sent to user %s", user.pk)
        return Response({"detail": RESET_REQUEST_MESSAGE}, status=status.HTTP_200_OK)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False, min_length=8, max_length=128)


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        invalid = serializers.ValidationError(
            {"detail": "This reset link is invalid or has expired. Please request a new one."}
        )
        try:
            user_id = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, DjangoValidationError):
            raise invalid from None
        if not default_token_generator.check_token(user, data["token"]):
            raise invalid
        check_new_password(data["new_password"], user)
        # Changing the password also invalidates this token.
        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        membership = (
            OrganizationMembership.objects.filter(user=user, is_active=True)
            .select_related("organization")
            .first()
        )
        if membership is not None:
            record_audit_log(
                organization=membership.organization,
                actor=user,
                action="USER_PASSWORD_RESET_BY_EMAIL",
                resource_type="User",
                resource_id=str(user.id),
                metadata={"email": user.email},
            )
        return Response({"detail": "Password updated. You can sign in now."}, status=status.HTTP_200_OK)
