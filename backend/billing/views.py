from datetime import date
from decimal import Decimal
import calendar

from django.db.models import DecimalField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Invoice, InvoiceLine, Payment, PaymentAllocation, PromiseToPay
from billing.revenue_intelligence import build_revenue_intelligence
from billing.serializers import (
    CancelInvoiceSerializer,
    CustomInvoiceCreateSerializer,
    FinancialLedgerSerializer,
    GenerateInvoiceSerializer,
    InvoiceDetailSerializer,
    InvoiceSerializer,
    MonthlyBillingRunSerializer,
    PaymentReceiptSerializer,
    PaymentReversalSerializer,
    PaymentSerializer,
    PromiseToPayCreateSerializer,
    PromiseToPaySerializer,
    PromiseToPayStatusTransitionSerializer,
    RecordInvoicePaymentSerializer,
    RecordPaymentWithAllocationsSerializer,
    RevenueIntelligenceSerializer,
)
from billing.services import (
    BillingDomainError,
    cancel_invoice,
    create_promise_to_pay,
    generate_custom_invoice,
    generate_monthly_invoices,
    generate_service_invoice,
    get_financial_ledger,
    get_payment_receipt_data,
    record_invoice_payment,
    record_payment_with_allocations,
    reverse_payment,
    transition_promise_status,
)
from customers.models import BillingProfile
from tenancy.pagination import StandardResultsSetPagination
from tenancy.permissions import (
    CanCancelInvoice,
    CanManageBilling,
    HasActiveTenantContext,
    IsOrganizationStaffOrOwner,
)


def _invoice_queryset_for_organization(organization):
    line_subquery = (
        InvoiceLine.objects
        .filter(invoice=OuterRef("pk"))
        .values("invoice")
        .annotate(total=Sum("amount"))
        .values("total")[:1]
    )

    alloc_subquery = (
        PaymentAllocation.objects
        .filter(invoice=OuterRef("pk"))
        .values("invoice")
        .annotate(total=Sum("amount"))
        .values("total")[:1]
    )

    return (
        Invoice.objects
        .for_organization(organization)
        .select_related(
            "service_account",
            "service_account__customer",
            "service_account__internet_package",
            "billing_profile",
        )
        .annotate(
            annotated_total_amount=Coalesce(
                Subquery(line_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
            annotated_paid_amount=Coalesce(
                Subquery(alloc_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
        )
    )


class InvoiceListView(APIView):
    permission_classes = [CanManageBilling]

    def get(self, request):
        invoices = _invoice_queryset_for_organization(request.organization)

        invoice_status = request.query_params.get("status", "").strip()
        service_account_id = request.query_params.get("service_account_id", "").strip()
        customer_id = request.query_params.get("customer_id", "").strip()
        billing_period = request.query_params.get("billing_period", "").strip()
        due_state = request.query_params.get("due_state", "").strip().upper()
        search = request.query_params.get("search", "").strip()

        if invoice_status:
            invoices = invoices.filter(status=invoice_status)

        if service_account_id:
            invoices = invoices.filter(service_account_id=service_account_id)

        if customer_id:
            invoices = invoices.filter(service_account__customer_id=customer_id)

        if billing_period:
            try:
                billing_year, billing_month = billing_period.split("-", 1)
                billing_year = int(billing_year)
                billing_month = int(billing_month)
                if billing_month < 1 or billing_month > 12:
                    raise ValueError
            except (TypeError, ValueError):
                return Response(
                    {"detail": "billing_period must use YYYY-MM format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            invoices = invoices.filter(
                billing_period_start__year=billing_year,
                billing_period_start__month=billing_month,
            )

        today = date.today()

        if due_state == "OVERDUE":
            invoices = invoices.filter(due_date__lt=today).exclude(
                status=Invoice.Status.PAID
            )
        elif due_state == "DUE":
            invoices = invoices.filter(due_date__gte=today).exclude(
                status=Invoice.Status.PAID
            )
        elif due_state == "PAID":
            invoices = invoices.filter(status=Invoice.Status.PAID)
        elif due_state:
            return Response(
                {"detail": "due_state must be OVERDUE, DUE, or PAID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if search:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search)
                | Q(service_account__service_number__icontains=search)
                | Q(service_account__customer__customer_number__icontains=search)
                | Q(service_account__customer__first_name__icontains=search)
                | Q(service_account__customer__last_name__icontains=search)
            )

        invoices = invoices.order_by("-issue_date", "-created_at")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(invoices, request)
        if page is not None:
            serializer = InvoiceSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        return Response(InvoiceSerializer(invoices, many=True).data)


class InvoiceDetailView(APIView):
    permission_classes = [CanManageBilling]

    def get(self, request, invoice_id):
        try:
            invoice = (
                _invoice_queryset_for_organization(request.organization)
                .prefetch_related("lines", "allocations__payment")
                .get(id=invoice_id)
            )
        except Invoice.DoesNotExist as exc:
            raise NotFound("Invoice was not found in this organization.") from exc

        return Response(InvoiceDetailSerializer(invoice).data)


class PaymentListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        payments = (
            Payment.objects
            .for_organization(request.organization)
            .select_related("service_account", "service_account__customer", "received_by")
        )

        service_account_id = request.query_params.get("service_account_id", "").strip()
        customer_id = request.query_params.get("customer_id", "").strip()
        payment_method = request.query_params.get("payment_method", "").strip()
        search = request.query_params.get("search", "").strip()

        if service_account_id:
            payments = payments.filter(service_account_id=service_account_id)

        if customer_id:
            payments = payments.filter(service_account__customer_id=customer_id)

        if payment_method:
            payments = payments.filter(payment_method=payment_method)

        if search:
            payments = payments.filter(
                Q(payment_number__icontains=search)
                | Q(reference__icontains=search)
                | Q(service_account__service_number__icontains=search)
                | Q(service_account__customer__customer_number__icontains=search)
                | Q(service_account__customer__first_name__icontains=search)
                | Q(service_account__customer__last_name__icontains=search)
            )

        payments = payments.order_by("-paid_at", "-created_at")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(payments, request)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        return Response(PaymentSerializer(payments, many=True).data)


class RecordInvoicePaymentView(APIView):
    permission_classes = [CanManageBilling]

    def post(self, request, invoice_id):
        input_serializer = RecordInvoicePaymentSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated_data = input_serializer.validated_data

        try:
            result = record_invoice_payment(
                organization=request.organization,
                actor=request.user,
                invoice_id=invoice_id,
                amount=validated_data["amount"],
                payment_method=validated_data["payment_method"],
                reference=validated_data["reference"],
                notes=validated_data["notes"],
                paid_at=validated_data.get("paid_at"),
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payment = (
            Payment.objects
            .for_organization(request.organization)
            .select_related("service_account", "service_account__customer", "received_by")
            .get(id=result.payment.id)
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class BillingSummaryView(APIView):
    permission_classes = [CanManageBilling]

    def get(self, request):
        invoices = (
            Invoice.objects
            .for_organization(request.organization)
            .prefetch_related("lines", "allocations")
        )

        total_invoiced = Decimal("0.00")
        total_paid = Decimal("0.00")
        total_outstanding = Decimal("0.00")
        overdue_outstanding = Decimal("0.00")
        unpaid_count = 0
        partially_paid_count = 0
        paid_count = 0
        overdue_count = 0
        cancelled_count = 0
        today = date.today()

        for invoice in invoices:
            if invoice.status == Invoice.Status.CANCELLED:
                cancelled_count += 1
                continue

            total_invoiced += invoice.total_amount
            total_paid += invoice.paid_amount
            total_outstanding += invoice.outstanding_amount

            if invoice.status == Invoice.Status.UNPAID:
                unpaid_count += 1
            elif invoice.status == Invoice.Status.PARTIALLY_PAID:
                partially_paid_count += 1
            elif invoice.status == Invoice.Status.PAID:
                paid_count += 1

            if invoice.status != Invoice.Status.PAID and invoice.due_date < today:
                overdue_count += 1
                overdue_outstanding += invoice.outstanding_amount

        collection_rate = (
            (total_paid / total_invoiced * Decimal("100.00")).quantize(Decimal("0.01"))
            if total_invoiced > Decimal("0.00")
            else Decimal("0.00")
        )

        return Response(
            {
                "currency": request.organization.currency,
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "total_outstanding": total_outstanding,
                "overdue_outstanding": overdue_outstanding,
                "collection_rate": collection_rate,
                "invoice_count": invoices.count(),
                "unpaid_count": unpaid_count,
                "partially_paid_count": partially_paid_count,
                "paid_count": paid_count,
                "overdue_count": overdue_count,
                "cancelled_count": cancelled_count,
            }
        )


class RevenueIntelligenceView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        intelligence = build_revenue_intelligence(organization=request.organization)
        return Response(RevenueIntelligenceSerializer(intelligence).data)


class GenerateInvoiceView(APIView):
    permission_classes = [CanManageBilling]

    def post(self, request):
        serializer = GenerateInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        billing_year = data["billing_year"]
        billing_month = data["billing_month"]
        last_day = calendar.monthrange(billing_year, billing_month)[1]

        try:
            billing_profile = (
                BillingProfile.objects
                .for_organization(request.organization)
                .select_related("service_account")
                .get(service_account_id=data["service_account_id"])
            )
        except BillingProfile.DoesNotExist as exc:
            raise NotFound(
                "Billing profile was not found in this organization."
            ) from exc

        if not billing_profile.is_active:
            return Response(
                {"detail": "Billing profile is inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        issue_day = min(billing_profile.billing_day, last_day)
        due_day = min(billing_profile.due_day, last_day)
        issue_date = date(billing_year, billing_month, issue_day)
        due_date = date(billing_year, billing_month, due_day)

        try:
            result = generate_service_invoice(
                organization=request.organization,
                actor=request.user,
                service_account_id=data["service_account_id"],
                billing_period_start=date(billing_year, billing_month, 1),
                billing_period_end=date(billing_year, billing_month, last_day),
                issue_date=issue_date,
                due_date=due_date,
            )
        except BillingDomainError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            InvoiceSerializer(result.invoice).data,
            status=status.HTTP_201_CREATED,
        )


class PromiseToPayListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        qs = (
            PromiseToPay.objects.for_organization(request.organization)
            .select_related("customer", "service_account", "invoice", "created_by", "approved_by")
        )

        customer_id = request.query_params.get("customer_id", "").strip()
        service_account_id = request.query_params.get("service_account_id", "").strip()
        promise_status = request.query_params.get("status", "").strip()
        search = request.query_params.get("search", "").strip()

        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if service_account_id:
            qs = qs.filter(service_account_id=service_account_id)
        if promise_status:
            qs = qs.filter(status=promise_status)
        if search:
            qs = qs.filter(
                Q(promise_number__icontains=search)
                | Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(customer__customer_number__icontains=search)
                | Q(service_account__service_number__icontains=search)
            )

        qs = qs.order_by("-created_at")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = PromiseToPaySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        return Response(PromiseToPaySerializer(qs, many=True).data)

    def post(self, request):
        serializer = PromiseToPayCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            promise = create_promise_to_pay(
                organization=request.organization,
                actor=request.user,
                **serializer.validated_data,
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PromiseToPaySerializer(promise).data, status=status.HTTP_201_CREATED)


class PromiseToPayDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_promise(self, request, promise_id):
        promise = (
            PromiseToPay.objects.for_organization(request.organization)
            .select_related("customer", "service_account", "invoice", "created_by", "approved_by")
            .filter(id=promise_id)
            .first()
        )
        if not promise:
            raise NotFound("Promise to pay not found in this organization.")
        return promise

    def get(self, request, promise_id):
        promise = self._get_promise(request, promise_id)
        return Response(PromiseToPaySerializer(promise).data)

    def patch(self, request, promise_id):
        promise = self._get_promise(request, promise_id)
        if promise.status in [PromiseToPay.Status.FULFILLED, PromiseToPay.Status.BROKEN, PromiseToPay.Status.EXPIRED, PromiseToPay.Status.CANCELLED]:
            return Response(
                {"detail": f"Cannot edit a completed promise (current status: {promise.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        notes = request.data.get("notes")
        deadline = request.data.get("deadline")

        update_fields = ["updated_at"]
        if notes is not None:
            promise.notes = notes
            update_fields.append("notes")
        if deadline is not None:
            promise.deadline = deadline
            update_fields.append("deadline")

        promise.save(update_fields=update_fields)
        return Response(PromiseToPaySerializer(promise).data)


class PromiseToPayStatusTransitionView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, promise_id):
        serializer = PromiseToPayStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            promise = transition_promise_status(
                promise_id=promise_id,
                organization=request.organization,
                actor=request.user,
                new_status=serializer.validated_data["status"],
                failure_reason=serializer.validated_data.get("failure_reason", ""),
                notes=serializer.validated_data.get("notes", ""),
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PromiseToPaySerializer(promise).data)


class CancelInvoiceView(APIView):
    permission_classes = [CanCancelInvoice]

    def post(self, request, invoice_id):
        serializer = CancelInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoice = cancel_invoice(
                organization=request.organization,
                actor=request.user,
                invoice_id=invoice_id,
                cancellation_reason=serializer.validated_data["cancellation_reason"],
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InvoiceSerializer(invoice).data)


class CustomInvoiceCreateView(APIView):
    permission_classes = [CanManageBilling]

    def post(self, request):
        serializer = CustomInvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            invoice = generate_custom_invoice(
                organization=request.organization,
                actor=request.user,
                service_account_id=data["service_account_id"],
                billing_period_start=data["billing_period_start"],
                billing_period_end=data["billing_period_end"],
                issue_date=data["issue_date"],
                due_date=data["due_date"],
                line_items=data["line_items"],
                notes=data.get("notes", ""),
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InvoiceDetailSerializer(invoice).data, status=status.HTTP_201_CREATED)


class MonthlyBillingRunView(APIView):
    permission_classes = [CanManageBilling]

    def post(self, request):
        serializer = MonthlyBillingRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = generate_monthly_invoices(
                organization=request.organization,
                actor=request.user,
                billing_year=data["billing_year"],
                billing_month=data["billing_month"],
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "billing_year": result.billing_year,
                "billing_month": result.billing_month,
                "eligible_services": result.eligible_services,
                "generated_invoices": result.generated_invoices,
                "skipped_existing_invoices": result.skipped_existing_invoices,
                "failed_services": result.failed_services,
            },
            status=status.HTTP_200_OK,
        )


class RecordPaymentWithAllocationsView(APIView):
    permission_classes = [CanManageBilling]

    def post(self, request):
        serializer = RecordPaymentWithAllocationsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            payment = record_payment_with_allocations(
                organization=request.organization,
                actor=request.user,
                service_account_id=data["service_account_id"],
                amount=data["amount"],
                payment_method=data["payment_method"],
                reference=data.get("reference", ""),
                notes=data.get("notes", ""),
                allocations=data.get("allocations"),
                paid_at=data.get("paid_at"),
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payment = (
            Payment.objects
            .for_organization(request.organization)
            .select_related("service_account", "service_account__customer", "received_by")
            .prefetch_related("allocations__invoice")
            .get(id=payment.id)
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentReversalView(APIView):
    permission_classes = [CanCancelInvoice]

    def post(self, request, payment_id):
        serializer = PaymentReversalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            payment = reverse_payment(
                organization=request.organization,
                actor=request.user,
                payment_id=payment_id,
                reversal_reason=data["reversal_reason"],
                reversal_reference=data.get("reversal_reference", ""),
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PaymentSerializer(payment).data)


class PaymentReceiptView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, payment_id):
        try:
            receipt_data = get_payment_receipt_data(
                organization=request.organization,
                payment_id=payment_id,
            )
        except BillingDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PaymentReceiptSerializer(receipt_data)
        return Response(serializer.data)


class FinancialLedgerView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        customer_id = request.query_params.get("customer_id", "").strip() or None
        service_account_id = request.query_params.get("service_account_id", "").strip() or None
        start_date = request.query_params.get("start_date", "").strip() or None
        end_date = request.query_params.get("end_date", "").strip() or None

        ledger = get_financial_ledger(
            organization=request.organization,
            customer_id=customer_id,
            service_account_id=service_account_id,
            start_date=start_date,
            end_date=end_date,
        )

        serializer = FinancialLedgerSerializer(ledger)
        return Response(serializer.data)


