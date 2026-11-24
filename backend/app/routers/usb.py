import os
import sys
import string
import secrets
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..config import settings, WORKSPACE_DIR
from ..database import get_db
from ..models import User, UserProfile, UsbDevice, utc_now
from ..schemas import RegisterUsbDevice, VerifyUsbDevice
from .auth import get_current_user, create_access_token
from ..crypto.hashing import sha256_hash
from ..blockchain.audit_chain import record_audit_event

router = APIRouter(prefix="/usb", tags=["USB Security Devices"])


def extract_fingerprint_from_keycontent(raw_content: str) -> str:
    """Extract SHA-256 device fingerprint from wariscrypt.key content or raw key."""
    fp = raw_content.strip()
    if "FINGERPRINT=" in fp:
        for line in fp.splitlines():
            line_s = line.strip()
            if line_s.startswith("FINGERPRINT="):
                return line_s.split("=", 1)[1].strip()
    if "RAW_KEY=" in fp:
        for line in fp.splitlines():
            line_s = line.strip()
            if line_s.startswith("RAW_KEY="):
                raw_val = line_s.split("=", 1)[1].strip()
                return sha256_hash(raw_val)
    if fp.startswith("WARISCRYPT-USBKEY-"):
        return sha256_hash(fp)
    return fp


def write_bootable_files_to_drive(
    drive_root: str,
    fingerprint: str,
    username: str,
    device_id: int,
    device_name: str,
    raw_key: str | None = None
) -> dict:
    """
    Write wariscrypt.key, Boot_WARISCRYPT.bat, and autorun.inf directly to the plugged-in USB flashdisk.
    """
    drive_path = Path(drive_root)
    if not drive_path.exists():
        raise IOError(f"Drive {drive_root} tidak ditemukan atau tidak terpasang.")

    key_lines = [
        "WARISCRYPT-DEVICE-KEY",
        f"FINGERPRINT={fingerprint}",
        f"USER={username}",
        f"ID={device_id}",
        f"DEVICE_NAME={device_name}",
    ]
    if raw_key:
        key_lines.append(f"RAW_KEY={raw_key}")

    key_file = drive_path / "wariscrypt.key"
    key_file.write_text("\n".join(key_lines) + "\n", encoding="utf-8")

    bat_content = (
        "@echo off\r\n"
        "title WARISCRYPT - Bootable USB Security Key\r\n"
        "color 0E\r\n"
        "echo =============================================================\r\n"
        "echo        WARISCRYPT - BOOTABLE HARDWARE USB KEY LAUNCHER\r\n"
        "echo =============================================================\r\n"
        "echo.\r\n"
        f"echo [+] Perangkat  : {device_name}\r\n"
        f"echo [+] Pemilik    : {username}\r\n"
        "echo [+] Kunci File : %~d0\\wariscrypt.key\r\n"
        "echo.\r\n"
        "echo [*] Membuka Halaman Login WARISCRYPT di Browser...\r\n"
        "start http://127.0.0.1:8000/static/sign-in.html\r\n"
        "timeout /t 2 >nul\r\n"
        "exit\r\n"
    )
    bat_file = drive_path / "Boot_WARISCRYPT.bat"
    bat_file.write_text(bat_content, encoding="utf-8")

    autorun_content = (
        "[Autorun]\r\n"
        "Open=Boot_WARISCRYPT.bat\r\n"
        "Action=Buka WARISCRYPT Digital Will Vault\r\n"
        f"Label=WARISCRYPT ({username})\r\n"
    )
    autorun_file = drive_path / "autorun.inf"
    try:
        autorun_file.write_text(autorun_content, encoding="utf-8")
    except Exception:
        # Some antivirus tools block writing autorun.inf; wariscrypt.key and Boot_WARISCRYPT.bat are sufficient
        pass

    return {
        "drive": drive_root,
        "files_written": ["wariscrypt.key", "Boot_WARISCRYPT.bat", "autorun.inf"]
    }


def scan_plugged_usb_drives(db: Session) -> dict:
    """
    Scan physical removable USB flashdisks plugged into the host computer
    and verify any wariscrypt.key found against the database.
    """
    drives_info = []

    if sys.platform == "win32":
        import ctypes
        from ctypes import windll

        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_root = f"{letter}:\\"
                dtype = windll.kernel32.GetDriveTypeW(drive_root)
                # dtype == 2 is DRIVE_REMOVABLE (USB Flashdisk)
                if dtype == 2:
                    vol_buf = ctypes.create_unicode_buffer(256)
                    fs_buf = ctypes.create_unicode_buffer(256)
                    res = windll.kernel32.GetVolumeInformationW(
                        drive_root, vol_buf, 256, None, None, None, fs_buf, 256
                    )
                    # If GetVolumeInformationW succeeds (res != 0), media is mounted and ready
                    if res != 0 or os.path.exists(drive_root):
                        label = vol_buf.value or "USB Flashdisk"
                        fs_type = fs_buf.value or "FAT32"
                        key_path = Path(drive_root) / "wariscrypt.key"
                        has_keyfile = False
                        verified = False
                        device_id = None
                        device_name = None
                        owner_user_id = None
                        owner_username = None
                        owner_full_name = None
                        owner_role = None

                        try:
                            if key_path.exists() and key_path.is_file():
                                has_keyfile = True
                                raw_content = key_path.read_text(encoding="utf-8").strip()
                                fp = extract_fingerprint_from_keycontent(raw_content)
                                device = db.query(UsbDevice).filter(
                                    UsbDevice.device_fingerprint == fp,
                                    UsbDevice.device_status == "active"
                                ).first()
                                if device:
                                    user = db.query(User).filter(User.user_id == device.user_id).first()
                                    if user and user.account_status == "active":
                                        profile = db.query(UserProfile).filter(UserProfile.user_id == user.user_id).first()
                                        verified = True
                                        device_id = device.device_id
                                        device_name = device.device_name
                                        owner_user_id = user.user_id
                                        owner_username = user.username
                                        owner_full_name = profile.full_name if profile else user.username
                                        owner_role = user.role
                        except Exception:
                            pass

                        drives_info.append({
                            "drive": drive_root,
                            "label": label,
                            "filesystem": fs_type,
                            "has_keyfile": has_keyfile,
                            "verified": verified,
                            "device_id": device_id,
                            "device_name": device_name,
                            "owner_user_id": owner_user_id,
                            "owner_username": owner_username,
                            "owner_full_name": owner_full_name,
                            "owner_role": owner_role
                        })
            bitmask >>= 1

    # Also check optional local simulation folder (WORKSPACE_DIR / "usb_drive") if present
    sim_dir = WORKSPACE_DIR / "usb_drive"
    sim_key = sim_dir / "wariscrypt.key"
    if sim_dir.exists() and sim_key.exists():
        has_keyfile = True
        verified = False
        device_id = None
        device_name = None
        owner_user_id = None
        owner_username = None
        owner_full_name = None
        owner_role = None
        try:
            raw_content = sim_key.read_text(encoding="utf-8").strip()
            fp = extract_fingerprint_from_keycontent(raw_content)
            device = db.query(UsbDevice).filter(
                UsbDevice.device_fingerprint == fp,
                UsbDevice.device_status == "active"
            ).first()
            if device:
                user = db.query(User).filter(User.user_id == device.user_id).first()
                if user and user.account_status == "active":
                    profile = db.query(UserProfile).filter(UserProfile.user_id == user.user_id).first()
                    verified = True
                    device_id = device.device_id
                    device_name = device.device_name
                    owner_user_id = user.user_id
                    owner_username = user.username
                    owner_full_name = profile.full_name if profile else user.username
                    owner_role = user.role
        except Exception:
            pass

        drives_info.append({
            "drive": str(sim_dir),
            "label": "VIRTUAL_USB",
            "filesystem": "LOCAL",
            "has_keyfile": has_keyfile,
            "verified": verified,
            "device_id": device_id,
            "device_name": device_name,
            "owner_user_id": owner_user_id,
            "owner_username": owner_username,
            "owner_full_name": owner_full_name,
            "owner_role": owner_role
        })

    usb_plugged = len(drives_info) > 0
    verified_drive = next((d for d in drives_info if d["verified"]), None)
    keyfile_drive = next((d for d in drives_info if d["has_keyfile"]), None)
    primary_drive = verified_drive or keyfile_drive or (drives_info[0] if drives_info else None)

    if not usb_plugged:
        msg = "Flashdisk belum terpasang. Colokkan Flashdisk ke port USB untuk membuka akses login."
    elif verified_drive:
        msg = (
            f"Flashdisk Bootable Terverifikasi di {verified_drive['drive']} ({verified_drive['label']}) "
            f"— Terdaftar untuk: {verified_drive['owner_full_name']} (@{verified_drive['owner_username']})"
        )
    elif keyfile_drive:
        msg = (
            f"Flashdisk terdeteksi di {keyfile_drive['drive']} ({keyfile_drive['label']}), "
            "namun berkas wariscrypt.key di dalamnya tidak cocok atau telah dicabut."
        )
    else:
        msg = (
            f"Flashdisk fisik terdeteksi di {primary_drive['drive']} ({primary_drive['label']}). "
            "Akses login dibuka — Anda dapat memasang kunci bootable di menu Flashdisk setelah masuk."
        )

    return {
        "usb_plugged": usb_plugged,
        "drives": drives_info,
        "active_drive": primary_drive["drive"] if primary_drive else None,
        "active_label": primary_drive["label"] if primary_drive else None,
        "has_keyfile": any(d["has_keyfile"] for d in drives_info),
        "verified": verified_drive is not None,
        "device_id": verified_drive["device_id"] if verified_drive else None,
        "device_name": verified_drive["device_name"] if verified_drive else None,
        "owner_user_id": verified_drive["owner_user_id"] if verified_drive else None,
        "owner_username": verified_drive["owner_username"] if verified_drive else None,
        "owner_full_name": verified_drive["owner_full_name"] if verified_drive else None,
        "owner_role": verified_drive["owner_role"] if verified_drive else None,
        "message": msg
    }


@router.get("/detect")
def detect_plugged_usb(db: Session = Depends(get_db)):
    """
    Live USB hardware detection endpoint polled by sign-in.html and usb-setup.html.
    """
    return scan_plugged_usb_drives(db)


@router.post("/boot-login")
def usb_boot_login(db: Session = Depends(get_db)):
    """
    1-Click Bootable USB Login: Authenticates the user directly using the verified
    wariscrypt.key on the plugged-in physical USB Flashdisk.
    """
    state = scan_plugged_usb_drives(db)
    if not state["usb_plugged"]:
        raise HTTPException(
            status_code=403,
            detail="Akses Ditolak: Tidak ada Flashdisk yang tercolok pada port USB komputer."
        )
    if not state["verified"] or not state["owner_user_id"]:
        raise HTTPException(
            status_code=403,
            detail="Flashdisk yang tercolok belum memiliki berkas kunci wariscrypt.key yang terdaftar. Silakan login dengan password lalu pasang kunci di menu Flashdisk."
        )

    user = db.query(User).filter(User.user_id == state["owner_user_id"]).first()
    if not user or user.account_status != "active":
        raise HTTPException(status_code=403, detail="Akun pemilik Flashdisk tidak aktif.")

    device = db.query(UsbDevice).filter(UsbDevice.device_id == state["device_id"]).first()
    if device:
        device.last_used_at = utc_now()
    user.last_login_at = utc_now()
    db.commit()

    record_audit_event(
        db=db,
        activity_type="USER_LOGIN_USB_BOOTABLE",
        user_id=user.user_id,
        entity_type="usb_devices",
        entity_id=state["device_id"],
        event_metadata={
            "drive": state["active_drive"],
            "device_name": state["device_name"]
        }
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


@router.get("/")
def list_usb_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = scan_plugged_usb_drives(db)
    plugged_device_id = state.get("device_id")

    devices = db.query(UsbDevice).filter(UsbDevice.user_id == current_user.user_id).all()
    return [
        {
            "device_id": d.device_id,
            "device_name": d.device_name,
            "device_fingerprint": d.device_fingerprint[:16] + "...",
            "full_fingerprint": d.device_fingerprint,
            "device_status": d.device_status,
            "is_currently_plugged": (d.device_id == plugged_device_id),
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
        device_name=payload.device_name or "Flashdisk Bootable WARISCRYPT",
        device_fingerprint=device_fingerprint,
        public_key_fingerprint=None,
        device_status="active",
        registered_at=utc_now()
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    # Check if a physical removable drive is plugged in right now, and write directly to it!
    state = scan_plugged_usb_drives(db)
    written_drive = None
    write_error = None
    if state["usb_plugged"] and state["drives"]:
        target_drive = state["drives"][0]["drive"]
        try:
            write_bootable_files_to_drive(
                drive_root=target_drive,
                fingerprint=device.device_fingerprint,
                username=current_user.username,
                device_id=device.device_id,
                device_name=device.device_name,
                raw_key=raw_key
            )
            written_drive = target_drive
        except Exception as e:
            write_error = str(e)

    record_audit_event(
        db=db,
        activity_type="USB_DEVICE_REGISTERED",
        user_id=current_user.user_id,
        entity_type="usb_devices",
        entity_id=device.device_id,
        event_metadata={
            "device_name": device.device_name,
            "written_to_drive": written_drive
        }
    )

    key_content = (
        f"WARISCRYPT-DEVICE-KEY\n"
        f"FINGERPRINT={device.device_fingerprint}\n"
        f"USER={current_user.username}\n"
        f"ID={device.device_id}\n"
        f"DEVICE_NAME={device.device_name}\n"
        f"RAW_KEY={raw_key}\n"
    )

    return {
        "device_id": device.device_id,
        "device_name": device.device_name,
        "device_fingerprint": device.device_fingerprint,
        "raw_key_payload": key_content,
        "written_to_drive": written_drive,
        "write_error": write_error,
        "instructions": (
            f"Kunci Bootable telah otomatis dipasang ke Flashdisk {written_drive}!"
            if written_drive
            else "Simpan berkas 'wariscrypt.key' ke direktori utama (root) flashdisk Anda."
        )
    }


@router.post("/install-to-drive/{device_id}")
def install_key_to_plugged_drive(device_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Write an existing registered USB key directly to the currently plugged-in USB flashdisk.
    """
    device = db.query(UsbDevice).filter(
        UsbDevice.device_id == device_id,
        UsbDevice.user_id == current_user.user_id
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Data kunci perangkat tidak ditemukan.")

    state = scan_plugged_usb_drives(db)
    if not state["usb_plugged"] or not state["drives"]:
        raise HTTPException(
            status_code=400,
            detail="Tidak ada Flashdisk yang tercolok di port USB saat ini. Harap colokkan Flashdisk terlebih dahulu."
        )

    target_drive = state["drives"][0]["drive"]
    try:
        res = write_bootable_files_to_drive(
            drive_root=target_drive,
            fingerprint=device.device_fingerprint,
            username=current_user.username,
            device_id=device.device_id,
            device_name=device.device_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menulis ke Flashdisk {target_drive}: {e}")

    device.last_used_at = utc_now()
    db.commit()

    return {
        "status": "success",
        "drive": target_drive,
        "files_written": res["files_written"],
        "message": f"Berhasil memasang kunci bootable (wariscrypt.key & Boot_WARISCRYPT.bat) langsung ke Flashdisk {target_drive}!"
    }


@router.delete("/{device_id}")
def delete_usb_device(device_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Revoke and delete a registered USB device, and clean wariscrypt.key from plugged drive if it matches.
    """
    device = db.query(UsbDevice).filter(
        UsbDevice.device_id == device_id,
        UsbDevice.user_id == current_user.user_id
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Perangkat USB tidak ditemukan.")

    # Check if plugged drive has this device's keyfile and remove it
    state = scan_plugged_usb_drives(db)
    removed_from_drive = None
    for d in state.get("drives", []):
        if d.get("device_id") == device.device_id:
            try:
                for fname in ["wariscrypt.key", "Boot_WARISCRYPT.bat", "autorun.inf"]:
                    p = Path(d["drive"]) / fname
                    if p.exists():
                        p.unlink()
                removed_from_drive = d["drive"]
            except Exception:
                pass

    db.delete(device)
    db.commit()

    return {
        "status": "deleted",
        "removed_from_drive": removed_from_drive,
        "message": "Kunci Flashdisk berhasil dicabut dan dihapus."
    }


@router.get("/download-keyfile/{device_id}")
def download_keyfile(device_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.query(UsbDevice).filter(
        UsbDevice.device_id == device_id,
        UsbDevice.user_id == current_user.user_id
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Perangkat USB tidak ditemukan")

    content = (
        f"WARISCRYPT-DEVICE-KEY\n"
        f"FINGERPRINT={device.device_fingerprint}\n"
        f"USER={current_user.username}\n"
        f"ID={device.device_id}\n"
        f"DEVICE_NAME={device.device_name}\n"
    )
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
    fp = extract_fingerprint_from_keycontent(payload.device_fingerprint)

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
        "redirect_url": "/static/dashboard.html",
        "message": "Autentikasi USB Flashdisk WARISCRYPT berhasil!"
    }
