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

@router.get("/settings/models/available")
async def get_available_models():
    """
    Fetches the list of available Gemini models.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             return {"models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-lite"]} # Fallback list if no key
        
        genai.configure(api_key=api_key)
        # Typically we only want text/generation models for these tasks
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # remove "models/" prefix from the name returned by API usually
                name = m.name.replace("models/", "")
                models.append(name)
        
        # If API fails to return or returns empty, provide fallbacks
        if not models:
             models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-3-pro"]

        return {"models": models}
    except Exception as e:
        print(f"Error fetching models: {e}")
        # Return a default list if internet is down or API key is invalid
        return {"models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-3-pro"]}

from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ModelConfig as DBModelConfig
from ..services.model_manager import model_manager

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
        orm_mode = True

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
