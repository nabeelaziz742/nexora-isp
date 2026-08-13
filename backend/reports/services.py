from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, Sum
from django.db import models

from billing.models import (
    InvoiceLine,
    PaymentAllocation,
)
from customers.models import (
    Customer,
    InternetPackage,
    ServiceAccount,
)
from tenancy.models import Organization


@dataclass(frozen=True)
class SubscriberOverview:
    total_customers: int
    active_customers: int
    inactive_customers: int

    total_services: int
    active_services: int
    non_active_services: int

    customers_with_services: int
    customers_without_services: int

    total_packages: int
    active_packages: int


@dataclass(frozen=True)
class ServiceStatusDistributionItem:
    status: str
    service_count: int


@dataclass(frozen=True)
class PackageContributionItem:
    package_id: str
    package_code: str
    package_name: str
    download_speed_mbps: int
    upload_speed_mbps: int
    monthly_price: Decimal
    is_active: bool
    service_count: int
    active_service_count: int


@dataclass(frozen=True)
class PackageRevenueContextItem:
    package_id: str
    package_code: str
    package_name: str
    service_count: int
    invoiced_amount: Decimal
    collected_amount: Decimal
    outstanding_amount: Decimal


def get_subscriber_overview(
    *,
    organization: Organization,
) -> SubscriberOverview:
    customers = Customer.objects.for_organization(
        organization
    )

    services = ServiceAccount.objects.for_organization(
        organization
    )

    packages = InternetPackage.objects.for_organization(
        organization
    )

    total_customers = customers.count()

    active_customers = customers.filter(
        is_active=True,
    ).count()

    total_services = services.count()

    active_services = services.filter(
        status=ServiceAccount.Status.ACTIVE,
    ).count()

    customers_with_services = (
        customers
        .filter(service_accounts__organization=organization)
        .distinct()
        .count()
    )

    return SubscriberOverview(
        total_customers=total_customers,
        active_customers=active_customers,
        inactive_customers=(
            total_customers - active_customers
        ),
        total_services=total_services,
        active_services=active_services,
        non_active_services=(
            total_services - active_services
        ),
        customers_with_services=customers_with_services,
        customers_without_services=(
            total_customers - customers_with_services
        ),
        total_packages=packages.count(),
        active_packages=packages.filter(
            is_active=True,
        ).count(),
    )


def get_service_status_distribution(
    *,
    organization: Organization,
) -> list[ServiceStatusDistributionItem]:
    services = ServiceAccount.objects.for_organization(
        organization
    )

    status_counts = {
        row["status"]: row["service_count"]
        for row in (
            services
            .values("status")
            .annotate(service_count=Count("id"))
        )
    }

    return [
        ServiceStatusDistributionItem(
            status=status,
            service_count=status_counts.get(status, 0),
        )
        for status, _label in ServiceAccount.Status.choices
    ]


def get_package_contribution(
    *,
    organization: Organization,
) -> list[PackageContributionItem]:
    packages = (
        InternetPackage.objects
        .for_organization(organization)
        .annotate(
            service_count=Count(
                "service_accounts",
                distinct=True,
            ),
            active_service_count=Count(
                "service_accounts",
                filter=models.Q(
                    service_accounts__status=(
                        ServiceAccount.Status.ACTIVE
                    ),
                    service_accounts__organization=organization,
                ),
                distinct=True,
            ),
        )
        .order_by(
            "-service_count",
            "monthly_price",
            "name",
        )
    )

    return [
        PackageContributionItem(
            package_id=str(package.id),
            package_code=package.code,
            package_name=package.name,
            download_speed_mbps=(
                package.download_speed_mbps
            ),
            upload_speed_mbps=(
                package.upload_speed_mbps
            ),
            monthly_price=package.monthly_price,
            is_active=package.is_active,
            service_count=package.service_count,
            active_service_count=(
                package.active_service_count
            ),
        )
        for package in packages
    ]


def get_package_revenue_context(
    *,
    organization: Organization,
) -> list[PackageRevenueContextItem]:
    packages = (
        InternetPackage.objects
        .for_organization(organization)
        .annotate(
            service_count=Count(
                "service_accounts",
                distinct=True,
            ),
        )
        .order_by("name")
    )

    invoice_totals = {
        str(row["invoice__service_account__internet_package_id"]): (
            row["invoiced_amount"] or Decimal("0.00")
        )
        for row in (
            InvoiceLine.objects
            .for_organization(organization)
            .values(
                "invoice__service_account__internet_package_id"
            )
            .annotate(
                invoiced_amount=Sum("amount")
            )
        )
    }

    collection_totals = {
        str(row["invoice__service_account__internet_package_id"]): (
            row["collected_amount"] or Decimal("0.00")
        )
        for row in (
            PaymentAllocation.objects
            .for_organization(organization)
            .values(
                "invoice__service_account__internet_package_id"
            )
            .annotate(
                collected_amount=Sum("amount")
            )
        )
    }

    result = []

    for package in packages:
        package_id = str(package.id)

        invoiced_amount = invoice_totals.get(
            package_id,
            Decimal("0.00"),
        )

        collected_amount = collection_totals.get(
            package_id,
            Decimal("0.00"),
        )

        result.append(
            PackageRevenueContextItem(
                package_id=package_id,
                package_code=package.code,
                package_name=package.name,
                service_count=package.service_count,
                invoiced_amount=invoiced_amount,
                collected_amount=collected_amount,
                outstanding_amount=(
                    invoiced_amount - collected_amount
                ),
            )
        )

    return sorted(
        result,
        key=lambda item: (
            -item.invoiced_amount,
            item.package_name,
        ),
    )