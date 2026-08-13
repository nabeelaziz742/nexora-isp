from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from tenancy.models import OrganizationMembership


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

        request.organization = membership.organization
        request.organization_membership = membership
        request.organization_role = membership.role

        return user, validated_token