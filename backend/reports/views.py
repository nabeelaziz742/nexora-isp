from datetime import date
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.serializers import (
    PackageContributionSerializer,
    PackageRevenueContextSerializer,
    ServiceStatusDistributionSerializer,
    SubscriberOverviewSerializer,
)
from reports.services import (
    generate_csv_response,
    get_area_revenue_density_report,
    get_balance_sheet_statement,
    get_cash_and_bank_position_report,
    get_cashier_shift_close_report,
    get_complaint_sla_mttr_report,
    get_customer_collections_report,
    get_customer_growth_churn_report,
    get_customer_master_report,
    get_dealer_360_performance_report,
    get_defaulters_aging_report,
    get_device_custody_report,
    get_invoice_register_report,
    get_lead_conversion_funnel_report,
    get_package_contribution,
    get_package_revenue_context,
    get_profit_and_loss_statement,
    get_promise_to_pay_report,
    get_field_recovery_scorecard_report,
    get_service_status_distribution,
    get_subscriber_overview,
)
from tenancy.permissions import (
    HasActiveTenantContext,
    IsOrganizationOwner,
    IsOrganizationStaffOrOwner,
)


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except Exception:
        return None


def _parse_int(val: str | None, default: int) -> int:
    try:
        return int(val) if val else default
    except Exception:
        return default


from rest_framework.renderers import BaseRenderer, JSONRenderer


class PlainCSVRenderer(BaseRenderer):
    media_type = "text/csv"
    format = "csv"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, str):
            return data.encode("utf-8")
        return data


class ReportsBaseAPIView(APIView):
    renderer_classes = [JSONRenderer, PlainCSVRenderer]
    permission_classes = [
        HasActiveTenantContext,
        IsOrganizationStaffOrOwner,
    ]


# =========================================================================
# PRESERVED EXISTING VIEWS (100% Backward Compatible)
# =========================================================================

class SubscriberOverviewAPIView(ReportsBaseAPIView):
    def get(self, request):
        overview = get_subscriber_overview(organization=request.organization)
        serializer = SubscriberOverviewSerializer(overview)
        return Response(serializer.data)


class ServiceStatusDistributionAPIView(ReportsBaseAPIView):
    def get(self, request):
        distribution = get_service_status_distribution(organization=request.organization)
        serializer = ServiceStatusDistributionSerializer(distribution, many=True)
        return Response(serializer.data)


class PackageContributionAPIView(ReportsBaseAPIView):
    def get(self, request):
        contribution = get_package_contribution(organization=request.organization)
        serializer = PackageContributionSerializer(contribution, many=True)
        return Response(serializer.data)


class PackageRevenueContextAPIView(ReportsBaseAPIView):
    def get(self, request):
        revenue_context = get_package_revenue_context(organization=request.organization)
        serializer = PackageRevenueContextSerializer(revenue_context, many=True)
        return Response(serializer.data)


# =========================================================================
# DOMAIN 1: CUSTOMERS & SUBSCRIBERS
# =========================================================================

class CustomerMasterReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        status_filter = request.query_params.get("status")
        area_filter = request.query_params.get("area_id")
        package_filter = request.query_params.get("package_id")
        dealer_filter = request.query_params.get("dealer_id")
        search = request.query_params.get("search")
        page = _parse_int(request.query_params.get("page"), 1)
        page_size = _parse_int(request.query_params.get("page_size"), 25)

        data = get_customer_master_report(
            organization=request.organization,
            status=status_filter,
            area_id=area_filter,
            package_id=package_filter,
            dealer_id=dealer_filter,
            search=search,
            page=page,
            page_size=page_size,
        )

        if request.query_params.get("format") == "csv":
            headers = ["Customer #", "Full Name", "Phone", "Area", "City", "Service #", "Package", "Speed", "Price", "Status", "IP", "Node", "Created"]
            rows = [
                [r["customer_number"], r["customer_name"], r["phone"], r["area"], r["city"], r["service_number"], r["package_name"], r["speed_mbps"], r["monthly_price"], r["status"], r["ip_address"], r["node_name"], r["created_at"]]
                for r in data["records"]
            ]
            csv_data = generate_csv_response("customer_master_report.csv", headers, rows)
            resp = HttpResponse(csv_data, content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="customer_master_report.csv"'
            return resp

        return Response(data)


class CustomerGrowthChurnReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))

        data = get_customer_growth_churn_report(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(data)


class AreaRevenueDensityReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        data = get_area_revenue_density_report(organization=request.organization)
        return Response(data)


# =========================================================================
# DOMAIN 2: COLLECTIONS & CASHIER
# =========================================================================

class CustomerCollectionsReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))
        collector_id = request.query_params.get("collector_id")
        payment_method = request.query_params.get("payment_method")
        search = request.query_params.get("search")
        page = _parse_int(request.query_params.get("page"), 1)
        page_size = _parse_int(request.query_params.get("page_size"), 25)

        data = get_customer_collections_report(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
            collector_id=collector_id,
            payment_method=payment_method,
            search=search,
            page=page,
            page_size=page_size,
        )

        if request.query_params.get("format") == "csv":
            headers = ["Payment #", "Paid Date", "Customer #", "Customer Name", "Service #", "Package", "Method", "Amount", "Reference", "Collector"]
            rows = [
                [r["payment_number"], r["paid_at"], r["customer_number"], r["customer_name"], r["service_number"], r["package_name"], r["payment_method"], r["amount"], r["reference"], r["received_by_name"]]
                for r in data["records"]
            ]
            csv_data = generate_csv_response("customer_collections_report.csv", headers, rows)
            resp = HttpResponse(csv_data, content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="customer_collections_report.csv"'
            return resp

        return Response(data)


class DefaultersAgingReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        aging_bucket = request.query_params.get("aging_bucket")
        area_id = request.query_params.get("area_id")
        package_id = request.query_params.get("package_id")
        dealer_id = request.query_params.get("dealer_id")
        page = _parse_int(request.query_params.get("page"), 1)
        page_size = _parse_int(request.query_params.get("page_size"), 25)
        as_of_date = _parse_date(request.query_params.get("as_of_date"))

        data = get_defaulters_aging_report(
            organization=request.organization,
            aging_bucket=aging_bucket,
            area_id=area_id,
            package_id=package_id,
            dealer_id=dealer_id,
            page=page,
            page_size=page_size,
            as_of_date=as_of_date,
        )

        if request.query_params.get("format") == "csv":
            headers = ["Invoice #", "Due Date", "Days Overdue", "Aging Bucket", "Customer #", "Customer Name", "Phone", "Area", "Service #", "Package", "Dealer", "Invoiced", "Paid", "Outstanding"]
            rows = [
                [r["invoice_number"], r["due_date"], r["days_overdue"], r["aging_bucket"], r["customer_number"], r["customer_name"], r["phone"], r["area"], r["service_number"], r["package_name"], r["dealer_name"], r["total_invoiced"], r["paid_amount"], r["outstanding_amount"]]
                for r in data["records"]
            ]
            csv_data = generate_csv_response("defaulters_aging_report.csv", headers, rows)
            resp = HttpResponse(csv_data, content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="defaulters_aging_report.csv"'
            return resp

        return Response(data)


class CashierShiftCloseReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        collector_id = request.query_params.get("collector_id") or str(request.user.id)
        shift_date = _parse_date(request.query_params.get("shift_date"))

        data = get_cashier_shift_close_report(
            organization=request.organization,
            collector_id=collector_id,
            shift_date=shift_date,
        )
        return Response(data)


# =========================================================================
# DOMAIN 3: BILLING & INVOICES
# =========================================================================

class InvoiceRegisterReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        status_filter = request.query_params.get("status")
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))
        search = request.query_params.get("search")
        page = _parse_int(request.query_params.get("page"), 1)
        page_size = _parse_int(request.query_params.get("page_size"), 25)

        data = get_invoice_register_report(
            organization=request.organization,
            status=status_filter,
            start_date=start_date,
            end_date=end_date,
            search=search,
            page=page,
            page_size=page_size,
        )

        if request.query_params.get("format") == "csv":
            headers = ["Invoice #", "Issue Date", "Due Date", "Billing Period", "Customer #", "Customer Name", "Service #", "Package", "Total Amount", "Paid Amount", "Outstanding", "Status"]
            rows = [
                [r["invoice_number"], r["issue_date"], r["due_date"], r["period"], r["customer_number"], r["customer_name"], r["service_number"], r["package_name"], r["total_amount"], r["paid_amount"], r["outstanding_amount"], r["status"]]
                for r in data["records"]
            ]
            csv_data = generate_csv_response("invoice_register_report.csv", headers, rows)
            resp = HttpResponse(csv_data, content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="invoice_register_report.csv"'
            return resp

        return Response(data)


# =========================================================================
# DOMAIN 4: RECOVERY & PROMISES
# =========================================================================

class PromiseToPayReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))
        status_filter = request.query_params.get("status")
        staff_id = request.query_params.get("staff_id")
        page = _parse_int(request.query_params.get("page"), 1)
        page_size = _parse_int(request.query_params.get("page_size"), 25)

        data = get_promise_to_pay_report(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
            status=status_filter,
            staff_id=staff_id,
            page=page,
            page_size=page_size,
        )
        return Response(data)


class FieldRecoveryScorecardReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))
        staff_id = request.query_params.get("staff_id")

        data = get_field_recovery_scorecard_report(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
            staff_id=staff_id,
        )
        return Response(data)


# =========================================================================
# DOMAIN 5: DEALER 360 & COMMISSIONS
# =========================================================================

class Dealer360PerformanceReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))
        dealer_id = request.query_params.get("dealer_id")

        data = get_dealer_360_performance_report(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
            dealer_id=dealer_id,
        )

        if request.query_params.get("format") == "csv":
            headers = ["Dealer Code", "Dealer Name", "Area", "Commission Type", "Rate", "Total Subs", "Active Subs", "Invoiced", "Collected", "Accrued Comm", "Settled Comm", "Outstanding Comm", "Net ISP Margin"]
            rows = [
                [r["dealer_code"], r["dealer_name"], r["area_name"], r["commission_type"], r["commission_rate"], r["total_subscribers"], r["active_subscribers"], r["invoiced_amount"], r["collected_amount"], r["commission_accrued"], r["commission_settled"], r["commission_outstanding"], r["net_isp_margin"]]
                for r in data
            ]
            csv_data = generate_csv_response("dealer_360_performance.csv", headers, rows)
            resp = HttpResponse(csv_data, content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="dealer_360_performance.csv"'
            return resp

        return Response(data)


# =========================================================================
# DOMAIN 6: FORMAL FINANCIAL STATEMENTS (Consuming Batch 10 GL)
# =========================================================================

class ProfitAndLossReportAPIView(ReportsBaseAPIView):
    permission_classes = [HasActiveTenantContext, IsOrganizationStaffOrOwner]

    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))

        data = get_profit_and_loss_statement(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(data)


class BalanceSheetReportAPIView(ReportsBaseAPIView):
    permission_classes = [HasActiveTenantContext, IsOrganizationStaffOrOwner]

    def get(self, request):
        as_of_date = _parse_date(request.query_params.get("as_of_date"))

        data = get_balance_sheet_statement(
            organization=request.organization,
            as_of_date=as_of_date,
        )
        return Response(data)


class CashBankPositionReportAPIView(ReportsBaseAPIView):
    permission_classes = [HasActiveTenantContext, IsOrganizationStaffOrOwner]

    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))

        data = get_cash_and_bank_position_report(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(data)


# =========================================================================
# DOMAIN 7: SUPPORT, SLA & INVENTORY
# =========================================================================

class ComplaintSlaMttrReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))
        category = request.query_params.get("category")
        priority = request.query_params.get("priority")

        data = get_complaint_sla_mttr_report(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
            category=category,
            priority=priority,
        )
        return Response(data)


class LeadConversionFunnelReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        start_date = _parse_date(request.query_params.get("start_date"))
        end_date = _parse_date(request.query_params.get("end_date"))

        data = get_lead_conversion_funnel_report(
            organization=request.organization,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(data)


class DeviceCustodyReportAPIView(ReportsBaseAPIView):
    def get(self, request):
        device_type = request.query_params.get("device_type")
        status_filter = request.query_params.get("status")
        page = _parse_int(request.query_params.get("page"), 1)
        page_size = _parse_int(request.query_params.get("page_size"), 25)

        data = get_device_custody_report(
            organization=request.organization,
            device_type=device_type,
            status=status_filter,
            page=page,
            page_size=page_size,
        )

        if request.query_params.get("format") == "csv":
            headers = ["Asset Tag", "Device Type", "Manufacturer", "Model", "Serial #", "MAC Address", "Status", "Assigned Customer", "Service #", "Assigned Date"]
            rows = [
                [r["asset_tag"], r["device_type"], r["manufacturer"], r["model_name"], r["serial_number"], r["mac_address"], r["status"], r["assigned_customer"], r["assigned_service"], r["assigned_date"]]
                for r in data["records"]
            ]
            csv_data = generate_csv_response("device_custody_report.csv", headers, rows)
            resp = HttpResponse(csv_data, content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="device_custody_report.csv"'
            return resp

        return Response(data)