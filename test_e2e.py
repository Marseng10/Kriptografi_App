import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent / "backend"))

import os
import io
import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Beneficiary, BeneficiaryReferenceImage, DigitalAsset, UsbDevice
from app.crypto.hashing import hash_password, verify_password, sha256_hash
from app.crypto.aes_gcm import generate_aes_key, encrypt_message, decrypt_message
from app.crypto.chacha import generate_chacha_key, encrypt_file_data, decrypt_file_data
from app.crypto.rsa_envelope import ensure_master_keypair, encrypt_token_rsa, decrypt_token_rsa
from app.crypto.steganography import generate_default_cover_image, embed_secret_in_image, extract_secret_from_image
from app.crypto.vigenere import vigenere_encrypt, vigenere_decrypt
from app.biometrics.face_service import compute_face_similarity
from app.blockchain.audit_chain import record_audit_event, verify_audit_chain_integrity

def run_direct_tests():
    print("=" * 65)
    print("      WARISCRYPT - COMPLETE PIPELINE VERIFICATION")
    print("=" * 65)

    db: Session = SessionLocal()
    try:
        # 1. Cryptographic Hashes (Argon2id)
        print("\n--- 1. Testing Password Hashing (Argon2id) ---")
        pw = "SuperSecureWill2026!"
        hashed = hash_password(pw)
        print("Argon2id hash generated:", hashed[:35] + "...")
        assert verify_password(pw, hashed) is True
        assert verify_password("WrongPassword", hashed) is False
        print("[PASS] Argon2id hashing & verification verified.")

        # 2. Symmetric Message Encryption (AES-256-GCM)
        print("\n--- 2. Testing Message Encryption (AES-256-GCM) ---")
        secret_msg = "Wasiat Tersegel: Surat wasiat tanah warisan & brankas no. 129038"
        aes_key = generate_aes_key()
        enc_aes = encrypt_message(secret_msg, aes_key)
        print("Ciphertext (AES-256-GCM b64):", enc_aes["ciphertext"][:32] + "...")
        print("Nonce (96-bit b64):", enc_aes["nonce"])
        print("Auth Tag (128-bit b64):", enc_aes["auth_tag"])

        decrypted_msg = decrypt_message(enc_aes["ciphertext"], enc_aes["nonce"], enc_aes["auth_tag"], aes_key)
        assert decrypted_msg == secret_msg
        print("[PASS] AES-256-GCM AEAD encryption & decryption verified.")

        # 3. Document Encryption (ChaCha20-Poly1305)
        print("\n--- 3. Testing Document Encryption (ChaCha20-Poly1305) ---")
        doc_bytes = b"PDF-DOCUMENT-CONTENT-TESTAMENT-SIGNATURE-BINARY-BLOB-DATA"
        chacha_key = generate_chacha_key()
        enc_doc = encrypt_file_data(doc_bytes, chacha_key)
        print("Encrypted payload size:", len(enc_doc["encrypted_data"]), "bytes")
        decrypted_doc = decrypt_file_data(enc_doc["encrypted_data"], chacha_key)
        assert decrypted_doc == doc_bytes
        print("[PASS] ChaCha20-Poly1305 document encryption & decryption verified.")

        # 4. Asymmetric Token Protection (RSA-OAEP 2048 SHA-256)
        print("\n--- 4. Testing Token Protection (RSA-OAEP 2048) ---")
        priv_p, pub_p = ensure_master_keypair("wariscrypt_test")
        token_plain = "WARIS-TOKEN-CLAIM-XYZ-9876543210"
        enc_token = encrypt_token_rsa(token_plain, pub_p)
        print("RSA Ciphertext (b64):", enc_token[:40] + "...")
        dec_token = decrypt_token_rsa(enc_token, priv_p)
        assert dec_token == token_plain
        print("[PASS] RSA-OAEP token envelopment verified.")

        # 5. Steganography Engine (LSB PNG)
        print("\n--- 5. Testing LSB PNG Steganography ---")
        cover_path = Path("test_carrier_cover.png")
        generate_default_cover_image(cover_path, "TEST CARRIER WILL")
        stego_path = Path("test_carrier_stego.png")

        embed_secret_in_image(cover_path, token_plain.encode("utf-8"), stego_path)
        print("Secret embedded into pixels of:", stego_path)

        extracted_secret = extract_secret_from_image(stego_path).decode("utf-8")
        assert extracted_secret == token_plain
        print(f"Extracted secret from PNG: '{extracted_secret}'")
        print("[PASS] LSB PNG Steganography embedding & extraction verified.")

        # Clean up test images
        if cover_path.exists(): cover_path.unlink()
        if stego_path.exists(): stego_path.unlink()

        # 6. Biometrics Face Recognition & Matching (OpenCV)
        print("\n--- 6. Testing Biometric Face Matching (OpenCV) ---")
        # Reference Face
        ref_face = np.ones((250, 250, 3), dtype=np.uint8) * 160
        cv2.circle(ref_face, (125, 125), 70, (215, 185, 145), -1)
        cv2.circle(ref_face, (100, 105), 10, (50, 30, 20), -1)
        cv2.circle(ref_face, (150, 105), 10, (50, 30, 20), -1)
        cv2.ellipse(ref_face, (125, 150), (25, 15), 0, 0, 180, (60, 40, 160), 3)

        # Slightly variant face of same person
        same_person_face = ref_face.copy()
        cv2.circle(same_person_face, (125, 125), 68, (215, 185, 145), -1)

        # Completely different face (different structure & colors)
        diff_person_face = np.zeros((250, 250, 3), dtype=np.uint8)
        cv2.rectangle(diff_person_face, (40, 40), (210, 210), (0, 200, 255), -1)

        _, ref_bytes = cv2.imencode(".jpg", ref_face)
        _, same_bytes = cv2.imencode(".jpg", same_person_face)
        _, diff_bytes = cv2.imencode(".jpg", diff_person_face)

        match_same = compute_face_similarity(ref_bytes.tobytes(), same_bytes.tobytes())
        match_diff = compute_face_similarity(ref_bytes.tobytes(), diff_bytes.tobytes())

        print(f"Matching same claimant score: {match_same['score']*100:.1f}% (Passed: {match_same['passed']})")
        print(f"Matching impostor score:     {match_diff['score']*100:.1f}% (Passed: {match_diff['passed']})")
        assert match_same["passed"] is True
        assert match_diff["passed"] is False
        print("[PASS] Biometric facial recognition anti-impersonation verified.")

        # 7. Blockchain Tamper-Evident Audit Trail (SHA-256 Chain)
        print("\n--- 7. Testing Blockchain Audit Trail & Integrity ---")
        owner = db.query(User).filter(User.username == "pewaris").first()
        log_entry = record_audit_event(
            db=db,
            activity_type="E2E_VERIFICATION_TEST",
            user_id=owner.user_id if owner else None,
            entity_type="system",
            entity_id=1,
            event_metadata={"test": "integration_check", "status": "ok"}
        )
        print(f"Block #{log_entry.log_id} created with SHA-256 hash: {log_entry.current_hash}")
        assert len(log_entry.current_hash) == 64

        chain_check = verify_audit_chain_integrity(db)
        print("Blockchain Integrity Status:", chain_check)
        assert chain_check["is_valid"] is True
        print("[PASS] Blockchain ledger continuity verified.")

        # 8. Educational Vigenère vs Modern AES
        print("\n--- 8. Testing Educational Vigenère Cipher ---")
        vig_pt = "WARISAN"
        vig_ct = vigenere_encrypt(vig_pt, "KUNCI")
        vig_dt = vigenere_decrypt(vig_ct, "KUNCI")
        assert vig_dt == vig_pt
        print(f"Vigenère: '{vig_pt}' -> '{vig_ct}' -> '{vig_dt}'")
        print("[PASS] Educational cipher engine verified.")

        # 9. USB Hardware Device Key Fingerprinting
        print("\n--- 9. Testing USB Hardware Key Fingerprinting ---")
        raw_usb_token = "WARISCRYPT-USBKEY-abcdef0123456789abcdef0123456789"
        fingerprint = sha256_hash(raw_usb_token)
        print(f"Raw USB Key: {raw_usb_token}")
        print(f"Cryptographic Fingerprint: {fingerprint}")
        assert len(fingerprint) == 64
        print("[PASS] USB Hardware Key mechanism verified.")

        print("\n" + "=" * 65)
        print("  ALL 9 CORE WARISCRYPT SECURITY MODULES PASSED 100%!")
        print("=" * 65)

    finally:
        db.close()

if __name__ == "__main__":
    run_direct_tests()
