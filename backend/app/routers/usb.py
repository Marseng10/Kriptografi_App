import secrets
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User, UsbDevice, utc_now
from ..schemas import RegisterUsbDevice, VerifyUsbDevice
from .auth import get_current_user
from ..crypto.hashing import sha256_hash
from ..blockchain.audit_chain import record_audit_event

router = APIRouter(prefix="/usb", tags=["USB Security Devices"])

@router.get("/")
def list_usb_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    devices = db.query(UsbDevice).filter(UsbDevice.user_id == current_user.user_id).all()
    return [
        {
            "device_id": d.device_id,
            "device_name": d.device_name,
            "device_fingerprint": d.device_fingerprint[:16] + "...",
            "device_status": d.device_status,
            "registered_at": d.registered_at,
            "last_used_at": d.last_used_at
        } for d in devices
    ]

@router.post("/register")
def register_usb_device(payload: RegisterUsbDevice, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Generate cryptographic device token & fingerprint
    raw_key = f"WARISCRYPT-USBKEY-{secrets.token_hex(32)}"
    device_fingerprint = sha256_hash(raw_key)
    
    device = UsbDevice(
        user_id=current_user.user_id,
        device_name=payload.device_name or "My WARISCRYPT USB Drive",
        device_fingerprint=device_fingerprint,
        public_key_fingerprint=None,
        device_status="active",
        registered_at=utc_now()
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    
    record_audit_event(
        db=db,
        activity_type="USB_DEVICE_REGISTERED",
        user_id=current_user.user_id,
        entity_type="usb_devices",
        entity_id=device.device_id,
        event_metadata={"device_name": device.device_name}
    )
    
    return {
        "device_id": device.device_id,
        "device_name": device.device_name,
        "device_fingerprint": device.device_fingerprint,
        "raw_key_payload": raw_key,
        "instructions": "Simpan raw_key_payload ke file bernama 'wariscrypt.key' di root flashdisk Anda."
    }

@router.get("/download-keyfile/{device_id}")
def download_keyfile(device_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.query(UsbDevice).filter(
        UsbDevice.device_id == device_id,
        UsbDevice.user_id == current_user.user_id
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Perangkat USB tidak ditemukan")
        
    content = f"WARISCRYPT-DEVICE-KEY\nFINGERPRINT={device.device_fingerprint}\nUSER={current_user.username}\nID={device.device_id}\n"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="wariscrypt.key"'}
    )

@router.post("/verify")
def verify_usb_device(payload: VerifyUsbDevice, db: Session = Depends(get_db)):
    """
    Public or client verification endpoint invoked by USB Launcher app.
    """
    # Check if raw key was passed or direct fingerprint
    fp = payload.device_fingerprint.strip()
    if fp.startswith("WARISCRYPT-USBKEY-"):
        fp = sha256_hash(fp)
    elif "FINGERPRINT=" in fp:
        for line in fp.splitlines():
            if line.startswith("FINGERPRINT="):
                fp = line.split("=", 1)[1].strip()
                break

    device = db.query(UsbDevice).filter(UsbDevice.device_fingerprint == fp).first()
    if not device or device.device_status != "active":
        return {
            "authenticated": False,
            "message": "USB Drive tidak sah, dicabut, atau belum terdaftar di sistem."
        }
        
    device.last_used_at = utc_now()
    db.commit()
    
    record_audit_event(
        db=db,
        activity_type="USB_LAUNCHER_AUTHENTICATED",
        user_id=device.user_id,
        entity_type="usb_devices",
        entity_id=device.device_id,
        event_metadata={"device_name": device.device_name}
    )
    
    user = db.query(User).filter(User.user_id == device.user_id).first()
    return {
        "authenticated": True,
        "device_name": device.device_name,
        "owner_username": user.username if user else "Unknown",
        "redirect_url": "/dashboard.html",
        "message": "Autentikasi USB Flashdisk WARISCRYPT berhasil!"
    }
