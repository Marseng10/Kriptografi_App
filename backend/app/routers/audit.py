from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, AuditLog
from ..schemas import AuditLogResponse
from .auth import get_current_user
from ..blockchain.audit_chain import verify_audit_chain_integrity

router = APIRouter(prefix="/audit", tags=["Blockchain Audit Ledger"])

@router.get("/chain")
def get_audit_chain(limit: int = 50, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve audit log blocks with tamper-evident SHA-256 chain metadata."""
    query = db.query(AuditLog)
    # If not owner, filter to current user's events
    if current_user.role != "owner":
        query = query.filter(AuditLog.user_id == current_user.user_id)
        
    logs = query.order_by(AuditLog.log_id.desc()).limit(limit).all()
    
    res = []
    for log in logs:
        res.append({
            "log_id": log.log_id,
            "user_id": log.user_id,
            "activity_type": log.activity_type,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "event_metadata": log.event_metadata,
            "previous_hash": log.previous_hash,
            "current_hash": log.current_hash,
            "created_at": log.created_at
        })
    return res

@router.get("/verify")
def verify_chain(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Perform full cryptographic blockchain verification."""
    result = verify_audit_chain_integrity(db)
    return result
