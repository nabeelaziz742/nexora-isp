from datetime import date

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from billing.automation import run_collection_automation
from tenancy.models import Organization


class Command(BaseCommand):
    help = (
        "Run tenant-safe invoice collection automation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of",
            type=str,
            default="",
        )

        parser.add_argument(
            "--overdue-reminder-days",
            type=int,
            default=1,
        )

        parser.add_argument(
            "--final-warning-days",
            type=int,
            default=7,
        )

        parser.add_argument(
            "--suspension-days",
            type=int,
            default=15,
        )

        parser.add_argument(
            "--organization-code",
            type=str,
            default="",
        )

    def handle(self, *args, **options):
        as_of_value = options["as_of"].strip()

        if as_of_value:
            try:
                as_of_date = date.fromisoformat(
                    as_of_value
                )
            except ValueError as exc:
                raise CommandError(
                    "--as-of must use YYYY-MM-DD format."
                ) from exc
        else:
            as_of_date = date.today()

        overdue_reminder_days = options[
            "overdue_reminder_days"
        ]
        final_warning_days = options[
            "final_warning_days"
        ]
        suspension_days = options[
            "suspension_days"
        ]

        if not (
            overdue_reminder_days
            < final_warning_days
            < suspension_days
        ):
            raise CommandError(
                "Thresholds must satisfy: "
                "overdue reminder < final warning "
                "< suspension."
            )

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

        total_reminders = 0
        total_warnings = 0
        total_suspensions = 0
        total_failed = 0

        for organization in organizations:
            try:
                result = run_collection_automation(
                    organization=organization,
                    as_of_date=as_of_date,
                    overdue_reminder_days=(
                        overdue_reminder_days
                    ),
                    final_warning_days=(
                        final_warning_days
                    ),
                    suspension_days=suspension_days,
                    actor=None,
                )
            except ValueError as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"{organization.code}: {exc}"
                    )
                )
                total_failed += 1
                continue

            total_reminders += result.overdue_reminders
            total_warnings += result.final_warnings
            total_suspensions += (
                result.suspension_requests
            )
            total_failed += result.failed_invoices

            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"{organization.code}: "
                        f"evaluated="
                        f"{result.evaluated_invoices}, "
                        f"reminders="
                        f"{result.overdue_reminders}, "
                        f"warnings="
                        f"{result.final_warnings}, "
                        f"suspensions="
                        f"{result.suspension_requests}, "
                        f"skipped="
                        f"{result.skipped_invoices}, "
                        f"failed="
                        f"{result.failed_invoices}"
                    )
                )
            )

        summary = (
            "Collections automation complete. "
            f"as_of={as_of_date.isoformat()}, "
            f"reminders={total_reminders}, "
            f"warnings={total_warnings}, "
            f"suspensions={total_suspensions}, "
            f"failed={total_failed}"
        )

        if total_failed:
            self.stderr.write(self.style.ERROR(summary))
            raise CommandError(
                f"Collections automation completed with {total_failed} failure(s)."
            )

        self.stdout.write(self.style.SUCCESS(summary))
