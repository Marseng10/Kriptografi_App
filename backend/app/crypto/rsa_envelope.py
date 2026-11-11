import base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from ..config import settings

def ensure_master_keypair(key_identifier: str = "wariscrypt_master") -> tuple[Path, Path]:
    """
    Ensure an RSA-2048 keypair exists in keys directory for the given identifier.
    Returns (private_key_path, public_key_path).
    """
    priv_path = settings.KEYS_PATH / f"{key_identifier}_private.pem"
    pub_path = settings.KEYS_PATH / f"{key_identifier}_public.pem"

    if not priv_path.exists() or not pub_path.exists():
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        priv_path.write_bytes(priv_pem)
        pub_path.write_bytes(pub_pem)

    return priv_path, pub_path

def encrypt_token_rsa(token_string: str, pub_key_path: Path) -> str:
    """Encrypt a token string with RSA-OAEP SHA-256 and return base64 ciphertext."""
    pub_pem = pub_key_path.read_bytes()
    public_key = serialization.load_pem_public_key(pub_pem)
    
    ciphertext = public_key.encrypt(
        token_string.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(ciphertext).decode("utf-8")

def decrypt_token_rsa(ciphertext_b64: str, priv_key_path: Path) -> str:
    """Decrypt a base64 ciphertext using RSA-OAEP SHA-256."""
    priv_pem = priv_key_path.read_bytes()
    private_key = serialization.load_pem_private_key(priv_pem, password=None)
    
    raw_ciphertext = base64.b64decode(ciphertext_b64)
    plaintext = private_key.decrypt(
        raw_ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext.decode("utf-8")

def store_key_bytes(key_id_str: str, key_bytes: bytes) -> Path:
    """Store raw symmetric key in the secure keys directory."""
    path = settings.KEYS_PATH / f"sym_{key_id_str}.key"
    path.write_bytes(key_bytes)
    return path

def retrieve_key_bytes(key_id_str: str) -> bytes:
    """Retrieve raw symmetric key bytes."""
    path = settings.KEYS_PATH / f"sym_{key_id_str}.key"
    if not path.exists():
        raise FileNotFoundError(f"Key {key_id_str} not found in key vault")
    return path.read_bytes()
