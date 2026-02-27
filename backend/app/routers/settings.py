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
    MODEL_VISION_FALLBACK: Optional[str] = None
    MODEL_TEACHING_PRIMARY: Optional[str] = None
    MODEL_TEACHING_FALLBACK: Optional[str] = None
    MODEL_UTILITY_PRIMARY: Optional[str] = None
    MODEL_UTILITY_FALLBACK: Optional[str] = None

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

@router.get("/settings/models/config", response_model=ModelConfig)
async def get_model_config():
    """
    Reads the current model configuration from environment variables.
    """
    return ModelConfig(
        MODEL_VISION_PRIMARY=os.getenv("MODEL_VISION_PRIMARY", ""),
        MODEL_VISION_FALLBACK=os.getenv("MODEL_VISION_FALLBACK", ""),
        MODEL_TEACHING_PRIMARY=os.getenv("MODEL_TEACHING_PRIMARY", ""),
        MODEL_TEACHING_FALLBACK=os.getenv("MODEL_TEACHING_FALLBACK", ""),
        MODEL_UTILITY_PRIMARY=os.getenv("MODEL_UTILITY_PRIMARY", ""),
        MODEL_UTILITY_FALLBACK=os.getenv("MODEL_UTILITY_FALLBACK", "")
    )

@router.post("/settings/models/config")
async def update_model_config(config: ModelConfig):
    """
    Updates the model configuration in the .env file and current environment.
    """
    try:
        # Calculate path to .env file
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_file = os.path.join(base_dir, ".env")

        # Create .env if it doesn't exist
        if not os.path.exists(env_file):
            with open(env_file, 'w') as f:
                pass

        updates = config.dict(exclude_unset=True)
        
        for key, value in updates.items():
            if value is not None:
                # Update current running environment
                os.environ[key] = value
                # Persist to .env file
                set_key(env_file, key, value)
                
        return {"message": "Configuration updated successfully", "config": config}
    except Exception as e:
        print(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration")
