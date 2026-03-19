import logging
from sqlalchemy.orm import Session
from ..models import ModelConfig, ExamType
from typing import Dict

logger = logging.getLogger(__name__)

class DBModelManager:
    """
    Manages fetching Gemini model configurations from the database.
    Supports dynamic model selection based on exam type.
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

    def get_teaching_model_for_exam_type(self, db: Session, exam_type: ExamType) -> str:
        """
        Returns the appropriate teaching model based on exam type.
        
        Logic:
        - exam_type == 'custom': Use MODEL_ROUTINE_TEACHING_PRIMARY (recommend Flash)
        - exam_type in ['diagnostic', 'midterm', 'final']: Use MODEL_ADVANCED_ASSESSMENT_PRIMARY (recommend Pro)
        
        Args:
            db: SQLAlchemy session
            exam_type: ExamType enum value
            
        Returns:
            Model name string
            
        Raises:
            ValueError: If model configuration not found for the exam type
        """
        if exam_type == ExamType.CUSTOM:
            role = "routine_teaching"
        elif exam_type in [ExamType.DIAGNOSTIC, ExamType.MIDTERM, ExamType.FINAL]:
            role = "advanced_assessment"
        else:
            raise ValueError(f"Unknown exam type: {exam_type}")
        
        config = db.query(ModelConfig).filter(ModelConfig.role == role).first()
        if not config:
            raise ValueError(f"No database configuration found for model role: '{role}' (exam_type: {exam_type})")
        
        logger.info(f"[ModelManager] Selected {role} model for exam_type: {exam_type.value}")
        return config.model_name

    def clear_cache(self):
        """
        No-op since cache is removed, but kept for compatibility with existing code.
        """
        logger.info("[ModelManager] Cache clear requested, but cache is disabled.")

# Singleton instance
model_manager = DBModelManager()
