import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User, Beneficiary, BeneficiaryReferenceImage, UserProfile, utc_now
from ..schemas import BeneficiaryAdd, BeneficiaryResponse
from .auth import get_current_user
from ..biometrics.face_service import save_image_array, decode_image_input
from ..blockchain.audit_chain import record_audit_event

router = APIRouter(prefix="/beneficiaries", tags=["Beneficiaries"])

@router.get("/", response_model=list[BeneficiaryResponse])
def list_beneficiaries(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Hanya pewaris (owner) yang dapat mengelola daftar ahli waris")
        
    bens = db.query(Beneficiary).filter(
        Beneficiary.owner_id == current_user.user_id,
        Beneficiary.status != "revoked"
    ).all()
    
    result = []
    for b in bens:
        ben_user = db.query(User).filter(User.user_id == b.beneficiary_user_id).first()
        profile = db.query(UserProfile).filter(UserProfile.user_id == b.beneficiary_user_id).first()
        ref_img = db.query(BeneficiaryReferenceImage).filter(
            BeneficiaryReferenceImage.beneficiary_id == b.beneficiary_id,
            BeneficiaryReferenceImage.status == "active"
        ).first()
        
        result.append({
            "beneficiary_id": b.beneficiary_id,
            "beneficiary_user_id": b.beneficiary_user_id,
            "username": ben_user.username if ben_user else "unknown",
            "full_name": profile.full_name if profile else (ben_user.username if ben_user else "unknown"),
            "email": ben_user.email if ben_user else "",
            "relationship": b.relationship_label,
            "status": b.status,
            "has_reference_image": ref_img is not None,
            "created_at": b.created_at
        })
    return result

@router.post("/add", response_model=BeneficiaryResponse)
def add_beneficiary(payload: BeneficiaryAdd, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Hanya pewaris (owner) yang dapat menambah ahli waris")
        
    ben_user = db.query(User).filter(
        (User.username == payload.beneficiary_username_or_email) | (User.email == payload.beneficiary_username_or_email)
    ).first()
    
    if not ben_user:
        raise HTTPException(status_code=404, detail="Akun calon ahli waris tidak ditemukan. Pastikan mereka telah mendaftar di sistem.")
        
    if ben_user.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Anda tidak dapat menambahkan diri sendiri sebagai ahli waris")
        
    # Check existing relation
    existing = db.query(Beneficiary).filter(
        Beneficiary.owner_id == current_user.user_id,
        Beneficiary.beneficiary_user_id == ben_user.user_id
    ).first()
    
    if existing:
        if existing.status == "revoked":
            existing.status = "active"
            existing.relationship_label = payload.relationship
            db.commit()
            beneficiary = existing
        else:
            raise HTTPException(status_code=400, detail="Ahli waris ini sudah terdaftar dalam daftar Anda")
    else:
        beneficiary = Beneficiary(
            owner_id=current_user.user_id,
            beneficiary_user_id=ben_user.user_id,
            relationship_label=payload.relationship,
            status="active",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(beneficiary)
        db.commit()
        db.refresh(beneficiary)
        
    # Save reference image if provided
    has_ref = False
    if payload.reference_image_base64:
        try:
            img = decode_image_input(payload.reference_image_base64)
            filename = f"ref_ben_{beneficiary.beneficiary_id}_{uuid.uuid4().hex[:8]}.jpg"
            save_path = settings.REF_IMAGES_PATH / filename
            save_image_array(img, save_path)
            
            ref_image = BeneficiaryReferenceImage(
                beneficiary_id=beneficiary.beneficiary_id,
                image_path=str(save_path),
                consent_confirmed=payload.consent_confirmed,
                uploaded_at=utc_now(),
                status="active"
            )
            db.add(ref_image)
            db.commit()
            has_ref = True
        except Exception:
            pass
            
    record_audit_event(
        db=db,
        activity_type="BENEFICIARY_ADDED",
        user_id=current_user.user_id,
        entity_type="beneficiaries",
        entity_id=beneficiary.beneficiary_id,
        event_metadata={
            "beneficiary_user_id": ben_user.user_id,
            "relationship": payload.relationship,
            "has_ref_image": has_ref
        }
    )
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == ben_user.user_id).first()
    return {
        "beneficiary_id": beneficiary.beneficiary_id,
        "beneficiary_user_id": ben_user.user_id,
        "username": ben_user.username,
        "full_name": profile.full_name if profile else ben_user.username,
        "email": ben_user.email,
        "relationship": beneficiary.relationship_label,
        "status": beneficiary.status,
        "has_reference_image": has_ref,
        "created_at": beneficiary.created_at
    }

@router.delete("/{beneficiary_id}")
def revoke_beneficiary(beneficiary_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ben = db.query(Beneficiary).filter(
        Beneficiary.beneficiary_id == beneficiary_id,
        Beneficiary.owner_id == current_user.user_id
    ).first()
    
    if not ben:
        raise HTTPException(status_code=404, detail="Ahli waris tidak ditemukan")
        
    ben.status = "revoked"
    db.commit()
    
    record_audit_event(
        db=db,
        activity_type="BENEFICIARY_REVOKED",
        user_id=current_user.user_id,
        entity_type="beneficiaries",
        entity_id=beneficiary_id
    )
    return {"message": "Ahli waris berhasil dicabut"}
