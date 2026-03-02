import logging
from sqlalchemy.orm import Session
from ..models import ModelConfig
from typing import Dict

logger = logging.getLogger(__name__)

class DBModelManager:
    """
    Manages fetching and caching Gemini model configurations from the database.
    """
    
    def __init__(self):
        # Format: {role_name: model_name} (e.g. {'vision': 'gemini-2.0-flash'})
        self._cache: Dict[str, str] = {}

    def get_model_name(self, db: Session, role: str) -> str:
        """
        Fetches the model name for the given role from cache, or DB if not in cache.
        """
        if role in self._cache:
            return self._cache[role]
            
        return self._fetch_and_cache(db, role)

    def _fetch_and_cache(self, db: Session, role: str) -> str:
        """
        Force fetches the model config from the database and updates cache.
        """
        config = db.query(ModelConfig).filter(ModelConfig.role == role).first()
        if not config:
            raise ValueError(f"No database configuration found for model role: '{role}'")
            
        model_name = config.model_name
        self._cache[role] = model_name
        return model_name

    def clear_cache(self):
        """
        Clears the current cache to force standard DB fetching on the next request.
        """
        self._cache.clear()
        logger.info("[ModelManager] Cache successfully cleared.")

# Singleton instance
model_manager = DBModelManager()
