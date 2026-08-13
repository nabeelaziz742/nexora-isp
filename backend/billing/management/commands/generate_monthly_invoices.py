from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from billing.services import (
    BillingDomainError,
    generate_monthly_invoices,
)
from tenancy.models import Organization


class Command(BaseCommand):
    help = (
        "Generate monthly invoices for eligible "
        "service accounts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--month",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--organization-code",
            type=str,
            default="",
        )

    def handle(self, *args, **options):
        billing_year = options["year"]
        billing_month = options["month"]

        organization_code = (
            options["organization_code"].strip()
        )

        organizations = Organization.objects.filter(
            is_active=True
        ).order_by("code")

        if organization_code:
            organizations = organizations.filter(
                code=organization_code
            )

        if not organizations.exists():
            raise CommandError(
                "No active organizations matched."
            )

        total_generated = 0
        total_skipped = 0
        total_failed = 0

        for organization in organizations:
            try:
                result = generate_monthly_invoices(
                    organization=organization,
                    actor=None,
                    billing_year=billing_year,
                    billing_month=billing_month,
                )
            except BillingDomainError as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"{organization.code}: {exc}"
                    )
                )
                total_failed += 1
                continue

            total_generated += (
                result.generated_invoices
            )
            total_skipped += (
                result.skipped_existing_invoices
            )
            total_failed += result.failed_services

            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"{organization.code}: "
                        f"eligible="
                        f"{result.eligible_services}, "
                        f"generated="
                        f"{result.generated_invoices}, "
                        f"skipped="
                        f"{result.skipped_existing_invoices}, "
                        f"failed="
                        f"{result.failed_services}"
                    )
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Monthly billing complete. "
                    f"generated={total_generated}, "
                    f"skipped={total_skipped}, "
                    f"failed={total_failed}"
                )
            )
        )