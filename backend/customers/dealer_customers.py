"""Dealer portal customer actions: assign, edit contact, deactivate, ledger, import & export."""
import io
import re
from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from billing.models import Invoice, Payment
from customers.dealer_portal import DealerPortalView, _dealer_services, _service_row
from customers.import_services import (
    CustomerImportError,
    build_import_template,
    import_customers,
    parse_import_file,
    validate_import_rows,
)
from customers.import_views import XLSX_CONTENT_TYPE, _batch_data
from customers.models import (
    Customer,
    CustomerImportBatch,
    DealerArea,
    DealerEmployee,
    ServiceAccount,
    ServiceSuspensionLog,
)
from customers.suspension_services import execute_service_suspension
from tenancy.services import record_audit_log


def _get_dealer_customer(request, customer_id) -> Customer:
    qs = Customer.objects.for_organization(request.organization).filter(dealer=request.dealer)
    employee = getattr(request, "dealer_employee", None)
    if employee is not None and not employee.can_view_all_customers:
        qs = qs.filter(assigned_dealer_employee=employee)
    customer = (
        qs.select_related("assigned_dealer_employee__membership__user")
        .filter(id=customer_id)
        .first()
    )
    if customer is None:
        raise NotFound("This customer was not found for your account.")
    return customer


def _filtered_customer_rows(request) -> list[dict]:
    today = timezone.localdate()
    services = _dealer_services(request).order_by("customer__first_name", "service_number")
    search = request.query_params.get("search", "").strip()
    if search:
        from django.db.models import Q

        services = services.filter(
            Q(customer__first_name__icontains=search)
            | Q(customer__last_name__icontains=search)
            | Q(customer__phone__icontains=search)
            | Q(customer__customer_number__icontains=search)
            | Q(service_number__icontains=search)
        )
    rows = [_service_row(svc, today) for svc in services[:2000]]
    show = request.query_params.get("show", "").strip().lower()
    if show == "due":
        rows = [row for row in rows if Decimal(row["outstanding"]) > 0]
    elif show == "expiring":
        rows = [row for row in rows if row["days_to_expiry"] is not None and row["days_to_expiry"] <= 3]
    return rows


# ---------------------------------------------------------------------------
# Assign customers to an employee
# ---------------------------------------------------------------------------

class AssignCustomersSerializer(serializers.Serializer):
    customer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=500,
    )
    employee_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class DealerCustomerAssignOptionsView(DealerPortalView):
    required_rights = ("can_manage_employees",)

    def get(self, request):
        employees = (
            DealerEmployee.objects.for_organization(request.organization)
            .filter(dealer=request.dealer, membership__is_active=True, membership__user__is_active=True)
            .select_related("membership__user")
            .order_by("membership__user__first_name", "membership__user__email")
        )
        return Response({
            "employees": [
                {
                    "id": str(emp.id),
                    "full_name": emp.membership.user.get_full_name() or emp.membership.user.email,
                    "email": emp.membership.user.email,
                }
                for emp in employees
            ]
        })


class DealerCustomerAssignView(DealerPortalView):
    required_rights = ("can_manage_employees",)

    @transaction.atomic
    def post(self, request):
        serializer = AssignCustomersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer_ids = list(dict.fromkeys(serializer.validated_data["customer_ids"]))
        employee_id = serializer.validated_data["employee_id"]

        employee = None
        if employee_id is not None:
            employee = (
                DealerEmployee.objects.for_organization(request.organization)
                .filter(dealer=request.dealer, id=employee_id)
                .first()
            )
            if employee is None:
                raise NotFound("Employee was not found for this dealer.")

        customers = list(
            Customer.objects.for_organization(request.organization)
            .filter(dealer=request.dealer, id__in=customer_ids)
        )
        if len(customers) != len(customer_ids):
            raise NotFound("One or more customers do not belong to your dealer account.")

        Customer.objects.for_organization(request.organization).filter(
            dealer=request.dealer,
            id__in=customer_ids,
        ).update(assigned_dealer_employee=employee)

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_CUSTOMERS_ASSIGNED",
            resource_type="Dealer",
            resource_id=str(request.dealer.id),
            metadata={
                "dealer_code": request.dealer.dealer_code,
                "employee_id": str(employee.id) if employee else None,
                "customer_ids": [str(cid) for cid in customer_ids],
                "count": len(customer_ids),
            },
        )
        return Response({
            "assigned_count": len(customer_ids),
            "employee_id": str(employee.id) if employee else None,
        })


# ---------------------------------------------------------------------------
# Edit customer contact fields only
# ---------------------------------------------------------------------------

class DealerCustomerEditSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False)
    alternate_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    cnic = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address_line = serializers.CharField(max_length=255, required=False)
    area = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_first_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("First name cannot be blank.")
        return cleaned

    def validate_phone(self, value):
        cleaned = re.sub(r"[\s\-()]", "", value.strip())
        if not re.match(r"^\+?\d{10,15}$", cleaned):
            raise serializers.ValidationError("Enter a valid phone number.")
        return cleaned

    def validate_alternate_phone(self, value):
        raw = value.strip()
        if not raw:
            return ""
        cleaned = re.sub(r"[\s\-()]", "", raw)
        if not re.match(r"^\+?\d{10,15}$", cleaned):
            raise serializers.ValidationError("Enter a valid alternate phone number.")
        return cleaned

    def validate_cnic(self, value):
        digits = re.sub(r"\D", "", value or "")
        if not digits:
            return ""
        if len(digits) != 13:
            raise serializers.ValidationError("CNIC must have 13 digits.")
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"

    def validate_address_line(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Address cannot be blank.")
        return cleaned


class DealerCustomerDetailEditView(DealerPortalView):
    required_rights = ("can_edit_customers",)

    def get(self, request, customer_id):
        customer = _get_dealer_customer(request, customer_id)
        areas = (
            DealerArea.objects.for_organization(request.organization)
            .filter(dealer=request.dealer, is_active=True)
            .order_by("name")
        )
        return Response({
            "customer": {
                "id": str(customer.id),
                "customer_number": customer.customer_number,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "phone": customer.phone,
                "alternate_phone": customer.alternate_phone,
                "cnic": customer.cnic,
                "address_line": customer.address_line,
                "area": customer.area,
            },
            "areas": [{"id": str(a.id), "name": a.name, "city": a.city} for a in areas],
        })

    @transaction.atomic
    def patch(self, request, customer_id):
        customer = _get_dealer_customer(request, customer_id)
        serializer = DealerCustomerEditSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "phone" in data:
            if (
                Customer.objects.for_organization(request.organization)
                .filter(phone=data["phone"])
                .exclude(pk=customer.pk)
                .exists()
            ):
                raise ValidationError({"phone": "A customer with this phone number already exists."})

        if "area" in data:
            wanted_area = data["area"].strip()
            if wanted_area and wanted_area != customer.area:
                matched = (
                    DealerArea.objects.for_organization(request.organization)
                    .filter(dealer=request.dealer, is_active=True, name__iexact=wanted_area)
                    .first()
                )
                if matched is None:
                    raise ValidationError({"area": "Select one of your active dealer areas."})
                data["area"] = matched.name
            else:
                data["area"] = wanted_area

        changes = {}
        for field in ("first_name", "last_name", "phone", "alternate_phone", "cnic", "address_line", "area"):
            if field in data:
                new_val = data[field].strip() if isinstance(data[field], str) else data[field]
                old_val = getattr(customer, field)
                if new_val != old_val:
                    changes[field] = {"from": old_val, "to": new_val}
                    setattr(customer, field, new_val)

        if changes:
            customer.save()
            record_audit_log(
                organization=request.organization,
                actor=request.user,
                action="DEALER_CUSTOMER_UPDATED",
                resource_type="Customer",
                resource_id=str(customer.id),
                metadata={
                    "dealer_code": request.dealer.dealer_code,
                    "customer_number": customer.customer_number,
                    "changes": changes,
                },
            )

        today = timezone.localdate()
        services = (
            _dealer_services(request)
            .filter(customer=customer)
            .order_by("service_number")
        )
        return Response({
            "customer": {
                "id": str(customer.id),
                "customer_number": customer.customer_number,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "phone": customer.phone,
                "alternate_phone": customer.alternate_phone,
                "cnic": customer.cnic,
                "address_line": customer.address_line,
                "area": customer.area,
            },
            "services": [_service_row(svc, today) for svc in services],
        })


# ---------------------------------------------------------------------------
# Deactivate customer (uses existing suspension flow; never deletes)
# ---------------------------------------------------------------------------

class DeactivateCustomerSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)

    def validate_reason(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Reason is required.")
        return cleaned


class DealerCustomerDeactivateView(DealerPortalView):
    required_rights = ("can_deactivate_customers",)

    @transaction.atomic
    def post(self, request, customer_id):
        customer = _get_dealer_customer(request, customer_id)
        serializer = DeactivateCustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        services = list(
            ServiceAccount.objects.for_organization(request.organization)
            .filter(customer=customer)
            .select_related("internet_package", "customer")
        )
        suspendable = [
            svc
            for svc in services
            if svc.status in {
                ServiceAccount.Status.ACTIVE,
                ServiceAccount.Status.GRACE_PERIOD,
                ServiceAccount.Status.SUSPENSION_PENDING,
            }
        ]
        if not suspendable:
            raise ValidationError({"detail": "This customer's connection is already suspended."})

        for svc in suspendable:
            execute_service_suspension(
                service_account=svc,
                trigger_type=ServiceSuspensionLog.TriggerType.MANUAL_STAFF,
                reason=f"Dealer deactivation ({request.dealer.dealer_code}): {reason}",
                actor=request.user,
            )

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_CUSTOMER_DEACTIVATED",
            resource_type="Customer",
            resource_id=str(customer.id),
            metadata={
                "dealer_code": request.dealer.dealer_code,
                "customer_number": customer.customer_number,
                "reason": reason,
                "service_ids": [str(svc.id) for svc in suspendable],
            },
        )

        today = timezone.localdate()
        refreshed = _dealer_services(request).filter(customer=customer).order_by("service_number")
        return Response({
            "detail": "Customer connection deactivated.",
            "services": [_service_row(svc, today) for svc in refreshed],
        })


# ---------------------------------------------------------------------------
# Customer ledger (invoices + payments in date order with running balance)
# ---------------------------------------------------------------------------

class DealerCustomerLedgerView(DealerPortalView):
    required_rights = ("can_view_ledger",)

    def get(self, request, customer_id):
        customer = _get_dealer_customer(request, customer_id)
        invoices = list(
            Invoice.objects.for_organization(request.organization)
            .filter(service_account__customer=customer)
            .exclude(status=Invoice.Status.CANCELLED)
            .prefetch_related("lines")
            .select_related("service_account")
        )
        payments = list(
            Payment.objects.for_organization(request.organization)
            .filter(service_account__customer=customer)
            .select_related("service_account", "received_by")
        )

        raw_entries = []
        for inv in invoices:
            amount = inv.total_amount
            descriptions = [line.description for line in inv.lines.all()]
            raw_entries.append({
                "sort_date": inv.issue_date,
                "sort_kind": 0,
                "created_at": inv.created_at,
                "id": str(inv.id),
                "date": inv.issue_date.isoformat(),
                "type": "INVOICE",
                "reference": inv.invoice_number,
                "service_number": inv.service_account.service_number,
                "description": "; ".join(descriptions) or "Invoice",
                "debit": amount,
                "credit": Decimal("0.00"),
                "is_reversed": False,
            })

        for pay in payments:
            pay_date = timezone.localtime(pay.paid_at).date() if timezone.is_aware(pay.paid_at) else pay.paid_at.date()
            raw_entries.append({
                "sort_date": pay_date,
                "sort_kind": 1,
                "created_at": pay.created_at,
                "id": str(pay.id),
                "date": pay_date.isoformat(),
                "type": "PAYMENT",
                "reference": pay.payment_number,
                "service_number": pay.service_account.service_number,
                "description": f"{pay.get_payment_method_display()}" + (f" · {pay.reference}" if pay.reference else ""),
                "debit": Decimal("0.00"),
                "credit": pay.amount,
                "is_reversed": pay.is_reversed,
            })

        raw_entries.sort(key=lambda item: (item["sort_date"], item["sort_kind"], item["created_at"]))

        running = Decimal("0.00")
        entries = []
        for item in raw_entries:
            if not item["is_reversed"]:
                running += item["debit"] - item["credit"]
            entries.append({
                "id": item["id"],
                "date": item["date"],
                "type": item["type"],
                "reference": item["reference"],
                "service_number": item["service_number"],
                "description": item["description"],
                "debit": str(item["debit"]),
                "credit": str(item["credit"]),
                "is_reversed": item["is_reversed"],
                "running_balance": str(running),
            })

        return Response({
            "customer": {
                "id": str(customer.id),
                "customer_number": customer.customer_number,
                "full_name": customer.full_name,
                "phone": customer.phone,
            },
            "current_balance": str(running),
            "entries": entries,
        })


# ---------------------------------------------------------------------------
# Dealer Import (always this dealer, always create_on_router=False)
# ---------------------------------------------------------------------------

class DealerCustomerImportTemplateView(DealerPortalView):
    required_rights = ("can_import_customers",)

    def get(self, request):
        content = build_import_template(organization=request.organization, dealer=request.dealer)
        response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = 'attachment; filename="nexora_dealer_customer_import_template.xlsx"'
        return response


class DealerCustomerImportPreviewView(DealerPortalView):
    required_rights = ("can_import_customers",)
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            rows = parse_import_file(request.FILES.get("file"), dealer=request.dealer)
        except CustomerImportError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        validated = validate_import_rows(
            organization=request.organization,
            rows=rows,
            dealer=request.dealer,
        )
        valid_count = sum(1 for item in validated if item.is_valid)
        return Response({
            "total_rows": len(validated),
            "valid_count": valid_count,
            "invalid_count": len(validated) - valid_count,
            "rows": [
                {
                    "row": item.row,
                    "valid": item.is_valid,
                    "errors": item.errors,
                    "values": item.values,
                }
                for item in validated
            ],
        })


class DealerCustomerImportView(DealerPortalView):
    required_rights = ("can_import_customers",)
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            result = import_customers(
                organization=request.organization,
                actor=request.user,
                uploaded_file=request.FILES.get("file"),
                create_on_router=False,
                dealer=request.dealer,
            )
        except CustomerImportError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_batch_data(result.batch), status=status.HTTP_201_CREATED)


class DealerCustomerImportHistoryView(DealerPortalView):
    required_rights = ("can_import_customers",)

    def get(self, request):
        batches = (
            CustomerImportBatch.objects.for_organization(request.organization)
            .filter(dealer=request.dealer)
            .select_related("created_by")[:50]
        )
        return Response([_batch_data(batch) for batch in batches])


# ---------------------------------------------------------------------------
# Dealer Export (.xlsx and .pdf)
# ---------------------------------------------------------------------------

def _export_xlsx(rows: list[dict]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Customers"
    headers = [
        "Customer #",
        "Name",
        "Phone",
        "Area",
        "Package",
        "Status",
        "Expiry",
        "Outstanding",
        "Assigned Employee",
    ]
    ws.append(headers)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E79")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill

    for row in rows:
        ws.append([
            row["customer_number"],
            row["customer_name"],
            row["phone"],
            row["area"],
            row["package_name"],
            row["status"],
            row["expiry_date"] or "",
            row["outstanding"],
            row["assigned_employee_name"],
        ])

    for col in ws.columns:
        letter = col[0].column_letter
        ws.column_dimensions[letter].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _export_pdf(rows: list[dict], dealer_name: str, org_name: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = styles["Heading3"]
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)

    elements = [
        Paragraph(f"{org_name} — {dealer_name} Customers", title_style),
        Spacer(1, 4 * mm),
    ]
    table_data = [[
        "Customer #",
        "Name",
        "Phone",
        "Area",
        "Package",
        "Status",
        "Expiry",
        "Outstanding",
        "Employee",
    ]]
    for row in rows:
        table_data.append([
            Paragraph(row["customer_number"], cell_style),
            Paragraph(row["customer_name"], cell_style),
            Paragraph(row["phone"], cell_style),
            Paragraph(row["area"] or "—", cell_style),
            Paragraph(row["package_name"], cell_style),
            Paragraph(row["status"], cell_style),
            Paragraph(row["expiry_date"] or "—", cell_style),
            Paragraph(row["outstanding"], cell_style),
            Paragraph(row["assigned_employee_name"] or "—", cell_style),
        ])

    table = Table(
        table_data,
        colWidths=[24 * mm, 36 * mm, 26 * mm, 28 * mm, 32 * mm, 32 * mm, 22 * mm, 24 * mm, 34 * mm],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    elements.append(table)
    doc.build(elements)
    return buf.getvalue()


class DealerCustomerExportView(DealerPortalView):
    required_rights = ("can_export_customers",)

    def perform_content_negotiation(self, request, force=False):
        # Allow ?format=xlsx or ?format=pdf without DRF raising 406.
        renderer = self.get_renderers()[0]
        return (renderer, renderer.media_type)

    def get(self, request):
        fmt = (
            request.query_params.get("file_format")
            or request.query_params.get("format")
            or "xlsx"
        ).strip().lower()
        if fmt not in {"xlsx", "pdf"}:
            raise ValidationError({"format": "Use xlsx or pdf."})

        rows = _filtered_customer_rows(request)
        if fmt == "pdf":
            content = _export_pdf(rows, request.dealer.name, request.organization.name)
            response = HttpResponse(content, content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="dealer_customers.pdf"'
            return response

        content = _export_xlsx(rows)
        response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = 'attachment; filename="dealer_customers.xlsx"'
        return response
