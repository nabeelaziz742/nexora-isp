import logging

from celery import shared_task

from network.models import ProvisioningRequest
from network.provisioning import (
    ProvisioningExecutionError,
    execute_provisioning_request,
)

logger = logging.getLogger("nexora.network.tasks")


@shared_task
def execute_provisioning_request_task(provisioning_request_id: str):
    """Push one provisioning request to its node's provider (router or manual)."""
    try:
        result = execute_provisioning_request(
            provisioning_request_id=provisioning_request_id,
        )
    except ProvisioningExecutionError as exc:
        logger.error(
            f"Provisioning request {provisioning_request_id} could not be executed: {exc}"
        )
        return {"error": str(exc)}

    request = result.provisioning_request
    if request.status == ProvisioningRequest.Status.FAILED:
        logger.warning(
            f"Provisioning request {request.id} ({request.action}) failed: {request.error_message}"
        )

    return {
        "provisioning_request_id": str(request.id),
        "status": request.status,
        "processed": result.processed,
    }


@shared_task
def process_pending_provisioning_task(limit: int = 50):
    """Safety net for requests whose immediate execution never ran (e.g. worker restart)."""
    pending_ids = list(
        ProvisioningRequest.objects
        .filter(status=ProvisioningRequest.Status.PENDING)
        .order_by("requested_at")
        .values_list("id", flat=True)[:limit]
    )

    for provisioning_request_id in pending_ids:
        execute_provisioning_request_task(str(provisioning_request_id))

    return {"queued": len(pending_ids)}
