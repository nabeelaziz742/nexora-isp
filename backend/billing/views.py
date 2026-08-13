from datetime import date
from decimal import Decimal

from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from billing.serializers import GenerateInvoiceSerializer
from billing.services import generate_service_invoice

from billing.models import (
    Invoice,
    Payment,
)
from billing.revenue_intelligence import (
    build_revenue_intelligence,
)
from billing.serializers import (
    InvoiceDetailSerializer,
    InvoiceSerializer,
    PaymentSerializer,
    RecordInvoicePaymentSerializer,
    RevenueIntelligenceSerializer,
)
from billing.services import (
    BillingDomainError,
    record_invoice_payment,
)
from tenancy.permissions import (
    IsOrganizationStaffOrOwner,
)


def _invoice_queryset_for_organization(
    organization,
):
    return (
        Invoice.objects
        .for_organization(organization)
        .select_related(
            "service_account",
            "service_account__customer",
            "service_account__internet_package",
            "billing_profile",
        )
    )


class InvoiceListView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner
    ]

    def get(self, request):
        invoices = (
            _invoice_queryset_for_organization(
                request.organization
            )
        )

        invoice_status = request.query_params.get(
            "status",
            "",
        ).strip()

        service_account_id = (
            request.query_params.get(
                "service_account_id",
                "",
            )
            .strip()
        )

        customer_id = request.query_params.get(
            "customer_id",
            "",
        ).strip()

        billing_period = request.query_params.get(
            "billing_period",
            "",
        ).strip()

        due_state = request.query_params.get(
            "due_state",
            "",
        ).strip().upper()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if invoice_status:
            invoices = invoices.filter(
                status=invoice_status
            )

        if service_account_id:
            invoices = invoices.filter(
                service_account_id=service_account_id
            )

        if customer_id:
            invoices = invoices.filter(
                service_account__customer_id=customer_id
            )

        if billing_period:
            try:
                billing_year, billing_month = (
                    billing_period.split("-", 1)
                )

                billing_year = int(billing_year)
                billing_month = int(billing_month)

                if (
                    billing_month < 1
                    or billing_month > 12
                ):
                    raise ValueError
            except (
                TypeError,
                ValueError,
            ):
                return Response(
                    {
                        "detail": (
                            "billing_period must use "
                            "YYYY-MM format."
                        ),
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

            invoices = invoices.filter(
                billing_period_start__year=(
                    billing_year
                ),
                billing_period_start__month=(
                    billing_month
                ),
            )

        today = date.today()

        if due_state == "OVERDUE":
            invoices = invoices.filter(
                due_date__lt=today,
            ).exclude(
                status=Invoice.Status.PAID
            )
        elif due_state == "DUE":
            invoices = invoices.filter(
                due_date__gte=today,
            ).exclude(
                status=Invoice.Status.PAID
            )
        elif due_state == "PAID":
            invoices = invoices.filter(
                status=Invoice.Status.PAID
            )
        elif due_state:
            return Response(
                {
                    "detail": (
                        "due_state must be OVERDUE, "
                        "DUE, or PAID."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if search:
            invoices = invoices.filter(
                Q(
                    invoice_number__icontains=search
                )
                | Q(
                    service_account__service_number__icontains=search
                )
                | Q(
                    service_account__customer__customer_number__icontains=search
                )
                | Q(
                    service_account__customer__first_name__icontains=search
                )
                | Q(
                    service_account__customer__last_name__icontains=search
                )
            )

        invoices = invoices.order_by(
            "-issue_date",
            "-created_at",
        )

        serializer = InvoiceSerializer(
            invoices,
            many=True,
        )

        return Response(serializer.data)


class InvoiceDetailView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner
    ]

    def get(self, request, invoice_id):
        try:
            invoice = (
                _invoice_queryset_for_organization(
                    request.organization
                )
                .prefetch_related(
                    "lines",
                    "allocations__payment",
                )
                .get(id=invoice_id)
            )
        except Invoice.DoesNotExist as exc:
            raise NotFound(
                "Invoice was not found "
                "in this organization."
            ) from exc

        serializer = InvoiceDetailSerializer(
            invoice
        )

        return Response(serializer.data)


class PaymentListView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner
    ]

    def get(self, request):
        payments = (
            Payment.objects
            .for_organization(request.organization)
            .select_related(
                "service_account",
                "service_account__customer",
                "received_by",
            )
        )

        service_account_id = (
            request.query_params.get(
                "service_account_id",
                "",
            )
            .strip()
        )

        customer_id = request.query_params.get(
            "customer_id",
            "",
        ).strip()

        payment_method = request.query_params.get(
            "payment_method",
            "",
        ).strip()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        if service_account_id:
            payments = payments.filter(
                service_account_id=service_account_id
            )

        if customer_id:
            payments = payments.filter(
                service_account__customer_id=customer_id
            )

        if payment_method:
            payments = payments.filter(
                payment_method=payment_method
            )

        if search:
            payments = payments.filter(
                Q(
                    payment_number__icontains=search
                )
                | Q(reference__icontains=search)
                | Q(
                    service_account__service_number__icontains=search
                )
                | Q(
                    service_account__customer__customer_number__icontains=search
                )
                | Q(
                    service_account__customer__first_name__icontains=search
                )
                | Q(
                    service_account__customer__last_name__icontains=search
                )
            )

        payments = payments.order_by(
            "-paid_at",
            "-created_at",
        )

        serializer = PaymentSerializer(
            payments,
            many=True,
        )

        return Response(serializer.data)


class RecordInvoicePaymentView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner
    ]

    def post(self, request, invoice_id):
        input_serializer = (
            RecordInvoicePaymentSerializer(
                data=request.data
            )
        )
        input_serializer.is_valid(
            raise_exception=True
        )

        validated_data = (
            input_serializer.validated_data
        )

        try:
            result = record_invoice_payment(
                organization=request.organization,
                actor=request.user,
                invoice_id=invoice_id,
                amount=validated_data["amount"],
                payment_method=validated_data[
                    "payment_method"
                ],
                reference=validated_data[
                    "reference"
                ],
                notes=validated_data["notes"],
                paid_at=validated_data.get(
                    "paid_at"
                ),
            )
        except BillingDomainError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        payment = (
            Payment.objects
            .for_organization(request.organization)
            .select_related(
                "service_account",
                "service_account__customer",
                "received_by",
            )
            .get(id=result.payment.id)
        )

        serializer = PaymentSerializer(payment)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class BillingSummaryView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner
    ]

    def get(self, request):
        invoices = (
            Invoice.objects
            .for_organization(request.organization)
            .prefetch_related(
                "lines",
                "allocations",
            )
        )

        total_invoiced = Decimal("0.00")
        total_paid = Decimal("0.00")
        total_outstanding = Decimal("0.00")
        overdue_outstanding = Decimal("0.00")

        unpaid_count = 0
        partially_paid_count = 0
        paid_count = 0
        overdue_count = 0

        today = date.today()

        for invoice in invoices:
            total_invoiced += invoice.total_amount
            total_paid += invoice.paid_amount
            total_outstanding += (
                invoice.outstanding_amount
            )

            if invoice.status == Invoice.Status.UNPAID:
                unpaid_count += 1
            elif (
                invoice.status
                == Invoice.Status.PARTIALLY_PAID
            ):
                partially_paid_count += 1
            elif (
                invoice.status
                == Invoice.Status.PAID
            ):
                paid_count += 1

            if (
                invoice.status != Invoice.Status.PAID
                and invoice.due_date < today
            ):
                overdue_count += 1
                overdue_outstanding += (
                    invoice.outstanding_amount
                )

        return Response(
            {
                "currency": (
                    request.organization.currency
                ),
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "total_outstanding": (
                    total_outstanding
                ),
                "overdue_outstanding": (
                    overdue_outstanding
                ),
                "invoice_count": invoices.count(),
                "unpaid_count": unpaid_count,
                "partially_paid_count": (
                    partially_paid_count
                ),
                "paid_count": paid_count,
                "overdue_count": overdue_count,
            }
        )


class RevenueIntelligenceView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner
    ]

    def get(self, request):
        intelligence = build_revenue_intelligence(
            organization=request.organization,
        )

        serializer = RevenueIntelligenceSerializer(
            intelligence
        )

        return Response(serializer.data)
    
class GenerateInvoiceView(APIView):
    permission_classes = [
        IsOrganizationStaffOrOwner
    ]

    def post(self, request):

        serializer = GenerateInvoiceSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        data = serializer.validated_data

        billing_year = data["billing_year"]
        billing_month = data["billing_month"]

        import calendar
        from datetime import date
        from customers.models import BillingProfile

        last_day = calendar.monthrange(
            billing_year,
            billing_month,
        )[1]

        billing_profile = BillingProfile.objects.get(
            service_account_id=data["service_account_id"]
        )

        issue_day = min(
            billing_profile.billing_day,
            last_day,
        )

        due_day = min(
            billing_profile.due_day,
            last_day,
        )

        issue_date = date(
            billing_year,
            billing_month,
            issue_day,
        )

        due_date = date(
            billing_year,
            billing_month,
            due_day,
        )

        print("====================================")
        print("Billing Year:", billing_year)
        print("Billing Month:", billing_month)
        print("Issue Date:", issue_date)
        print("Due Date:", due_date)
        print("====================================")

        result = generate_service_invoice(
            organization=request.organization,
            actor=request.user,
            service_account_id=data["service_account_id"],
            billing_period_start=date(
                billing_year,
                billing_month,
                1,
            ),
            billing_period_end=date(
                billing_year,
                billing_month,
                last_day,
            ),
            issue_date=issue_date,
            due_date=due_date,
        )

        return Response(
            InvoiceSerializer(result.invoice).data,
            status=status.HTTP_201_CREATED,
        )