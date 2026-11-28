"""Short-lived impersonation ('Jump') JWT helpers and Back-to-Home endpoint."""
from datetime import timedelta

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from tenancy.models import OrganizationMembership
from tenancy.permissions import HasActiveTenantContext
from tenancy.services import record_audit_log

JUMP_ACCESS_LIFETIME = timedelta(minutes=30)
JUMP_REFRESH_LIFETIME = timedelta(hours=2)


def issue_jump_tokens(*, target_user, organization, actor_user, jump_kind: str) -> dict:
    """Mint short-lived JWT tokens for viewing another account's portal."""
    impersonator_name = actor_user.get_full_name() or actor_user.email
    refresh = RefreshToken.for_user(target_user)
    refresh.set_exp(lifetime=JUMP_REFRESH_LIFETIME)
    refresh["organization_id"] = str(organization.id)
    refresh["organization_code"] = organization.code
    refresh["role"] = OrganizationMembership.Role.DEALER
    refresh["impersonated_by"] = str(actor_user.id)
    refresh["impersonated_by_name"] = impersonator_name
    refresh["jump_kind"] = jump_kind

    access = refresh.access_token
    access.set_exp(lifetime=JUMP_ACCESS_LIFETIME)

    return {
        "access": str(access),
        "refresh": str(refresh),
        "jump_kind": jump_kind,
        "target_name": target_user.get_full_name() or target_user.email,
        "target_email": target_user.email,
        "impersonated_by": str(actor_user.id),
        "impersonated_by_name": impersonator_name,
        "user": {
            "id": str(target_user.id),
            "email": target_user.email,
            "first_name": target_user.first_name,
            "last_name": target_user.last_name,
        },
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "code": organization.code,
        },
        "role": OrganizationMembership.Role.DEALER,
    }


class JumpBackSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True, default="")


class JumpBackAPIView(APIView):
    """Blacklist the jumped refresh token and audit-log return to the parent session."""

    allow_dealer = True
    permission_classes = [HasActiveTenantContext]

    def post(self, request):
        serializer = JumpBackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_refresh = serializer.validated_data.get("refresh", "").strip()
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass

        auth = getattr(request, "auth", None)
        impersonated_by = auth.get("impersonated_by") if auth else None
        jump_kind = auth.get("jump_kind") if auth else ""
        if impersonated_by or raw_refresh:
            record_audit_log(
                organization=request.organization,
                actor=request.user,
                action="IMPERSONATION_ENDED",
                resource_type="User",
                resource_id=str(request.user.id),
                metadata={
                    "impersonated_by": impersonated_by,
                    "jump_kind": jump_kind,
                },
            )
        return Response({"detail": "Returned to your original account."}, status=status.HTTP_200_OK)
