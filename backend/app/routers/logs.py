from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from ..database import get_db
from ..models import User, SystemLog, OperationLog
from ..auth_deps import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/logs",
    tags=["logs"]
)

class SystemLogSchema(BaseModel):
    id: int
    level: str
    category: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True

class OperationLogSchema(BaseModel):
    id: int
    user_id: Optional[int] = None
    action_type: str
    status: str
    details: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/system", response_model=List[SystemLogSchema])
def get_system_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches the most recent system logs. Accessible by all authenticated users."""
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()
    return logs

@router.get("/operations", response_model=List[OperationLogSchema])
def get_operation_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the most recent operation logs (business operations like grading) with pagination.
    Supports skip and limit parameters for pagination.
    Results are ordered by timestamp (newest first).
    """
    logs = db.query(OperationLog)\
        .filter(OperationLog.user_id == current_user.id)\
        .order_by(OperationLog.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return logs
