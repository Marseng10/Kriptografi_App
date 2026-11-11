from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel

# Auth & User
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "owner"  # "owner" or "beneficiary"
    phone_number: Optional[str] = None
    face_image_base64: Optional[str] = None  # Optional face registration

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class FaceLoginRequest(BaseModel):
    username_or_email: str
    face_image_base64: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserProfileResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    full_name: str
    phone_number: Optional[str]
    has_face_registered: bool
    created_at: datetime

# Beneficiaries
class BeneficiaryAdd(BaseModel):
    beneficiary_username_or_email: str
    relationship: Optional[str] = None
    consent_confirmed: bool = True
    reference_image_base64: Optional[str] = None

class BeneficiaryResponse(BaseModel):
    beneficiary_id: int
    beneficiary_user_id: int
    username: str
    full_name: str
    email: str
    relationship: Optional[str]
    status: str
    has_reference_image: bool
    created_at: datetime

# Digital Assets
class CreateMessageAsset(BaseModel):
    asset_name: str
    message_content: str
    beneficiary_ids: List[int]
    generate_stego: bool = True

class AssetPermissionUpdate(BaseModel):
    permission_id: int
    release_status: str  # "locked" or "released"

class AssetResponse(BaseModel):
    asset_id: int
    asset_name: str
    asset_type: str
    original_filename: Optional[str]
    mime_type: Optional[str]
    file_size: Optional[int]
    encryption_algorithm: str
    asset_status: str
    created_at: datetime
    permissions: List[dict]
    latest_stego_download_url: Optional[str] = None

# Claims
class SubmitClaimRequest(BaseModel):
    face_image_base64: str  # Live selfie/photo for biometric matching

class ClaimResultResponse(BaseModel):
    claim_id: int
    status: str
    token_valid: bool
    face_match_passed: bool
    similarity_score: float
    failure_reason: Optional[str]
    released_assets: List[dict]

# USB Devices
class RegisterUsbDevice(BaseModel):
    device_name: str
    device_fingerprint: Optional[str] = None

class VerifyUsbDevice(BaseModel):
    device_fingerprint: str

# Educational Crypto Demo
class CryptoDemoRequest(BaseModel):
    plaintext: str
    key: str

class CryptoDemoResponse(BaseModel):
    plaintext: str
    vigenere_ciphertext: str
    aes_ciphertext: str
    chacha_ciphertext: str
    comparison_notes: str

# Audit Log
class AuditLogResponse(BaseModel):
    log_id: int
    user_id: Optional[int]
    username: Optional[str]
    activity_type: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    event_metadata: Optional[dict]
    previous_hash: Optional[str]
    current_hash: str
    created_at: datetime
