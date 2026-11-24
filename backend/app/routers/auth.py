import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User, UserProfile, BiometricTemplate, utc_now
from ..schemas import UserCreate, UserLogin, FaceLoginRequest, TokenResponse, UserProfileResponse
from ..crypto.hashing import hash_password, verify_password
from ..biometrics.face_service import save_image_array, decode_image_input, compute_face_similarity
from ..blockchain.audit_chain import record_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    user = db.query(User).filter(User.user_id == int(user_id)).first()
    if user is None or user.account_status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or not found")
    return user

@router.post("/register", response_model=TokenResponse)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    # Check if username or email already exists
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
        
    # Hash password with Argon2id
    pw_hash = hash_password(payload.password)
    
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=pw_hash,
        role=payload.role if payload.role in ["owner", "beneficiary"] else "owner",
        account_status="active",
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create profile
    profile = UserProfile(
        user_id=user.user_id,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(profile)
    
    # Process optional face registration
    if payload.face_image_base64:
        try:
            img = decode_image_input(payload.face_image_base64)
            filename = f"user_{user.user_id}_{uuid.uuid4().hex[:8]}.jpg"
            save_path = settings.BIOMETRICS_PATH / filename
            save_image_array(img, save_path)
            
            biometric = BiometricTemplate(
                user_id=user.user_id,
                template_path=str(save_path),
                template_version="1.0-lbph-orb",
                consent_status=True,
                consented_at=utc_now(),
                status="active"
            )
            db.add(biometric)
            profile.profile_photo_path = str(save_path)
        except Exception as e:
            # Non-fatal if face registration fails during signup
            pass
            
    db.commit()
    
    # Log to blockchain audit trail
    record_audit_event(
        db=db,
        activity_type="USER_REGISTERED",
        user_id=user.user_id,
        entity_type="users",
        entity_id=user.user_id,
        event_metadata={"username": user.username, "role": user.role}
    )
    
    token = create_access_token(data={"sub": str(user.user_id), "role": user.role, "username": user.username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "full_name": profile.full_name
        }
    }

def enforce_usb_requirement(user: User, db: Session):
    """
    Pastikan Flashdisk fisik sedang tercolok di port USB saat login.
    Jika akun sudah memiliki kunci Flashdisk terdaftar, pastikan wariscrypt.key di Flashdisk cocok.
    """
    from .usb import scan_plugged_usb_drives
    from ..models import UsbDevice

    usb_state = scan_plugged_usb_drives(db)
    if not usb_state["usb_plugged"]:
        raise HTTPException(
            status_code=403,
            detail="Akses Login Ditolak: Flashdisk wajib dicolokkan ke port USB komputer untuk dapat login!"
        )

    user_devices = db.query(UsbDevice).filter(
        UsbDevice.user_id == user.user_id,
        UsbDevice.device_status == "active"
    ).all()

    if user_devices:
        user_device_ids = {d.device_id for d in user_devices}
        matched_drive = next(
            (dr for dr in usb_state.get("drives", []) if dr.get("verified") and dr.get("device_id") in user_device_ids),
            None
        )
        if not matched_drive:
            raise HTTPException(
                status_code=403,
                detail="Akses Login Ditolak: Akun Anda telah dikunci dengan Flashdisk khusus, namun berkas wariscrypt.key yang sesuai tidak ditemukan di Flashdisk yang tercolok!"
            )
        matched_dev = next((d for d in user_devices if d.device_id == matched_drive["device_id"]), None)
        if matched_dev:
            matched_dev.last_used_at = utc_now()


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == payload.username_or_email) | (User.email == payload.username_or_email)
    ).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        record_audit_event(
            db=db,
            activity_type="LOGIN_FAILED_BAD_PASSWORD",
            user_id=user.user_id if user else None,
            event_metadata={"identifier": payload.username_or_email}
        )
        raise HTTPException(status_code=401, detail="Kredensial login tidak valid")
        
    if user.account_status != "active":
        raise HTTPException(status_code=403, detail="Akun dinonaktifkan atau disuspend")

    # Wajib ada Flashdisk yang tercolok (& cocok jika sudah setup kunci)
    enforce_usb_requirement(user, db)
        
    user.last_login_at = utc_now()
    db.commit()
    
    record_audit_event(
        db=db,
        activity_type="USER_LOGIN_PASSWORD",
        user_id=user.user_id,
        entity_type="users",
        entity_id=user.user_id,
        event_metadata={"role": user.role}
    )
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.user_id).first()
    full_name = profile.full_name if profile else user.username
    
    token = create_access_token(data={"sub": str(user.user_id), "role": user.role, "username": user.username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "full_name": full_name
        }
    }

@router.post("/face-login", response_model=TokenResponse)
def face_login(payload: FaceLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == payload.username_or_email) | (User.email == payload.username_or_email)
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")

    # Wajib ada Flashdisk yang tercolok (& cocok jika sudah setup kunci)
    enforce_usb_requirement(user, db)
        
    # Get active biometric template
    biometric = db.query(BiometricTemplate).filter(
        BiometricTemplate.user_id == user.user_id,
        BiometricTemplate.status == "active"
    ).order_by(BiometricTemplate.biometric_id.desc()).first()
    
    if not biometric or not Path(biometric.template_path).exists():
        raise HTTPException(status_code=400, detail="Wajah belum didaftarkan untuk akun ini. Silakan login dengan password terlebih dahulu.")
        
    match_result = compute_face_similarity(biometric.template_path, payload.face_image_base64)
    
    if not match_result["passed"]:
        record_audit_event(
            db=db,
            activity_type="FACE_LOGIN_FAILED",
            user_id=user.user_id,
            event_metadata={"similarity": match_result["score"]}
        )
        raise HTTPException(
            status_code=401, 
            detail=f"Verifikasi wajah gagal. Skor kecocokan: {match_result['score'] * 100:.1f}% (Minimum {settings.FACE_MATCH_THRESHOLD * 100:.1f}%)"
        )
        
    user.last_login_at = utc_now()
    db.commit()
    
    record_audit_event(
        db=db,
        activity_type="USER_LOGIN_FACE",
        user_id=user.user_id,
        entity_type="users",
        entity_id=user.user_id,
        event_metadata={"similarity_score": match_result["score"]}
    )
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.user_id).first()
    full_name = profile.full_name if profile else user.username
    
    token = create_access_token(data={"sub": str(user.user_id), "role": user.role, "username": user.username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "full_name": full_name
        }
    }

@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.user_id).first()
    biometric = db.query(BiometricTemplate).filter(
        BiometricTemplate.user_id == current_user.user_id,
        BiometricTemplate.status == "active"
    ).first()
    
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": profile.full_name if profile else current_user.username,
        "phone_number": profile.phone_number if profile else None,
        "has_face_registered": biometric is not None,
        "created_at": current_user.created_at
    }
