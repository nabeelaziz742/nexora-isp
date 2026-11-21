from rest_framework import serializers

from customers.models import (
    Area,
    BillingProfile,
    City,
    Country,
    Customer,
    Dealer,
    FeasibilityAssessment,
    Inquiry,
    InternetPackage,
)
from customers.dealer_payout import replace_payout_slabs


class CountrySerializer(serializers.ModelSerializer):
    cities_count = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "code",
            "is_active",
            "cities_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_cities_count(self, obj):
        return getattr(obj, "_cities_count", obj.cities.count())


class CitySerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(
        source="country.name",
        read_only=True,
    )
    areas_count = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = [
            "id",
            "country",
            "country_name",
            "name",
            "code",
            "is_active",
            "areas_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_areas_count(self, obj):
        return getattr(obj, "_areas_count", obj.areas.count())


class AreaSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(
        source="city.name",
        read_only=True,
    )
    country_name = serializers.CharField(
        source="city.country.name",
        read_only=True,
    )

    class Meta:
        model = Area
        fields = [
            "id",
            "city",
            "city_name",
            "country_name",
            "name",
            "code",
            "postal_code",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CustomerActivationSerializer(serializers.Serializer):
    internet_package_id = serializers.UUIDField()
    network_node_id = serializers.UUIDField()
    device_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )

    phone = serializers.CharField(max_length=30)
    alternate_phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )

    email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )

    address_line = serializers.CharField(max_length=255)
    area = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    city = serializers.CharField(max_length=150)

    network_username = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    network_password = serializers.CharField(
        max_length=128,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        write_only=True,
    )
    network_ip_address = serializers.IPAddressField(
        required=False,
        allow_null=True,
    )

    device_assignment_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    billing_day = serializers.IntegerField(
        min_value=1,
        max_value=28,
    )
    due_day = serializers.IntegerField(
        min_value=1,
        max_value=28,
    )
    billing_cycle = serializers.ChoiceField(
        choices=BillingProfile.BillingCycle.choices,
        default=BillingProfile.BillingCycle.MONTHLY,
    )

    sms_enabled = serializers.BooleanField(default=True)
    whatsapp_enabled = serializers.BooleanField(default=True)


class InternetPackageSerializer(serializers.ModelSerializer):
    subscribers_count = serializers.SerializerMethodField()

    class Meta:
        model = InternetPackage
        fields = [
            "id",
            "name",
            "code",
            "description",
            "download_speed_mbps",
            "upload_speed_mbps",
            "monthly_price",
            "router_profile",
            "is_active",
            "subscribers_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_subscribers_count(self, obj):
        return getattr(obj, "_subscribers_count", obj.service_accounts.count())


class InternetPackageCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternetPackage
        fields = [
            "name",
            "code",
            "description",
            "download_speed_mbps",
            "upload_speed_mbps",
            "monthly_price",
            "router_profile",
            "is_active",
        ]

    def validate_monthly_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Monthly price cannot be negative.")
        return value

    def validate_download_speed_mbps(self, value):
        if value <= 0:
            raise serializers.ValidationError("Download speed must be greater than 0.")
        return value

    def validate_upload_speed_mbps(self, value):
        if value <= 0:
            raise serializers.ValidationError("Upload speed must be greater than 0.")
        return value



class CustomerListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    service_number = serializers.SerializerMethodField()
    service_status = serializers.SerializerMethodField()
    package_name = serializers.SerializerMethodField()
    monthly_price = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "customer_number",
            "full_name",
            "phone",
            "email",
            "area",
            "city",
            "is_active",
            "service_number",
            "service_status",
            "package_name",
            "monthly_price",
            "created_at",
        ]

    def _get_primary_service(self, obj):
        cache_attribute = "_customer_list_primary_service"

        if not hasattr(obj, cache_attribute):
            prefetched_services = getattr(
                obj,
                "_prefetched_objects_cache",
                {},
            ).get("service_accounts")

            if prefetched_services is not None:
                service = (
                    prefetched_services[0]
                    if prefetched_services
                    else None
                )
            else:
                service = (
                    obj.service_accounts
                    .select_related("internet_package")
                    .first()
                )

            setattr(
                obj,
                cache_attribute,
                service,
            )

        return getattr(obj, cache_attribute)

    def get_service_number(self, obj):
        service = self._get_primary_service(obj)

        return (
            service.service_number
            if service
            else None
        )

    def get_service_status(self, obj):
        service = self._get_primary_service(obj)

        return (
            service.status
            if service
            else None
        )

    def get_package_name(self, obj):
        service = self._get_primary_service(obj)

        if service is None:
            return None

        return service.internet_package.name

    def get_monthly_price(self, obj):
        service = self._get_primary_service(obj)

        if service is None:
            return None

        return service.internet_package.monthly_price


class CustomerDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    service_accounts = serializers.SerializerMethodField()
    notification_preference = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "customer_number",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "alternate_phone",
            "email",
            "address_line",
            "area",
            "city",
            "cnic",
            "legacy_id",
            "is_active",
            "service_accounts",
            "notification_preference",
            "created_at",
            "updated_at",
        ]

    def get_service_accounts(self, obj):
        services = obj.service_accounts.select_related(
            "internet_package"
        ).all()

        return [
            {
                "id": str(service.id),
                "service_number": service.service_number,
                "status": service.status,
                "activated_at": service.activated_at,
                "expiry_date": service.expiry_date,
                "internet_package": {
                    "id": str(service.internet_package.id),
                    "name": service.internet_package.name,
                    "code": service.internet_package.code,
                    "download_speed_mbps": (
                        service.internet_package.download_speed_mbps
                    ),
                    "upload_speed_mbps": (
                        service.internet_package.upload_speed_mbps
                    ),
                    "monthly_price": (
                        service.internet_package.monthly_price
                    ),
                },
                "network_assignment": (
                    {
                        "id": str(
                            service.network_assignment.id
                        ),
                        "network_node_id": str(
                            service.network_assignment.network_node_id
                        ),
                        "network_node_name": (
                            service.network_assignment.network_node.name
                        ),
                        "network_node_code": (
                            service.network_assignment.network_node.code
                        ),
                        "username": (
                            service.network_assignment.username
                        ),
                        "ip_address": (
                            service.network_assignment.ip_address
                        ),
                        "is_active": (
                            service.network_assignment.is_active
                        ),
                    }
                    if hasattr(service, "network_assignment")
                    else None
                ),
                "device_assignments": [
                    {
                        "id": str(assignment.id),
                        "device_id": str(assignment.device_id),
                        "asset_tag": assignment.device.asset_tag,
                        "device_type": assignment.device.device_type,
                        "device_status": assignment.device.status,
                        "assigned_at": assignment.assigned_at,
                        "returned_at": assignment.returned_at,
                        "return_condition": assignment.return_condition,
                        "is_active": assignment.is_active,
                    }
                    for assignment in service.device_assignments.all()
                ],
                "billing_profile": (
                    {
                        "billing_cycle": (
                            service.billing_profile.billing_cycle
                        ),
                        "billing_day": (
                            service.billing_profile.billing_day
                        ),
                        "due_day": service.billing_profile.due_day,
                        "is_active": (
                            service.billing_profile.is_active
                        ),
                    }
                    if hasattr(service, "billing_profile")
                    else None
                ),
            }
            for service in services
        ]

    def get_notification_preference(self, obj):
        if not hasattr(obj, "notification_preference"):
            return None

        preference = obj.notification_preference

        return {
            "sms_enabled": preference.sms_enabled,
            "whatsapp_enabled": preference.whatsapp_enabled,
        }


class CustomerUpdateSerializer(serializers.ModelSerializer):
    sms_enabled = serializers.BooleanField(required=False)
    whatsapp_enabled = serializers.BooleanField(required=False)

    class Meta:
        model = Customer
        fields = [
            "first_name",
            "last_name",
            "phone",
            "alternate_phone",
            "email",
            "address_line",
            "area",
            "city",
            "cnic",
            "legacy_id",
            "is_active",
            "sms_enabled",
            "whatsapp_enabled",
        ]

    def validate_cnic(self, value):
        digits = "".join(ch for ch in (value or "") if ch.isdigit())
        if not digits:
            return ""
        if len(digits) != 13:
            raise serializers.ValidationError("CNIC must have 13 digits.")
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"

    def validate_phone(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Phone number cannot be blank.")
        organization = self.context.get("organization") or (self.instance.organization if self.instance else None)
        if organization:
            qs = Customer.objects.for_organization(organization).filter(phone=value)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError("A customer with this phone number already exists in this organization.")
        return value

    def update(self, instance, validated_data):
        from customers.models import NotificationPreference

        sms_enabled = validated_data.pop("sms_enabled", None)
        whatsapp_enabled = validated_data.pop("whatsapp_enabled", None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if sms_enabled is not None or whatsapp_enabled is not None:
            pref, _ = NotificationPreference.objects.get_or_create(
                customer=instance,
                defaults={"organization": instance.organization},
            )
            if sms_enabled is not None:
                pref.sms_enabled = sms_enabled
            if whatsapp_enabled is not None:
                pref.whatsapp_enabled = whatsapp_enabled
            pref.save()

        return instance


MAX_PAYOUT_SLABS = 20


class PayoutSlabSerializer(serializers.Serializer):
    min_active_users = serializers.IntegerField(min_value=1, max_value=1_000_000)
    monthly_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class DealerSerializer(serializers.ModelSerializer):
    assigned_area_name = serializers.CharField(
        source="assigned_area.name",
        read_only=True,
        default=None,
    )
    customers_count = serializers.SerializerMethodField()
    # A sub dealer works under parent_dealer; the parent is paid for both.
    parent_dealer = serializers.PrimaryKeyRelatedField(
        queryset=Dealer.objects.all(),
        required=False,
        allow_null=True,
    )
    parent_dealer_name = serializers.CharField(source="parent_dealer.name", read_only=True, default=None)
    parent_dealer_code = serializers.CharField(source="parent_dealer.dealer_code", read_only=True, default=None)
    sub_dealers_count = serializers.SerializerMethodField()
    # Monthly payout table for MONTHLY_SLAB dealers; sending it replaces the whole table.
    payout_slabs = PayoutSlabSerializer(many=True, required=False)

    class Meta:
        model = Dealer
        fields = [
            "id",
            "dealer_code",
            "name",
            "company_name",
            "cnic",
            "phone",
            "alternate_phone",
            "email",
            "address_line",
            "country",
            "city",
            "area",
            "assigned_area",
            "assigned_area_name",
            "commission_rate_percentage",
            "commission_type",
            "payout_slabs",
            "parent_dealer",
            "parent_dealer_name",
            "parent_dealer_code",
            "sub_dealers_count",
            "joining_date",
            "status",
            "notes",
            "customers_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "dealer_code",
            "created_at",
            "updated_at",
        ]

    def get_customers_count(self, obj):
        return getattr(obj, "_customers_count", obj.customers.count())

    def get_sub_dealers_count(self, obj):
        return obj.sub_dealers.count()

    def validate(self, attrs):
        instance = self.instance
        organization = self.context.get("organization") or (instance.organization if instance else None)

        if "parent_dealer" in attrs and attrs["parent_dealer"] is not None:
            parent = attrs["parent_dealer"]
            if organization is None or parent.organization_id != organization.id:
                raise serializers.ValidationError({"parent_dealer": "Dealer was not found in this organization."})
            if instance and parent.pk == instance.pk:
                raise serializers.ValidationError({"parent_dealer": "A dealer cannot be their own parent."})
            if parent.parent_dealer_id:
                raise serializers.ValidationError({"parent_dealer": "A sub dealer cannot have sub dealers of their own."})
            if instance and instance.sub_dealers.exists():
                raise serializers.ValidationError(
                    {"parent_dealer": "This dealer has sub dealers, so they cannot become a sub dealer."}
                )

        if "payout_slabs" in attrs:
            slabs = attrs["payout_slabs"]
            if len(slabs) > MAX_PAYOUT_SLABS:
                raise serializers.ValidationError({"payout_slabs": f"At most {MAX_PAYOUT_SLABS} slabs."})
            users = [slab["min_active_users"] for slab in slabs]
            if len(users) != len(set(users)):
                raise serializers.ValidationError({"payout_slabs": "Each slab needs a different number of users."})

        commission_type = attrs.get("commission_type", instance.commission_type if instance else None)
        is_sub_dealer = attrs.get("parent_dealer", instance.parent_dealer if instance else None) is not None
        if commission_type == Dealer.CommissionType.MONTHLY_SLAB and not is_sub_dealer:
            if "payout_slabs" in attrs:
                has_slabs = bool(attrs["payout_slabs"])
            else:
                has_slabs = bool(instance and instance.payout_slabs.exists())
            if not has_slabs:
                raise serializers.ValidationError({"payout_slabs": "Add at least one slab for a monthly dealer."})
        return attrs

    def update(self, instance, validated_data):
        slabs = validated_data.pop("payout_slabs", None)
        instance = super().update(instance, validated_data)
        if slabs is not None:
            replace_payout_slabs(instance, slabs)
        return instance

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Dealer name is required.")
        return value.strip()

    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError("Phone number is required.")
        return value.strip()


class InquirySerializer(serializers.ModelSerializer):
    preferred_package_name = serializers.CharField(
        source="preferred_package.name",
        read_only=True,
        default=None,
    )
    preferred_package_speed = serializers.IntegerField(
        source="preferred_package.download_speed_mbps",
        read_only=True,
        default=None,
    )
    preferred_package_price = serializers.DecimalField(
        source="preferred_package.monthly_price",
        max_digits=12,
        decimal_places=2,
        read_only=True,
        default=None,
    )
    assigned_staff_name = serializers.SerializerMethodField()
    dealer_name = serializers.CharField(
        source="dealer.name",
        read_only=True,
        default=None,
    )
    converted_customer_number = serializers.CharField(
        source="converted_customer.customer_number",
        read_only=True,
        default=None,
    )
    feasibilities_count = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "inquiry_number",
            "full_name",
            "phone",
            "alternate_phone",
            "email",
            "cnic",
            "address_line",
            "country",
            "city",
            "area",
            "preferred_package",
            "preferred_package_name",
            "preferred_package_speed",
            "preferred_package_price",
            "connection_type",
            "source",
            "assigned_staff",
            "assigned_staff_name",
            "dealer",
            "dealer_name",
            "status",
            "notes",
            "follow_up_date",
            "converted_customer",
            "converted_customer_number",
            "converted_at",
            "feasibilities_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "inquiry_number",
            "converted_customer",
            "converted_at",
            "created_at",
            "updated_at",
        ]

    def get_assigned_staff_name(self, obj):
        if obj.assigned_staff:
            return obj.assigned_staff.get_full_name() or obj.assigned_staff.username
        return None

    def get_feasibilities_count(self, obj):
        return obj.feasibility_assessments.count()


class InquiryCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            "full_name",
            "phone",
            "alternate_phone",
            "email",
            "cnic",
            "address_line",
            "country",
            "city",
            "area",
            "preferred_package",
            "connection_type",
            "source",
            "assigned_staff",
            "dealer",
            "status",
            "notes",
            "follow_up_date",
        ]

    def validate_full_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Full name is required.")
        return value.strip()

    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError("Phone number is required.")
        return value.strip()


class InquiryStatusTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Inquiry.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    follow_up_date = serializers.DateField(required=False, allow_null=True)


class InquiryConversionSerializer(serializers.Serializer):
    internet_package_id = serializers.UUIDField(required=False, allow_null=True)
    billing_day = serializers.IntegerField(default=1, min_value=1, max_value=28)
    due_day = serializers.IntegerField(default=10, min_value=1, max_value=28)
    sms_enabled = serializers.BooleanField(default=True)
    whatsapp_enabled = serializers.BooleanField(default=True)
    network_node_id = serializers.UUIDField(required=False, allow_null=True)
    network_username = serializers.CharField(required=False, allow_blank=True)
    network_ip_address = serializers.IPAddressField(required=False, allow_null=True)
    device_id = serializers.UUIDField(required=False, allow_null=True)
    device_assignment_notes = serializers.CharField(required=False, allow_blank=True)


class FeasibilityAssessmentSerializer(serializers.ModelSerializer):
    inquiry_number = serializers.CharField(
        source="inquiry.inquiry_number",
        read_only=True,
        default=None,
    )
    customer_number = serializers.CharField(
        source="customer.customer_number",
        read_only=True,
        default=None,
    )
    customer_name = serializers.CharField(
        source="customer.full_name",
        read_only=True,
        default=None,
    )
    package_name = serializers.CharField(
        source="package.name",
        read_only=True,
        default=None,
    )
    network_node_name = serializers.CharField(
        source="network_node.name",
        read_only=True,
        default=None,
    )
    assigned_technician_name = serializers.SerializerMethodField()

    class Meta:
        model = FeasibilityAssessment
        fields = [
            "id",
            "feasibility_number",
            "inquiry",
            "inquiry_number",
            "customer",
            "customer_number",
            "customer_name",
            "address_line",
            "city",
            "area",
            "package",
            "package_name",
            "connection_type",
            "network_node",
            "network_node_name",
            "assigned_technician",
            "assigned_technician_name",
            "status",
            "not_feasible_reason",
            "not_feasible_details",
            "assessment_date",
            "completion_date",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "feasibility_number",
            "created_at",
            "updated_at",
        ]

    def get_assigned_technician_name(self, obj):
        if obj.assigned_technician:
            return obj.assigned_technician.get_full_name() or obj.assigned_technician.username
        return None


class FeasibilityAssessmentCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeasibilityAssessment
        fields = [
            "inquiry",
            "customer",
            "address_line",
            "city",
            "area",
            "package",
            "connection_type",
            "network_node",
            "assigned_technician",
            "status",
            "not_feasible_reason",
            "not_feasible_details",
            "assessment_date",
            "completion_date",
            "remarks",
        ]

    def validate(self, attrs):
        status = attrs.get(
            "status",
            self.instance.status if self.instance else FeasibilityAssessment.Status.PENDING,
        )
        reason = attrs.get(
            "not_feasible_reason",
            self.instance.not_feasible_reason if self.instance else "",
        )
        if status == FeasibilityAssessment.Status.NOT_FEASIBLE and not reason:
            raise serializers.ValidationError(
                {"not_feasible_reason": "Not Feasible reason is strictly required when status is Not Feasible."}
            )
        return attrs

