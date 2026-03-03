from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum as SAEnum, Float, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class DifficultyLevel(enum.Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3

class ProblemStatus(enum.Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    PENDING = "pending"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    name = Column(String, index=True, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    path = Column(String, nullable=False, index=True) # ltree is stored as string in SQLAlchemy usually unless using geoalchemy/specific extensions

class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Start nullable for migration
    image_path = Column(String, nullable=False)
    latex_content = Column(Text, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    difficulty = Column(Integer, nullable=True) # 1-5 scale or similar
    knowledge_path = Column(String, nullable=True, index=True) 
    ai_model = Column(String, nullable=True) # Successfully used AI model name
    source_problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True) # For generated variations
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="problems")
    learning_records = relationship("LearningRecord", back_populates="problem")
    solution_attempts = relationship("SolutionAttempt", back_populates="problem")
    practice_problems = relationship("PracticeProblem", back_populates="source_problem")

class PracticeProblem(Base):
    __tablename__ = "practice_problems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source_problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)
    latex_content = Column(Text, nullable=True)
    difficulty = Column(Integer, nullable=True)
    knowledge_path = Column(String, nullable=True, index=True) 
    ai_model = Column(String, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="practice_problems")
    source_problem = relationship("Problem", back_populates="practice_problems")

class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    parent_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=True)
    
    children = relationship("KnowledgePoint", remote_side=[id])

class LearningRecord(Base):
    __tablename__ = "learning_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    problem_id = Column(Integer, ForeignKey("problems.id"))
    status = Column(String, default="pending") # correct, wrong
    mastery_level = Column(Integer, nullable=True) # 1: Won't, 2: Half, 3: Mastered
    
    # SM-2 Fields
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=0) # Interval in days
    repetitions = Column(Integer, default=0)
    
    review_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="learning_records")
    problem = relationship("Problem", back_populates="learning_records")

class SolutionAttempt(Base):
    __tablename__ = "solution_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    problem_id = Column(Integer, ForeignKey("problems.id"))
    image_path = Column(String, nullable=False)
    ai_model_used = Column(String(100), nullable=True) # The model that performed this specific grading
    ai_score = Column(Float, nullable=True) # System-given score
    ai_evaluation = Column(JSON, nullable=True) # Detailed correction evaluation (copy of feedback_json or subset)
    feedback_json = Column(JSON, nullable=True) # { score: int, logic_gaps: [], calculation_errors: [], suggestions: [], formatting_feedback: str }
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="solution_attempts")
    problem = relationship("Problem", back_populates="solution_attempts")

class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    week_start = Column(Date, nullable=False) # The Monday of the week
    pdf_path = Column(String, nullable=False)
    summary_json = Column(JSON, nullable=True) # Snapshot of stats
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="weekly_reports")

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), default="ERROR")
    category = Column(String(50), nullable=True) # e.g. vision, teaching, utility
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)  # Store robust error tracebacks or input states
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    knowledge_path = Column(String, index=True, nullable=False) # Maps to ltree
    is_learned = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="progress_records")

class GeminiToken(Base):
    __tablename__ = "gemini_tokens"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    api_key = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    error_count = Column(Integer, default=0)
    cooldown_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), unique=True, nullable=False, index=True) # e.g. vision, teaching, utility
    model_name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class APICallLog(Base):
    __tablename__ = "api_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False) # e.g. vision, teaching, utility
    action_type = Column(String(50), nullable=False) # e.g. PARSE_PROBLEM, GRADE_SOLUTION
    target_id = Column(Integer, nullable=True) # e.g. problem_id
    model_used = Column(String(100), nullable=False)
    token_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
