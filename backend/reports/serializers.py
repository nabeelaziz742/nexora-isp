from rest_framework import serializers


class SubscriberOverviewSerializer(serializers.Serializer):
    total_customers = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    inactive_customers = serializers.IntegerField()

    total_services = serializers.IntegerField()
    active_services = serializers.IntegerField()
    non_active_services = serializers.IntegerField()

    customers_with_services = serializers.IntegerField()
    customers_without_services = serializers.IntegerField()

    total_packages = serializers.IntegerField()
    active_packages = serializers.IntegerField()


class ServiceStatusDistributionSerializer(
    serializers.Serializer
):
    status = serializers.CharField()
    service_count = serializers.IntegerField()


class PackageContributionSerializer(serializers.Serializer):
    package_id = serializers.UUIDField()
    package_code = serializers.CharField()
    package_name = serializers.CharField()

    download_speed_mbps = serializers.IntegerField()
    upload_speed_mbps = serializers.IntegerField()

    monthly_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    is_active = serializers.BooleanField()

    service_count = serializers.IntegerField()
    active_service_count = serializers.IntegerField()


class PackageRevenueContextSerializer(serializers.Serializer):
    package_id = serializers.UUIDField()
    package_code = serializers.CharField()
    package_name = serializers.CharField()

    service_count = serializers.IntegerField()

    invoiced_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    collected_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    outstanding_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )