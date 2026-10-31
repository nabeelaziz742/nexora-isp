import base64
import hashlib
import secrets
import string

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class NetworkCredentialError(Exception):
    pass


def _get_fernet() -> Fernet:
    configured_key = settings.NETWORK_CREDENTIALS_KEY
    if configured_key:
        return Fernet(configured_key.encode())

    derived_key = base64.urlsafe_b64encode(
        hashlib.sha256(
            f"nexora-network-credentials:{settings.SECRET_KEY}".encode()
        ).digest()
    )
    return Fernet(derived_key)


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise NetworkCredentialError(
            "Stored network credential could not be decrypted. "
            "Check NETWORK_CREDENTIALS_KEY."
        ) from exc


def generate_network_password(length: int = 12) -> str:
    # Avoid look-alike characters so staff can read the password to customers over the phone.
    alphabet = "".join(
        ch for ch in string.ascii_letters + string.digits
        if ch not in "0O1lI"
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))
