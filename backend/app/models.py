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

class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Start nullable for migration
    image_path = Column(String, nullable=False)
    latex_content = Column(Text, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    difficulty = Column(Integer, nullable=True) # 1-5 scale or similar
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="problems")
    learning_records = relationship("LearningRecord", back_populates="problem")
    solution_attempts = relationship("SolutionAttempt", back_populates="problem")

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
    feedback_json = Column(JSON, nullable=True) # { score: int, logic_gaps: [], calculation_errors: [], suggestions: [] }
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


