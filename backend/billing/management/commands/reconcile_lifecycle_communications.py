from django.core.management.base import BaseCommand

from billing.models import Invoice
from communications.automation_service import CommunicationAutomationService
from communications.models import CommunicationAutomation, CommunicationQueue
from network.models import ProvisioningRequest
from tenancy.models import Organization


class Command(BaseCommand):
    help = "Reconcile payment, suspension, and restoration communication triggers."

    def add_arguments(self, parser):
        parser.add_argument("--organization-code", default="")

    def handle(self, *args, **options):
        code = options["organization_code"].strip()
        organizations = Organization.objects.filter(is_active=True)
        if code:
            organizations = organizations.filter(code=code)

        counts = {"payments": 0, "suspensions": 0, "restorations": 0}
        for organization in organizations:
            counts["payments"] += self._payment_confirmations(organization)
            counts["suspensions"] += self._provisioning_notifications(
                organization,
                ProvisioningRequest.Action.SUSPEND,
                CommunicationAutomation.Trigger.SERVICE_SUSPENDED,
            )
            counts["restorations"] += self._provisioning_notifications(
                organization,
                ProvisioningRequest.Action.RESTORE,
                CommunicationAutomation.Trigger.SERVICE_RESTORED,
            )

        self.stdout.write(self.style.SUCCESS(
            "Lifecycle communications reconciled: "
            f"payments={counts['payments']}, "
            f"suspensions={counts['suspensions']}, "
            f"restorations={counts['restorations']}"
        ))

    @staticmethod
    def _payment_confirmations(organization):
        if not CommunicationAutomation.objects.filter(
            organization=organization,
            trigger=CommunicationAutomation.Trigger.PAYMENT_VERIFIED,
            is_enabled=True,
        ).exists():
            return 0

        count = 0
        invoices = (
            Invoice.objects.for_organization(organization)
            .filter(status=Invoice.Status.PAID)
            .select_related("service_account__customer")
        )
        for invoice in invoices:
            customer = invoice.service_account.customer
            if CommunicationQueue.objects.filter(
                organization=organization,
                customer=customer,
                payload__invoice_id=str(invoice.id),
                payload__lifecycle_event="PAYMENT_VERIFIED",
            ).exists():
                continue
            CommunicationAutomationService.execute_trigger(
                organization=organization,
                trigger=CommunicationAutomation.Trigger.PAYMENT_VERIFIED,
                customer=customer,
                invoice=invoice,
            )
            count += 1
        return count

    @staticmethod
    def _provisioning_notifications(organization, action, trigger):
        if not CommunicationAutomation.objects.filter(
            organization=organization,
            trigger=trigger,
            is_enabled=True,
        ).exists():
            return 0

        count = 0
        requests = (
            ProvisioningRequest.objects.for_organization(organization)
            .filter(action=action, status=ProvisioningRequest.Status.SUCCEEDED)
            .select_related("service_account__customer")
        )
        for request in requests:
            customer = request.service_account.customer
            if CommunicationQueue.objects.filter(
                organization=organization,
                customer=customer,
                payload__provisioning_request_id=str(request.id),
            ).exists():
                continue
            CommunicationAutomationService.execute_trigger(
                organization=organization,
                trigger=trigger,
                customer=customer,
            )
            count += 1
        return count
