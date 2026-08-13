from dataclasses import dataclass
from datetime import date
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from customers.models import (
    BillingProfile,
    Customer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from inventory.models import DeviceAssignment
from inventory.services import (
    InventoryCustodyError,
    assign_device_to_service,
)
from network.models import (
    NetworkAssignment,
    ProvisioningRequest,
)
from network.services import (
    NetworkAssignmentError,
    create_activation_network_request,
)
from tenancy.models import Organization
from tenancy.services import record_audit_log


User = get_user_model()


class CustomerActivationError(Exception):
    pass


@dataclass(frozen=True)
class CustomerActivationResult:
    customer: Customer
    service_account: ServiceAccount
    billing_profile: BillingProfile
    notification_preference: NotificationPreference
    network_assignment: NetworkAssignment | None = None
    provisioning_request: ProvisioningRequest | None = None
    device_assignment: DeviceAssignment | None = None


def _build_customer_number(
    *,
    organization: Organization,
) -> str:
    prefix = organization.code.upper()[:12]

    last_customer = (
        Customer.objects.for_organization(organization)
        .order_by("-created_at")
        .first()
    )

    sequence = (
        Customer.objects.for_organization(organization).count()
        + 1
    )

    if last_customer is not None:
        sequence = max(sequence, 1)

    return f"{prefix}-CUST-{sequence:06d}"


def _build_service_number(
    *,
    organization: Organization,
) -> str:
    prefix = organization.code.upper()[:12]

    sequence = (
        ServiceAccount.objects.for_organization(organization).count()
        + 1
    )

    return f"{prefix}-SRV-{sequence:06d}"


@transaction.atomic
def activate_customer_service(
    *,
    organization: Organization,
    actor: User,
    internet_package_id,
    first_name: str,
    last_name: str = "",
    phone: str,
    alternate_phone: str = "",
    email: str = "",
    address_line: str,
    area: str = "",
    city: str,
    billing_day: int,
    due_day: int,
    sms_enabled: bool = True,
    whatsapp_enabled: bool = True,
    network_node_id=None,
    network_username: str = "",
    network_ip_address: str | None = None,
    device_id=None,
    device_assignment_notes: str = "",
    provisioning_payload: dict[str, Any] | None = None,
    activation_metadata: dict[str, Any] | None = None,
) -> CustomerActivationResult:
    if not organization.is_active:
        raise CustomerActivationError(
            "Organization is inactive."
        )

    first_name = first_name.strip()
    last_name = last_name.strip()
    phone = phone.strip()
    alternate_phone = alternate_phone.strip()
    email = email.strip().lower()
    address_line = address_line.strip()
    area = area.strip()
    city = city.strip()
    device_assignment_notes = device_assignment_notes.strip()

    if not first_name:
        raise CustomerActivationError(
            "Customer first name is required."
        )

    if not phone:
        raise CustomerActivationError(
            "Customer phone is required."
        )

    if not address_line:
        raise CustomerActivationError(
            "Service address is required."
        )

    if not city:
        raise CustomerActivationError(
            "Customer city is required."
        )

    if billing_day < 1 or billing_day > 28:
        raise CustomerActivationError(
            "Billing day must be between 1 and 28."
        )

    if due_day < 1 or due_day > 28:
        raise CustomerActivationError(
            "Due day must be between 1 and 28."
        )

    try:
        internet_package = (
            InternetPackage.objects
            .for_organization(organization)
            .get(
                id=internet_package_id,
                is_active=True,
            )
        )
    except InternetPackage.DoesNotExist as exc:
        raise CustomerActivationError(
            "Active internet package was not found "
            "for this organization."
        ) from exc

    duplicate_phone_exists = (
        Customer.objects
        .for_organization(organization)
        .filter(phone=phone)
        .exists()
    )

    if duplicate_phone_exists:
        raise CustomerActivationError(
            "A customer with this phone already exists "
            "in this organization."
        )

    customer = Customer.objects.create(
        organization=organization,
        customer_number=_build_customer_number(
            organization=organization,
        ),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        alternate_phone=alternate_phone,
        email=email,
        address_line=address_line,
        area=area,
        city=city,
    )

    service_account = ServiceAccount.objects.create(
        organization=organization,
        service_number=_build_service_number(
            organization=organization,
        ),
        customer=customer,
        internet_package=internet_package,
        status=ServiceAccount.Status.ACTIVE,
        activated_at=timezone.now(),
    )

    network_assignment = None
    provisioning_request = None
    device_assignment = None

    if network_node_id is not None:
        try:
            network_result = create_activation_network_request(
                organization=organization,
                service_account=service_account,
                network_node_id=network_node_id,
                username=network_username,
                ip_address=network_ip_address,
                provisioning_payload=provisioning_payload,
            )
        except NetworkAssignmentError as exc:
            raise CustomerActivationError(str(exc)) from exc

        network_assignment = network_result.network_assignment
        provisioning_request = network_result.provisioning_request

    if device_id is not None:
        try:
            inventory_result = assign_device_to_service(
                organization=organization,
                actor=actor,
                device_id=device_id,
                service_account_id=service_account.id,
                assignment_notes=device_assignment_notes,
            )
        except InventoryCustodyError as exc:
            raise CustomerActivationError(str(exc)) from exc

        device_assignment = inventory_result.assignment

    billing_profile = BillingProfile.objects.create(
        organization=organization,
        service_account=service_account,
        billing_cycle=BillingProfile.BillingCycle.MONTHLY,
        billing_day=billing_day,
        due_day=due_day,
    )

    notification_preference = (
        NotificationPreference.objects.create(
            organization=organization,
            customer=customer,
            sms_enabled=sms_enabled,
            whatsapp_enabled=whatsapp_enabled,
        )
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="CUSTOMER_SERVICE_ACTIVATED",
        resource_type="ServiceAccount",
        resource_id=service_account.id,
        metadata={
            "customer_id": str(customer.id),
            "customer_number": customer.customer_number,
            "service_number": service_account.service_number,
            "internet_package_id": str(internet_package.id),
            "network_assignment_id": (
                str(network_assignment.id)
                if network_assignment
                else None
            ),
            "provisioning_request_id": (
                str(provisioning_request.id)
                if provisioning_request
                else None
            ),
            "device_assignment_id": (
                str(device_assignment.id)
                if device_assignment
                else None
            ),
            "device_id": (
                str(device_assignment.device_id)
                if device_assignment
                else None
            ),
            "activation_date": date.today().isoformat(),
            **(activation_metadata or {}),
        },
    )

    return CustomerActivationResult(
        customer=customer,
        service_account=service_account,
        billing_profile=billing_profile,
        notification_preference=notification_preference,
        network_assignment=network_assignment,
        provisioning_request=provisioning_request,
        device_assignment=device_assignment,
    )