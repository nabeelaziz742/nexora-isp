from typing import Any

from django.contrib.auth import get_user_model

from tenancy.models import AuditLog, Organization


User = get_user_model()


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

    return AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action=action.strip(),
        resource_type=resource_type.strip(),
        resource_id=str(resource_id).strip(),
        metadata=metadata or {},
    )