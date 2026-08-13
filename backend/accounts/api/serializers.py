from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from tenancy.models import OrganizationMembership


class TenantLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    organization_code = serializers.CharField(
        max_length=50,
    )

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["password"]
        organization_code = attrs["organization_code"]

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                {
                    "detail": "Invalid email or password.",
                }
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {
                    "detail": "User account is inactive.",
                }
            )

        try:
            membership = (
                OrganizationMembership.objects
                .select_related("organization")
                .get(
                    user=user,
                    organization__code=organization_code,
                    organization__is_active=True,
                    is_active=True,
                )
            )
        except OrganizationMembership.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "No active organization membership "
                        "was found for this user."
                    ),
                }
            )

        refresh = RefreshToken.for_user(user)

        refresh["organization_id"] = str(
            membership.organization_id
        )
        refresh["organization_code"] = (
            membership.organization.code
        )
        refresh["role"] = membership.role

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "organization": {
                "id": str(membership.organization.id),
                "name": membership.organization.name,
                "code": membership.organization.code,
            },
            "role": membership.role,
        }