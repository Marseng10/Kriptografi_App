import sys
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

import os
import secrets
import numpy as np
import cv2
from sqlalchemy.orm import Session
from app.config import settings
from app.database import engine, SessionLocal, Base
from app.models import (
    User, UserProfile, Beneficiary, BeneficiaryReferenceImage,
    DigitalAsset, AssetPermission, ClaimToken, EncryptionKey, utc_now
)
from app.crypto.hashing import hash_password, sha256_hash
from app.crypto.aes_gcm import generate_aes_key, encrypt_message
from app.crypto.rsa_envelope import ensure_master_keypair, encrypt_token_rsa, store_key_bytes
from app.crypto.steganography import generate_default_cover_image, embed_secret_in_image
from app.blockchain.audit_chain import record_audit_event, verify_audit_chain_integrity

def seed():
    print("--- Initializing Database Tables ---")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Create or get Owner
        owner = db.query(User).filter(User.username == "pewaris").first()
        if not owner:
            print("Creating demo owner: 'pewaris' (password: Password123!)...")
            owner = User(
                username="pewaris",
                email="pewaris@wariscrypt.local",
                password_hash=hash_password("Password123!"),
                role="owner",
                account_status="active",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            db.add(UserProfile(
                user_id=owner.user_id,
                full_name="Raden Mas Pewaris",
                phone_number="+6281234567890",
                created_at=utc_now(),
                updated_at=utc_now()
            ))
            db.commit()

            record_audit_event(
                db=db,
                activity_type="USER_REGISTERED",
                user_id=owner.user_id,
                entity_type="users",
                entity_id=owner.user_id,
                event_metadata={"username": "pewaris", "role": "owner"}
            )
        else:
            print("Owner 'pewaris' already exists.")

        # 2. Create or get Beneficiary
        ben_user = db.query(User).filter(User.username == "ahliwaris").first()
        if not ben_user:
            print("Creating demo beneficiary: 'ahliwaris' (password: Password123!)...")
            ben_user = User(
                username="ahliwaris",
                email="ahliwaris@wariscrypt.local",
                password_hash=hash_password("Password123!"),
                role="beneficiary",
                account_status="active",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(ben_user)
            db.commit()
            db.refresh(ben_user)

            db.add(UserProfile(
                user_id=ben_user.user_id,
                full_name="Ananda Ahli Waris",
                phone_number="+6281987654321",
                created_at=utc_now(),
                updated_at=utc_now()
            ))
            db.commit()

            record_audit_event(
                db=db,
                activity_type="USER_REGISTERED",
                user_id=ben_user.user_id,
                entity_type="users",
                entity_id=ben_user.user_id,
                event_metadata={"username": "ahliwaris", "role": "beneficiary"}
            )
        else:
            print("Beneficiary 'ahliwaris' already exists.")

        # 3. Create Beneficiary Relationship
        ben_rel = db.query(Beneficiary).filter(
            Beneficiary.owner_id == owner.user_id,
            Beneficiary.beneficiary_user_id == ben_user.user_id
        ).first()

        if not ben_rel:
            print("Linking beneficiary to owner with relationship 'Anak Kandung'...")
            ben_rel = Beneficiary(
                owner_id=owner.user_id,
                beneficiary_user_id=ben_user.user_id,
                relationship_label="Anak Kandung",
                status="active",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(ben_rel)
            db.commit()
            db.refresh(ben_rel)

            # Generate reference face image for the beneficiary
            ref_img_path = settings.REF_IMAGES_PATH / f"ref_demo_{ben_rel.beneficiary_id}.jpg"
            face_canvas = np.ones((250, 250, 3), dtype=np.uint8) * 160
            cv2.circle(face_canvas, (125, 125), 70, (215, 185, 145), -1)
            cv2.circle(face_canvas, (100, 105), 10, (50, 30, 20), -1)
            cv2.circle(face_canvas, (150, 105), 10, (50, 30, 20), -1)
            cv2.ellipse(face_canvas, (125, 150), (25, 15), 0, 0, 180, (60, 40, 160), 3)
            cv2.imwrite(str(ref_img_path), face_canvas)

            db.add(BeneficiaryReferenceImage(
                beneficiary_id=ben_rel.beneficiary_id,
                image_path=str(ref_img_path),
                consent_confirmed=True,
                uploaded_at=utc_now(),
                status="active"
            ))
            db.commit()

            record_audit_event(
                db=db,
                activity_type="BENEFICIARY_ADDED",
                user_id=owner.user_id,
                entity_type="beneficiaries",
                entity_id=ben_rel.beneficiary_id,
                event_metadata={"relationship": "Anak Kandung"}
            )
        else:
            print("Beneficiary relationship already linked.")

        # 4. Create Sample Encrypted Will Asset
        existing_asset = db.query(DigitalAsset).filter(
            DigitalAsset.owner_id == owner.user_id,
            DigitalAsset.asset_name == "Surat Rahasia Brankas Keluarga"
        ).first()

        if not existing_asset:
            print("Creating sample encrypted digital will message...")
            aes_key = generate_aes_key()
            key_id_str = f"aes_demo_{secrets.token_hex(8)}"
            store_key_bytes(key_id_str, aes_key)

            enc_key = EncryptionKey(
                user_id=owner.user_id,
                key_identifier=key_id_str,
                algorithm="AES-256-GCM",
                key_version=1,
                key_status="active",
                created_at=utc_now()
            )
            db.add(enc_key)
            db.commit()
            db.refresh(enc_key)

            secret_text = (
                "Kepada Ananda tercinta,\n"
                "Inilah wasiat dan pesan rahasia keluarga kita: Kode kombinasi brankas besi lantai dua adalah "
                "[78-42-91-B]. Kunci fisik tersimpan di balik lukisan kereta tua.\n"
                "Gunakanlah dengan penuh tanggung jawab dan lindungi keluarga."
            )
            enc_res = encrypt_message(secret_text, aes_key)

            enc_file_path = settings.ASSETS_PATH / "demo_will_brankas.enc"
            enc_file_path.write_text(enc_res["full_payload"], encoding="utf-8")

            asset = DigitalAsset(
                owner_id=owner.user_id,
                asset_name="Surat Rahasia Brankas Keluarga",
                asset_type="message",
                original_filename=None,
                encrypted_file_path=str(enc_file_path),
                mime_type="text/plain",
                file_size=len(secret_text.encode("utf-8")),
                encryption_algorithm="AES-256-GCM",
                key_id=enc_key.key_id,
                nonce=enc_res["nonce"],
                auth_tag=enc_res["auth_tag"],
                asset_status="active",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)

            # Permission
            perm = AssetPermission(
                asset_id=asset.asset_id,
                beneficiary_id=ben_rel.beneficiary_id,
                access_status="authorized",
                release_status="released",  # Released so beneficiary can claim immediately
                released_at=utc_now(),
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(perm)
            db.commit()

            # Claim Token & RSA Envelope
            _, pub_key_path = ensure_master_keypair("wariscrypt_master")
            raw_token = f"WARIS-{secrets.token_hex(16).upper()}-{asset.asset_id}-{ben_rel.beneficiary_id}"
            token_hash = sha256_hash(raw_token)
            token_ciphertext = encrypt_token_rsa(raw_token, pub_key_path)

            token_rec = ClaimToken(
                beneficiary_id=ben_rel.beneficiary_id,
                asset_id=asset.asset_id,
                token_hash=token_hash,
                token_ciphertext=token_ciphertext,
                token_status="active",
                created_at=utc_now()
            )
            db.add(token_rec)
            db.commit()

            # Stego Image Generation
            cover_path = settings.STORAGE_PATH / "temp_cover_demo.png"
            generate_default_cover_image(cover_path, title=f"DEMO WILL: {asset.asset_name}")

            stego_fn = f"stego_asset_{asset.asset_id}_ben_{ben_rel.beneficiary_id}.png"
            stego_path = settings.STEGO_PATH / stego_fn
            embed_secret_in_image(cover_path, raw_token.encode("utf-8"), stego_path)
            if cover_path.exists():
                cover_path.unlink()

            record_audit_event(
                db=db,
                activity_type="ASSET_CREATED_MESSAGE",
                user_id=owner.user_id,
                entity_type="digital_assets",
                entity_id=asset.asset_id,
                event_metadata={"asset_name": asset.asset_name, "stego_image": stego_fn}
            )
            print(f"Sample asset created! Stego image generated at: {stego_path}")
        else:
            print("Sample asset already exists.")

        # 5. Verify Blockchain Integrity
        chain_status = verify_audit_chain_integrity(db)
        print("Blockchain Integrity Status:", chain_status)
        print("Demo seeding complete!")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
