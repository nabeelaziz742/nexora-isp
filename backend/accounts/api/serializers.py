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

        self.user = user
        self.membership = membership

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


class TenantTokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)

    def validate(self, attrs):
        refresh_str = attrs.get("refresh")
        if not refresh_str:
            raise serializers.ValidationError({"refresh": "This field is required."})

        try:
            refresh_token = RefreshToken(refresh_str)
        except Exception as exc:
            raise serializers.ValidationError({"detail": "Invalid or expired refresh token."}) from exc

        user_id = refresh_token.payload.get("user_id")
        organization_id = refresh_token.payload.get("organization_id")

        if not user_id or not organization_id:
            raise serializers.ValidationError({"detail": "Refresh token lacks required tenant context."})

        try:
            membership = (
                OrganizationMembership.objects
                .select_related("organization", "user")
                .get(
                    user_id=user_id,
                    organization_id=organization_id,
                    is_active=True,
                    organization__is_active=True,
                    user__is_active=True,
                )
            )
        except OrganizationMembership.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "Active organization membership is no longer valid."}
            )

        from tenancy.models import StaffProfile
        if membership.role == OrganizationMembership.Role.OWNER:
            effective_role = StaffProfile.Role.OWNER
        else:
            profile = StaffProfile.objects.filter(membership=membership).first()
            if profile and profile.role:
                effective_role = profile.role
            elif membership.role == OrganizationMembership.Role.TECHNICIAN:
                effective_role = StaffProfile.Role.TECHNICIAN
            else:
                effective_role = StaffProfile.Role.STAFF

        # Blacklist old refresh token and rotate
        try:
            refresh_token.blacklist()
        except AttributeError:
            pass

        # Generate fresh token pair with authoritative database-verified claims
        new_refresh = RefreshToken.for_user(membership.user)
        new_refresh["organization_id"] = str(membership.organization_id)
        new_refresh["organization_code"] = membership.organization.code
        new_refresh["role"] = effective_role

        self.user = membership.user
        self.membership = membership
        self.effective_role = effective_role

        return {
            "access": str(new_refresh.access_token),
            "refresh": str(new_refresh),
            "role": effective_role,
            "organization": {
                "id": str(membership.organization.id),
                "name": membership.organization.name,
                "code": membership.organization.code,
            },
            "user": {
                "id": str(membership.user.id),
                "email": membership.user.email,
                "first_name": membership.user.first_name,
                "last_name": membership.user.last_name,
            },
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate(self, attrs):
        refresh_str = attrs.get("refresh")
        if not refresh_str:
            raise serializers.ValidationError({"refresh": "This field is required."})
        return attrs

    def save(self, **kwargs):
        refresh_str = self.validated_data.get("refresh")
        try:
            token = RefreshToken(refresh_str)
            token.blacklist()
        except Exception:
            # Idempotent: already blacklisted, expired, or malformed
            pass