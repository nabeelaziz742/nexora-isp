from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from network.models import ProvisioningRequest
from network.provisioning import _fail_provisioning_request


class Command(BaseCommand):
    help = (
        "Safely recover stale provisioning requests that have remained "
        "in PROCESSING beyond the configured timeout."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=30,
            help="Age in minutes after which a PROCESSING request is stale.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of stale requests to recover.",
        )

    def handle(self, *args, **options):
        minutes = options["minutes"]
        limit = options["limit"]

        if minutes <= 0:
            self.stderr.write(
                self.style.ERROR("--minutes must be greater than zero.")
            )
            return

        if limit <= 0:
            self.stderr.write(
                self.style.ERROR("--limit must be greater than zero.")
            )
            return

        cutoff = timezone.now() - timedelta(minutes=minutes)

        request_ids = list(
            ProvisioningRequest.objects.filter(
                status=ProvisioningRequest.Status.PROCESSING,
                started_at__isnull=False,
                started_at__lt=cutoff,
            )
            .order_by("started_at")
            .values_list("id", flat=True)[:limit]
        )

        if not request_ids:
            self.stdout.write(
                self.style.SUCCESS("No stale provisioning requests found.")
            )
            return

        recovered = 0

        for request_id in request_ids:
            with transaction.atomic():
                request = (
                    ProvisioningRequest.objects
                    .select_for_update()
                    .select_related("service_account")
                    .get(id=request_id)
                )

                if request.status != ProvisioningRequest.Status.PROCESSING:
                    continue

                _fail_provisioning_request(
                    provisioning_request_id=request.id,
                    error_message=(
                        "Provisioning request was automatically marked "
                        "failed because it remained in PROCESSING beyond "
                        f"the {minutes}-minute recovery threshold. "
                        "No automatic re-execution was attempted."
                    ),
                )

                recovered += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"RECOVERED {request.id} "
                        f"{request.service_account.service_number}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Stale provisioning recovery complete. "
                f"Recovered={recovered}"
            )
        )
