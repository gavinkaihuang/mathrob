from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from ..database import get_db
from ..models import User, SystemLog
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

@router.get("/system", response_model=List[SystemLogSchema])
def get_system_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches the most recent system logs. Accessible by all authenticated users."""
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()
    return logs
