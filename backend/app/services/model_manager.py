import logging
from sqlalchemy.orm import Session
from ..models import ModelConfig
from typing import Dict

logger = logging.getLogger(__name__)

class DBModelManager:
    """
    Manages fetching Gemini model configurations from the database.
    (In-memory caching removed to ensure real-time synchronization with DB updates)
    """
    
    def __init__(self):
        pass

    def get_model_name(self, db: Session, role: str) -> str:
        """
        Fetches the model name for the given role directly from the DB.
        """
        config = db.query(ModelConfig).filter(ModelConfig.role == role).first()
        if not config:
            raise ValueError(f"No database configuration found for model role: '{role}'")
            
        return config.model_name

    def clear_cache(self):
        """
        No-op since cache is removed, but kept for compatibility with existing code.
        """
        logger.info("[ModelManager] Cache clear requested, but cache is disabled.")

# Singleton instance
model_manager = DBModelManager()
