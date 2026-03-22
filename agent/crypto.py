import os
from cryptography.fernet import Fernet

_raw = os.getenv("ENCRYPTION_KEY", "")
_fernet = Fernet(_raw.encode()) if _raw else None

def encrypt(plaintext: str) -> str:
    if not plaintext or not _fernet:
        return plaintext
    return _fernet.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    if not ciphertext or not _fernet:
        return ciphertext
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""
