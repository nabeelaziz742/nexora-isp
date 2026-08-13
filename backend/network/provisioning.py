from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from customers.models import (
    InternetPackage,
    ServiceAccount,
)
from network.models import ProvisioningRequest
from network.providers import (
    ProvisioningProviderError,
    get_provisioning_provider,
)
from tenancy.services import record_audit_log


class ProvisioningExecutionError(Exception):
    pass


@dataclass(frozen=True)
class ProvisioningExecutionResult:
    provisioning_request: ProvisioningRequest
    processed: bool


def _apply_successful_service_transition(
    *,
    provisioning_request: ProvisioningRequest,
) -> None:
    service_account = provisioning_request.service_account
    action = provisioning_request.action

    if action == ProvisioningRequest.Action.ACTIVATE:
        service_account.status = ServiceAccount.Status.ACTIVE

        service_account.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return

    if action == ProvisioningRequest.Action.SUSPEND:
        service_account.status = (
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        )

        service_account.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return

    if action == ProvisioningRequest.Action.RESTORE:
        service_account.status = ServiceAccount.Status.ACTIVE

        service_account.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return

    if (
        action
        == ProvisioningRequest.Action.CHANGE_PACKAGE
    ):
        target_package_id = (
            provisioning_request
            .requested_payload
            .get("target_package_id")
        )

        if not target_package_id:
            raise ProvisioningExecutionError(
                "Package change request does not contain "
                "target_package_id."
            )

        try:
            target_package = (
                InternetPackage.objects
                .for_organization(
                    provisioning_request.organization
                )
                .get(
                    id=target_package_id,
                    is_active=True,
                )
            )
        except InternetPackage.DoesNotExist as exc:
            raise ProvisioningExecutionError(
                "Target internet package is not active "
                "or does not belong to this organization."
            ) from exc

        service_account.internet_package = target_package

        service_account.save(
            update_fields=[
                "internet_package",
                "updated_at",
            ]
        )

        return

    raise ProvisioningExecutionError(
        "Unsupported provisioning action."
    )


def _apply_failed_service_transition(
    *,
    provisioning_request: ProvisioningRequest,
) -> None:
    service_account = provisioning_request.service_account
    action = provisioning_request.action

    if (
        action
        == ProvisioningRequest.Action.SUSPEND
        and service_account.status
        == ServiceAccount.Status.SUSPENSION_PENDING
    ):
        service_account.status = ServiceAccount.Status.ACTIVE

        service_account.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return

    if (
        action
        == ProvisioningRequest.Action.RESTORE
        and service_account.status
        == ServiceAccount.Status.RESTORE_PENDING
    ):
        service_account.status = (
            ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        )

        service_account.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )


@transaction.atomic
def _claim_provisioning_request(
    *,
    provisioning_request_id,
) -> ProvisioningRequest | None:
    try:
        provisioning_request = (
            ProvisioningRequest.objects
            .select_for_update()
            .select_related(
                "organization",
                "service_account",
                "service_account__internet_package",
                "network_assignment",
                "network_assignment__network_node",
            )
            .get(id=provisioning_request_id)
        )
    except ProvisioningRequest.DoesNotExist as exc:
        raise ProvisioningExecutionError(
            "Provisioning request was not found."
        ) from exc

    if (
        provisioning_request.status
        != ProvisioningRequest.Status.PENDING
    ):
        return None

    provisioning_request.status = (
        ProvisioningRequest.Status.PROCESSING
    )
    provisioning_request.started_at = timezone.now()
    provisioning_request.completed_at = None
    provisioning_request.error_message = ""

    provisioning_request.save(
        update_fields=[
            "status",
            "started_at",
            "completed_at",
            "error_message",
            "updated_at",
        ]
    )

    return provisioning_request


@transaction.atomic
def _complete_provisioning_request(
    *,
    provisioning_request_id,
    provider_reference: str,
) -> ProvisioningRequest:
    provisioning_request = (
        ProvisioningRequest.objects
        .select_for_update()
        .select_related(
            "organization",
            "service_account",
            "service_account__internet_package",
            "network_assignment",
            "network_assignment__network_node",
        )
        .get(id=provisioning_request_id)
    )

    if (
        provisioning_request.status
        != ProvisioningRequest.Status.PROCESSING
    ):
        raise ProvisioningExecutionError(
            "Provisioning request is no longer processing."
        )

    _apply_successful_service_transition(
        provisioning_request=provisioning_request,
    )

    provisioning_request.status = (
        ProvisioningRequest.Status.SUCCEEDED
    )
    provisioning_request.provider_reference = (
        provider_reference
    )
    provisioning_request.error_message = ""
    provisioning_request.completed_at = timezone.now()

    provisioning_request.save(
        update_fields=[
            "status",
            "provider_reference",
            "error_message",
            "completed_at",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=provisioning_request.organization,
        actor=None,
        action="PROVISIONING_REQUEST_SUCCEEDED",
        resource_type="ProvisioningRequest",
        resource_id=provisioning_request.id,
        metadata={
            "service_number": (
                provisioning_request
                .service_account
                .service_number
            ),
            "action": provisioning_request.action,
            "provider_reference": provider_reference,
        },
    )

    return provisioning_request


@transaction.atomic
def _fail_provisioning_request(
    *,
    provisioning_request_id,
    error_message: str,
) -> ProvisioningRequest:
    provisioning_request = (
        ProvisioningRequest.objects
        .select_for_update()
        .select_related(
            "organization",
            "service_account",
            "network_assignment",
        )
        .get(id=provisioning_request_id)
    )

    if (
        provisioning_request.status
        != ProvisioningRequest.Status.PROCESSING
    ):
        return provisioning_request

    _apply_failed_service_transition(
        provisioning_request=provisioning_request,
    )

    provisioning_request.status = (
        ProvisioningRequest.Status.FAILED
    )
    provisioning_request.error_message = error_message
    provisioning_request.completed_at = timezone.now()

    provisioning_request.save(
        update_fields=[
            "status",
            "error_message",
            "completed_at",
            "updated_at",
        ]
    )

    record_audit_log(
        organization=provisioning_request.organization,
        actor=None,
        action="PROVISIONING_REQUEST_FAILED",
        resource_type="ProvisioningRequest",
        resource_id=provisioning_request.id,
        metadata={
            "service_number": (
                provisioning_request
                .service_account
                .service_number
            ),
            "action": provisioning_request.action,
            "error_message": error_message,
        },
    )

    return provisioning_request


def execute_provisioning_request(
    *,
    provisioning_request_id,
) -> ProvisioningExecutionResult:
    provisioning_request = _claim_provisioning_request(
        provisioning_request_id=provisioning_request_id,
    )

    if provisioning_request is None:
        existing_request = (
            ProvisioningRequest.objects
            .get(id=provisioning_request_id)
        )

        return ProvisioningExecutionResult(
            provisioning_request=existing_request,
            processed=False,
        )

    try:
        provider = get_provisioning_provider(
            provisioning_request=provisioning_request,
        )

        provider_result = provider.execute(
            provisioning_request=provisioning_request,
        )

        completed_request = (
            _complete_provisioning_request(
                provisioning_request_id=(
                    provisioning_request.id
                ),
                provider_reference=(
                    provider_result.provider_reference
                ),
            )
        )

        return ProvisioningExecutionResult(
            provisioning_request=completed_request,
            processed=True,
        )

    except (
        ProvisioningProviderError,
        ProvisioningExecutionError,
        Exception,
    ) as exc:
        failed_request = _fail_provisioning_request(
            provisioning_request_id=(
                provisioning_request.id
            ),
            error_message=str(exc),
        )

        return ProvisioningExecutionResult(
            provisioning_request=failed_request,
            processed=True,
        )