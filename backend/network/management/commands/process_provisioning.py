from django.core.management.base import BaseCommand

from network.models import ProvisioningRequest
from network.provisioning import (
    execute_provisioning_request,
)


class Command(BaseCommand):
    help = (
        "Process pending NEXORA provisioning requests."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help=(
                "Maximum number of pending provisioning "
                "requests to process."
            ),
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        if limit <= 0:
            self.stderr.write(
                self.style.ERROR(
                    "--limit must be greater than zero."
                )
            )

            return

        provisioning_request_ids = list(
            ProvisioningRequest.objects
            .filter(
                status=ProvisioningRequest.Status.PENDING
            )
            .order_by("requested_at")
            .values_list("id", flat=True)[:limit]
        )

        if not provisioning_request_ids:
            self.stdout.write(
                self.style.WARNING(
                    "No pending provisioning requests."
                )
            )

            return

        processed_count = 0
        succeeded_count = 0
        failed_count = 0
        skipped_count = 0

        for provisioning_request_id in (
            provisioning_request_ids
        ):
            result = execute_provisioning_request(
                provisioning_request_id=(
                    provisioning_request_id
                ),
            )

            request = result.provisioning_request

            if not result.processed:
                skipped_count += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"SKIPPED {request.id} "
                        f"[{request.status}]"
                    )
                )

                continue

            processed_count += 1

            if (
                request.status
                == ProvisioningRequest.Status.SUCCEEDED
            ):
                succeeded_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"SUCCEEDED {request.id} "
                        f"{request.action} "
                        f"{request.service_account.service_number}"
                    )
                )

            elif (
                request.status
                == ProvisioningRequest.Status.FAILED
            ):
                failed_count += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"FAILED {request.id} "
                        f"{request.action} "
                        f"{request.error_message}"
                    )
                )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Provisioning processing complete. "
                f"Processed={processed_count}, "
                f"Succeeded={succeeded_count}, "
                f"Failed={failed_count}, "
                f"Skipped={skipped_count}"
            )
        )