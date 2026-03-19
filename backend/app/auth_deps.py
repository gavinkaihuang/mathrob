from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from .database import get_db, db_retry, engine
from .models import User
from .services.auth_service import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    username = auth_service.decode_token(token)
    if username is None:
        raise credentials_exception
    
    # Wrap DB query with retry logic for transient connection errors
    # This prevents 500 errors on polling endpoints when connections are dropped
    try:
        @db_retry
        def _query_user():
            return db.query(User).filter(User.username == username).first()
        
        user = _query_user()
    except OperationalError:
        # Force pool disposal so next request gets a fresh connection
        engine.dispose()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection temporarily unavailable, please retry",
        )
    
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
