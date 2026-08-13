from django.urls import path

from billing.views import (
    BillingSummaryView,
    InvoiceDetailView,
    InvoiceListView,
    PaymentListView,
    RecordInvoicePaymentView,
    RevenueIntelligenceView,
    GenerateInvoiceView,
)


urlpatterns = [
    path(
        "invoices/",
        InvoiceListView.as_view(),
        name="billing-invoice-list",
    ),
    path(
        "invoices/<uuid:invoice_id>/",
        InvoiceDetailView.as_view(),
        name="billing-invoice-detail",
    ),
    path(
        "invoices/<uuid:invoice_id>/payments/",
        RecordInvoicePaymentView.as_view(),
        name="billing-invoice-payment-record",
    ),
    path(
        "payments/",
        PaymentListView.as_view(),
        name="billing-payment-list",
    ),
    path(
        "summary/",
        BillingSummaryView.as_view(),
        name="billing-summary",
    ),
    path(
        "revenue-intelligence/",
        RevenueIntelligenceView.as_view(),
        name="billing-revenue-intelligence",
    ),

    path(
    "invoices/generate/",
    GenerateInvoiceView.as_view(),
    name="billing-generate-invoice",
    )
]