from rest_framework import serializers

from customers.models import Area
from tenancy.models import OrganizationMembership, StaffProfile


class StaffProfileNestedSerializer(serializers.ModelSerializer):
    assigned_area_name = serializers.CharField(
        source="assigned_area.name",
        read_only=True,
        default=None,
    )
    supervisor_name = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = [
            "id",
            "staff_code",
            "phone",
            "alternate_phone",
            "cnic",
            "department",
            "designation",
            "role",
            "assigned_area",
            "assigned_area_name",
            "supervisor",
            "supervisor_name",
            "joining_date",
            "status",
            "notes",
        ]

    def get_supervisor_name(self, obj):
        if obj.supervisor and obj.supervisor.user:
            return obj.supervisor.user.get_full_name() or obj.supervisor.user.email
        return None


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
    staff_code = serializers.SerializerMethodField()
    operational_role = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    alternate_phone = serializers.SerializerMethodField()
    cnic = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    designation = serializers.SerializerMethodField()
    assigned_area_id = serializers.SerializerMethodField()
    assigned_area_name = serializers.SerializerMethodField()
    joining_date = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

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
            "operational_role",
            "staff_code",
            "status",
            "phone",
            "alternate_phone",
            "cnic",
            "department",
            "designation",
            "assigned_area_id",
            "assigned_area_name",
            "joining_date",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def _get_profile(self, obj):
        return getattr(obj, "profile", None) or StaffProfile.objects.filter(membership=obj).first()

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_staff_code(self, obj):
        p = self._get_profile(obj)
        return p.staff_code if p else ""

    def get_operational_role(self, obj):
        p = self._get_profile(obj)
        return p.role if p else obj.role

    def get_status(self, obj):
        p = self._get_profile(obj)
        if p:
            return p.status
        return StaffProfile.Status.ACTIVE if obj.is_active else StaffProfile.Status.INACTIVE

    def get_phone(self, obj):
        p = self._get_profile(obj)
        return p.phone if p else ""

    def get_alternate_phone(self, obj):
        p = self._get_profile(obj)
        return p.alternate_phone if p else ""

    def get_cnic(self, obj):
        p = self._get_profile(obj)
        return p.cnic if p else ""

    def get_department(self, obj):
        p = self._get_profile(obj)
        return p.department if p else ""

    def get_designation(self, obj):
        p = self._get_profile(obj)
        return p.designation if p else ""

    def get_assigned_area_id(self, obj):
        p = self._get_profile(obj)
        return str(p.assigned_area_id) if p and p.assigned_area_id else None

    def get_assigned_area_name(self, obj):
        p = self._get_profile(obj)
        return p.assigned_area.name if p and p.assigned_area else None

    def get_joining_date(self, obj):
        p = self._get_profile(obj)
        return p.joining_date.isoformat() if p and p.joining_date else None

    def get_notes(self, obj):
        p = self._get_profile(obj)
        return p.notes if p else ""


class CreateOrganizationStaffSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(
        min_length=8,
        write_only=True,
        trim_whitespace=False,
    )
    role = serializers.ChoiceField(
        choices=StaffProfile.Role.choices,
        default=StaffProfile.Role.STAFF,
    )
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    alternate_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    cnic = serializers.CharField(max_length=30, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    designation = serializers.CharField(max_length=100, required=False, allow_blank=True)
    assigned_area_id = serializers.UUIDField(required=False, allow_null=True)
    supervisor_id = serializers.UUIDField(required=False, allow_null=True)
    joining_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class UpdateOrganizationStaffSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    role = serializers.ChoiceField(choices=StaffProfile.Role.choices, required=False)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    alternate_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    cnic = serializers.CharField(max_length=30, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    designation = serializers.CharField(max_length=100, required=False, allow_blank=True)
    assigned_area_id = serializers.UUIDField(required=False, allow_null=True)
    supervisor_id = serializers.UUIDField(required=False, allow_null=True)
    joining_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class StaffActiveStateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class StaffStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StaffProfile.Status.choices)