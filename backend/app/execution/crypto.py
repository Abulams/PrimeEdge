import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet

MASTER_SECRET = os.getenv("EXECUTION_MASTER_KEY", "MarketOS_Cloud_Execution_Secret_Master_Key_2026_Prod")
_key_bytes = hashlib.sha256(MASTER_SECRET.encode("utf-8")).digest()
_fernet_key = base64.urlsafe_b64encode(_key_bytes)
_cipher = Fernet(_fernet_key)


def encrypt_credential(plain_text: str) -> str:
    """Encrypts sensitive broker credential (e.g. password) for secure storage at rest."""
    if not plain_text:
        return ""
    encrypted_bytes = _cipher.encrypt(plain_text.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_credential(cipher_text: str) -> str:
    """Decrypts broker credential for authorized worker dispatch."""
    if not cipher_text:
        return ""
    try:
        decrypted_bytes = _cipher.decrypt(cipher_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return ""


def mask_credential(plain_text: Optional[str]) -> str:
    """Returns masked credential for display in logs or UI (never exposes raw password)."""
    return "••••••••"
