from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
import google.generativeai as genai
from typing import List, Dict, Optional
from dotenv import set_key

router = APIRouter()

# Pydantic models for request/response validation
class ModelConfig(BaseModel):
    MODEL_VISION_PRIMARY: Optional[str] = None
    MODEL_TEACHING_PRIMARY: Optional[str] = None
    MODEL_UTILITY_PRIMARY: Optional[str] = None

from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ModelConfig as DBModelConfig
from ..services.model_manager import model_manager
from ..services.token_manager import token_manager
from ..auth_deps import get_current_user
from ..models import User

import time

# Module-level cache for available models to prevent slow page loads
_cached_models = None
_cache_time = 0
CACHE_DURATION = 3600  # 1 hour

@router.get("/settings/models/available")
async def get_available_models(db: Session = Depends(get_db)):
    """
    Fetches the list of available Gemini models using a dynamic DB token.
    Uses an in-memory cache to prevent blocking the frontend on every page load.
    """
    global _cached_models, _cache_time
    
    # Return from cache if valid
    if _cached_models and (time.time() - _cache_time < CACHE_DURATION):
        return {"models": _cached_models}
        
    try:
        api_key = None
        try:
            token_record = token_manager.get_available_token(db)
            api_key = token_record.api_key
        except Exception as msg:
            print(f"Token pool empty or issues accessing DB tokens: {msg}")

        # Fallback to local env if DB token not found
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
            
        if not api_key:
             return {"models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-lite"]} 
        
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.replace("models/", "")
                models.append(name)
        
        if not models:
             models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-3-pro"]
             return {"models": models}

        # Update cache
        _cached_models = models
        _cache_time = time.time()

        return {"models": models}
    except Exception as e:
        print(f"Error fetching models dynamically: {e}")
        # Return cache even if expired if we encounter an error, else fallback list
        if _cached_models:
            return {"models": _cached_models}
        return {"models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-3-pro"]}

@router.get("/settings/models/config", response_model=ModelConfig)
async def get_model_config(db: Session = Depends(get_db)):
    """
    Reads the current model configuration from the database.
    """
    configs = db.query(DBModelConfig).all()
    config_dict = {f"MODEL_{c.role.upper()}_PRIMARY": c.model_name for c in configs}
    
    return ModelConfig(
        MODEL_VISION_PRIMARY=config_dict.get("MODEL_VISION_PRIMARY", ""),
        MODEL_TEACHING_PRIMARY=config_dict.get("MODEL_TEACHING_PRIMARY", ""),
        MODEL_UTILITY_PRIMARY=config_dict.get("MODEL_UTILITY_PRIMARY", "")
    )

@router.post("/settings/models/config")
async def update_model_config(config: ModelConfig, db: Session = Depends(get_db)):
    """
    Updates the model configuration in the database.
    """
    try:
        # Map frontend format back to DB roles
        updates = {
            "vision": config.MODEL_VISION_PRIMARY,
            "teaching": config.MODEL_TEACHING_PRIMARY,
            "utility": config.MODEL_UTILITY_PRIMARY
        }
        
        for role, new_model in updates.items():
            if new_model:
                db_config = db.query(DBModelConfig).filter(DBModelConfig.role == role).first()
                if db_config:
                    db_config.model_name = new_model
                else:
                    db_config = DBModelConfig(role=role, model_name=new_model, description=f"Model for {role}")
                    db.add(db_config)
                    
        db.commit()
        
        # Clear the memory cache so ai_service uses the latest on next run
        model_manager.clear_cache()
                
        return {"message": "Configuration updated successfully", "config": config}
    except Exception as e:
        print(f"Failed to update config in DB: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update configuration")

@router.get("/settings/active-vision-info")
async def get_active_vision_info(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the currently active model and token name for vision tasks.
    """
    try:
        model_name = model_manager.get_model_name(db, 'vision')
        
        try:
            token_record = token_manager.get_available_token(db)
            token_name = token_record.name
        except Exception:
            token_name = "Environment Key" if os.getenv("GEMINI_API_KEY") else "None Available"
            
        return {
            "model": model_name,
            "keyName": token_name
        }
    except Exception as e:
        print(f"Error fetching active vision info: {e}")
        return {"model": "Unknown", "keyName": "Unknown"}

# Token Management CRUD

from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db
from ..models import GeminiToken

class TokenCreate(BaseModel):
    name: str
    api_key: str

class TokenUpdate(BaseModel):
    is_active: Optional[bool] = None
    clear_cooldown: Optional[bool] = False

class TokenResponse(BaseModel):
    id: int
    name: str
    api_key: str
    is_active: bool
    error_count: int
    cooldown_until: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.get("/settings/tokens", response_model=List[TokenResponse])
def get_tokens(db: Session = Depends(get_db)):
    return db.query(GeminiToken).order_by(GeminiToken.id).all()

@router.post("/settings/tokens", response_model=TokenResponse)
def create_token(token: TokenCreate, db: Session = Depends(get_db)):
    existing = db.query(GeminiToken).filter(GeminiToken.name == token.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Token with this name already exists")
    
    new_token = GeminiToken(
        name=token.name,
        api_key=token.api_key
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    return new_token

@router.put("/settings/tokens/{token_id}", response_model=TokenResponse)
def update_token(token_id: int, config: TokenUpdate, db: Session = Depends(get_db)):
    token = db.query(GeminiToken).filter(GeminiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
        
    if config.is_active is not None:
        token.is_active = config.is_active
        
    if config.clear_cooldown:
        token.cooldown_until = None
        token.error_count = 0  # optionally reset error count
        
    db.commit()
    db.refresh(token)
    return token

@router.delete("/settings/tokens/{token_id}")
def delete_token(token_id: int, db: Session = Depends(get_db)):
    token = db.query(GeminiToken).filter(GeminiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
        
    db.delete(token)
    db.commit()
    return {"message": "Token deleted successfully"}
