import base64
from fastapi import APIRouter
from ..schemas import CryptoDemoRequest, CryptoDemoResponse
from ..crypto.vigenere import vigenere_encrypt, vigenere_decrypt
from ..crypto.aes_gcm import generate_aes_key, encrypt_message
from ..crypto.chacha import generate_chacha_key, encrypt_file_data

router = APIRouter(prefix="/demo", tags=["Educational Cryptography Lab"])

@router.post("/compare", response_model=CryptoDemoResponse)
def compare_ciphers(payload: CryptoDemoRequest):
    # 1. Vigenere (Classic polyalphabetic)
    vig_result = vigenere_encrypt(payload.plaintext, payload.key)
    
    # 2. Modern AES-256-GCM
    aes_key = generate_aes_key()
    aes_res = encrypt_message(payload.plaintext, aes_key)
    
    # 3. Modern ChaCha20-Poly1305
    chacha_key = generate_chacha_key()
    chacha_res = encrypt_file_data(payload.plaintext.encode("utf-8"), chacha_key)
    chacha_b64 = base64.b64encode(chacha_res["encrypted_data"]).decode("utf-8")
    
    notes = (
        "Analisis Kriptografi:\n"
        "1. Vigenère Cipher (Klasik): Bersifat rentan terhadap Kasiski examination dan analisis frekuensi huruf. "
        "Tidak menyediakan Authentication Tag (tidak ada integritas data).\n"
        "2. AES-256-GCM: Standar militer modern berkinerja tinggi, menyediakan enkripsi simetris 256-bit dan "
        "autentikasi pesan (AEAD - Authenticated Encryption with Associated Data). Anti-tampering.\n"
        "3. ChaCha20-Poly1305: Stream cipher modern rancangan Daniel J. Bernstein dengan MAC Poly1305, "
        "sangat efisien di perangkat tanpa akselerasi hardware AES dan tahan terhadap cache-timing attacks."
    )
    
    return {
        "plaintext": payload.plaintext,
        "vigenere_ciphertext": vig_result,
        "aes_ciphertext": aes_res["ciphertext"],
        "chacha_ciphertext": chacha_b64,
        "comparison_notes": notes
    }
