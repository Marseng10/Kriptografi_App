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
    ensure_master_keypair, encrypt_token_rsa, 
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
            
        res.append({
            "asset_id": a.asset_id,
            "asset_name": a.asset_name,
            "asset_type": a.asset_type,
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
