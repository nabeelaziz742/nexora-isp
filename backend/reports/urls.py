from django.urls import path

from reports.views import (
    AreaRevenueDensityReportAPIView,
    BalanceSheetReportAPIView,
    CashBankPositionReportAPIView,
    CashierShiftCloseReportAPIView,
    ComplaintSlaMttrReportAPIView,
    CustomerCollectionsReportAPIView,
    CustomerGrowthChurnReportAPIView,
    CustomerMasterReportAPIView,
    Dealer360PerformanceReportAPIView,
    DefaultersAgingReportAPIView,
    DeviceCustodyReportAPIView,
    FieldRecoveryScorecardReportAPIView,
    InvoiceRegisterReportAPIView,
    LeadConversionFunnelReportAPIView,
    PackageContributionAPIView,
    PackageRevenueContextAPIView,
    ProfitAndLossReportAPIView,
    PromiseToPayReportAPIView,
    ServiceStatusDistributionAPIView,
    SubscriberOverviewAPIView,
)

app_name = "reports"

urlpatterns = [
    # Preserved backward-compatible legacy report routes
    path("subscriber-overview/", SubscriberOverviewAPIView.as_view(), name="subscriber-overview"),
    path("service-status-distribution/", ServiceStatusDistributionAPIView.as_view(), name="service-status-distribution"),
    path("package-contribution/", PackageContributionAPIView.as_view(), name="package-contribution"),
    path("package-revenue-context/", PackageRevenueContextAPIView.as_view(), name="package-revenue-context"),

    # Domain 1: Customers & Subscribers
    path("customers/master/", CustomerMasterReportAPIView.as_view(), name="customer-master-report"),
    path("customers/growth-churn/", CustomerGrowthChurnReportAPIView.as_view(), name="customer-growth-churn-report"),
    path("customers/area-density/", AreaRevenueDensityReportAPIView.as_view(), name="area-revenue-density-report"),

    # Domain 2: Collections & Cashier Shift
    path("collections/register/", CustomerCollectionsReportAPIView.as_view(), name="customer-collections-report"),
    path("collections/defaulters-aging/", DefaultersAgingReportAPIView.as_view(), name="defaulters-aging-report"),
    path("collections/cashier-shift/", CashierShiftCloseReportAPIView.as_view(), name="cashier-shift-report"),

    # Domain 3: Billing & Invoices
    path("billing/invoice-register/", InvoiceRegisterReportAPIView.as_view(), name="invoice-register-report"),

    # Domain 4: Recovery & Promises
    path("recovery/ptp-performance/", PromiseToPayReportAPIView.as_view(), name="ptp-performance-report"),
    path("recovery/officer-scorecard/", FieldRecoveryScorecardReportAPIView.as_view(), name="recovery-scorecard-report"),

    # Domain 5: Dealer 360 & Commissions
    path("dealers/performance-360/", Dealer360PerformanceReportAPIView.as_view(), name="dealer-performance-report"),

    # Domain 6: Formal Financial Statements (Consuming Batch 10 GL)
    path("financial/profit-and-loss/", ProfitAndLossReportAPIView.as_view(), name="profit-and-loss-report"),
    path("financial/balance-sheet/", BalanceSheetReportAPIView.as_view(), name="balance-sheet-report"),
    path("financial/cash-position/", CashBankPositionReportAPIView.as_view(), name="cash-position-report"),

    # Domain 7: Support & SLA
    path("support/sla-mttr/", ComplaintSlaMttrReportAPIView.as_view(), name="support-sla-report"),

    # Domain 8: Inquiries & Sales
    path("inquiries/conversion-funnel/", LeadConversionFunnelReportAPIView.as_view(), name="inquiry-funnel-report"),

    # Domain 9: Inventory & Device Custody
    path("inventory/device-custody/", DeviceCustodyReportAPIView.as_view(), name="device-custody-report"),
]