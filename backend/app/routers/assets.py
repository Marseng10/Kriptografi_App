import os
import uuid
import secrets
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import (
    User, DigitalAsset, AssetPermission, Beneficiary, 
    EncryptionKey, ClaimToken, utc_now
)
from ..schemas import CreateMessageAsset, AssetResponse, AssetPermissionUpdate
from .auth import get_current_user
from ..crypto.aes_gcm import generate_aes_key, encrypt_message
from ..crypto.chacha import generate_chacha_key, encrypt_file_data
from ..crypto.rsa_envelope import (
    ensure_master_keypair, encrypt_token_rsa, decrypt_token_rsa,
    store_key_bytes
)
from ..crypto.steganography import (
    generate_default_cover_image, embed_secret_in_image
)
from ..crypto.hashing import sha256_hash
from ..blockchain.audit_chain import record_audit_event

router = APIRouter(prefix="/assets", tags=["Digital Assets"])

@router.post("/message", response_model=AssetResponse)
def create_message_asset(payload: CreateMessageAsset, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Hanya pewaris (owner) yang dapat membuat aset wasiat")
        
    if not payload.beneficiary_ids:
        raise HTTPException(status_code=400, detail="Minimal tentukan 1 ahli waris untuk menerima pesan ini")
        
    # Verify beneficiaries belong to this owner
    valid_bens = db.query(Beneficiary).filter(
        Beneficiary.beneficiary_id.in_(payload.beneficiary_ids),
        Beneficiary.owner_id == current_user.user_id,
        Beneficiary.status == "active"
    ).all()
    
    if not valid_bens:
        raise HTTPException(status_code=400, detail="Ahli waris tidak valid atau belum aktif")
        
    # 1. Generate AES-256-GCM key
    aes_key = generate_aes_key()
    key_id_str = f"aes_{uuid.uuid4().hex}"
    store_key_bytes(key_id_str, aes_key)
    
    enc_key_record = EncryptionKey(
        user_id=current_user.user_id,
        key_identifier=key_id_str,
        algorithm="AES-256-GCM",
        key_version=1,
        key_status="active",
        created_at=utc_now()
    )
    db.add(enc_key_record)
    db.commit()
    db.refresh(enc_key_record)
    
    # 2. Encrypt message
    enc_result = encrypt_message(payload.message_content, aes_key)
    
    # Save ciphertext file to storage
    file_uuid = uuid.uuid4().hex
    enc_file_path = settings.ASSETS_PATH / f"asset_msg_{file_uuid}.enc"
    enc_file_path.write_text(enc_result["full_payload"], encoding="utf-8")
    
    # 3. Save DigitalAsset record
    asset = DigitalAsset(
        owner_id=current_user.user_id,
        asset_name=payload.asset_name,
        asset_type="message",
        original_filename=None,
        encrypted_file_path=str(enc_file_path),
        mime_type="text/plain",
        file_size=len(payload.message_content.encode("utf-8")),
        encryption_algorithm="AES-256-GCM",
        key_id=enc_key_record.key_id,
        nonce=enc_result["nonce"],
        auth_tag=enc_result["auth_tag"],
        asset_status="active",
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    # 4. Generate RSA Keypair for token protection
    _, pub_key_path = ensure_master_keypair("wariscrypt_master")
    
    # 5. Create Permissions, Claim Tokens & Steganography PNG
    latest_stego_filename = None
    for ben in valid_bens:
        perm = AssetPermission(
            asset_id=asset.asset_id,
            beneficiary_id=ben.beneficiary_id,
            access_status="authorized",
            release_status="locked",  # Locked until condition or owner release
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(perm)
        db.commit()
        
        # High-entropy claim token
        raw_token = f"WARIS-{secrets.token_hex(16).upper()}-{asset.asset_id}-{ben.beneficiary_id}"
        token_hash = sha256_hash(raw_token)
        token_ciphertext = encrypt_token_rsa(raw_token, pub_key_path)
        
        claim_token = ClaimToken(
            beneficiary_id=ben.beneficiary_id,
            asset_id=asset.asset_id,
            token_hash=token_hash,
            token_ciphertext=token_ciphertext,
            token_status="active",
            created_at=utc_now()
        )
        db.add(claim_token)
        db.commit()
        
        # Embed in Stego PNG
        cover_path = settings.STORAGE_PATH / f"temp_cover_{uuid.uuid4().hex[:6]}.png"
        generate_default_cover_image(cover_path, title=f"WILL: {asset.asset_name}")
        
        stego_filename = f"stego_asset_{asset.asset_id}_ben_{ben.beneficiary_id}.png"
        stego_out_path = settings.STEGO_PATH / stego_filename
        
        # Secret bytes embedded in stego: JSON or formatted raw token string
        embed_secret_in_image(cover_path, raw_token.encode("utf-8"), stego_out_path)
        if cover_path.exists():
            cover_path.unlink()
            
        latest_stego_filename = stego_filename
        
    record_audit_event(
        db=db,
        activity_type="ASSET_CREATED_MESSAGE",
        user_id=current_user.user_id,
        entity_type="digital_assets",
        entity_id=asset.asset_id,
        event_metadata={
            "asset_name": asset.asset_name,
            "algorithm": asset.encryption_algorithm,
            "beneficiary_count": len(valid_bens)
        }
    )
    
    perms_data = [
        {"beneficiary_id": b.beneficiary_id, "release_status": "locked"} for b in valid_bens
    ]
    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "asset_type": asset.asset_type,
        "original_filename": None,
        "mime_type": asset.mime_type,
        "file_size": asset.file_size,
        "encryption_algorithm": asset.encryption_algorithm,
        "asset_status": asset.asset_status,
        "created_at": asset.created_at,
        "permissions": perms_data,
        "latest_stego_download_url": f"/api/assets/download-stego/{latest_stego_filename}" if latest_stego_filename else None
    }

@router.post("/document")
async def create_document_asset(
    asset_name: str = Form(...),
    beneficiary_ids: str = Form(...),  # comma-separated IDs
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Hanya pewaris (owner) yang dapat mengunggah dokumen wasiat")
        
    ben_id_list = [int(x.strip()) for x in beneficiary_ids.split(",") if x.strip().isdigit()]
    if not ben_id_list:
        raise HTTPException(status_code=400, detail="Pilih minimal 1 ahli waris")
        
    valid_bens = db.query(Beneficiary).filter(
        Beneficiary.beneficiary_id.in_(ben_id_list),
        Beneficiary.owner_id == current_user.user_id,
        Beneficiary.status == "active"
    ).all()
    
    if not valid_bens:
        raise HTTPException(status_code=400, detail="Ahli waris tidak valid")
        
    raw_content = await file.read()
    
    # 1. Generate ChaCha20-Poly1305 key
    chacha_key = generate_chacha_key()
    key_id_str = f"chacha_{uuid.uuid4().hex}"
    store_key_bytes(key_id_str, chacha_key)
    
    enc_key_record = EncryptionKey(
        user_id=current_user.user_id,
        key_identifier=key_id_str,
        algorithm="ChaCha20-Poly1305",
        key_version=1,
        key_status="active",
        created_at=utc_now()
    )
    db.add(enc_key_record)
    db.commit()
    db.refresh(enc_key_record)
    
    # 2. Encrypt document
    enc_result = encrypt_file_data(raw_content, chacha_key)
    
    file_uuid = uuid.uuid4().hex
    enc_file_path = settings.ASSETS_PATH / f"asset_doc_{file_uuid}.enc"
    enc_file_path.write_bytes(enc_result["encrypted_data"])
    
    # 3. Save asset
    asset = DigitalAsset(
        owner_id=current_user.user_id,
        asset_name=asset_name,
        asset_type="document",
        original_filename=file.filename,
        encrypted_file_path=str(enc_file_path),
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(raw_content),
        encryption_algorithm="ChaCha20-Poly1305",
        key_id=enc_key_record.key_id,
        nonce=enc_result["nonce"],
        auth_tag=enc_result["auth_tag"],
        asset_status="active",
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    # 4. Token & Steganography
    _, pub_key_path = ensure_master_keypair("wariscrypt_master")
    latest_stego = None
    
    for ben in valid_bens:
        perm = AssetPermission(
            asset_id=asset.asset_id,
            beneficiary_id=ben.beneficiary_id,
            access_status="authorized",
            release_status="locked",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(perm)
        db.commit()
        
        raw_token = f"WARIS-{secrets.token_hex(16).upper()}-{asset.asset_id}-{ben.beneficiary_id}"
        token_hash = sha256_hash(raw_token)
        token_ciphertext = encrypt_token_rsa(raw_token, pub_key_path)
        
        claim_token = ClaimToken(
            beneficiary_id=ben.beneficiary_id,
            asset_id=asset.asset_id,
            token_hash=token_hash,
            token_ciphertext=token_ciphertext,
            token_status="active",
            created_at=utc_now()
        )
        db.add(claim_token)
        db.commit()
        
        cover_path = settings.STORAGE_PATH / f"temp_cover_doc_{uuid.uuid4().hex[:6]}.png"
        generate_default_cover_image(cover_path, title=f"DOCUMENT: {asset.asset_name}")
        
        stego_filename = f"stego_doc_{asset.asset_id}_ben_{ben.beneficiary_id}.png"
        stego_out_path = settings.STEGO_PATH / stego_filename
        embed_secret_in_image(cover_path, raw_token.encode("utf-8"), stego_out_path)
        if cover_path.exists():
            cover_path.unlink()
        latest_stego = stego_filename
        
    record_audit_event(
        db=db,
        activity_type="ASSET_CREATED_DOCUMENT",
        user_id=current_user.user_id,
        entity_type="digital_assets",
        entity_id=asset.asset_id,
        event_metadata={
            "asset_name": asset.asset_name,
            "filename": asset.original_filename,
            "algorithm": asset.encryption_algorithm,
            "file_size": asset.file_size
        }
    )
    
    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "asset_type": asset.asset_type,
        "original_filename": asset.original_filename,
        "encryption_algorithm": asset.encryption_algorithm,
        "stego_download_url": f"/api/assets/download-stego/{latest_stego}" if latest_stego else None,
        "message": "Dokumen berhasil dienkripsi dengan ChaCha20-Poly1305 dan disisipkan ke gambar steganografi."
    }


@router.post("/unified")
async def create_unified_asset(
    asset_name: str = Form(...),
    beneficiary_ids: str = Form(...),  # comma-separated IDs
    message_content: str = Form(""),
    file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Buat satu wasiat terpadu yang dapat berisi Pesan Teks, Berkas Dokumen, atau Keduanya sekaligus.
    - Pesan teks dienkripsi dengan AES-256-GCM
    - Berkas dokumen dienkripsi dengan ChaCha20-Poly1305
    """
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Hanya pewaris (owner) yang dapat membuat wasiat")

    ben_id_list = [int(x.strip()) for x in beneficiary_ids.split(",") if x.strip().isdigit()]
    if not ben_id_list:
        raise HTTPException(status_code=400, detail="Pilih minimal 1 ahli waris penerima wasiat")

    valid_bens = db.query(Beneficiary).filter(
        Beneficiary.beneficiary_id.in_(ben_id_list),
        Beneficiary.owner_id == current_user.user_id,
        Beneficiary.status == "active"
    ).all()
    if not valid_bens:
        raise HTTPException(status_code=400, detail="Ahli waris tidak valid atau belum aktif")

    clean_msg = (message_content or "").strip()
    has_msg = len(clean_msg) > 0
    has_file = file is not None and bool(file.filename)

    if not has_msg and not has_file:
        raise HTTPException(status_code=400, detail="Isi pesan teks atau lampirkan berkas dokumen (minimal salah satu atau keduanya).")

    raw_file_bytes = b""
    if has_file:
        raw_file_bytes = await file.read()
        if len(raw_file_bytes) == 0:
            has_file = False

    if not has_msg and not has_file:
        raise HTTPException(status_code=400, detail="Berkas dokumen kosong dan pesan teks kosong.")

    # 1. Generate 256-bit master encryption key for this Will
    master_key = generate_aes_key()  # 32 bytes (256-bit), valid for both AES-256-GCM and ChaCha20-Poly1305
    key_id_str = f"willkey_{uuid.uuid4().hex}"
    store_key_bytes(key_id_str, master_key)

    if has_msg and has_file:
        algo_label = "AES-256-GCM + ChaCha20-Poly1305"
        db_asset_type = "document"
    elif has_file:
        algo_label = "ChaCha20-Poly1305"
        db_asset_type = "document"
    else:
        algo_label = "AES-256-GCM"
        db_asset_type = "message"

    enc_key_record = EncryptionKey(
        user_id=current_user.user_id,
        key_identifier=key_id_str,
        algorithm=algo_label,
        key_version=1,
        key_status="active",
        created_at=utc_now()
    )
    db.add(enc_key_record)
    db.commit()
    db.refresh(enc_key_record)

    file_uuid = uuid.uuid4().hex
    msg_file_path_str = ""
    doc_file_path_str = ""
    nonce_val = None
    tag_val = None
    total_size = 0

    # 2A. Encrypt text message if provided (AES-256-GCM)
    if has_msg:
        enc_msg = encrypt_message(clean_msg, master_key)
        msg_path = settings.ASSETS_PATH / f"asset_msg_{file_uuid}.enc"
        msg_path.write_text(enc_msg["full_payload"], encoding="utf-8")
        msg_file_path_str = str(msg_path)
        nonce_val = enc_msg["nonce"]
        tag_val = enc_msg["auth_tag"]
        total_size += len(clean_msg.encode("utf-8"))

    # 2B. Encrypt attached document if provided (ChaCha20-Poly1305)
    if has_file:
        enc_doc = encrypt_file_data(raw_file_bytes, master_key)
        doc_path = settings.ASSETS_PATH / f"asset_doc_{file_uuid}.enc"
        doc_path.write_bytes(enc_doc["encrypted_data"])
        doc_file_path_str = str(doc_path)
        if not nonce_val:
            nonce_val = enc_doc["nonce"]
            tag_val = enc_doc["auth_tag"]
        total_size += len(raw_file_bytes)

    if has_msg and has_file:
        combined_path = f"{msg_file_path_str}|{doc_file_path_str}"
    elif has_file:
        combined_path = doc_file_path_str
    else:
        combined_path = msg_file_path_str

    # 3. Save DigitalAsset record
    asset = DigitalAsset(
        owner_id=current_user.user_id,
        asset_name=asset_name,
        asset_type=db_asset_type,
        original_filename=file.filename if has_file else None,
        encrypted_file_path=combined_path,
        mime_type=(file.content_type or "application/octet-stream") if has_file else "text/plain",
        file_size=total_size,
        encryption_algorithm=algo_label,
        key_id=enc_key_record.key_id,
        nonce=nonce_val,
        auth_tag=tag_val,
        asset_status="active",
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # 4. Generate Claim Tokens & Steganography Access Cards for each Beneficiary
    _, pub_key_path = ensure_master_keypair("wariscrypt_master")
    latest_stego = None

    for ben in valid_bens:
        perm = AssetPermission(
            asset_id=asset.asset_id,
            beneficiary_id=ben.beneficiary_id,
            access_status="authorized",
            release_status="locked",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(perm)
        db.commit()

        raw_token = f"WARIS-{secrets.token_hex(16).upper()}-{asset.asset_id}-{ben.beneficiary_id}"
        token_hash = sha256_hash(raw_token)
        token_ciphertext = encrypt_token_rsa(raw_token, pub_key_path)

        claim_token = ClaimToken(
            beneficiary_id=ben.beneficiary_id,
            asset_id=asset.asset_id,
            token_hash=token_hash,
            token_ciphertext=token_ciphertext,
            token_status="active",
            created_at=utc_now()
        )
        db.add(claim_token)
        db.commit()

        cover_path = settings.STORAGE_PATH / f"temp_cover_will_{uuid.uuid4().hex[:6]}.png"
        generate_default_cover_image(cover_path, title=f"WILL: {asset.asset_name}")

        prefix = "stego_asset" if db_asset_type == "message" else "stego_doc"
        stego_filename = f"{prefix}_{asset.asset_id}_ben_{ben.beneficiary_id}.png"
        stego_out_path = settings.STEGO_PATH / stego_filename
        embed_secret_in_image(cover_path, raw_token.encode("utf-8"), stego_out_path)
        if cover_path.exists():
            cover_path.unlink()
        latest_stego = stego_filename

    record_audit_event(
        db=db,
        activity_type="ASSET_CREATED_UNIFIED",
        user_id=current_user.user_id,
        entity_type="digital_assets",
        entity_id=asset.asset_id,
        event_metadata={
            "asset_name": asset.asset_name,
            "has_message": has_msg,
            "has_document": has_file,
            "filename": asset.original_filename,
            "algorithm": asset.encryption_algorithm,
            "beneficiary_count": len(valid_bens)
        }
    )

    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "asset_type": asset.asset_type,
        "has_message": has_msg,
        "has_document": has_file,
        "original_filename": asset.original_filename,
        "encryption_algorithm": asset.encryption_algorithm,
        "stego_download_url": f"/api/assets/download-stego/{latest_stego}" if latest_stego else None,
        "latest_stego_download_url": f"/api/assets/download-stego/{latest_stego}" if latest_stego else None,
        "message": "Wasiat berhasil dienkripsi dan kartu akses foto telah dibuat."
    }


@router.get("/", response_model=list[dict])
def list_assets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Hanya owner yang dapat mengakses daftar aset ini")
        
    assets = db.query(DigitalAsset).filter(
        DigitalAsset.owner_id == current_user.user_id,
        DigitalAsset.asset_status != "deleted"
    ).order_by(DigitalAsset.asset_id.desc()).all()
    
    res = []
    for a in assets:
        perms = db.query(AssetPermission).filter(AssetPermission.asset_id == a.asset_id).all()
        perm_list = []
        for p in perms:
            ben = db.query(Beneficiary).filter(Beneficiary.beneficiary_id == p.beneficiary_id).first()
            ben_user = db.query(User).filter(User.user_id == ben.beneficiary_user_id).first() if ben else None
            # Find stego file if exists
            stego_fn = f"stego_asset_{a.asset_id}_ben_{p.beneficiary_id}.png"
            if not (settings.STEGO_PATH / stego_fn).exists():
                stego_fn = f"stego_doc_{a.asset_id}_ben_{p.beneficiary_id}.png"
            stego_exists = (settings.STEGO_PATH / stego_fn).exists()
            
            perm_list.append({
                "permission_id": p.permission_id,
                "beneficiary_id": p.beneficiary_id,
                "beneficiary_name": ben_user.username if ben_user else "Unknown",
                "access_status": p.access_status,
                "release_status": p.release_status,
                "released_at": p.released_at,
                "stego_url": f"/api/assets/download-stego/{stego_fn}" if stego_exists else None
            })

        is_combined = "|" in (a.encrypted_file_path or "")
        has_message = is_combined or (a.asset_type == "message")
        has_document = is_combined or (a.asset_type == "document" and bool(a.original_filename))

        res.append({
            "asset_id": a.asset_id,
            "asset_name": a.asset_name,
            "asset_type": a.asset_type,
            "has_message": has_message,
            "has_document": has_document,
            "original_filename": a.original_filename,
            "mime_type": a.mime_type,
            "file_size": a.file_size,
            "encryption_algorithm": a.encryption_algorithm,
            "asset_status": a.asset_status,
            "created_at": a.created_at,
            "permissions": perm_list
        })
    return res

@router.put("/permission/release-toggle")
def toggle_release_status(payload: AssetPermissionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    perm = db.query(AssetPermission).filter(AssetPermission.permission_id == payload.permission_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail="Izin aset tidak ditemukan")
        
    asset = db.query(DigitalAsset).filter(DigitalAsset.asset_id == perm.asset_id).first()
    if not asset or asset.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Tidak memiliki akses ke aset ini")
        
    perm.release_status = payload.release_status
    if payload.release_status == "released":
        perm.released_at = utc_now()
    else:
        perm.released_at = None
        
    db.commit()
    
    record_audit_event(
        db=db,
        activity_type=f"ASSET_RELEASE_TOGGLED_{payload.release_status.upper()}",
        user_id=current_user.user_id,
        entity_type="asset_permissions",
        entity_id=perm.permission_id,
        event_metadata={"asset_id": asset.asset_id, "new_status": payload.release_status}
    )
    
    return {"message": f"Status rilis aset diperbarui menjadi {payload.release_status}"}

@router.get("/download-stego/{filename}")
def download_stego_image(filename: str):
    file_path = settings.STEGO_PATH / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Berkas gambar steganografi tidak ditemukan")
    return FileResponse(
        path=file_path,
        media_type="image/png",
        filename=filename
    )


@router.post("/{asset_id}/access-key")
async def create_access_key(
    asset_id: int,
    beneficiary_id: int = Form(...),
    photo: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Buat ulang kartu akses (gambar) untuk satu ahli waris, memakai foto pilihan pewaris."""
    from io import BytesIO
    from PIL import Image

    asset = db.query(DigitalAsset).filter(
        DigitalAsset.asset_id == asset_id,
        DigitalAsset.owner_id == current_user.user_id,
        DigitalAsset.asset_status != "deleted"
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Wasiat tidak ditemukan")

    token = db.query(ClaimToken).filter(
        ClaimToken.asset_id == asset_id,
        ClaimToken.beneficiary_id == beneficiary_id,
        ClaimToken.token_status.in_(["active", "used"])
    ).order_by(ClaimToken.token_id.desc()).first()
    if not token or not token.token_ciphertext:
        raise HTTPException(status_code=404, detail="Kartu akses untuk ahli waris ini tidak tersedia atau sudah dipakai")

    priv_path, _ = ensure_master_keypair("wariscrypt_master")
    raw_token = decrypt_token_rsa(token.token_ciphertext, priv_path)

    prefix = "stego_asset" if asset.asset_type == "message" else "stego_doc"
    stego_filename = f"{prefix}_{asset_id}_ben_{beneficiary_id}.png"
    stego_out_path = settings.STEGO_PATH / stego_filename

    cover_path = settings.STORAGE_PATH / f"temp_cover_{uuid.uuid4().hex[:8]}.png"
    try:
        if photo is not None and photo.filename:
            data = await photo.read()
            try:
                img = Image.open(BytesIO(data)).convert("RGB")
            except Exception:
                raise HTTPException(status_code=400, detail="File foto tidak dapat dibaca")
            img.thumbnail((1600, 1600))
            img.save(cover_path, format="PNG")
        else:
            generate_default_cover_image(cover_path, title=asset.asset_name)
        try:
            embed_secret_in_image(cover_path, raw_token.encode("utf-8"), stego_out_path)
        except ValueError:
            raise HTTPException(status_code=400, detail="Foto terlalu kecil. Gunakan foto dengan resolusi lebih besar.")
    finally:
        if cover_path.exists():
            cover_path.unlink()

    record_audit_event(
        db=db,
        activity_type="ACCESS_KEY_CREATED",
        user_id=current_user.user_id,
        entity_type="digital_assets",
        entity_id=asset_id,
        event_metadata={"beneficiary_id": beneficiary_id, "custom_photo": bool(photo and photo.filename)}
    )
    return {"download_url": f"/api/assets/download-stego/{stego_filename}", "filename": stego_filename}


@router.delete("/{asset_id}")
def delete_asset(asset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = db.query(DigitalAsset).filter(
        DigitalAsset.asset_id == asset_id,
        DigitalAsset.owner_id == current_user.user_id
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Wasiat tidak ditemukan")
    asset.asset_status = "deleted"
    for t in db.query(ClaimToken).filter(ClaimToken.asset_id == asset_id, ClaimToken.token_status == "active").all():
        t.token_status = "revoked"
    db.commit()
    record_audit_event(
        db=db,
        activity_type="ASSET_DELETED",
        user_id=current_user.user_id,
        entity_type="digital_assets",
        entity_id=asset_id
    )
    return {"message": "Wasiat dihapus"}
