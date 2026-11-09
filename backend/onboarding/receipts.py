"""Receipts for the subscription fees an ISP pays to Nexora."""
import io
import logging
from xml.sax.saxutils import escape

from django.core.mail import EmailMessage
from django.db.models import Max
from django.utils import timezone
from django.utils.formats import date_format
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from onboarding.models import ISPSubscriptionPayment

logger = logging.getLogger(__name__)

RECEIPT_PREFIX = "NXR-"
BRAND = colors.HexColor("#1D4ED8")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#CBD5E1")


def next_receipt_number() -> str:
    """Next number in the platform-wide sequence (the unique column guards races)."""
    last = ISPSubscriptionPayment.objects.filter(receipt_number__startswith=RECEIPT_PREFIX).aggregate(
        last=Max("receipt_number")
    )["last"]
    sequence = int(last[len(RECEIPT_PREFIX):]) + 1 if last else 1
    return f"{RECEIPT_PREFIX}{sequence:06d}"


def _owner_email(organization) -> str:
    from onboarding.platform_services import _owner_of

    owner = _owner_of(organization)
    return owner.email if owner else ""


def _pkr(value) -> str:
    return f"PKR {value:,.2f}"


def _day(value) -> str:
    return date_format(value, "d M Y")


def receipt_filename(payment: ISPSubscriptionPayment) -> str:
    return f"{payment.receipt_number or 'receipt'}-{payment.organization.code}.pdf"


def build_receipt_pdf(payment: ISPSubscriptionPayment) -> bytes:
    organization = payment.organization
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=MUTED)
    label = ParagraphStyle("label", parent=small, fontName="Helvetica-Bold")
    right = ParagraphStyle("right", parent=body, alignment=TA_RIGHT)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Receipt {payment.receipt_number}", author="Nexora",
    )
    width = doc.width
    story = []

    header = Table(
        [[
            Paragraph('<font size="20" color="#1D4ED8"><b>Nexora</b></font><br/>'
                      '<font size="8" color="#64748B">ISP management platform</font>', body),
            Paragraph('<font size="14"><b>PAYMENT RECEIPT</b></font><br/>'
                      f'<font size="9">No. <b>{payment.receipt_number or "-"}</b></font><br/>'
                      f'<font size="9">Date: {_day(timezone.localtime(payment.created_at))}</font>', right),
        ]],
        colWidths=[width * 0.5, width * 0.5],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))
    story += [header, Spacer(1, 8 * mm)]

    address = ", ".join(part for part in [organization.address, organization.city] if part)
    contact = " · ".join(part for part in [organization.phone, _owner_email(organization)] if part)
    received_from = [
        Paragraph("RECEIVED FROM", label),
        Paragraph(f"<b>{escape(organization.name)}</b> ({escape(organization.code)})", body),
    ]
    if address:
        received_from.append(Paragraph(escape(address), body))
    if contact:
        received_from.append(Paragraph(escape(contact), body))
    story += received_from + [Spacer(1, 7 * mm)]

    months = f"{payment.months} month{'s' if payment.months != 1 else ''}"
    lines = Table(
        [
            ["Description", "Period", "Amount"],
            [
                Paragraph(f"Nexora subscription fee ({months})", body),
                f"{_day(payment.period_start)} to {_day(payment.period_end)}",
                _pkr(payment.amount),
            ],
            ["", "Total paid", _pkr(payment.amount)],
        ],
        colWidths=[width * 0.45, width * 0.33, width * 0.22],
    )
    lines.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
        ("LINEBELOW", (0, 0), (-1, 1), 0.5, LINE),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("FONTNAME", (1, 2), (2, 2), "Helvetica-Bold"),
        ("FONTSIZE", (1, 2), (2, 2), 11),
        ("LINEABOVE", (1, 2), (2, 2), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [lines, Spacer(1, 7 * mm)]

    details = [
        ["Payment method", payment.get_method_display()],
        ["Reference", Paragraph(escape(payment.reference) or "-", body)],
        ["Service paid until", _day(payment.period_end)],
    ]
    if payment.recorded_by:
        details.append(["Received by", payment.recorded_by.get_full_name() or payment.recorded_by.email])
    details_table = Table(details, colWidths=[width * 0.3, width * 0.7])
    details_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [details_table, Spacer(1, 14 * mm)]

    story.append(Paragraph(
        "Thank you for your payment. This is a computer-generated receipt and needs no signature.", small,
    ))
    doc.build(story)
    return buffer.getvalue()


def email_receipt(payment: ISPSubscriptionPayment) -> bool:
    """Email the receipt PDF to the ISP owner. Never raises: the payment is already saved."""
    recipient = _owner_email(payment.organization)
    if not recipient:
        return False
    organization = payment.organization
    message = EmailMessage(
        subject=f"Nexora payment receipt {payment.receipt_number}",
        body=(
            f"Dear {organization.name},\n\n"
            f"We have received {_pkr(payment.amount)} for your Nexora subscription "
            f"({_day(payment.period_start)} to {_day(payment.period_end)}).\n"
            f"Your service is now paid until {_day(payment.period_end)}.\n\n"
            "The receipt is attached. You can also download it any time from Settings in your Nexora account.\n\n"
            "Nexora"
        ),
        to=[recipient],
    )
    message.attach(receipt_filename(payment), build_receipt_pdf(payment), "application/pdf")
    try:
        message.send(fail_silently=False)
    except Exception:  # noqa: BLE001 - mail outages must not undo a recorded payment
        logger.exception("Could not email subscription receipt %s", payment.receipt_number)
        return False
    return True
