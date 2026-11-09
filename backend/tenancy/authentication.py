from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from tenancy.models import OrganizationMembership

DEALER_ALLOWED_PREFIXES = ("/api/v1/dealer-portal/", "/api/v1/auth/")


class TenantJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        authentication_result = super().authenticate(request)

        if authentication_result is None:
            return None

        user, validated_token = authentication_result

        organization_id = validated_token.get("organization_id")

        if not organization_id:
            raise AuthenticationFailed(
                "Tenant context is missing from the access token."
            )

        try:
            membership = (
                OrganizationMembership.objects
                .select_related("organization")
                .get(
                    user=user,
                    organization_id=organization_id,
                    organization__is_active=True,
                    is_active=True,
                )
            )
        except OrganizationMembership.DoesNotExist:
            raise AuthenticationFailed(
                "Active tenant membership is no longer valid."
            )

        # Dealer tokens work only on the dealer portal and session endpoints,
        # even for views that only check IsAuthenticated.
        if membership.role == OrganizationMembership.Role.DEALER and not request.path.startswith(
            DEALER_ALLOWED_PREFIXES
        ):
            raise PermissionDenied("Dealer accounts can only use the dealer portal.")

        request.organization = membership.organization
        request.organization_membership = membership
        request.organization_role = membership.role

        return user, validated_token