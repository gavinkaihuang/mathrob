from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum as SAEnum, Float, Date, Boolean, UniqueConstraint
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

class ExamType(enum.Enum):
    """Exam type enumeration for weighted grading logic"""
    CUSTOM = "custom"           # 日常练习 (Routine Practice)
    DIAGNOSTIC = "diagnostic"   # 摸底评测 (Diagnostic Assessment)
    MIDTERM = "midterm"         # 期中评测 (Midterm Exam)
    FINAL = "final"             # 期末评测 (Final Exam)

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

class PracticeSession(Base):
    """Groups a batch of PracticeProblems generated in one request."""
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source_problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)
    ai_model = Column(String, nullable=True)
    problem_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="practice_sessions")
    source_problem = relationship("Problem", backref="practice_sessions")
    problems = relationship("PracticeProblem", back_populates="session")


class PracticeProblem(Base):
    __tablename__ = "practice_problems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source_problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("practice_sessions.id"), nullable=True)
    latex_content = Column(Text, nullable=True)
    difficulty = Column(Integer, nullable=True)
    knowledge_path = Column(String, nullable=True, index=True) 
    ai_model = Column(String, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="practice_problems")
    source_problem = relationship("Problem", back_populates="practice_problems")
    session = relationship("PracticeSession", back_populates="problems")

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
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="learning_records")
    problem = relationship("Problem", back_populates="learning_records")

class DailyReview(Base):
    __tablename__ = "daily_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    review_date = Column(Date, nullable=False, index=True) # The calendar date for this specific review batch
    problem_ids = Column(JSON, nullable=False) # Store the selected problem IDs
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="daily_reviews")


class DailyReviewTask(Base):
    """Daily review task snapshot (generate once per day, read many times)."""
    __tablename__ = "daily_review_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "task_date", name="uq_daily_review_task_user_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_date = Column(Date, nullable=False, index=True)
    problem_ids = Column(JSON, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="daily_review_tasks")

class SolutionAttempt(Base):
    __tablename__ = "solution_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    problem_id = Column(Integer, ForeignKey("problems.id"))
    image_path = Column(String, nullable=False)
    ai_model_used = Column(String(100), nullable=True) # The model that performed this specific grading
    ai_score = Column(Float, nullable=True) # System-given score
    ai_evaluation = Column(JSON, nullable=True) # Detailed correction evaluation (copy of feedback_json or subset)
    formatting_feedback = Column(Text, nullable=True) # Feedback related to writing and format
    feedback_json = Column(JSON, nullable=True) # { score: int, logic_gaps: [], calculation_errors: [], suggestions: [], formatting_feedback: str }
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="solution_attempts")
    problem = relationship("Problem", back_populates="solution_attempts")

class UserKnowledgeMastery(Base):
    __tablename__ = "user_knowledge_mastery"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    knowledge_tag = Column(String, index=True, nullable=False)
    user_self_rating = Column(Float, nullable=True) # 1=Won't, 2=Half, 3=Mastered
    ai_assessed_rating = Column(Float, nullable=True) # AI Objective Score 1-10
    comprehensive_score = Column(Float, nullable=True) # Computed score
    total_weight = Column(Float, default=0.0) # Accumulated weight sum from historical exams
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="knowledge_mastery_records")

    user = relationship("User", backref="knowledge_mastery_records")

class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(50), default="in_progress") # in_progress, paper_generated, completed
    overall_score = Column(Float, nullable=True) # Computed at the end
    report_markdown = Column(Text, nullable=True) # AI generated report
    # Paper exam fields
    paper_snapshot = Column(JSON, nullable=True)  # Full paper questions + answers JSON
    paper_image_paths = Column(JSON, nullable=True)  # List of uploaded answer sheet photo paths
    graded_problems = Column(JSON, nullable=True)  # Per-question grading results from full paper
    formatting_feedback = Column(Text, nullable=True)  # Holistic handwriting/format feedback
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="assessment_sessions")
    problems = relationship("AssessmentProblem", back_populates="session", cascade="all, delete")

class AssessmentProblem(Base):
    __tablename__ = "assessment_problems"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("assessment_sessions.id"), nullable=False, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    image_path = Column(String(255), nullable=True) # User's upload
    ai_score = Column(Float, nullable=True) # Graded score
    ai_feedback = Column(JSON, nullable=True) # Full grading json
    is_submitted = Column(Boolean, default=False)
    
    session = relationship("AssessmentSession", back_populates="problems")
    problem = relationship("Problem")

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

class ExamRecord(Base):
    __tablename__ = "exam_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exam_type = Column(SAEnum(ExamType), default=ExamType.CUSTOM, nullable=False) # custom, diagnostic, midterm, final
    status = Column(String(50), default="processing") # processing, completed, failed
    total_score = Column(Float, nullable=True)
    overall_evaluation = Column(Text, nullable=True)
    # New fields for paper metadata and model used
    paper_name = Column(String(255), nullable=True)
    ai_model = Column(String(100), nullable=True)
    overall_feedback = Column(Text, nullable=True)
    image_paths = Column(JSON, nullable=True) # Paths to uploaded images
    # Persistent accessible URLs for uploaded images (served under /static/...)
    image_urls = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="exam_records")
    results = relationship("ExamProblemResult", back_populates="exam", cascade="all, delete-orphan")

class ExamProblemResult(Base):
    __tablename__ = "exam_problem_results"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exam_records.id"), nullable=False, index=True)
    problem_number = Column(String(50), nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    knowledge_tag = Column(String(100), nullable=False, index=True)
    feedback = Column(Text, nullable=True)
    # Extracted OCR original question and user answer texts for context
    original_question_text = Column(Text, nullable=True)
    user_answer_text = Column(Text, nullable=True)
    
    exam = relationship("ExamRecord", back_populates="results")

class OperationLog(Base):
    """业务运行日志表 - 记录核心业务操作（单题/整卷批阅等）"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action_type = Column(String(100), nullable=False, index=True)  # e.g. "单题智能批阅", "整卷智能批阅"
    status = Column(String(20), nullable=False, default="success")  # success, failed
    details = Column(JSON, nullable=True)  # Flexible payload: model_used, cost_time_ms, exam_type, weight_applied, etc.
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
