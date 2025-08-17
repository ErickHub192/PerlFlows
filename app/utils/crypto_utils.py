# app/utils/crypto_utils.py

import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

def _get_aesgcm_key() -> bytes:
    """
    Deriva una clave de 32 bytes a partir de settings.SECRET_KEY usando SHA-256.
    """
    secret = settings.SECRET_KEY.encode()
    return hashlib.sha256(secret).digest()

def encrypt_bytes(plaintext: bytes) -> bytes:
    """
    Cifra los bytes ´plaintext´ usando AES-GCM.
    Retorna un blob de bytes: nonce(12) || ciphertext.
    """
    key = _get_aesgcm_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext

def decrypt_bytes(cipher_blob: bytes) -> str:
    """
    Desencripta el blob cifrado (nonce(12) || ciphertext) usando AES-GCM.
    Retorna el texto descifrado como cadena UTF-8.
    """
    key = _get_aesgcm_key()
    aesgcm = AESGCM(key)
    nonce = cipher_blob[:12]
    ciphertext = cipher_blob[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
