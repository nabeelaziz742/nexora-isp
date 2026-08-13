from rest_framework import serializers

from customers.models import (
    Customer,
    InternetPackage,
)


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

    sms_enabled = serializers.BooleanField(default=True)
    whatsapp_enabled = serializers.BooleanField(default=True)


class InternetPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternetPackage
        fields = [
            "id",
            "name",
            "code",
            "download_speed_mbps",
            "upload_speed_mbps",
            "monthly_price",
            "is_active",
        ]


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