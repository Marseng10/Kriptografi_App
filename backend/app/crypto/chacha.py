import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

def generate_chacha_key() -> bytes:
    """Generate a random 256-bit (32 bytes) ChaCha20 key."""
    return ChaCha20Poly1305.generate_key()

def encrypt_file_data(data: bytes, key: bytes) -> dict:
    """
    Encrypt raw file bytes with ChaCha20-Poly1305.
    Returns ciphertext bytes, nonce b64, and auth_tag b64.
    """
    chacha = ChaCha20Poly1305(key)
    nonce = os.urandom(12)  # 96-bit nonce
    ct_with_tag = chacha.encrypt(nonce, data, None)
    
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]
    
    return {
        "encrypted_data": nonce + ct_with_tag,
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "auth_tag": base64.b64encode(tag).decode("utf-8")
    }

def decrypt_file_data(encrypted_payload: bytes, key: bytes) -> bytes:
    """Decrypt payload (nonce [12 bytes] + ciphertext + tag [16 bytes])."""
    chacha = ChaCha20Poly1305(key)
    nonce = encrypted_payload[:12]
    ct_with_tag = encrypted_payload[12:]
    return chacha.decrypt(nonce, ct_with_tag, None)
