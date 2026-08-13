from rest_framework import serializers

from tenancy.models import OrganizationMembership


class OrganizationStaffSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(
        source="user.id",
        read_only=True,
    )

    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    first_name = serializers.CharField(
        source="user.first_name",
        read_only=True,
    )

    last_name = serializers.CharField(
        source="user.last_name",
        read_only=True,
    )

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMembership

        fields = [
            "id",
            "user_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class CreateOrganizationStaffSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        max_length=150,
    )

    last_name = serializers.CharField(
        max_length=150,
    )

    email = serializers.EmailField()

    password = serializers.CharField(
        min_length=8,
        write_only=True,
        trim_whitespace=False,
    )

    role = serializers.ChoiceField(
        choices=[
            OrganizationMembership.Role.STAFF,
            OrganizationMembership.Role.TECHNICIAN,
        ]
    )


class UpdateOrganizationStaffSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        max_length=150,
        required=False,
    )

    last_name = serializers.CharField(
        max_length=150,
        required=False,
    )

    role = serializers.ChoiceField(
        choices=[
            OrganizationMembership.Role.STAFF,
            OrganizationMembership.Role.TECHNICIAN,
        ],
        required=False,
    )


class StaffActiveStateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()