import calendar
from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from billing.models import Invoice
from billing.recharge_services import expire_prepaid_services
from billing.services import (
    BillingDomainError,
    generate_service_invoice,
)
from customers.models import BillingProfile
from customers.suspension_services import run_daily_suspension_cycle
from onboarding.platform_services import enforce_subscription_expiry, send_subscription_reminders
from tenancy.models import Organization


class Command(BaseCommand):
    help = (
        "Run the daily billing automation cycle: generate invoices "
        "whose billing day is today, run collections, and process "
        "the communication queue."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of",
            type=str,
            default="",
            help="Run the cycle for YYYY-MM-DD instead of today.",
        )
        parser.add_argument(
            "--organization-code",
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

    def handle(self, *args, **options):
        as_of_value = options["as_of"].strip()
        if as_of_value:
            try:
                as_of_date = date.fromisoformat(as_of_value)
            except ValueError as exc:
                self.stderr.write(
                    self.style.ERROR(
                        "--as-of must use YYYY-MM-DD format."
                    )
                )
                raise SystemExit(1) from exc
        else:
            as_of_date = timezone.localdate()

        organization_code = options["organization_code"].strip()

        # Platform-wide: lock ISPs whose Nexora subscription is long overdue
        # before running their tenant jobs.
        if not organization_code:
            reminder_result = send_subscription_reminders(today=as_of_date)
            lock_result = enforce_subscription_expiry(today=as_of_date)
            self.stdout.write(
                self.style.SUCCESS(
                    f"ISP subscriptions: reminders={reminder_result['sent_count']}, "
                    f"locked={lock_result['locked_count']}"
                )
            )

        organizations = Organization.objects.filter(
            is_active=True
        ).order_by("code")

        if organization_code:
            organizations = organizations.filter(
                code=organization_code
            )

        generated = 0
        skipped = 0
        failed = 0

        for organization in organizations:
            try:
                generated_count, skipped_count, failed_count = (
                    self._generate_due_invoices(
                        organization=organization,
                        as_of_date=as_of_date,
                    )
                )
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"{organization.code}: invoice generation failed: {exc}"
                    )
                )
                failed += 1
                continue

            generated += generated_count
            skipped += skipped_count
            failed += failed_count

        self.stdout.write(
            self.style.SUCCESS(
                f"Invoice cycle: generated={generated}, skipped={skipped}, failed={failed}"
            )
        )

        expired = 0
        expiry_failed = 0
        for organization in organizations:
            result = expire_prepaid_services(organization=organization)
            expired += result["suspended_count"]
            expiry_failed += result["failed_count"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Prepaid expiry: suspended={expired}, failed={expiry_failed}"
            )
        )

        policy_suspended = 0
        restores_retried = 0
        for organization in organizations:
            try:
                result = run_daily_suspension_cycle(organization)
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"{organization.code}: suspension cycle failed: {exc}"
                    )
                )
                continue
            policy_suspended += result.get("suspended_count", 0)
            restores_retried += result.get("retried_count", 0)

        self.stdout.write(
            self.style.SUCCESS(
                f"Suspension policy: suspended={policy_suspended}, restores_retried={restores_retried}"
            )
        )

        call_command(
            "run_collections",
            as_of=as_of_date.isoformat(),
            overdue_reminder_days=options["overdue_reminder_days"],
            final_warning_days=options["final_warning_days"],
            suspension_days=options["suspension_days"],
            organization_code=organization_code,
        )

        # --once: the daily cron run must exit instead of looping forever.
        call_command("process_communication_queue", once=True)

    def _generate_due_invoices(
        self,
        *,
        organization,
        as_of_date,
    ):
        billing_year = as_of_date.year
        billing_month = as_of_date.month
        last_day = calendar.monthrange(
            billing_year,
            billing_month,
        )[1]

        profiles = (
            BillingProfile.objects
            .for_organization(organization)
            .filter(
                is_active=True,
                service_account__status__in=[
                    "ACTIVE",
                    "GRACE_PERIOD",
                ],
            )
            .exclude(billing_cycle=BillingProfile.BillingCycle.PREPAID)
            .select_related(
                "service_account",
                "service_account__internet_package",
            )
        )

        generated = 0
        skipped = 0
        failed = 0

        for profile in profiles:
            issue_day = min(profile.billing_day, last_day)
            if issue_day != as_of_date.day:
                continue

            service_account = profile.service_account
            period_start = date(
                billing_year,
                billing_month,
                1,
            )
            period_end = date(
                billing_year,
                billing_month,
                last_day,
            )

            exists = Invoice.objects.for_organization(
                organization
            ).filter(
                service_account=service_account,
                billing_period_start=period_start,
                billing_period_end=period_end,
            ).exists()

            if exists:
                skipped += 1
                continue

            due_day = min(profile.due_day, last_day)
            due_date = date(
                billing_year,
                billing_month,
                due_day,
            )

            try:
                generate_service_invoice(
                    organization=organization,
                    actor=None,
                    service_account_id=service_account.id,
                    billing_period_start=period_start,
                    billing_period_end=period_end,
                    issue_date=as_of_date,
                    due_date=due_date,
                )
            except BillingDomainError as exc:
                failed += 1
                self.stderr.write(
                    self.style.WARNING(
                        f"{organization.code}/{service_account.service_number}: {exc}"
                    )
                )
                continue

            generated += 1

        return generated, skipped, failed
