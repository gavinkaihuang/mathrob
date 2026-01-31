from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import Problem, KnowledgePoint, LearningRecord
from datetime import datetime

router = APIRouter()

# Pydantic Schemas
class ProblemSchema(BaseModel):
    id: int
    image_path: str
    latex_content: Optional[str] = None
    difficulty: Optional[int] = None
    ai_analysis: Optional[dict] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class KnowledgePointSchema(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    children: List['KnowledgePointSchema'] = []

    class Config:
        orm_mode = True

# Problem Endpoints
@router.get("/problems", response_model=List[ProblemSchema])
def get_problems(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    problems = db.query(Problem).order_by(Problem.created_at.desc()).offset(skip).limit(limit).all()
    return problems

@router.get("/problems/{problem_id}", response_model=ProblemSchema)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem

# Knowledge Points Endpoints
@router.get("/knowledge-points", response_model=List[KnowledgePointSchema])
def get_knowledge_tree(db: Session = Depends(get_db)):
    # Simple tree retrieval - fetch root nodes (parent_id is NULL)
    # Recursion handled by Pydantic model response structure if relationships are set up correctly
    # Note: For deep trees, this might need optimization (CTE or eager loading)
    roots = db.query(KnowledgePoint).filter(KnowledgePoint.parent_id == None).all()
    return roots

@router.get("/daily-review", response_model=List[ProblemSchema])
def get_daily_review_problems(db: Session = Depends(get_db)):
    # Mock logic: Review problems that are wrong or pending
    # In real logic, update based on Ebbinghaus curve (review_date <= today)
    records = db.query(LearningRecord).filter(LearningRecord.status != 'correct').all()
    ids = [r.problem_id for r in records]
    problems = db.query(Problem).filter(Problem.id.in_(ids)).all()
    return problems
