"""A dealer's portal password is made by the system and sent only on WhatsApp.

Nobody at the ISP ever sees or types it. Adding a dealer with a login, or
pressing "Resend password", makes a new password, sets it, and sends it to the
dealer's phone on the ISP's own WhatsApp number. If the message cannot be sent
nothing changes: the login is not created and an old password keeps working.

The password is never written to the communication queue or logs; the message
is sent directly through the provider.
"""
import secrets
import string

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from communications.models import CommunicationProvider, CommunicationTemplate
from communications.providers.factory import ProviderFactory
from customers.dealer_portal import _get_dealer, grant_portal_access
from tenancy.services import record_audit_log

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


def check_can_send(organization, dealer) -> CommunicationProvider:
    provider = whatsapp_provider(organization)
    if provider is None:
        raise ValidationError({
            "detail": (
                "Connect your WhatsApp number first (Settings > Communications). "
                "Dealer passwords are sent only on WhatsApp."
            )
        })
    if not (dealer.phone or "").strip():
        raise ValidationError({"detail": "Add the dealer's WhatsApp phone number first."})
    return provider


@transaction.atomic
def send_dealer_login(*, organization, actor, dealer_id, email: str = "") -> dict:
    """Create the dealer's login (or give it a new password) and WhatsApp it to them."""
    dealer = _get_dealer(organization, dealer_id)
    provider = check_can_send(organization, dealer)

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
    values = {
        "dealer_name": dealer.name,
        "isp_name": organization.name,
        "login_email": email,
        "password": password,
        "login_url": login_url,
    }
    text = (
        f"Assalam o Alaikum {dealer.name}!\n"
        f"Your {organization.name} dealer login:\n"
        f"Link: {login_url}\n"
        f"Email: {email}\n"
        f"Password: {password}\n"
        "Please change the password after signing in (Change Password)."
    )
    result = send_whatsapp(
        provider=provider,
        phone=dealer.phone,
        text=text,
        template_message=_template_message(organization, provider, values),
    )
    if not result.get("success"):
        # Raising rolls back the transaction: no new login, old password still valid.
        reason = result.get("error") or "WhatsApp did not accept the message."
        raise ValidationError({
            "detail": f"The password could not be sent on WhatsApp ({reason}). Nothing was changed."
        })

    sent_to = masked_phone(dealer.phone)
    record_audit_log(
        organization=organization,
        actor=actor,
        action="DEALER_LOGIN_SENT_ON_WHATSAPP" if is_new else "DEALER_PASSWORD_RESENT_ON_WHATSAPP",
        resource_type="Dealer",
        resource_id=dealer.id,
        metadata={"dealer_code": dealer.dealer_code, "email": email, "sent_to": sent_to},
    )
    return {"dealer": dealer, "sent_to": sent_to, "is_new": is_new}
