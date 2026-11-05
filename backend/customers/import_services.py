"""Bulk import of existing customers (e.g. an ISP moving from other software).

Imported customers are taken as already connected: by default the router is
not touched, no first-month invoice is raised and no messages are sent. An
opening balance becomes one "Opening balance" invoice and an advance becomes
unallocated credit.
"""
import csv
import io
import ipaddress
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from customers.models import (
    BillingProfile,
    Customer,
    CustomerImportBatch,
    Dealer,
    InternetPackage,
    NotificationPreference,
    ServiceAccount,
)
from customers.services import (
    _build_customer_number,
    _build_service_number,
    _lock_organization_for_numbering,
)
from network.credentials import encrypt_secret
from network.models import NetworkAssignment, NetworkNode
from tenancy.services import record_audit_log

MAX_IMPORT_ROWS = 2000
MAX_IMPORT_BYTES = 5 * 1024 * 1024
SHEET_NAME = "Customers"


class CustomerImportError(Exception):
    pass


@dataclass(frozen=True)
class ImportColumn:
    key: str
    required: bool
    example: str
    notes: str


# Single source of truth for the template, parsing and validation.
COLUMNS = [
    ImportColumn("first_name", True, "Ali", ""),
    ImportColumn("last_name", False, "Khan", ""),
    ImportColumn("phone", True, "03001234567", "Used to detect duplicates."),
    ImportColumn("alternate_phone", False, "03211234567", ""),
    ImportColumn("email", False, "ali@example.com", ""),
    ImportColumn("cnic", False, "35202-1234567-1", "13 digits, with or without dashes."),
    ImportColumn("address", True, "House 12, Street 4", ""),
    ImportColumn("area", False, "Johar Town", ""),
    ImportColumn("city", True, "Lahore", ""),
    ImportColumn("legacy_id", False, "WAS-1043", "Customer ID in your old software."),
    ImportColumn("dealer_code", False, "", "From the Codes sheet."),
    ImportColumn("package_code", True, "F-20", "From the Codes sheet."),
    ImportColumn("billing_mode", True, "MONTHLY", "MONTHLY or PREPAID."),
    ImportColumn("billing_day", False, "1", "1-28, monthly only. Default 1."),
    ImportColumn("due_day", False, "10", "1-28, monthly only. Default 10."),
    ImportColumn("expiry_date", False, "", "Required for PREPAID. YYYY-MM-DD."),
    ImportColumn("opening_balance", False, "2500", "Previous dues; becomes one invoice."),
    ImportColumn("advance", False, "", "Credit the customer already has."),
    ImportColumn("status", False, "ACTIVE", "ACTIVE or SUSPENDED. Default ACTIVE."),
    ImportColumn("activation_date", False, "2025-03-15", "When the customer joined. Default today."),
    ImportColumn("node_code", False, "RTR-01", "From the Codes sheet."),
    ImportColumn("pppoe_username", False, "ali-johar", "Requires node_code."),
    ImportColumn("pppoe_password", False, "", "Stored encrypted."),
    ImportColumn("ip_address", False, "", "Static IP, if any."),
    ImportColumn("whatsapp_enabled", False, "YES", "YES or NO. Default YES."),
    ImportColumn("sms_enabled", False, "NO", "YES or NO. Default NO."),
]
COLUMN_KEYS = [column.key for column in COLUMNS]
REQUIRED_KEYS = [column.key for column in COLUMNS if column.required]
TEXT_COLUMNS = {"phone", "alternate_phone", "cnic", "legacy_id", "pppoe_username", "pppoe_password", "ip_address"}


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

def build_import_template(*, organization) -> bytes:
    """Excel workbook: an empty Customers sheet, instructions and the tenant's codes."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    workbook = Workbook()
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E79")
    required_fill = PatternFill("solid", fgColor="9C2A2A")

    sheet = workbook.active
    sheet.title = SHEET_NAME
    sheet.append(COLUMN_KEYS)
    for index, column in enumerate(COLUMNS, start=1):
        cell = sheet.cell(row=1, column=index)
        cell.font = header_font
        cell.fill = required_fill if column.required else header_fill
        letter = cell.column_letter
        sheet.column_dimensions[letter].width = max(14, len(column.key) + 4)
        if column.key in TEXT_COLUMNS:
            # Text format keeps the leading 0 of phone numbers and CNIC dashes.
            for row in range(2, MAX_IMPORT_ROWS + 2):
                sheet.cell(row=row, column=index).number_format = "@"
    sheet.freeze_panes = "A2"

    guide = workbook.create_sheet("Instructions")
    guide.append(["How to use this template"])
    guide["A1"].font = Font(bold=True, size=13)
    guide.append(["Fill one customer per row on the Customers sheet. Red headers are required."])
    guide.append(["Use the exact codes from the Codes sheet for packages, nodes and dealers."])
    guide.append(["Imported customers are treated as already connected: the router is not changed,"])
    guide.append(["no first bill is created and no messages are sent."])
    guide.append([])
    guide.append(["Column", "Required", "Example", "Notes"])
    for cell in guide[7]:
        cell.font = header_font
        cell.fill = header_fill
    for column in COLUMNS:
        guide.append([column.key, "Yes" if column.required else "", column.example, column.notes])
    guide.append([])
    guide.append(["Example row (copy to the Customers sheet and replace with real data):"])
    guide.append(COLUMN_KEYS)
    guide.append([column.example for column in COLUMNS])
    for letter, width in zip("ABCD", (20, 10, 22, 48)):
        guide.column_dimensions[letter].width = width

    codes = workbook.create_sheet("Codes")
    codes.append(["Package code", "Package name", "Price", "", "Node code", "Node name", "", "Dealer code", "Dealer name"])
    for cell in codes[1]:
        if cell.value:
            cell.font = header_font
            cell.fill = header_fill
    packages = list(
        InternetPackage.objects.for_organization(organization).filter(is_active=True).order_by("name")
    )
    nodes = list(
        NetworkNode.objects.for_organization(organization).filter(is_active=True).order_by("code")
    )
    dealers = list(Dealer.objects.for_organization(organization).order_by("dealer_code"))
    for row in range(max(len(packages), len(nodes), len(dealers))):
        package = packages[row] if row < len(packages) else None
        node = nodes[row] if row < len(nodes) else None
        dealer = dealers[row] if row < len(dealers) else None
        codes.append([
            package.code if package else "",
            package.name if package else "",
            float(package.monthly_price) if package else "",
            "",
            node.code if node else "",
            node.name if node else "",
            "",
            dealer.dealer_code if dealer else "",
            dealer.name if dealer else "",
        ])
    for letter in "ABCDEFGHI":
        codes.column_dimensions[letter].width = 18

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _normalize_header(value) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _cell_to_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_import_file(uploaded_file) -> list[dict]:
    """Rows as {column_key: text}, each with its spreadsheet row number."""
    if uploaded_file is None:
        raise CustomerImportError("Choose an Excel (.xlsx) or CSV file to upload.")
    if uploaded_file.size > MAX_IMPORT_BYTES:
        raise CustomerImportError("The file must be 5 MB or smaller.")

    name = (uploaded_file.name or "").lower()
    uploaded_file.seek(0)
    head = uploaded_file.read(4)
    uploaded_file.seek(0)

    if head.startswith(b"PK"):
        raw_rows = _read_xlsx(uploaded_file)
    elif name.endswith(".csv") or name.endswith(".txt"):
        raw_rows = _read_csv(uploaded_file)
    else:
        raise CustomerImportError("Upload the Excel (.xlsx) template or a CSV file.")

    if not raw_rows:
        raise CustomerImportError("The file is empty.")

    headers = [_normalize_header(value) for value in raw_rows[0]]
    missing = [key for key in REQUIRED_KEYS if key not in headers]
    if missing:
        raise CustomerImportError(
            "Missing required columns: " + ", ".join(missing) + ". Please use the template."
        )

    rows = []
    for offset, values in enumerate(raw_rows[1:], start=2):
        record = {
            header: _cell_to_text(values[index]) if index < len(values) else ""
            for index, header in enumerate(headers)
            if header in COLUMN_KEYS
        }
        if not any(record.values()):
            continue
        record["_row"] = offset
        rows.append(record)

    if not rows:
        raise CustomerImportError("No customer rows were found in the file.")
    if len(rows) > MAX_IMPORT_ROWS:
        raise CustomerImportError(f"A file can hold at most {MAX_IMPORT_ROWS} customers; split it into smaller files.")
    return rows


def _read_xlsx(uploaded_file) -> list[list]:
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    except Exception as exc:
        raise CustomerImportError("The Excel file could not be read.") from exc
    sheet = workbook[SHEET_NAME] if SHEET_NAME in workbook.sheetnames else workbook.worksheets[0]
    rows = [list(row) for row in sheet.iter_rows(values_only=True)]
    workbook.close()
    return rows


def _read_csv(uploaded_file) -> list[list]:
    content = uploaded_file.read()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise CustomerImportError("The CSV file could not be read; save it as UTF-8.")
    return [row for row in csv.reader(io.StringIO(text))]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(r"^\+?\d{10,15}$")
YES = {"yes", "y", "true", "1"}
NO = {"no", "n", "false", "0"}


def _normalize_phone(value: str) -> str:
    phone = re.sub(r"[\s\-()]", "", value)
    # Excel drops the leading zero of mobile numbers stored as numbers.
    if len(phone) == 10 and phone.startswith("3"):
        phone = "0" + phone
    return phone


def _parse_date(value: str):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_money(value: str, label: str, errors: list) -> Decimal:
    if not value:
        return Decimal("0.00")
    try:
        amount = Decimal(value.replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation:
        errors.append(f"{label} must be a number.")
        return Decimal("0.00")
    if amount < 0:
        errors.append(f"{label} cannot be negative.")
    return amount


def _parse_flag(value: str, default: bool, label: str, errors: list) -> bool:
    if not value:
        return default
    lowered = value.lower()
    if lowered in YES:
        return True
    if lowered in NO:
        return False
    errors.append(f"{label} must be YES or NO.")
    return default


@dataclass
class ValidatedRow:
    row: int
    values: dict
    errors: list = field(default_factory=list)
    cleaned: dict = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_import_rows(*, organization, rows: list[dict]) -> list[ValidatedRow]:
    packages = {
        package.code.lower(): package
        for package in InternetPackage.objects.for_organization(organization).filter(is_active=True)
    }
    nodes = {
        node.code.lower(): node
        for node in NetworkNode.objects.for_organization(organization).filter(is_active=True)
    }
    dealers = {dealer.dealer_code.lower(): dealer for dealer in Dealer.objects.for_organization(organization)}
    existing_phones = set(Customer.objects.for_organization(organization).values_list("phone", flat=True))
    existing_legacy = {
        value.lower()
        for value in Customer.objects.for_organization(organization)
        .exclude(legacy_id="")
        .values_list("legacy_id", flat=True)
    }
    existing_usernames = {
        (node_id, username.lower())
        for node_id, username in NetworkAssignment.objects.for_organization(organization)
        .filter(is_active=True)
        .exclude(username="")
        .values_list("network_node_id", "username")
    }

    seen_phones, seen_legacy, seen_usernames = set(), set(), set()
    today = timezone.localdate()
    results = []

    for raw in rows:
        values = {key: raw.get(key, "").strip() for key in COLUMN_KEYS}
        result = ValidatedRow(row=raw["_row"], values=values)
        errors = result.errors

        for key in REQUIRED_KEYS:
            if not values[key]:
                errors.append(f"{key} is required.")

        phone = _normalize_phone(values["phone"]) if values["phone"] else ""
        if phone:
            if not PHONE_RE.match(phone):
                errors.append("phone is not a valid number.")
            elif phone in existing_phones:
                errors.append("A customer with this phone already exists.")
            elif phone in seen_phones:
                errors.append("This phone appears twice in the file.")
            seen_phones.add(phone)

        alternate_phone = _normalize_phone(values["alternate_phone"]) if values["alternate_phone"] else ""
        if alternate_phone and not PHONE_RE.match(alternate_phone):
            errors.append("alternate_phone is not a valid number.")

        email = values["email"].lower()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("email is not valid.")

        cnic_digits = re.sub(r"\D", "", values["cnic"])
        cnic = ""
        if values["cnic"]:
            if len(cnic_digits) != 13:
                errors.append("cnic must have 13 digits.")
            else:
                cnic = f"{cnic_digits[:5]}-{cnic_digits[5:12]}-{cnic_digits[12]}"

        legacy_id = values["legacy_id"]
        if legacy_id:
            if legacy_id.lower() in existing_legacy:
                errors.append("A customer with this legacy_id was already imported.")
            elif legacy_id.lower() in seen_legacy:
                errors.append("This legacy_id appears twice in the file.")
            seen_legacy.add(legacy_id.lower())

        dealer = None
        if values["dealer_code"]:
            dealer = dealers.get(values["dealer_code"].lower())
            if dealer is None:
                errors.append(f"Dealer code '{values['dealer_code']}' was not found.")

        package = None
        if values["package_code"]:
            package = packages.get(values["package_code"].lower())
            if package is None:
                errors.append(f"Package code '{values['package_code']}' was not found or is inactive.")

        billing_mode = values["billing_mode"].upper()
        if values["billing_mode"] and billing_mode not in BillingProfile.BillingCycle.values:
            errors.append("billing_mode must be MONTHLY or PREPAID.")

        billing_day, due_day = 1, 10
        for key, default in (("billing_day", 1), ("due_day", 10)):
            if values[key]:
                try:
                    number = int(float(values[key]))
                except ValueError:
                    number = 0
                if not 1 <= number <= 28:
                    errors.append(f"{key} must be between 1 and 28.")
                    number = default
            else:
                number = default
            if key == "billing_day":
                billing_day = number
            else:
                due_day = number

        expiry_date = None
        if values["expiry_date"]:
            expiry_date = _parse_date(values["expiry_date"])
            if expiry_date is None:
                errors.append("expiry_date must be a date like 2026-11-30.")
        elif billing_mode == BillingProfile.BillingCycle.PREPAID:
            errors.append("expiry_date is required for PREPAID customers.")

        activation_date = today
        if values["activation_date"]:
            activation_date = _parse_date(values["activation_date"])
            if activation_date is None:
                errors.append("activation_date must be a date like 2025-03-15.")
                activation_date = today
            elif activation_date > today:
                errors.append("activation_date cannot be in the future.")

        opening_balance = _parse_money(values["opening_balance"], "opening_balance", errors)
        advance = _parse_money(values["advance"], "advance", errors)
        if opening_balance > 0 and advance > 0:
            errors.append("Give either opening_balance or advance, not both.")

        status = (values["status"] or "ACTIVE").upper()
        if status not in {"ACTIVE", "SUSPENDED"}:
            errors.append("status must be ACTIVE or SUSPENDED.")

        node = None
        if values["node_code"]:
            node = nodes.get(values["node_code"].lower())
            if node is None:
                errors.append(f"Node code '{values['node_code']}' was not found or is inactive.")

        username = values["pppoe_username"]
        if username:
            if not values["node_code"]:
                errors.append("pppoe_username needs a node_code.")
            elif node is not None:
                key = (node.id, username.lower())
                if key in existing_usernames:
                    errors.append(f"PPPoE username '{username}' is already used on {node.code}.")
                elif key in seen_usernames:
                    errors.append(f"PPPoE username '{username}' appears twice for {node.code}.")
                seen_usernames.add(key)

        ip_address = values["ip_address"] or None
        if ip_address:
            try:
                ipaddress.ip_address(ip_address)
            except ValueError:
                errors.append("ip_address is not a valid IP address.")

        whatsapp_enabled = _parse_flag(values["whatsapp_enabled"], True, "whatsapp_enabled", errors)
        sms_enabled = _parse_flag(values["sms_enabled"], False, "sms_enabled", errors)

        if not errors:
            result.cleaned = {
                "first_name": values["first_name"],
                "last_name": values["last_name"],
                "phone": phone,
                "alternate_phone": alternate_phone,
                "email": email,
                "cnic": cnic,
                "address_line": values["address"],
                "area": values["area"],
                "city": values["city"],
                "legacy_id": legacy_id,
                "dealer": dealer,
                "package": package,
                "billing_mode": billing_mode,
                "billing_day": billing_day,
                "due_day": due_day,
                "expiry_date": expiry_date,
                "opening_balance": opening_balance,
                "advance": advance,
                "status": status,
                "activation_date": activation_date,
                "node": node,
                "pppoe_username": username,
                "pppoe_password": values["pppoe_password"],
                "ip_address": ip_address,
                "whatsapp_enabled": whatsapp_enabled,
                "sms_enabled": sms_enabled,
            }
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

@dataclass
class ImportResult:
    batch: CustomerImportBatch
    imported_customer_ids: list


def _import_one(*, organization, actor, data: dict, create_on_router: bool) -> Customer:
    from billing.models import Payment
    from billing.services import generate_custom_invoice, record_payment_with_allocations
    from network.services import create_activation_network_request

    organization = _lock_organization_for_numbering(organization=organization)

    customer = Customer.objects.create(
        organization=organization,
        customer_number=_build_customer_number(organization=organization),
        dealer=data["dealer"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone=data["phone"],
        alternate_phone=data["alternate_phone"],
        email=data["email"],
        cnic=data["cnic"],
        legacy_id=data["legacy_id"],
        address_line=data["address_line"],
        area=data["area"],
        city=data["city"],
        is_active=True,
    )

    activated_at = timezone.make_aware(datetime.combine(data["activation_date"], time(12, 0)))
    is_prepaid = data["billing_mode"] == BillingProfile.BillingCycle.PREPAID
    service_account = ServiceAccount.objects.create(
        organization=organization,
        service_number=_build_service_number(organization=organization),
        customer=customer,
        internet_package=data["package"],
        status=ServiceAccount.Status.ACTIVE,
        activated_at=activated_at,
        expiry_date=data["expiry_date"] if is_prepaid else None,
    )

    BillingProfile.objects.create(
        organization=organization,
        service_account=service_account,
        billing_cycle=data["billing_mode"],
        billing_day=data["billing_day"],
        due_day=data["due_day"],
    )

    NotificationPreference.objects.create(
        organization=organization,
        customer=customer,
        sms_enabled=data["sms_enabled"],
        whatsapp_enabled=data["whatsapp_enabled"],
    )

    node = data["node"]
    if node is not None:
        if create_on_router:
            create_activation_network_request(
                organization=organization,
                service_account=service_account,
                network_node_id=node.id,
                username=data["pppoe_username"],
                password=data["pppoe_password"],
                ip_address=data["ip_address"],
                provisioning_payload={"source": "customer_import"},
            )
        else:
            # Already live on the router: record the link only.
            NetworkAssignment.objects.create(
                organization=organization,
                service_account=service_account,
                network_node=node,
                username=data["pppoe_username"],
                network_password_encrypted=encrypt_secret(data["pppoe_password"]),
                ip_address=data["ip_address"],
            )

    today = timezone.localdate()
    if data["opening_balance"] > 0:
        generate_custom_invoice(
            organization=organization,
            actor=actor,
            service_account_id=service_account.id,
            billing_period_start=today,
            billing_period_end=today,
            issue_date=today,
            due_date=today,
            line_items=[{"description": "Opening balance (imported)", "amount": data["opening_balance"]}],
            notes="Previous dues carried over from customer import.",
        )

    if data["advance"] > 0:
        record_payment_with_allocations(
            organization=organization,
            actor=actor,
            service_account_id=service_account.id,
            amount=data["advance"],
            payment_method=Payment.Method.OTHER,
            reference="OPENING-ADVANCE",
            notes="Advance carried over from customer import.",
            notify=False,
        )

    # Status last, so the advance payment cannot trigger an automatic restore.
    if data["status"] == "SUSPENDED":
        service_account.status = ServiceAccount.Status.SUSPENDED_NON_PAYMENT
        service_account.save(update_fields=["status", "updated_at"])

    return customer


def import_customers(
    *,
    organization,
    actor,
    uploaded_file,
    create_on_router: bool = False,
) -> ImportResult:
    """Import every valid row; invalid rows are skipped and reported."""
    if not organization.is_active:
        raise CustomerImportError("Organization is inactive.")

    rows = parse_import_file(uploaded_file)
    validated = validate_import_rows(organization=organization, rows=rows)

    errors = [{"row": item.row, "errors": item.errors} for item in validated if not item.is_valid]
    imported_ids = []

    for item in validated:
        if not item.is_valid:
            continue
        try:
            with transaction.atomic():
                customer = _import_one(
                    organization=organization,
                    actor=actor,
                    data=item.cleaned,
                    create_on_router=create_on_router,
                )
            imported_ids.append(str(customer.id))
        except Exception as exc:
            errors.append({"row": item.row, "errors": [f"Could not be imported: {exc}"]})

    errors.sort(key=lambda entry: entry["row"])
    batch = CustomerImportBatch.objects.create(
        organization=organization,
        file_name=(uploaded_file.name or "")[:255],
        total_rows=len(validated),
        imported_count=len(imported_ids),
        skipped_count=len(validated) - len(imported_ids),
        create_on_router=create_on_router,
        errors=errors,
        created_by=actor,
    )

    record_audit_log(
        organization=organization,
        actor=actor,
        action="CUSTOMERS_IMPORTED",
        resource_type="CustomerImportBatch",
        resource_id=batch.id,
        metadata={
            "file_name": batch.file_name,
            "total_rows": batch.total_rows,
            "imported": batch.imported_count,
            "skipped": batch.skipped_count,
            "create_on_router": create_on_router,
        },
    )

    return ImportResult(batch=batch, imported_customer_ids=imported_ids)
