"""A dealer's portal password is made by the system and sent to the dealer.

Nobody at the ISP ever sees or types it. Adding a dealer with a login, or
pressing "Resend password", makes a new password, sets it, and sends it:
- always by email, to the dealer's login email (server SMTP settings);
- also on WhatsApp, from the ISP's own business number, when the ISP has one
  connected.
It is enough that one of them arrives. If neither can be sent nothing changes:
the login is not created and an old password keeps working.

The password is never written to the communication queue or logs; messages
are sent directly.
"""
import logging
import secrets
import string

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from rest_framework.exceptions import ValidationError

from communications.models import CommunicationProvider, CommunicationTemplate
from communications.providers.factory import ProviderFactory
from customers.dealer_portal import _get_dealer, grant_portal_access
from tenancy.services import record_audit_log

logger = logging.getLogger(__name__)

# The approved Meta template each ISP registers for this message. An ISP can
# use its own template by adding one named TEMPLATE_OVERRIDE_NAME in
# Communications > Templates.
META_TEMPLATE_NAME = "nexora_dealer_login"
META_TEMPLATE_PARAMS = ["dealer_name", "isp_name", "login_email", "password", "login_url"]
TEMPLATE_OVERRIDE_NAME = "Dealer login"

PASSWORD_ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")


def generate_password() -> str:
    return "Dl-" + "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(10))


def masked_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"{digits[:4]}****{digits[-3:]}" if len(digits) >= 7 else "****"


def whatsapp_provider(organization):
    """The ISP's connected WhatsApp number, or None."""
    candidates = CommunicationProvider.objects.filter(
        organization=organization,
        provider_type=CommunicationProvider.ProviderType.WHATSAPP,
        status=CommunicationProvider.Status.ACTIVE,
        is_connected=True,
    ).order_by("-is_default", "created_at")
    for provider in candidates:
        if ProviderFactory.get(provider).is_configured(provider=provider):
            return provider
    return None


def _template_message(organization, provider, values: dict) -> dict:
    override = (
        CommunicationTemplate.objects.filter(
            organization=organization,
            communication_provider=provider,
            name=TEMPLATE_OVERRIDE_NAME,
            status=CommunicationTemplate.Status.ACTIVE,
        )
        .exclude(whatsapp_template_name="")
        .first()
    )
    name = override.whatsapp_template_name if override else META_TEMPLATE_NAME
    params = (override.whatsapp_template_params or META_TEMPLATE_PARAMS) if override else META_TEMPLATE_PARAMS
    return {
        "name": name.strip(),
        "language": ((override.whatsapp_template_language if override else "") or "en").strip(),
        "parameters": [values.get(param, "") for param in params],
    }


def send_whatsapp(*, provider, phone: str, text: str, template_message: dict) -> dict:
    return ProviderFactory.get(provider).send(
        recipient=phone, message=text, provider=provider, template_message=template_message,
    )


def masked_email(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}" if domain else "***"


def send_email(*, to: str, subject: str, text: str) -> bool:
    try:
        EmailMessage(subject=subject, body=text, from_email=settings.DEFAULT_FROM_EMAIL, to=[to]).send(
            fail_silently=False,
        )
        return True
    except Exception:  # noqa: BLE001 - a mail outage is reported to the ISP, not raised
        logger.exception("Could not email a dealer login.")
        return False


@transaction.atomic
def send_dealer_login(*, organization, actor, dealer_id, email: str = "") -> dict:
    """Create the dealer's login (or give it a new password) and send it to them."""
    dealer = _get_dealer(organization, dealer_id)

    current = dealer.portal_membership
    email = (email or (current.user.email if current else "")).strip().lower()
    if not email:
        raise ValidationError({"email": "Enter the email the dealer will sign in with."})

    password = generate_password()
    is_new = current is None
    dealer = grant_portal_access(
        organization=organization, actor=actor, dealer_id=dealer.id, email=email, password=password,
    )

    login_url = f"{settings.FRONTEND_BASE_URL}/"
    text = (
        f"Assalam o Alaikum {dealer.name}!\n"
        f"Your {organization.name} dealer login:\n"
        f"Link: {login_url}\n"
        f"Email: {email}\n"
        f"Password: {password}\n"
        "Please change the password after signing in (Change Password)."
    )

    sent_to = []
    if send_email(to=email, subject=f"Your {organization.name} dealer login", text=text):
        sent_to.append(f"email {masked_email(email)}")

    provider = whatsapp_provider(organization)
    phone = (dealer.phone or "").strip()
    if provider is not None and phone:
        values = {
            "dealer_name": dealer.name,
            "isp_name": organization.name,
            "login_email": email,
            "password": password,
            "login_url": login_url,
        }
        result = send_whatsapp(
            provider=provider,
            phone=phone,
            text=text,
            template_message=_template_message(organization, provider, values),
        )
        if result.get("success"):
            sent_to.append(f"WhatsApp {masked_phone(phone)}")
        else:
            logger.warning("Dealer login WhatsApp was not accepted: %s", result.get("error"))

    if not sent_to:
        # Raising rolls back the transaction: no new login, old password still valid.
        raise ValidationError({
            "detail": (
                "The password could not be sent: the email did not go out"
                + ("" if provider else " and WhatsApp is not connected")
                + ". Check the email (SMTP) settings. Nothing was changed."
            )
        })

    sent_text = " and ".join(sent_to)
    record_audit_log(
        organization=organization,
        actor=actor,
        action="DEALER_LOGIN_SENT" if is_new else "DEALER_PASSWORD_RESENT",
        resource_type="Dealer",
        resource_id=dealer.id,
        metadata={"dealer_code": dealer.dealer_code, "email": email, "sent_to": sent_text},
    )
    return {"dealer": dealer, "sent_to": sent_text, "is_new": is_new}
