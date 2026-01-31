from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from pydantic import BaseModel
from ..database import get_db
from ..models import Problem, KnowledgePoint, LearningRecord
from datetime import datetime
from ..services.ai_service import AIService

router = APIRouter()
ai_service = AIService()

class ProblemSchema(BaseModel):
    id: int
    image_path: str
    latex_content: Optional[str] = None
    difficulty: Optional[int] = None
    ai_analysis: Optional[Union[dict, str]] = None
    created_at: datetime
    current_mastery_level: Optional[int] = None
    
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
def get_problems(
    skip: int = 0, 
    limit: int = 20, 
    mastery: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # Query problems with their learning records
    # We use outerjoin because we want problems even if they don't have records (unless filtering)
    query = db.query(Problem, LearningRecord).outerjoin(
        LearningRecord, Problem.id == LearningRecord.problem_id
    )
    
    if mastery is not None:
        query = query.filter(LearningRecord.mastery_level == mastery)
        
    # Sort by creation date
    results = query.order_by(Problem.created_at.desc()).offset(skip).limit(limit).all()
    
    problems = []
    for problem, record in results:
        # Populate transient attribute for Pydantic
        if record:
            problem.current_mastery_level = record.mastery_level
        else:
            problem.current_mastery_level = None
        problems.append(problem)
        
    return problems

@router.get("/problems/{problem_id}", response_model=ProblemSchema)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Fetch learning record to get mastery level
    record = db.query(LearningRecord).filter(LearningRecord.problem_id == problem_id).first()
    if record:
        problem.current_mastery_level = record.mastery_level
        
    return problem

# Knowledge Points Endpoints
@router.get("/knowledge-points", response_model=List[KnowledgePointSchema])
def get_knowledge_tree(db: Session = Depends(get_db)):
    # Simple tree retrieval - fetch root nodes (parent_id is NULL)
    # Recursion handled by Pydantic model response structure if relationships are set up correctly
    # Note: For deep trees, this might need optimization (CTE or eager loading)
    roots = db.query(KnowledgePoint).filter(KnowledgePoint.parent_id == None).all()
    return roots

class MasteryRequest(BaseModel):
    level: int # 1, 2, 3

@router.post("/problems/{problem_id}/mastery")
def update_mastery(problem_id: int, request: MasteryRequest, db: Session = Depends(get_db)):
    # Check if problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Find or create learning record
    record = db.query(LearningRecord).filter(LearningRecord.problem_id == problem_id).first()
    if not record:
        record = LearningRecord(problem_id=problem_id)
        db.add(record)
    
    record.mastery_level = request.level
    record.created_at = datetime.utcnow() # Update timestamp implies activity
    
    # Update status based on level
    if request.level == 3:
        record.status = "correct"
    else:
        record.status = "wrong" # or pending, treating anything < 3 as needing review
        
    db.commit()
    return {"message": "Mastery updated", "level": request.level, "status": record.status}

@router.get("/daily-review", response_model=List[ProblemSchema])
def get_daily_review_problems(db: Session = Depends(get_db)):
    # Mock logic: Review problems that are wrong or pending
    # In real logic, update based on Ebbinghaus curve (review_date <= today)
    records = db.query(LearningRecord).filter(LearningRecord.status != 'correct').all()
    ids = [r.problem_id for r in records]
    problems = db.query(Problem).filter(Problem.id.in_(ids)).all()
    return problems

@router.post("/problems/{problem_id}/similar")
async def generate_similar_practice(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Extract info
    latex = problem.latex_content or "N/A"
    
    # Handle knowledge points safely
    kps = []
    if problem.ai_analysis:
        # Check if dict or str (since we support Union now)
        if isinstance(problem.ai_analysis, dict):
             kps = problem.ai_analysis.get("knowledge_points", [])
        # If str, we ignore or try to parse, but let's just ignore for safety/speed
    
    # Call AI
    similar_problems = await ai_service.generate_similar_problems(latex, kps)
    
    return similar_problems
