import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def generate_aes_key() -> bytes:
    """Generate a random 256-bit (32 bytes) AES key."""
    return AESGCM.generate_key(bit_length=256)

def encrypt_message(plaintext: str, key: bytes) -> dict:
    """
    Encrypt plaintext string with AES-256-GCM.
    Returns base64 encoded ciphertext, nonce, and tag (included in AESGCM output).
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    data_bytes = plaintext.encode("utf-8")
    
    # AESGCM in cryptography appends the 16-byte authentication tag to the ciphertext
    ct_with_tag = aesgcm.encrypt(nonce, data_bytes, None)
    
    # Split ciphertext and tag for explicit database recording if desired
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]
    
    return {
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "auth_tag": base64.b64encode(tag).decode("utf-8"),
        "full_payload": base64.b64encode(nonce + ct_with_tag).decode("utf-8")
    }

def decrypt_message(ciphertext_b64: str, nonce_b64: str, auth_tag_b64: str, key: bytes) -> str:
    """Decrypt message given base64 components and key."""
    aesgcm = AESGCM(key)
    ciphertext = base64.b64decode(ciphertext_b64)
    nonce = base64.b64decode(nonce_b64)
    tag = base64.b64decode(auth_tag_b64)
    
    # Reassemble ciphertext + tag for AESGCM
    ct_with_tag = ciphertext + tag
    plaintext_bytes = aesgcm.decrypt(nonce, ct_with_tag, None)
    return plaintext_bytes.decode("utf-8")
