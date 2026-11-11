import json
import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models import AuditLog

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def calculate_log_hash(
    previous_hash: str | None,
    user_id: int | None,
    activity_type: str,
    entity_type: str | None,
    entity_id: int | None,
    event_metadata: dict | None,
    created_at_iso: str
) -> str:
    """
    Deterministic SHA-256 hash calculation for a blockchain audit block.
    """
    payload = {
        "previous_hash": previous_hash or GENESIS_HASH,
        "user_id": user_id,
        "activity_type": activity_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "event_metadata": event_metadata or {},
        "created_at": created_at_iso
    }
    canonical_string = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()

def record_audit_event(
    db: Session,
    activity_type: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    event_metadata: dict | None = None
) -> AuditLog:
    """
    Append an immutable event to the hash-linked audit blockchain.
    """
    # Sanitize metadata: remove any sensitive keys just in case
    clean_meta = {}
    if event_metadata:
        for k, v in event_metadata.items():
            if any(forbidden in k.lower() for forbidden in ["password", "key", "token_raw", "secret", "biometric"]):
                clean_meta[k] = "[REDACTED]"
            else:
                clean_meta[k] = v
                
    # Get last log entry to retrieve previous_hash
    last_log = db.query(AuditLog).order_by(AuditLog.log_id.desc()).first()
    previous_hash = last_log.current_hash if last_log else GENESIS_HASH
    
    now_utc = datetime.now(timezone.utc)
    created_at_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    current_hash = calculate_log_hash(
        previous_hash=previous_hash,
        user_id=user_id,
        activity_type=activity_type,
        entity_type=entity_type,
        entity_id=entity_id,
        event_metadata=clean_meta,
        created_at_iso=created_at_iso
    )
    
    log_entry = AuditLog(
        user_id=user_id,
        activity_type=activity_type,
        entity_type=entity_type,
        entity_id=entity_id,
        event_metadata=clean_meta,
        previous_hash=previous_hash,
        current_hash=current_hash,
        created_at=now_utc
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

def verify_audit_chain_integrity(db: Session) -> dict:
    """
    Verify the entire hash-chain continuity from genesis to the latest record.
    Returns audit verification status.
    """
    logs = db.query(AuditLog).order_by(AuditLog.log_id.asc()).all()
    if not logs:
        return {
            "is_valid": True,
            "total_blocks": 0,
            "genesis_block": None,
            "latest_block": None,
            "broken_at_block": None,
            "details": "Blockchain ledger is empty."
        }
        
    expected_prev = GENESIS_HASH
    for log in logs:
        if (log.previous_hash or GENESIS_HASH) != expected_prev:
            return {
                "is_valid": False,
                "total_blocks": len(logs),
                "broken_at_block": log.log_id,
                "details": f"Chain broken at block {log.log_id}: previous_hash mismatch."
            }
            
        created_at_iso = log.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        recalculated_hash = calculate_log_hash(
            previous_hash=log.previous_hash,
            user_id=log.user_id,
            activity_type=log.activity_type,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            event_metadata=log.event_metadata,
            created_at_iso=created_at_iso
        )
        
        if recalculated_hash != log.current_hash:
            return {
                "is_valid": False,
                "total_blocks": len(logs),
                "broken_at_block": log.log_id,
                "details": f"Tampering detected at block {log.log_id}: block data does not match current_hash."
            }
            
        expected_prev = log.current_hash
        
    return {
        "is_valid": True,
        "total_blocks": len(logs),
        "genesis_block": logs[0].current_hash,
        "latest_block": logs[-1].current_hash,
        "broken_at_block": None,
        "details": "All blocks and hash-chain signatures verified intact. No tampering detected."
    }
