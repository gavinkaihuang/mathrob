from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from pydantic import BaseModel
from ..database import get_db
from ..models import Problem, KnowledgePoint, KnowledgeNode, LearningRecord, SolutionAttempt, User, PracticeProblem, PracticeSession, UserProgress, APICallLog, SystemLog, DailyReview
import os
import json
from datetime import datetime
from ..services.ai_service import AIService, AIServiceException
from ..auth_deps import get_current_user

UPLOAD_DIR = "backend/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(dependencies=[Depends(get_current_user)])
ai_service = AIService()

class SolutionAttemptSchema(BaseModel):
    id: int
    image_path: str
    ai_model_used: Optional[str] = None
    ai_score: Optional[float] = None
    ai_evaluation: Optional[Union[dict, str]] = None
    formatting_feedback: Optional[str] = None
    feedback_json: Optional[Union[dict, str]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class APICallLogSchema(BaseModel):
    id: int
    category: str
    action_type: str
    target_id: Optional[int] = None
    model_used: str
    token_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ProblemSchema(BaseModel):
    id: int
    image_path: str
    latex_content: Optional[str] = None
    difficulty: Optional[int] = None
    ai_analysis: Optional[Union[dict, str]] = None
    created_at: datetime
    current_mastery_level: Optional[int] = None
    ai_model: Optional[str] = None
    solution_attempts: List[SolutionAttemptSchema] = []
    
    class Config:
        from_attributes = True

class KnowledgePointSchema(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    children: List['KnowledgePointSchema'] = []

    class Config:
        from_attributes = True

# Problem Endpoints
@router.get("/problems", response_model=List[ProblemSchema])
def get_problems(
    skip: int = 0, 
    limit: int = 20, 
    mastery: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Query problems with their learning records
    # We use outerjoin because we want problems even if they don't have records (unless filtering)
    query = db.query(Problem, LearningRecord).outerjoin(
        LearningRecord, 
        (Problem.id == LearningRecord.problem_id) & (LearningRecord.user_id == current_user.id)
    ).filter(Problem.user_id == current_user.id)
    
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
def get_problem(problem_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Fetch learning record to get mastery level
    record = db.query(LearningRecord).filter(
        LearningRecord.problem_id == problem_id,
        LearningRecord.user_id == current_user.id
    ).first()
    if record:
        problem.current_mastery_level = record.mastery_level
        
    return problem

# Knowledge Nodes Endpoints (Using ltree paths)
from ..models import KnowledgeNode

class KnowledgeNodeSchema(BaseModel):
    id: int
    name: str
    path: str
    
    class Config:
        from_attributes = True

@router.get("/knowledge-nodes", response_model=List[KnowledgeNodeSchema])
def get_knowledge_nodes(db: Session = Depends(get_db)):
    return db.query(KnowledgeNode).order_by(KnowledgeNode.path).all()


class MasteryRequest(BaseModel):
    level: int # 1, 2, 3

@router.post("/problems/{problem_id}/mastery")
def update_mastery(problem_id: int, request: MasteryRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Find or create learning record
    record = db.query(LearningRecord).filter(
        LearningRecord.problem_id == problem_id,
        LearningRecord.user_id == current_user.id
    ).first()
    if not record:
        record = LearningRecord(problem_id=problem_id, user_id=current_user.id)
        db.add(record)
    
    # SM-2 Algorithm Implementation
    # Mapping:
    # Level 1 (Red) -> Quality 1 (Reset)
    # Level 2 (Yellow) -> Quality 3 (Hard)
    # Level 3 (Green) -> Quality 5 (Easy)
    
    quality = 0
    if request.level == 1:
        quality = 1
    elif request.level == 2:
        quality = 3
    elif request.level == 3:
        quality = 5
        
    # Retrieve current values
    ef = record.ease_factor or 2.5
    reps = record.repetitions or 0
    interval = record.interval or 0
    
    if quality < 3:
        # Failed/Reset
        reps = 0
        interval = 1
    else:
        # Passed
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = int(interval * ef)
        
        reps += 1
        
        # Update EF
        ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if ef < 1.3:
            ef = 1.3
            
    # Update record
    record.ease_factor = round(ef, 2)
    record.repetitions = reps
    record.interval = interval
    record.mastery_level = request.level
    
    # Set next review date
    from datetime import timedelta
    record.review_date = datetime.utcnow() + timedelta(days=interval)
    record.last_reviewed_at = datetime.utcnow()
    record.created_at = datetime.utcnow() # Last activity time
    
    # Update legacy status field for compatibility
    if request.level == 3:
        record.status = "correct"
    else:
        record.status = "wrong"
        
    # Sync UserKnowledgeMastery
    from ..models import UserKnowledgeMastery, KnowledgeNode
    if problem.knowledge_path and problem.knowledge_path != "unknown":
        node = db.query(KnowledgeNode).filter(KnowledgeNode.path == problem.knowledge_path).first()
        tag = node.name if node else problem.knowledge_path
        
        ukm = db.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.user_id == current_user.id,
            UserKnowledgeMastery.knowledge_tag == tag
        ).first()
        
        if not ukm:
            ukm = UserKnowledgeMastery(
                user_id=current_user.id,
                knowledge_tag=tag,
                user_self_rating=float(request.level)
            )
            db.add(ukm)
        else:
            old_rating = ukm.user_self_rating or float(request.level)
            ukm.user_self_rating = 0.5 * float(request.level) + 0.5 * old_rating
            
        # recalculate
        norm_self = (ukm.user_self_rating / 3.0) * 10.0
        if ukm.ai_assessed_rating:
            ukm.comprehensive_score = 0.6 * ukm.ai_assessed_rating + 0.4 * norm_self
        else:
            ukm.comprehensive_score = norm_self

    db.commit()
    
    return {
        "message": "Mastery updated", 
        "level": request.level, 
        "next_review": record.review_date,
        "days_until_next": interval
    }

@router.get("/daily-review", response_model=List[ProblemSchema])
def get_daily_review_problems(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get problems due for review today based on SM-2.
    """
    now = datetime.utcnow()
    # Find records where review_date <= now OR (status != 'correct' AND review_date IS NULL)
    # This covers:
    # 1. Scheduled reviews that are due
    # 2. Problems marked wrong/pending that haven't been scheduled yet (treat as due immediately)
    
    from sqlalchemy import or_
    
    records = db.query(LearningRecord).filter(
        LearningRecord.user_id == current_user.id,
        or_(
            LearningRecord.review_date <= now,
            ((LearningRecord.status != 'correct') & (LearningRecord.review_date == None))
        )
    ).all()
    
    ids = [r.problem_id for r in records]
    problems = db.query(Problem).filter(Problem.id.in_(ids)).all()
    
    # Populate mastery for display
    for p in problems:
        # Find corresponding record (inefficient but simple for small scale)
        rec = next((r for r in records if r.problem_id == p.id), None)
        if rec:
            p.current_mastery_level = rec.mastery_level
            
    return problems

@router.post("/problems/{problem_id}/review")
async def review_problem(
    problem_id: int, 
    score: int, # 0, 1, 2
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    from ..services.srs_logic import calculate_next_review
    from ..models import LearningRecord
    
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Find or create learning record
    record = db.query(LearningRecord).filter(
        LearningRecord.problem_id == problem_id,
        LearningRecord.user_id == current_user.id
    ).first()
    
    if not record:
        record = LearningRecord(
            user_id=current_user.id,
            problem_id=problem_id,
            ease_factor=2.5,
            interval=0,
            repetitions=0
        )
        db.add(record)
    
    # Calculate new stats
    new_ef, new_interval, new_reps, next_date = calculate_next_review(
        record.ease_factor,
        record.interval,
        record.repetitions,
        score
    )
    
    # Update record
    record.ease_factor = new_ef
    record.interval = new_interval
    record.repetitions = new_reps
    record.review_date = next_date
    record.last_reviewed_at = datetime.utcnow()
    record.mastery_level = score # Sync with UI selection
    record.status = "correct" if score == 2 else "wrong" # Basic status sync
    
    # Map score (0,1,2) to level (1,2,3)
    user_self_rating = score + 1
    
    # Sync UserKnowledgeMastery
    from ..models import UserKnowledgeMastery, KnowledgeNode
    if problem.knowledge_path and problem.knowledge_path != "unknown":
        node = db.query(KnowledgeNode).filter(KnowledgeNode.path == problem.knowledge_path).first()
        tag = node.name if node else problem.knowledge_path
        
        ukm = db.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.user_id == current_user.id,
            UserKnowledgeMastery.knowledge_tag == tag
        ).first()
        
        if not ukm:
            ukm = UserKnowledgeMastery(
                user_id=current_user.id,
                knowledge_tag=tag,
                user_self_rating=float(user_self_rating)
            )
            db.add(ukm)
        else:
            old_rating = ukm.user_self_rating or float(user_self_rating)
            ukm.user_self_rating = 0.5 * float(user_self_rating) + 0.5 * old_rating
            
        # recalculate
        norm_self = (ukm.user_self_rating / 3.0) * 10.0
        if ukm.ai_assessed_rating:
            ukm.comprehensive_score = 0.6 * ukm.ai_assessed_rating + 0.4 * norm_self
        else:
            ukm.comprehensive_score = norm_self

    db.commit()
    db.refresh(record)
    
    return {
        "message": "Review recorded",
        "next_review_date": record.review_date.isoformat(),
        "interval": record.interval
    }

@router.post("/problems/{problem_id}/reanalyze")
async def reanalyze_problem(problem_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ..models import KnowledgeNode
    
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
        
    # Re-run AI analysis
    try:
        analysis_result = await ai_service.analyze_image(problem.image_path)
    except Exception as e:
        print(f"Re-analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI Analysis failed: {str(e)}")

    # Extract and Validate Knowledge Path
    kp_path = analysis_result.get("knowledge_path")
    if kp_path:
        exists = db.query(KnowledgeNode).filter(KnowledgeNode.path == kp_path).first()
        if not exists:
            print(f"Warning: AI returned non-existent knowledge path during re-analysis: {kp_path}")
    
    # Update Problem record
    ai_data = analysis_result.get("ai_analysis", {})
    if "knowledge_points" in analysis_result:
        ai_data["knowledge_points"] = analysis_result["knowledge_points"]

    problem.latex_content = analysis_result.get("latex_content")
    problem.ai_analysis = ai_data
    problem.difficulty = analysis_result.get("difficulty", 1)
    problem.knowledge_path = kp_path
    problem.ai_model = analysis_result.get("ai_model")
    
    db.commit()
    db.refresh(problem)
    
    return {"message": "Problem re-analyzed successfully", "id": problem.id, "knowledge_path": kp_path}

@router.post("/problems/{problem_id}/similar")
async def generate_similar_practice(problem_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ..models import KnowledgeNode
    
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Extract rich context
    latex = problem.latex_content or "N/A"
    difficulty = problem.difficulty or 1
    
    # Get knowledge node name for better AI context
    knowledge_path_name = "相关知识点"
    if problem.knowledge_path:
        root_path = problem.knowledge_path.split('.')[0] + '.' + problem.knowledge_path.split('.')[1] if len(problem.knowledge_path.split('.')) > 1 else problem.knowledge_path
        node = db.query(KnowledgeNode).filter(KnowledgeNode.path == problem.knowledge_path).first()
        if node:
            knowledge_path_name = node.name

    # Handle knowledge points safely from JSON
    kps = []
    if problem.ai_analysis and isinstance(problem.ai_analysis, dict):
        kps = problem.ai_analysis.get("knowledge_points", [])
    
    try:
        # Call AI with rich context
        result = await ai_service.generate_similar_problems(
            original_latex=latex, 
            knowledge_points=kps, 
            difficulty=difficulty,
            knowledge_path_name=knowledge_path_name,
            target_id=problem.id
        )
    except AIServiceException as e:
        status_code = 429 if e.error_type == "rate_limit" else 401 if e.error_type == "auth_error" else 503
        raise HTTPException(
            status_code=status_code, 
            detail={"message": e.args[0], "error_type": e.error_type, "retry_seconds": e.retry_seconds}
        )
    
    # Extract problems from result
    similar_problems = result.get("problems", [])
    
    # Create a PracticeSession to group this batch
    session = PracticeSession(
        user_id=current_user.id,
        source_problem_id=problem.id,
        ai_model=result.get("ai_model", "Utility Model"),
        problem_count=len(similar_problems)
    )
    db.add(session)
    db.flush()  # Get session.id before committing

    saved_problems = []
    for sp in similar_problems:
        new_prob = PracticeProblem(
            user_id=current_user.id,
            latex_content=sp.get("latex", ""),
            difficulty=difficulty,
            knowledge_path=problem.knowledge_path,
            ai_model=result.get("ai_model", "Utility Model"),
            source_problem_id=problem.id,
            session_id=session.id,
            ai_analysis={
                "topic": ["Generated Practice"],
                "solution": sp.get("solution", ""),
                "thinking_process": sp.get("thinking_process", ""),
                "answer": sp.get("answer", ""),
                "knowledge_points": kps
            }
        )
        db.add(new_prob)
        saved_problems.append(new_prob)
        
    db.commit()
    db.refresh(session)
    for sp in saved_problems:
        db.refresh(sp)
        
    # We return the schemas so frontend receives the newly generated DB IDs.
    return saved_problems

@router.get("/problems/{problem_id}/similar")
def get_similar_practice(problem_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetches previously generated practice problems linked to a specific source problem."""
    practice_problems = db.query(PracticeProblem).filter(
        PracticeProblem.source_problem_id == problem_id,
        PracticeProblem.user_id == current_user.id
    ).order_by(PracticeProblem.created_at.asc()).all()
    return practice_problems


# --- Practice History ---

class PracticeSessionSchema(BaseModel):
    id: int
    source_problem_id: Optional[int] = None
    ai_model: Optional[str] = None
    problem_count: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/practices/history", response_model=List[PracticeSessionSchema])
def get_practice_history(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a paginated list of past PracticeSession records for the current user,
    ordered by most recent first.
    """
    sessions = db.query(PracticeSession).filter(
        PracticeSession.user_id == current_user.id
    ).order_by(PracticeSession.created_at.desc()).offset(skip).limit(limit).all()
    return sessions


@router.get("/practices/sessions/{session_id}")
def get_practice_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the PracticeProblems belonging to a specific session.
    """
    session = db.query(PracticeSession).filter(
        PracticeSession.id == session_id,
        PracticeSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    problems = db.query(PracticeProblem).filter(
        PracticeProblem.session_id == session_id
    ).order_by(PracticeProblem.created_at.asc()).all()
    
    return {
        "session": {
            "id": session.id,
            "source_problem_id": session.source_problem_id,
            "ai_model": session.ai_model,
            "problem_count": session.problem_count,
            "created_at": session.created_at
        },
        "problems": problems
    }

@router.post("/practice-problems/{problem_id}/submit_solution")
async def submit_practice_solution(
    problem_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    practice = db.query(PracticeProblem).filter(
        PracticeProblem.id == problem_id, 
        PracticeProblem.user_id == current_user.id
    ).first()
    
    if not practice:
        raise HTTPException(status_code=404, detail="Practice problem not found")
        
    # Save file
    safe_filename = f"practice_{problem_id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_location, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    # Extract AI reference answer
    problem_latex = practice.latex_content or "N/A"
    standard_solution = "N/A"
    
    if practice.ai_analysis:
        if isinstance(practice.ai_analysis, dict):
            # The structure we injected during generation
            standard_solution = practice.ai_analysis.get("solution", "N/A")
            answer = practice.ai_analysis.get("answer")
            if answer:
                standard_solution += f"\n\nFinal Answer: {answer}"
        elif isinstance(practice.ai_analysis, str):
            standard_solution = practice.ai_analysis
            
    # Call AI Teaching Model to analyze the handwritten solution vs reference
    try:
        feedback_data = await ai_service.analyze_solution(problem_latex, standard_solution, file_location, target_id=problem_id)
        feedback = feedback_data["feedback_json"]
    except AIServiceException as e:
        status_code = 429 if e.error_type == "rate_limit" else 401 if e.error_type == "auth_error" else 503
        raise HTTPException(
            status_code=status_code, 
            detail={"message": e.args[0], "error_type": e.error_type, "retry_seconds": e.retry_seconds}
        )
    except Exception as e:
        print(f"AI Practice Analysis failed: {e}")
        feedback = {"score": 0, "error": str(e)}
        
    # Return directly, no need to clutter DB with solution attempts for practice
    return {"feedback_json": feedback}

@router.post("/problems/{problem_id}/submit_solution", response_model=SolutionAttemptSchema)
async def submit_solution(
    problem_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
        
    # Save file
    safe_filename = f"solution_{problem_id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_location, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    # Prepare context for AI
    problem_latex = problem.latex_content or "N/A"
    standard_solution = "N/A"
    
    # Try to extract standard solution from ai_analysis
    if problem.ai_analysis:
        if isinstance(problem.ai_analysis, dict):
            standard_solution = problem.ai_analysis.get("solution", "N/A")
        elif isinstance(problem.ai_analysis, str):
            # Fallback if string, maybe just pass the whole string
            standard_solution = problem.ai_analysis
            
    # Call AI
    try:
        ai_response = await ai_service.analyze_solution(problem_latex, standard_solution, file_location, target_id=problem_id)
        feedback = ai_response["feedback_json"]
        used_model = ai_response["ai_model"]
    except AIServiceException as e:
        status_code = 429 if e.error_type == "rate_limit" else 401 if e.error_type == "auth_error" else 503
        raise HTTPException(
            status_code=status_code, 
            detail={"message": e.args[0], "error_type": e.error_type, "retry_seconds": e.retry_seconds}
        )
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        feedback = {"score": 0, "error": str(e)}
        used_model = "error"
        
    # Save Attempt
    attempt = SolutionAttempt(
        problem_id=problem_id,
        user_id=current_user.id,
        image_path=safe_filename,
        ai_model_used=used_model,
        ai_score=feedback.get("score") if isinstance(feedback, dict) else None,
        ai_evaluation=feedback,
        feedback_json=feedback
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    
    return attempt

@router.post("/api/reviews/{session_id}/problems/{problem_id}/submit_homework", response_model=SolutionAttemptSchema)
async def submit_homework(
    session_id: int,
    problem_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import UserKnowledgeMastery
    
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
        
    # Save file
    safe_filename = f"homework_{problem_id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_location, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    # Prepare context for AI
    problem_latex = problem.latex_content or "N/A"
    standard_solution = "N/A"
    
    if problem.ai_analysis:
        if isinstance(problem.ai_analysis, dict):
            standard_solution = problem.ai_analysis.get("solution", "N/A")
        elif isinstance(problem.ai_analysis, str):
            standard_solution = problem.ai_analysis
            
    # Call AI
    try:
        ai_response = await ai_service.analyze_solution(problem_latex, standard_solution, file_location, target_id=problem_id)
        feedback = ai_response["feedback_json"]
        used_model = ai_response["ai_model"]
    except AIServiceException as e:
        status_code = 429 if e.error_type == "rate_limit" else 401 if e.error_type == "auth_error" else 503
        raise HTTPException(
            status_code=status_code, 
            detail={"message": e.args[0], "error_type": e.error_type, "retry_seconds": e.retry_seconds}
        )
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        feedback = {"score": 0, "error": str(e)}
        used_model = "error"
        
    # Save Attempt
    attempt = SolutionAttempt(
        problem_id=problem_id,
        user_id=current_user.id,
        image_path=safe_filename,
        ai_model_used=used_model,
        ai_score=feedback.get("score") if isinstance(feedback, dict) else None,
        ai_evaluation=feedback,
        formatting_feedback=feedback.get("formatting_feedback") if isinstance(feedback, dict) else None,
        feedback_json=feedback
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    
    # Process knowledge mastery if exist
    if isinstance(feedback, dict) and "knowledge_analysis" in feedback:
        analyses = feedback.get("knowledge_analysis", [])
        for ki in analyses:
            tag = ki.get("tag")
            score = ki.get("score") # 1-10
            if tag and score is not None:
                record = db.query(UserKnowledgeMastery).filter(
                    UserKnowledgeMastery.user_id == current_user.id,
                    UserKnowledgeMastery.knowledge_tag == tag
                ).first()
                if not record:
                    record = UserKnowledgeMastery(
                        user_id=current_user.id,
                        knowledge_tag=tag,
                        ai_assessed_rating=float(score)
                    )
                    db.add(record)
                else:
                    # Rolling average for ai_assessed_rating, or just overwrite?
                    # I'll use a weighted average favoring newer: new = 0.7 * new + 0.3 * old
                    old_score = record.ai_assessed_rating or float(score)
                    record.ai_assessed_rating = 0.7 * float(score) + 0.3 * old_score
                
                # Update comprehensive score
                user_self = record.user_self_rating # 1-3
                if user_self:
                    # Map 1-3 to 1-10 scale: 1 -> 3.33, 2 -> 6.66, 3 -> 10 
                    normalized_self = (user_self / 3.0) * 10.0
                    ai_rating = record.ai_assessed_rating
                    record.comprehensive_score = 0.6 * ai_rating + 0.4 * normalized_self
                else:
                    record.comprehensive_score = record.ai_assessed_rating
                    
        db.commit()
    
    return attempt



@router.delete("/solution-attempts/{attempt_id}")
async def delete_solution_attempt(attempt_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attempt = db.query(SolutionAttempt).filter(SolutionAttempt.id == attempt_id, SolutionAttempt.user_id == current_user.id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Solution attempt not found")
    
    # Optional: Delete file from disk
    try:
        if attempt.image_path:
            # Check if it's a relative path from UPLOAD_DIR
            file_path = os.path.join(UPLOAD_DIR, attempt.image_path)
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"Failed to delete file: {e}")

    db.delete(attempt)
    db.commit()
    return {"message": "Solution attempt deleted"}


@router.post("/solution-attempts/{attempt_id}/reanalyze", response_model=SolutionAttemptSchema)
async def reanalyze_solution_attempt(attempt_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attempt = db.query(SolutionAttempt).filter(SolutionAttempt.id == attempt_id, SolutionAttempt.user_id == current_user.id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Solution attempt not found")
    
    problem = attempt.problem
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    file_location = os.path.join(UPLOAD_DIR, attempt.image_path)
    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="Original image file not found on server")

    # Prepare context for AI
    problem_latex = problem.latex_content or "N/A"
    standard_solution = "N/A"
    
    if problem.ai_analysis:
        if isinstance(problem.ai_analysis, dict):
            standard_solution = problem.ai_analysis.get("solution", "N/A")
        elif isinstance(problem.ai_analysis, str):
            standard_solution = problem.ai_analysis

    # Call AI
    try:
        ai_response = await ai_service.analyze_solution(problem_latex, standard_solution, file_location, target_id=problem.id)
        feedback = ai_response["feedback_json"]
        used_model = ai_response["ai_model"]
    except AIServiceException as e:
        status_code = 429 if e.error_type == "rate_limit" else 401 if e.error_type == "auth_error" else 503
        raise HTTPException(
            status_code=status_code, 
            detail={"message": e.args[0], "error_type": e.error_type, "retry_seconds": e.retry_seconds}
        )
    except Exception as e:
        print(f"AI Re-analysis failed: {e}")
        feedback = {"score": 0, "error": str(e)}
        used_model = "error"

    # Update Attempt
    attempt.feedback_json = feedback
    attempt.ai_model_used = used_model
    attempt.ai_score = feedback.get("score") if isinstance(feedback, dict) else None
    attempt.ai_evaluation = feedback
    db.commit()
    db.refresh(attempt)
    
    return attempt


# --- Reports ---
from ..services.report_service import ReportService
from ..models import WeeklyReport
from fastapi.responses import FileResponse

@router.post("/reports/generate")
def generate_weekly_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ReportService(db)
    try:
        report = service.generate_weekly_report(user_id=current_user.id)
        return report
    except Exception as e:
        print(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reviews/today")
def get_today_reviews(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get problems due for review today with rich formatting for the review page.
    """
    from datetime import datetime
    from sqlalchemy import and_, or_
    import random
    
    today_date = datetime.utcnow().date()
    
    # 1. Check if we already generated a review set for today
    daily_review = db.query(DailyReview).filter(
        DailyReview.user_id == current_user.id,
        DailyReview.review_date == today_date
    ).first()

    if daily_review:
        # Return the previously generated selection
        raw_list = []
        for pid in daily_review.problem_ids:
            p = db.query(Problem).filter(Problem.id == pid).first()
            if p:
                rec = db.query(LearningRecord).filter(
                    LearningRecord.user_id == current_user.id,
                    LearningRecord.problem_id == p.id
                ).first()
                if rec:
                    from ..models import UserKnowledgeMastery
                    node_name = None
                    comp_score = None
                    if p.knowledge_path and p.knowledge_path != "unknown":
                        node = db.query(KnowledgeNode).filter(KnowledgeNode.path == p.knowledge_path).first()
                        if node:
                            node_name = node.name
                        tag = node_name if node_name else p.knowledge_path
                        ukm = db.query(UserKnowledgeMastery).filter(
                            UserKnowledgeMastery.user_id == current_user.id,
                            UserKnowledgeMastery.knowledge_tag == tag
                        ).first()
                        if ukm:
                            comp_score = ukm.comprehensive_score

                    item = {
                        "id": p.id,
                        "latex_content": p.latex_content or "",
                        "difficulty": p.difficulty or 0,
                        "knowledge_path": p.knowledge_path or "unknown",
                        "knowledge_node_name": node_name,
                        "comprehensive_score": comp_score,
                        "ai_analysis": p.ai_analysis,
                        "trigger_variant": (rec.ease_factor or 2.5) >= 2.8,
                        "mastery_level": rec.mastery_level or 0
                    }
                    raw_list.append(item)
        return raw_list

    # 2. If no existing review, generate a new batch
    today_dt = datetime.utcnow()
    print(f"[DEBUG] Generating new reviews for user {current_user.id} at {today_dt}")
    
    # Use the EXACT SAME query logic as daily-review
    due_records = db.query(LearningRecord).filter(
        LearningRecord.user_id == current_user.id,
        or_(
            LearningRecord.review_date <= today_dt,
            ((LearningRecord.status != 'correct') & (LearningRecord.review_date == None))
        )
    ).all()
    
    if not due_records:
        return []

    # Map to rich dict for frontend
    raw_list = []
    for rec in due_records:
        p = rec.problem
        if not p:
            continue
            
        from ..models import UserKnowledgeMastery
        node_name = None
        comp_score = None
        if p.knowledge_path and p.knowledge_path != "unknown":
            node = db.query(KnowledgeNode).filter(KnowledgeNode.path == p.knowledge_path).first()
            if node:
                node_name = node.name
            tag = node_name if node_name else p.knowledge_path
            ukm = db.query(UserKnowledgeMastery).filter(
                UserKnowledgeMastery.user_id == current_user.id,
                UserKnowledgeMastery.knowledge_tag == tag
            ).first()
            if ukm:
                comp_score = ukm.comprehensive_score

        item = {
            "id": p.id,
            "latex_content": p.latex_content or "",
            "difficulty": p.difficulty or 0,
            "knowledge_path": p.knowledge_path or "unknown",
            "knowledge_node_name": node_name,
            "comprehensive_score": comp_score,
            "ai_analysis": p.ai_analysis,
            "trigger_variant": (rec.ease_factor or 2.5) >= 2.8,
            "mastery_level": rec.mastery_level or 0
        }
        raw_list.append(item)

    # Interleaving/Shuffling logic
    by_kp = {}
    for item in raw_list:
        kp = item["knowledge_path"]
        if kp not in by_kp:
            by_kp[kp] = []
        by_kp[kp].append(item)
    
    final_selection = []
    kps = list(by_kp.keys())
    
    while kps and len(final_selection) < 15:
        random.shuffle(kps)
        target_kp = kps[0]
        batch_size = min(len(by_kp[target_kp]), random.randint(1, 2))
        for _ in range(batch_size):
            if len(final_selection) < 15:
                final_selection.append(by_kp[target_kp].pop(0))
        if not by_kp[target_kp]:
            kps.remove(target_kp)

    # 3. Save the new generated batch to the database
    problem_ids = [item["id"] for item in final_selection]
    if problem_ids:
        new_daily_review = DailyReview(
            user_id=current_user.id,
            review_date=today_date,
            problem_ids=problem_ids
        )
        db.add(new_daily_review)
        db.commit()

    return final_selection

class DailyReviewSchema(BaseModel):
    id: int
    review_date: str
    problem_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/reviews/history")
def get_review_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the history of generated DailyReview sessions.
    """
    sessions = db.query(DailyReview).filter(
        DailyReview.user_id == current_user.id
    ).order_by(DailyReview.review_date.desc()).limit(limit).all()
    
    result = []
    for s in sessions:
        # Convert model dates appropriately
        result.append({
            "id": s.id,
            "review_date": s.review_date.isoformat(),
            "problem_count": len(s.problem_ids),
            "created_at": s.created_at
        })
    return result

@router.get("/reviews/history/{session_id}")
def get_review_session_details(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all problems corresponding to a specific historical DailyReview session.
    """
    session = db.query(DailyReview).filter(
        DailyReview.id == session_id,
        DailyReview.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    problems = []
    for pid in session.problem_ids:
        p = db.query(Problem).filter(Problem.id == pid).first()
        if p:
            rec = db.query(LearningRecord).filter(
                LearningRecord.user_id == current_user.id,
                LearningRecord.problem_id == p.id
            ).first()
            if rec:
                node_name = None
                if p.knowledge_path and p.knowledge_path != "unknown":
                    node = db.query(KnowledgeNode).filter(KnowledgeNode.path == p.knowledge_path).first()
                    if node:
                        node_name = node.name

                item = {
                    "id": p.id,
                    "latex_content": p.latex_content or "",
                    "difficulty": p.difficulty or 0,
                    "knowledge_path": p.knowledge_path or "unknown",
                    "knowledge_node_name": node_name,
                    "ai_analysis": p.ai_analysis,
                    "trigger_variant": (rec.ease_factor or 2.5) >= 2.8,
                    "review_history_status": getattr(rec, 'status', 'pending'),
                    "mastery_level": rec.mastery_level or 0
                }
                problems.append(item)
                
    return {
        "id": session.id,
        "review_date": session.review_date.isoformat(),
        "problems": problems
    }

class MasteryUpdateSchema(BaseModel):
    mastery_level: int

@router.post("/reviews/problems/{problem_id}/mastery")
def update_problem_mastery(
    problem_id: int,
    data: MasteryUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the user's mastery level for a specific problem.
    Supported levels: 1 (Won't), 2 (Half), 3 (Mastered)
    """
    rec = db.query(LearningRecord).filter(
        LearningRecord.user_id == current_user.id,
        LearningRecord.problem_id == problem_id
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Learning record not found for this problem")
        
    rec.mastery_level = data.mastery_level
    db.commit()
    
    return {"status": "success", "mastery_level": data.mastery_level}

@router.get("/reports")
def get_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(WeeklyReport).filter(WeeklyReport.user_id == current_user.id).order_by(WeeklyReport.week_start.desc()).all()

@router.get("/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(WeeklyReport).filter(WeeklyReport.id == report_id, WeeklyReport.user_id == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    # Construct absolute path
    # stored relative path: "reports/filename.pdf"
    # static dir: backend/static
    
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads"))
    file_path = os.path.join(base_path, report.pdf_path) # report.pdf_path includes "reports/" prefix
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
        
    return FileResponse(file_path, filename=os.path.basename(file_path), media_type='application/pdf')

# --- Progress ---
class ProgressUpdateRequest(BaseModel):
    paths: List[str]

@router.get("/progress")
def get_progress(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    records = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.is_learned == True
    ).all()
    return [r.knowledge_path for r in records]

@router.post("/progress/batch-update")
def batch_update_progress(request: ProgressUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy import text
    
    # 1. Clear existing progress
    db.query(UserProgress).filter(UserProgress.user_id == current_user.id).delete()
    db.commit()

    if not request.paths:
        return {"status": "success", "learned_count": 0}

    # 2. Find all descendants using ltree
    # We pass the paths array to the ANY operator in Postgres
    query = text("SELECT path FROM knowledge_nodes WHERE path <@ ANY(:paths ::ltree[])")
    result = db.execute(query, {"paths": request.paths}).fetchall()
    
    learned_paths = [row[0] for row in result]
    
    # 3. Save new records
    new_records = [
        UserProgress(user_id=current_user.id, knowledge_path=path, is_learned=True)
        for path in set(learned_paths)
    ]
    db.add_all(new_records)
    db.commit()
    
    return {"status": "success", "learned_count": len(new_records)}
@router.get("/logs/calls", response_model=List[APICallLogSchema])
def get_call_logs(limit: int = 100, db: Session = Depends(get_db)):
    """Fetch recent successful AI call logs."""
    return db.query(APICallLog).order_by(APICallLog.created_at.desc()).limit(limit).all()

@router.get("/logs/system", response_model=List[dict])
def get_system_logs(limit: int = 100, db: Session = Depends(get_db)):
    """Fetch recent system error logs."""
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()
    # Convert to dict for easier frontend handling if needed, though Schema is better
    return [
        {
            "id": l.id,
            "level": l.level,
            "category": l.category,
            "message": l.message,
            "details": l.details,
            "created_at": l.created_at
        } for l in logs
    ]

# --- Personalized Daily Practice Generation ---

@router.post("/practices/generate_daily")
async def generate_daily_practice(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    [NEW] Generate Personalized Daily Practice via targeted tagging and AI mutation.
    """
    from datetime import datetime
    from sqlalchemy import asc
    from ..models import UserKnowledgeMastery, Problem, LearningRecord, DailyReview
    
    today_date = datetime.utcnow().date()
    
    # Check if a practice/review session already exists for today
    existing_session = db.query(DailyReview).filter(
        DailyReview.user_id == current_user.id,
        DailyReview.review_date == today_date
    ).first()
    
    if existing_session:
        # Just return the count or existing session info
        return {"status": "success", "message": "Today's review session already generated", "problem_count": len(existing_session.problem_ids)}

    # Step 1: Targeting (Find bottom 2-3 weak tags)
    weaknesses = db.query(UserKnowledgeMastery).filter(
        UserKnowledgeMastery.user_id == current_user.id
    ).order_by(
        asc(UserKnowledgeMastery.comprehensive_score)
    ).limit(3).all()
    
    target_tags = [w.knowledge_tag for w in weaknesses]
    
    if not target_tags:
        # Fallback if the user has no mastery data established yet
        return {"status": "error", "message": "No knowledge mastery data found to generate targeted practice"}

    # Step 2: Extraction (Find historical mistakes)
    selected_problems = []
    MAX_PROBLEMS = 5
    
    # We query the LearningRecord to find mistakes matching the tags
    for tag in target_tags:
        if len(selected_problems) >= MAX_PROBLEMS:
            break
            
        # Find problems matching this tag in user's history that are NOT mastered
        records = db.query(LearningRecord).join(Problem).filter(
            LearningRecord.user_id == current_user.id,
            LearningRecord.mastery_level < 3,
            # In our schema, knowledge_tag might be the direct path or the node name. 
            # We use a simple ilike to match both possibilities loosely for Extraction
            Problem.knowledge_path.ilike(f"%{tag}%")
        ).all()
        
        for r in records:
            if r.problem_id not in [p.id for p in selected_problems]:
                selected_problems.append(r.problem)
                if len(selected_problems) >= MAX_PROBLEMS:
                    break

    # Step 3: Mutation (Generate remaining problems via AI)
    deficit = MAX_PROBLEMS - len(selected_problems)
    
    if deficit > 0 and len(selected_problems) > 0:
        # We have at least 1 mistake to base the AI generation on
        base_problem = selected_problems[0]
        base_latex = base_problem.latex_content
        target_tag = target_tags[0] 
        
        try:
            ai_data = await ai_service.generate_variation(
                original_latex=base_latex,
                knowledge_tag=target_tag,
                quantity=deficit,
                difficulty=base_problem.difficulty or 3
            )
            
            ai_problems = ai_data.get("problems", [])
            for ai_prob in ai_problems:
                new_prob = Problem(
                    latex_content=ai_prob.get("question", ""),
                    text_content=ai_prob.get("question", ""),
                    difficulty=base_problem.difficulty or 3,
                    knowledge_path=target_tag,
                    source="AI Generated Variation",
                    is_public=False,
                    ai_analysis={
                        "solution": ai_prob.get("solution", ""),
                        "thinking_process": ai_prob.get("hint", "")
                    }
                )
                db.add(new_prob)
                db.flush() # Flush to get the ID
                selected_problems.append(new_prob)
                
                # Create a LearningRecord for the new problem so it shows up in reviews
                new_record = LearningRecord(
                    user_id=current_user.id,
                    problem_id=new_prob.id,
                    status="pending",
                    difficulty_rating=new_prob.difficulty
                )
                db.add(new_record)
                
        except Exception as e:
            print(f"Failed to generate AI variations for daily practice: {e}")
            pass # Keep going with whatever problems we did find
            
    # Assembly: Compile into today's DailyReview
    final_ids = [p.id for p in selected_problems]
    
    if final_ids:
        new_daily_review = DailyReview(
            user_id=current_user.id,
            review_date=today_date,
            problem_ids=final_ids
        )
        db.add(new_daily_review)
        db.commit()
    
    return {
        "status": "success", 
        "target_tags_focused": target_tags,
        "problems_assembled": len(final_ids),
        "ai_mutations_generated": deficit if deficit > 0 else 0
    }

# --- Diagnostic Assessment ---

@router.post("/assessment/generate_paper")
async def generate_paper(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a printable diagnostic exam paper (5-10 questions) using AI.
    Questions are selected from the user's learned topics via UserProgress.
    The paper_snapshot (questions + answers) is stored in AssessmentSession.
    """
    from ..models import UserProgress, AssessmentSession, AssessmentProblem
    from sqlalchemy import text as sql_text
    import random

    # 1. Get leaf-level learned topics (same algo as generate_test)
    learned_progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.is_learned == True
    ).all()

    # Build path -> name map from knowledge_nodes
    try:
        rows = db.execute(sql_text("SELECT name, path::text FROM knowledge_nodes")).fetchall()
        path_to_name = {row[1]: row[0] for row in rows}
    except Exception:
        path_to_name = {}

    all_paths = [p.knowledge_path for p in learned_progress]
    leaf_entries = []
    for p in learned_progress:
        is_parent = any(other.startswith(p.knowledge_path + '.') for other in all_paths if other != p.knowledge_path)
        if not is_parent:
            name = path_to_name.get(p.knowledge_path, p.knowledge_path)
            leaf_entries.append((p.knowledge_path, name))

    if not leaf_entries:
        raise HTTPException(status_code=400, detail="未找到已学知识点。请先在学习进度界面勾选您已学习的知识点。")

    # Pick up to 8 topics for the paper
    if len(leaf_entries) > 8:
        leaf_entries = random.sample(leaf_entries, 8)

    topic_names = [name for _, name in leaf_entries]

    # 2. Ask Gemini to generate the full paper
    from ..main import ai_service
    topics_str = "、".join(topic_names)
    prompt = f"""请为一位高中数学学生生成一套完整的摸底测试试卷，覆盖以下知识点：{topics_str}。

要求：
- 共生成 {min(len(topic_names), 8)} 道题（每个知识点各1道），难度适中（3-4颗星）
- 包含解答题（非选择题），需要学生写出完整解题过程
- 每道题必须有明确的标准答案和解析

请严格以如下 JSON 数组格式输出（不要使用markdown代码块包装）：
[
  {{
    "num": 1,
    "knowledge_tag": "知识点名称",
    "latex_content": "题目的完整LaTeX内容（含$符号）",
    "answer": "标准答案",
    "explanation": "详细解析步骤",
    "score": 10
  }},
  ...
]"""

    try:
        text, used_model, _ = await ai_service.call_gemini_with_fallback('teaching', prompt)
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        paper_questions = json.loads(text.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 生成试卷失败: {str(e)}")

    # 3. Create session with snapshot
    session = AssessmentSession(
        user_id=current_user.id,
        status="paper_generated",
        paper_snapshot=paper_questions
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "status": "success",
        "session_id": session.id,
        "paper": paper_questions,
        "topics": topic_names
    }


@router.post("/assessment/{session_id}/submit_full_paper")
async def submit_full_paper(
    session_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept multiple answer-sheet photos for an assessment session.
    Sends all images + original questions to Gemini for holistic grading.
    Updates AssessmentSession with grading results and report.
    """
    from ..models import AssessmentSession, UserKnowledgeMastery
    from datetime import datetime as dt

    session = db.query(AssessmentSession).filter(
        AssessmentSession.id == session_id,
        AssessmentSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="找不到该评测会话")
    if not session.paper_snapshot:
        raise HTTPException(status_code=400, detail="该会话没有试卷快照，请先调用 generate_paper")

    # 1. Save uploaded images
    upload_dir = f"uploads/assessments/{session_id}"
    os.makedirs(upload_dir, exist_ok=True)

    image_paths = []
    for i, file in enumerate(files):
        if not file.content_type.startswith("image/"):
            continue
        suffix = os.path.splitext(file.filename)[1] or ".jpg"
        save_path = os.path.join(upload_dir, f"answer_{i+1}{suffix}")
        with open(save_path, "wb") as f:
            f.write(await file.read())
        image_paths.append(save_path)

    if not image_paths:
        raise HTTPException(status_code=400, detail="请至少上传一张答卷图片")

    # 2. Call AI to grade
    from ..main import ai_service
    try:
        grading_result = await ai_service.grade_full_paper(
            paper_snapshot=session.paper_snapshot,
            image_paths=image_paths,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 批改失败: {str(e)}")

    # 3. Compute overall score
    graded = grading_result.get("graded_problems", [])
    total = sum(p.get("score", 0) for p in graded)
    max_total = sum(p.get("max_score", 10) for p in graded)
    overall_pct = round((total / max_total * 100) if max_total > 0 else 0, 1)

    # 4. Persist grading results
    session.graded_problems = graded
    session.report_markdown = grading_result.get("comprehensive_report", "")
    session.formatting_feedback = grading_result.get("formatting_feedback", "")
    session.paper_image_paths = image_paths
    session.overall_score = overall_pct
    session.status = "completed"
    session.completed_at = dt.utcnow()

    # 5. Update UserKnowledgeMastery for each graded topic
    for gp in graded:
        tag = gp.get("knowledge_tag", "")
        score = gp.get("score", 0)
        max_score = gp.get("max_score", 10)
        if not tag:
            continue
        ai_rating = round((score / max_score) * 10, 1) if max_score > 0 else 5.0

        mastery = db.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.user_id == current_user.id,
            UserKnowledgeMastery.knowledge_tag == tag
        ).first()

        if mastery:
            # Blend new rating with existing (weighted average)
            mastery.ai_assessed_rating = round((mastery.ai_assessed_rating or 5.0) * 0.4 + ai_rating * 0.6, 1)
            self_r = mastery.user_self_rating or 5.0
            mastery.comprehensive_score = round(mastery.ai_assessed_rating * 0.6 + self_r * 0.4, 1)
        else:
            new_mastery = UserKnowledgeMastery(
                user_id=current_user.id,
                knowledge_tag=tag,
                ai_assessed_rating=ai_rating,
                comprehensive_score=ai_rating
            )
            db.add(new_mastery)

    db.commit()

    return {
        "status": "success",
        "session_id": session_id,
        "overall_score": overall_pct,
        "graded_problems": graded,
        "comprehensive_report": session.report_markdown,
        "formatting_feedback": session.formatting_feedback
    }


@router.post("/assessment/generate_test")

async def generate_diagnostic_test(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new diagnostic test based on UserProgress (Learned Topics).
    """
    from ..models import UserProgress, Problem, AssessmentSession, AssessmentProblem
    from sqlalchemy import func
    
    # 1. Fetch learned topics
    learned_progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.is_learned == True
    ).all()
    
    # We should use Chinese knowledge names for AI generation / DB lookups
    # because knowledge_path stores ID codes like SH_MATH.01
    # Build a path -> name map by querying the knowledge_nodes table
    from sqlalchemy import text as sql_text
    try:
        rows = db.execute(sql_text("SELECT name, path::text FROM knowledge_nodes")).fetchall()
        path_to_name = {row[1]: row[0] for row in rows}
    except Exception:
        # If knowledge_nodes table doesn't exist, use the path directly
        path_to_name = {}

    all_paths = [p.knowledge_path for p in learned_progress]
    
    # Filter out parent nodes (if a longer path starts with this path + '.', it's a parent)
    leaf_entries = []
    for p in learned_progress:
        is_parent = any(other.startswith(p.knowledge_path + '.') for other in all_paths if other != p.knowledge_path)
        if not is_parent:
            name = path_to_name.get(p.knowledge_path, p.knowledge_path)  # Fallback to path if no name found
            leaf_entries.append((p.knowledge_path, name))
    
    if not leaf_entries:
        raise HTTPException(status_code=400, detail="No specific learned topics found. Please expand the tree and mark specific topics as learned.")
        
    # Limit to a maximum of 8 random topics to avoid overloaded tests
    import random
    if len(leaf_entries) > 8:
        leaf_entries = random.sample(leaf_entries, 8)
        
    # 2. Extract representative problems
    session_problems = []
    
    # We need the AI service locally if we fall back
    from ..main import ai_service
    import random
    
    for topic_path, topic_name in leaf_entries:
        # Get 1 random problem that matches this topic's path code (e.g. SH_MATH.01.01)
        prob = db.query(Problem).filter(
            Problem.knowledge_path == topic_path
        ).order_by(func.random()).first()
        
        if not prob:
            # Try a broader prefix match (e.g. problems tagged under SH_MATH.01.01 might match SH_MATH.01)
            prob = db.query(Problem).filter(
                Problem.knowledge_path.ilike(f"{topic_path}%")
            ).order_by(func.random()).first()
            
        if prob and prob.id not in [p.id for p in session_problems]:
            session_problems.append(prob)
        elif not prob:
            # Fallback: Dynamically generate an unseen problem using Gemini!
            try:
                # Generate dynamic problem using Gemini
                prompt = f"""
                生成一道全新的高中数学题目，考察的核心知识点是：{topic_name}。
                要求难度适中（3-4颗星），必须以规范的 JSON 格式直接输出。包括以下字段：
                - id: 临时填 0
                - subject: "数学"
                - chapter: "{topic_name}"
                - knowledge_node_name: "{topic_name}"
                - knowledge_path: "{topic_name}"
                - difficulty: 3
                - latex_content: "题目的LaTeX原始内容"
                - answer: "最终答案"
                - explanation: "详细解析"
                - options: [] (如果不是选择题，填空数组)

                请直接输出合法的JSON对象（不要使用markdown代码块包装）。
                """
                
                # Use 'teaching' role since it's the standard generation model configured
                text, _, _ = await ai_service.call_gemini_with_fallback('teaching', prompt)
                
                # Cleanup JSON
                text = text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                
                import json
                gen_data = json.loads(text.strip())
                
                # Save this dynamic problem to DB permanently
                new_prob = Problem(
                    user_id=current_user.id,
                    image_path="system_generated/diagnostic", # Image is required but this is AI generated text-only
                    latex_content=gen_data.get("latex_content", ""),
                    difficulty=gen_data.get("difficulty", 3),
                    knowledge_path=topic_path,
                    ai_model="teaching",
                    ai_analysis={
                        "answer": gen_data.get("answer", ""),
                        "explanation": gen_data.get("explanation", ""),
                        "options": gen_data.get("options", []),
                        "chapter": gen_data.get("chapter", "")
                    }
                )
                db.add(new_prob)
                db.flush() # flush to get the brand new id
                session_problems.append(new_prob)
                
            except Exception as e:
                print(f"Failed to dynamic fallback generate for {topic_name}: {e}")
                # Skip if generation fails
                pass
            
    if not session_problems:
        raise HTTPException(status_code=400, detail="本地题库该知识点为空，且自动向 AI 请求生成题目遇到网络波动。请稍后重试。")
        
    # Limit test length (max 10 questions)
    if len(session_problems) > 10:
        session_problems = random.sample(session_problems, 10)
        
    # 3. Create Session
    new_session = AssessmentSession(
        user_id=current_user.id,
        status="in_progress"
    )
    db.add(new_session)
    db.flush() # flush to get ID
    
    # 4. Attach Problems
    for prob in session_problems:
        ap = AssessmentProblem(
            session_id=new_session.id,
            problem_id=prob.id
        )
        db.add(ap)
        
    db.commit()
    
    return {
        "status": "success",
        "session_id": new_session.id,
        "problem_count": len(session_problems),
        "topics_covered": len(leaf_entries)
    }

@router.get("/assessment/{session_id}")
async def get_assessment_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch the details and problems of an assessment session.
    """
    from ..models import AssessmentSession, AssessmentProblem
    
    session = db.query(AssessmentSession).filter(
        AssessmentSession.id == session_id,
        AssessmentSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Assessment session not found")
        
    problems = db.query(AssessmentProblem).filter(AssessmentProblem.session_id == session_id).all()
    
    items = []
    for ap in problems:
        items.append({
            "id": ap.problem_id,
            "latex_content": ap.problem.latex_content,
            "knowledge_path": ap.problem.knowledge_path,
            "is_submitted": ap.is_submitted,
            "ai_score": ap.ai_score,
            "ai_feedback": ap.ai_feedback
        })
        
    return {
        "id": session.id,
        "status": session.status,
        "overall_score": session.overall_score,
        "report_markdown": session.report_markdown,
        "formatting_feedback": session.formatting_feedback,
        "paper_snapshot": session.paper_snapshot,
        "graded_problems": session.graded_problems,
        "problems": items
    }

@router.post("/assessment/{session_id}/problems/{problem_id}/submit")
async def submit_assessment_problem(
    session_id: int,
    problem_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import AssessmentSession, AssessmentProblem, Problem
    import shutil
    import uuid
    import time
    
    # Verify session and problem
    session = db.query(AssessmentSession).filter(
        AssessmentSession.id == session_id,
        AssessmentSession.user_id == current_user.id,
        AssessmentSession.status == "in_progress"
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Active Assessment session not found")
        
    ap = db.query(AssessmentProblem).filter(
        AssessmentProblem.session_id == session_id,
        AssessmentProblem.problem_id == problem_id
    ).first()
    
    if not ap:
        raise HTTPException(status_code=404, detail="Problem not found in this assessment")
        
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
        
    # Save Image
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"assess_{session_id}_{problem_id}_{uuid.uuid4().hex[:8]}_{int(time.time())}{file_ext}"
    file_location = os.path.join(UPLOAD_DIR, filename)

    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    # Get Standard Solution for AI compare
    problem_latex = problem.latex_content or "N/A"
    standard_solution = "N/A"
    if problem.ai_analysis:
        if isinstance(problem.ai_analysis, dict):
            standard_solution = problem.ai_analysis.get("solution", "N/A")
        elif isinstance(problem.ai_analysis, str):
            standard_solution = problem.ai_analysis

    # Call AI Grader
    try:
        ai_response = await ai_service.analyze_solution(problem_latex, standard_solution, file_location, target_id=problem.id)
        feedback = ai_response["feedback_json"]
        score = feedback.get("score", 0)
    except AIServiceException as e:
        status_code = 429 if e.error_type == "rate_limit" else 401 if e.error_type == "auth_error" else 503
        raise HTTPException(
            status_code=status_code, 
            detail={"message": e.args[0], "error_type": e.error_type, "retry_seconds": e.retry_seconds}
        )
    except Exception as e:
        feedback = {"score": 0, "error": str(e)}
        score = 0
        
    # Update DB
    ap.image_path = filename
    ap.ai_score = float(score)
    ap.ai_feedback = feedback
    ap.is_submitted = True
    db.commit()
    
    return {
        "status": "success",
        "ai_score": score,
        "ai_feedback": feedback
    }

@router.post("/assessment/{session_id}/finalize")
async def finalize_assessment(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import AssessmentSession, AssessmentProblem, UserProgress
    from datetime import datetime
    
    session = db.query(AssessmentSession).filter(
        AssessmentSession.id == session_id,
        AssessmentSession.user_id == current_user.id,
        AssessmentSession.status == "in_progress"
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Active Assessment session not found")
        
    problems = db.query(AssessmentProblem).filter(AssessmentProblem.session_id == session_id).all()
    
    total_score = 0
    results_payload = []
    
    for ap in problems:
        if ap.is_submitted and ap.ai_feedback:
            total_score += ap.ai_score or 0
            results_payload.append({
                "problem_knowledge_tag": ap.problem.knowledge_path,
                "score": ap.ai_score,
                "logic_gaps": ap.ai_feedback.get("logic_gaps", []),
                "calculation_errors": ap.ai_feedback.get("calculation_errors", []),
                "formatting_feedback": ap.ai_feedback.get("formatting_feedback", ""),
                "knowledge_analysis": ap.ai_feedback.get("knowledge_analysis", [])
            })
            
    # Compile prompt data
    learned_progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.is_learned == True
    ).all()
    learned_paths = [p.knowledge_path for p in learned_progress]
    
    # Fire Gemini Report Generator
    try:
        report_md = await ai_service.generate_diagnostic_report(
            learned_topics=learned_paths,
            assessment_results=results_payload
        )
    except Exception as e:
        report_md = f"Error generating report: {str(e)}"
        
    # Update Session
    final_score = total_score / len(problems) if problems else 0
    session.overall_score = final_score
    session.status = "completed"
    session.completed_at = datetime.utcnow()
    session.report_markdown = report_md
    
    db.commit()
    
    return {
        "status": "success",
        "session_id": session.id,
        "overall_score": final_score,
        "report_markdown": report_md
    }
