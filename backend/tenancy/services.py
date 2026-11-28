from contextvars import ContextVar
from typing import Any

from django.contrib.auth import get_user_model

from tenancy.models import AuditLog, Organization


User = get_user_model()
_impersonated_by: ContextVar[str | None] = ContextVar("impersonated_by", default=None)


def set_impersonation_context(actor_id: str | None) -> None:
    _impersonated_by.set(str(actor_id) if actor_id else None)


def get_impersonation_context() -> str | None:
    return _impersonated_by.get()


def record_audit_log(
    *,
    organization: Organization,
    action: str,
    resource_type: str,
    actor: User | None = None,
    resource_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    if not action.strip():
        raise ValueError("Audit action is required.")

    if not resource_type.strip():
        raise ValueError("Audit resource type is required.")

    enriched_metadata = dict(metadata or {})
    impersonator_id = get_impersonation_context()
    if impersonator_id and "impersonated_by" not in enriched_metadata:
        enriched_metadata["impersonated_by"] = impersonator_id

    return AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action=action.strip(),
        resource_type=resource_type.strip(),
        resource_id=str(resource_id).strip(),
        metadata=enriched_metadata,
    )