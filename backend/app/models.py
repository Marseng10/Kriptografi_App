from datetime import datetime, timezone
from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, DateTime, Boolean,
    ForeignKey, Enum, DECIMAL, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from .database import Base

def pk_bigint():
    """Generates BigInteger on MySQL/Postgres and Integer on SQLite so autoincrement works everywhere."""
    return BigInteger().with_variant(Integer, "sqlite")

def utc_now():
    return datetime.now(timezone.utc)

# 1. users
class User(Base):
    __tablename__ = "users"

    user_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("owner", "beneficiary", name="user_role_enum"), nullable=False, default="owner")
    account_status = Column(Enum("active", "suspended", "disabled", name="account_status_enum"), nullable=False, default="active")
    email_verified_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    biometrics = relationship("BiometricTemplate", back_populates="user", cascade="all, delete-orphan")
    usb_devices = relationship("UsbDevice", back_populates="user", cascade="all, delete-orphan")
    owned_beneficiaries = relationship("Beneficiary", foreign_keys="Beneficiary.owner_id", back_populates="owner")
    as_beneficiary = relationship("Beneficiary", foreign_keys="Beneficiary.beneficiary_user_id", back_populates="beneficiary_user")
    digital_assets = relationship("DigitalAsset", back_populates="owner")
    encryption_keys = relationship("EncryptionKey", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

# 2. user_profiles
class UserProfile(Base):
    __tablename__ = "user_profiles"

    profile_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    user_id = Column(pk_bigint(), ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(120), nullable=False)
    phone_number = Column(String(25), nullable=True)
    profile_photo_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="profile")

# 3. biometric_templates
class BiometricTemplate(Base):
    __tablename__ = "biometric_templates"

    biometric_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    user_id = Column(pk_bigint(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    template_path = Column(String(500), nullable=False)
    template_version = Column(String(30), nullable=True)
    consent_status = Column(Boolean, default=False, nullable=False)
    consented_at = Column(DateTime, nullable=True)
    status = Column(Enum("active", "revoked", "deleted", name="biometric_status_enum"), default="active", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="biometrics")

# 4. usb_devices
class UsbDevice(Base):
    __tablename__ = "usb_devices"

    device_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    user_id = Column(pk_bigint(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    device_name = Column(String(100), nullable=True)
    device_fingerprint = Column(String(255), unique=True, nullable=False)
    public_key_fingerprint = Column(String(255), nullable=True)
    device_status = Column(Enum("active", "revoked", "lost", name="usb_status_enum"), default="active", nullable=False)
    registered_at = Column(DateTime, default=utc_now, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="usb_devices")

    __table_args__ = (
        Index("idx_usb_user_status", "user_id", "device_status"),
    )

# 5. beneficiaries
class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    beneficiary_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    owner_id = Column(pk_bigint(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    beneficiary_user_id = Column(pk_bigint(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_label = Column("relationship", String(50), nullable=True)
    status = Column(Enum("active", "inactive", "revoked", name="beneficiary_status_enum"), default="active", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_beneficiaries")
    beneficiary_user = relationship("User", foreign_keys=[beneficiary_user_id], back_populates="as_beneficiary")
    reference_images = relationship("BeneficiaryReferenceImage", back_populates="beneficiary", cascade="all, delete-orphan")
    permissions = relationship("AssetPermission", back_populates="beneficiary", cascade="all, delete-orphan")
    tokens = relationship("ClaimToken", back_populates="beneficiary", cascade="all, delete-orphan")
    claims = relationship("InheritanceClaim", back_populates="beneficiary", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("owner_id", "beneficiary_user_id", name="uq_owner_beneficiary"),
        Index("idx_ben_user_status", "beneficiary_user_id", "status"),
    )

# 6. beneficiary_reference_images
class BeneficiaryReferenceImage(Base):
    __tablename__ = "beneficiary_reference_images"

    image_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    beneficiary_id = Column(pk_bigint(), ForeignKey("beneficiaries.beneficiary_id", ondelete="CASCADE"), nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    consent_confirmed = Column(Boolean, default=False, nullable=False)
    uploaded_at = Column(DateTime, default=utc_now, nullable=False)
    status = Column(Enum("active", "revoked", "deleted", name="ref_image_status_enum"), default="active", nullable=False)

    beneficiary = relationship("Beneficiary", back_populates="reference_images")

# 12. encryption_keys (defined before digital_assets due to FK)
class EncryptionKey(Base):
    __tablename__ = "encryption_keys"

    key_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    user_id = Column(pk_bigint(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    key_identifier = Column(String(255), unique=True, nullable=False)
    algorithm = Column(String(50), nullable=False)
    key_version = Column(Integer, nullable=False, default=1)
    key_status = Column(Enum("active", "rotated", "revoked", name="key_status_enum"), default="active", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    rotated_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="encryption_keys")
    assets = relationship("DigitalAsset", back_populates="key_metadata")

    __table_args__ = (
        Index("idx_key_user_status", "user_id", "key_status"),
    )

# 7. digital_assets
class DigitalAsset(Base):
    __tablename__ = "digital_assets"

    asset_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    owner_id = Column(pk_bigint(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    asset_name = Column(String(150), nullable=False)
    asset_type = Column(Enum("message", "document", name="asset_type_enum"), nullable=False)
    original_filename = Column(String(255), nullable=True)
    encrypted_file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    encryption_algorithm = Column(String(50), nullable=False)
    key_id = Column(pk_bigint(), ForeignKey("encryption_keys.key_id", ondelete="SET NULL"), nullable=True)
    nonce = Column(String(255), nullable=True)
    auth_tag = Column(String(255), nullable=True)
    asset_status = Column(Enum("active", "archived", "deleted", name="asset_status_enum"), default="active", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("User", back_populates="digital_assets")
    key_metadata = relationship("EncryptionKey", back_populates="assets")
    permissions = relationship("AssetPermission", back_populates="asset", cascade="all, delete-orphan")
    tokens = relationship("ClaimToken", back_populates="asset")

    __table_args__ = (
        Index("idx_asset_owner_status", "owner_id", "asset_status"),
    )

# 8. asset_permissions
class AssetPermission(Base):
    __tablename__ = "asset_permissions"

    permission_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    asset_id = Column(pk_bigint(), ForeignKey("digital_assets.asset_id", ondelete="CASCADE"), nullable=False)
    beneficiary_id = Column(pk_bigint(), ForeignKey("beneficiaries.beneficiary_id", ondelete="CASCADE"), nullable=False)
    access_status = Column(Enum("pending", "authorized", "revoked", name="access_status_enum"), default="authorized", nullable=False)
    release_status = Column(Enum("locked", "released", name="release_status_enum"), default="locked", nullable=False)
    released_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    asset = relationship("DigitalAsset", back_populates="permissions")
    beneficiary = relationship("Beneficiary", back_populates="permissions")

    __table_args__ = (
        UniqueConstraint("asset_id", "beneficiary_id", name="uq_asset_beneficiary"),
        Index("idx_perm_ben_release", "beneficiary_id", "release_status"),
    )

# 9. claim_tokens
class ClaimToken(Base):
    __tablename__ = "claim_tokens"

    token_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    beneficiary_id = Column(pk_bigint(), ForeignKey("beneficiaries.beneficiary_id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(pk_bigint(), ForeignKey("digital_assets.asset_id", ondelete="CASCADE"), nullable=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    token_ciphertext = Column(Text, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    token_status = Column(Enum("active", "used", "revoked", "expired", name="token_status_enum"), default="active", nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    beneficiary = relationship("Beneficiary", back_populates="tokens")
    asset = relationship("DigitalAsset", back_populates="tokens")
    claims = relationship("InheritanceClaim", back_populates="token")

    __table_args__ = (
        Index("idx_token_ben_status_exp", "beneficiary_id", "token_status", "expiry_date"),
    )

# 10. inheritance_claims
class InheritanceClaim(Base):
    __tablename__ = "inheritance_claims"

    claim_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    beneficiary_id = Column(pk_bigint(), ForeignKey("beneficiaries.beneficiary_id", ondelete="CASCADE"), nullable=False)
    token_id = Column(pk_bigint(), ForeignKey("claim_tokens.token_id", ondelete="CASCADE"), nullable=False)
    uploaded_image_path = Column(String(500), nullable=True)
    claim_status = Column(Enum("pending", "approved", "rejected", "expired", name="claim_status_enum"), default="pending", nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    beneficiary = relationship("Beneficiary", back_populates="claims")
    token = relationship("ClaimToken", back_populates="claims")
    verifications = relationship("ClaimVerification", back_populates="claim", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_claim_ben_status", "beneficiary_id", "claim_status"),
        Index("idx_claim_token", "token_id"),
    )

# 11. claim_verifications
class ClaimVerification(Base):
    __tablename__ = "claim_verifications"

    verification_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    claim_id = Column(pk_bigint(), ForeignKey("inheritance_claims.claim_id", ondelete="CASCADE"), nullable=False)
    verification_type = Column(Enum("token", "face_matching", "additional", name="verif_type_enum"), nullable=False)
    verification_result = Column(Enum("pending", "passed", "failed", name="verif_result_enum"), default="pending", nullable=False)
    similarity_score = Column(DECIMAL(6, 5), nullable=True)
    failure_reason_code = Column(String(50), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    claim = relationship("InheritanceClaim", back_populates="verifications")

    __table_args__ = (
        Index("idx_verif_claim_type", "claim_id", "verification_type"),
    )

# 13. audit_logs (Simple Blockchain / Tamper-evident ledger)
class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    user_id = Column(pk_bigint(), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    activity_type = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(BigInteger, nullable=True)
    event_metadata = Column(JSON, nullable=True)
    previous_hash = Column(String(64), nullable=True)
    current_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_created", "user_id", "created_at"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
        Index("idx_audit_created", "created_at"),
    )
