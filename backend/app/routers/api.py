from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from pydantic import BaseModel
from ..database import get_db
from ..models import Problem, KnowledgePoint, KnowledgeNode, LearningRecord, SolutionAttempt, User, PracticeProblem, PracticeSession, UserProgress, APICallLog, SystemLog, DailyReview
import os
import json
import re
import asyncio
from datetime import datetime
from ..services.ai_service import AIService, AIServiceException
from ..auth_deps import get_current_user
import PIL.Image

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
                # Build upgraded system prompt requesting structured extraction including paper title,
                # original question text and user answer text for each problem.
                prompt = f'''
你是一位资深数学阅卷专家。请阅读提供的试卷与答题照片，严格输出以下 JSON 结构（不要包含多余文本）：
{{
    "paper_title": "精准提取图片中的试卷大标题（如 '2025年高三一模数学'）。若无明显标题，请生成专业名称。",
    "total_score": 85,
    "overall_feedback": "整体评价和学情分析（简洁的 Markdown 文本）",
    "problems": [
        {{
            "problem_number": "1",
            "original_question_text": "精准识别并输出该题的完整原题文本",
            "user_answer_text": "识别并输出学生手写的具体解答过程",
            "score": 10,
            "max_score": 10,
            "knowledge_tag": "对数运算",
            "feedback": "批改意见与扣分点..."
        }}
    ]
}}

附注：当返回知识点标签时，**只能**从以下列表中选择：{standard_tags_list}。
请保证 JSON 字段完整且可解析，所有文本字段尽量保留换行（使用 \n 表示）。
'''
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



# --- Full Paper Grading ---
from fastapi import BackgroundTasks

class ExamSessionSchema(BaseModel):
    id: int
    status: str
    total_score: Optional[float] = None
    overall_evaluation: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

def _sanitize_json_string(s: str) -> str:
    r"""
    Sanitize JSON-ish text to handle unescaped backslashes and control chars
    This handles LaTeX commands like \sqrt, \frac that weren't escaped properly
    """
    # Normalize line endings
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    # Remove control chars except \n, \t
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    # Escape single backslashes that are not part of valid JSON escapes (\", \\, \/, \b, \f, \n, \r, \t, \uXXXX)
    s = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', s)
    return s


async def _extract_exam_structure(answer_image_paths: List[str], question_image_paths: List[str], ai_service):
    """
    Stage 1: Lightweight Structure Extraction
    Purpose: Scan answer images ONLY to build question index, ignoring question drafts
    
    Key Architectural Change: Explicitly separates answer images from question images
    to prevent AI from confusing draft work with the actual answers.
    
    Returns: {'paper_title', 'question_numbers', 'page_count', 'model'}
    """
    prompt = f'''你是一个试卷结构分析助手。本次分析，我向你提供两组独立的图片资源：
【第一组 - 学生答题卡/答题纸（共{len(answer_image_paths)}页）】：这些图片包含学生的最终作答
【第二组 - 试卷原题（共{len(question_image_paths)}页）】：这些图片包含题目原文（仅用于理解题意）

【核心指令 - 严格遵守】：
1. **答案唯一来源**：你必须且只能从【学生答题卡/答题纸】中识别题号
2. **无视草稿**：对于【试卷原题】上出现的任何手写笔迹、勾画或文字标注，必须**完全无视**
3. **防止混淆**：绝不能将试卷原题上的手写内容误认为是学生答案

请仅依赖第一组（答题卡）的内容，完整精确地列出所有题号。

严格输出 JSON 格式，不要任何额外文本：
{{
    "paper_title": "提取的试卷标题或名称",
    "total_question_count": {len(answer_image_paths)},
    "question_numbers": ["1", "2", "3", "4", "5", "6", "7", "8"],
    "notes": "如果有任何题号缺失或不清楚的地方，请说明"
}}
'''
    
    # Build content list with explicit ordering:
    # First add answer images, then question images
    # This helps Gemini understand the context
    content = [prompt]
    
    # Add answer images first (with inline text labels)
    for i, img_path in enumerate(answer_image_paths):
        try:
            img = PIL.Image.open(img_path)
            content.append(img)
        except Exception as e:
            print(f"Warning: failed to open answer image {img_path}: {e}")
    
    # Add question images second (with inline text labels)
    for i, img_path in enumerate(question_image_paths):
        try:
            img = PIL.Image.open(img_path)
            content.append(img)
        except Exception as e:
            print(f"Warning: failed to open question image {img_path}: {e}")
    
    # Call with pre-built content list
    text, used_model, _ = await ai_service.call_gemini_with_fallback(
        'teaching', 
        content
    )
    
    # Parse JSON with aggressive sanitization
    text = text.strip()
    for prefix in ["```json", "```"]:
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.endswith("```"):
        text = text[:-3]
    
    start = text.find('{')
    end = text.rfind('}')
    json_text = text[start:end+1] if start != -1 and end != -1 else text
    
    # Try multiple sanitization strategies
    last_exc = None
    for candidate in [json_text, _sanitize_json_string(json_text)]:
        try:
            result = json.loads(candidate.strip())
            last_exc = None
            break
        except Exception as e:
            last_exc = e
    
    if last_exc:
        # Last resort: try unicode-escape decode then sanitize
        try:
            alt = json_text.encode('utf-8').decode('unicode_escape')
            alt2 = _sanitize_json_string(alt)
            result = json.loads(alt2.strip())
            last_exc = None
        except Exception as e3:
            last_exc = e3
    
    if last_exc:
        raise ValueError(f"Failed to parse JSON from Stage 1: {str(last_exc)}\nJSON text: {json_text[:200]}")
    
    return {
        'paper_title': result.get('paper_title', '试卷'),
        'question_numbers': result.get('question_numbers', []),
        'total_question_count': result.get('total_question_count', 0),
        'model': used_model,
        'page_count': len(answer_image_paths)
    }


async def _grade_exam_batch(
    batch_numbers: List[str],
    question_image_paths: List[str],
    answer_image_paths: List[str],
    standard_tags_list: List[str],
    ai_service,
    batch_index: int,
    total_batches: int
):
    """
    Stage 2: Focused Batch Grading with Image Separation
    Purpose: Grade 2-3 questions per batch, using answer images as authoritative source
    
    Key Architectural Change: Explicitly separates question and answer images,
    ensuring AI grades only based on student's final answers in the answer sheet.
    
    Returns: {'problems': [...], 'batch_index', 'model', 'tokens_used'}
    """
    batch_str = ", ".join(batch_numbers)
    
    prompt = f'''你是一位严格的高中数学阅卷专家。本次批改，我向你提供两组独立的图片资源：
【第一组 - 答题卡/答题纸（共{len(answer_image_paths)}页）】：包含学生的最终作答
【第二组 - 试卷原题（共{len(question_image_paths)}页）】：包含题目的原始文本

你需要批改第 {batch_str} 题。

【绝对批改纪律 - 严格遵守】：
1. **答案唯一来源**：你必须且只能从【学生答题卡/答题纸】中提取学生的答案进行批改。
2. **题目理解参考**：【试卷原题】仅用于理解题意，不能作为学生答案的来源。
3. **无视草稿**：对于【试卷原题】上出现的任何手写笔迹、勾画、选项填涂或草稿演算，必须**绝对无视**，绝不能作为评分依据。
4. **防混淆比对**：对于选择题和填空题，必须在答题卡指定的题号位置寻找学生的最终结果。若答题卡上该题空白，即便原题上有任何手写内容，也必须判为未作答（0分）。

## 批改任务信息
- 这是批改任务的第 {batch_index+1}/{total_batches} 批
- 本批题号：{batch_str}
- 每题必须包含完整的原题文本（来自试卷原题）、学生答案（来自答题卡）和批改反馈

## 知识点标签限制
**只能**从以下列表中选择：{standard_tags_list}

## 输出格式（严格JSON）
{{
    "batch_index": {batch_index},
    "graded_question_count": {len(batch_numbers)},
    "problems": [
        {{
            "problem_number": "1",
            "original_question_text": "从试卷原题中提取的完整原题文本",
            "user_answer_text": "从答题卡中提取的学生手写答案",
            "score": 10,
            "max_score": 10,
            "knowledge_tag": "知识点名称",
            "feedback": "严格基于答题卡内容的批改反馈"
        }}
    ]
}}
'''
    
    # Build content list with explicit ordering:
    # Answer images first (as authoritative source), then question images (for context)
    content = [prompt]
    
    # Add answer images first (authoritative source)
    for img_path in answer_image_paths:
        try:
            img = PIL.Image.open(img_path)
            content.append(img)
        except Exception as e:
            print(f"Warning: failed to open answer image {img_path}: {e}")
    
    # Add question images second (context only)
    for img_path in question_image_paths:
        try:
            img = PIL.Image.open(img_path)
            content.append(img)
        except Exception as e:
            print(f"Warning: failed to open question image {img_path}: {e}")
    
    # Call with pre-built content list
    text, used_model, tokens = await ai_service.call_gemini_with_fallback('teaching', content)
    
    # Parse JSON with aggressive sanitization
    text = text.strip()
    for prefix in ["```json", "```"]:
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.endswith("```"):
        text = text[:-3]
    
    start = text.find('{')
    end = text.rfind('}')
    json_text = text[start:end+1] if start != -1 and end != -1 else text
    
    # Try multiple sanitization strategies
    last_exc = None
    for candidate in [json_text, _sanitize_json_string(json_text)]:
        try:
            result = json.loads(candidate.strip())
            last_exc = None
            break
        except Exception as e:
            last_exc = e
    
    if last_exc:
        # Last resort: try unicode-escape decode then sanitize
        try:
            alt = json_text.encode('utf-8').decode('unicode_escape')
            alt2 = _sanitize_json_string(alt)
            result = json.loads(alt2.strip())
            last_exc = None
        except Exception as e3:
            last_exc = e3
    
    if last_exc:
        raise ValueError(f"Failed to parse JSON from Stage 2 Batch {batch_index}: {str(last_exc)}\nJSON text: {json_text[:200]}")
    
    return {
        'batch_index': batch_index,
        'problems': result.get('problems', []),
        'model': used_model,
        'tokens_used': tokens,
        'graded_count': result.get('graded_question_count', 0)
    }


async def _generate_overall_feedback(
    all_problems: List[dict],
    paper_title: str,
    total_score: float,
    ai_service
):
    """
    Generate comprehensive feedback based on all graded problems
    """
    problem_summary = "\n".join([
        f"- 题{p['problem_number']}: {p['score']}/{p['max_score']} ({p['knowledge_tag']})"
        for p in all_problems
    ])
    
    prompt = f'''基于以下批改结果，生成一份简洁的学生学情分析反馈。

试卷：{paper_title}
总分：{total_score}

题目成绩概览：
{problem_summary}

请生成一份 50-100 字的学生学情分析，包括：
1. 总体表现评价
2. 主要优势领域
3. 需要改进的方向

输出纯文本，无需 JSON 格式。
'''
    
    text, used_model, _ = await ai_service.call_gemini_with_fallback('teaching', prompt, image_paths=None)
    return text.strip()


def _natural_sort_key(problem: dict) -> tuple:
    """
    Extract natural sort key from problem number for correct ordering
    Handles: "1", "10", "2", "4(1)", "12a", etc.
    Returns: tuple of integers for proper numeric ordering
    """
    num_str = str(problem.get("problem_number", "")).strip()
    if not num_str:
        return (0,)
    
    # Extract all digit sequences from problem_number
    # e.g., "4(1)" → [4, 1], "12a" → [12]
    numbers = re.findall(r'\d+', num_str)
    
    if numbers:
        return tuple(int(n) for n in numbers)
    else:
        # Fallback: return string hash for non-numeric problem numbers
        return (0, hash(num_str))


async def process_full_exam(
    task_id: int, 
    user_id: int, 
    question_image_paths: List[str], 
    answer_image_paths: List[str],
    image_urls: List[str] = None
):
    """
    Two-Stage Exam Grading Pipeline with Image Separation & Dynamic Model Routing:
    Stage 1: Lightweight structure extraction (identify all question numbers from answer images)
    Stage 2: Parallel batch grading (2-3 questions per batch using asyncio.gather)
    Stage 3: Result aggregation, weighted knowledge mastery update, and database persistence
    
    Key Improvements:
    - Dynamically routes to appropriate teaching model based on exam_type
    - Implements weighted moving average for knowledge mastery calculation
    - Explicitly separates question images from answer images
    """
    from ..database import SessionLocal
    from ..models import ExamRecord, ExamProblemResult, KnowledgeNode, UserKnowledgeMastery, SystemLog, ExamType
    from ..main import ai_service
    from ..services.model_manager import model_manager
    from ..services.knowledge_mastery_service import batch_update_knowledge_mastery
    
    db = SessionLocal()
    pipeline_start_time = datetime.utcnow()
    selected_teaching_model = None  # Will be set based on exam_type
    
    try:
        # ============================================================
        # FETCH EXAM RECORD & DETERMINE TEACHING MODEL
        # ============================================================
        exam = db.query(ExamRecord).filter(ExamRecord.id == task_id).first()
        if not exam:
            raise ValueError(f"Exam record {task_id} not found")
        
        exam_type: ExamType = exam.exam_type or ExamType.CUSTOM
        
        print(f"[Exam {task_id}] Exam Type: {exam_type.value}")
        
        # Get the appropriate teaching model based on exam type
        try:
            selected_teaching_model = model_manager.get_teaching_model_for_exam_type(db, exam_type)
            print(f"[Exam {task_id}] Selected Teaching Model: {selected_teaching_model}")
        except Exception as e:
            print(f"[Exam {task_id}] ⚠️ Failed to fetch exam_type-specific model: {e}")
            print(f"[Exam {task_id}] Falling back to default AI service model")
            selected_teaching_model = None  # Will use default ai_service model
        
        # Get standard knowledge tags
        nodes = db.query(KnowledgeNode).all()
        standard_tags_list = [n.name for n in nodes]
        
        # ============================================================
        # STAGE 1: STRUCTURE EXTRACTION (Lightweight Index Building)
        # ============================================================
        print(f"[Exam {task_id}] Stage 1: Extracting exam structure from {len(answer_image_paths)} answer images...")
        
        structure = await _extract_exam_structure(
            answer_image_paths=answer_image_paths,
            question_image_paths=question_image_paths,
            ai_service=ai_service
        )
        question_numbers = structure['question_numbers']
        paper_title = structure['paper_title']
        
        print(f"[Exam {task_id}] Stage 1 Complete: Found {len(question_numbers)} questions: {question_numbers}")
        
        if not question_numbers:
            raise ValueError("No questions detected in exam. OCR may have failed.")
        
        # Log Stage 1 completion
        log_s1 = SystemLog(
            level="INFO",
            category="teaching",
            message=f"Exam {task_id} Stage 1: Extracted {len(question_numbers)} questions",
            details={
                "stage": 1,
                "paper_title": paper_title,
                "question_numbers": question_numbers,
                "model_used": structure['model']
            }
        )
        db.add(log_s1)
        db.commit()
        
        # ============================================================
        # STAGE 2: PARALLEL BATCH GRADING (Chunked Processing)
        # ============================================================
        # Create batches of 2-3 questions each
        batch_size = 3
        batches = [
            question_numbers[i:i+batch_size]
            for i in range(0, len(question_numbers), batch_size)
        ]
        
        print(f"[Exam {task_id}] Stage 2: Processing {len(batches)} batches with asyncio.gather...")
        
        # Create concurrent grading tasks
        batch_tasks = [
            _grade_exam_batch(
                batch_numbers=batch,
                question_image_paths=question_image_paths,
                answer_image_paths=answer_image_paths,
                standard_tags_list=standard_tags_list,
                ai_service=ai_service,
                batch_index=idx,
                total_batches=len(batches)
            )
            for idx, batch in enumerate(batches)
        ]
        
        # Execute all batches concurrently
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Check for errors
        all_problems = []
        batch_models = []
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"[Exam {task_id}] Batch grading error: {result}")
                raise result
            
            problems = result.get('problems', [])
            all_problems.extend(problems)
            batch_models.append(result.get('model'))
            
            print(f"[Exam {task_id}] Batch {result['batch_index']}: Graded {result['graded_count']} questions")
        
        print(f"[Exam {task_id}] Stage 2 Complete: Total {len(all_problems)} problems graded")
        
        # Log Stage 2 completion
        log_s2 = SystemLog(
            level="INFO",
            category="teaching",
            message=f"Exam {task_id} Stage 2: Batch grading completed",
            details={
                "stage": 2,
                "total_batches": len(batches),
                "batch_size": batch_size,
                "problems_graded": len(all_problems),
                "models_used": list(set(batch_models))
            }
        )
        db.add(log_s2)
        db.commit()
        
        # ============================================================
        # APPLY NATURAL SORTING TO ALL PROBLEMS
        # ============================================================
        # Sort problems by natural numeric order (not lexicographic)
        # This fixes: "1", "10", "11", "2" → "1", "2", "10", "11"
        # Also handles: "4(1)", "4(2)", "12a", etc.
        print(f"[Exam {task_id}] Sorting {len(all_problems)} problems by natural order...")
        all_problems.sort(key=_natural_sort_key)
        
        # Log the sorted problem numbers for verification
        sorted_problem_numbers = [str(p.get('problem_number', '?')) for p in all_problems]
        print(f"[Exam {task_id}] Problem order after sorting: {sorted_problem_numbers}")
        
        # ============================================================
        # STAGE 3: RESULT AGGREGATION & DATABASE PERSISTENCE
        # ============================================================
        print(f"[Exam {task_id}] Stage 3: Aggregating results and saving to database...")
        
        exam = db.query(ExamRecord).filter(ExamRecord.id == task_id).first()
        if not exam:
            raise ValueError(f"Exam record {task_id} not found")
        
        # Set basic exam info
        exam.paper_name = paper_title
        exam.image_urls = image_urls
        
        # Calculate total score
        total_score = sum(p.get('score', 0) for p in all_problems)
        exam.total_score = total_score
        
        # Use the first batch model or the latest
        exam.ai_model = batch_models[0] if batch_models else "unknown"
        
        # Generate overall feedback
        print(f"[Exam {task_id}] Generating overall feedback...")
        overall_feedback = await _generate_overall_feedback(
            all_problems=all_problems,
            paper_title=paper_title,
            total_score=total_score,
            ai_service=ai_service
        )
        
        exam.overall_feedback = overall_feedback
        exam.overall_evaluation = f"Graded via two-stage pipeline on {datetime.utcnow().isoformat()}"
        exam.status = "completed"
        exam.completed_at = datetime.utcnow()
        
        # Persist the actual teaching model used in this exam
        if selected_teaching_model:
            exam.ai_model = selected_teaching_model
        else:
            exam.ai_model = batch_models[0] if batch_models else "unknown"
        
        # Save all problems to database
        problem_save_count = 0
        for p in all_problems:
            if not p.get('problem_number'):
                continue
                
            tag = p.get("knowledge_tag", "未知")
            score = p.get("score", 0)
            max_score = p.get("max_score", 10)
            
            # Save problem result
            prob_res = ExamProblemResult(
                exam_id=exam.id,
                problem_number=str(p.get("problem_number", "未知")),
                score=score,
                max_score=max_score,
                knowledge_tag=tag,
                feedback=p.get("feedback", ""),
                original_question_text=p.get("original_question_text", None),
                user_answer_text=p.get("user_answer_text", None)
            )
            db.add(prob_res)
            problem_save_count += 1
        
        # Flush problem results first
        db.flush()
        
        # Batch update knowledge mastery using weighted algorithm
        print(f"[Exam {task_id}] Stage 3: Updating knowledge mastery with weighted algorithm...")
        mastery_update_summary = batch_update_knowledge_mastery(
            db=db,
            user_id=user_id,
            problems=all_problems,
            exam_type=exam_type,
            standard_tags_list=standard_tags_list
        )
        
        print(f"[Exam {task_id}] Knowledge mastery updated: {mastery_update_summary['updated_mastery_count']} records")
        if mastery_update_summary['skipped']:
            print(f"[Exam {task_id}] Skipped knowledge points: {mastery_update_summary['skipped']}")
        
        db.commit()
        
        pipeline_duration = (datetime.utcnow() - pipeline_start_time).total_seconds()
        
        # Final log
        log_s3 = SystemLog(
            level="INFO",
            category="teaching",
            message=f"Exam {task_id} completed via two-stage pipeline with weighted knowledge mastery",
            details={
                "stage": 3,
                "exam_type": exam_type.value,
                "teaching_model": selected_teaching_model or "default",
                "problems_saved": problem_save_count,
                "mastery_updated": mastery_update_summary['updated_mastery_count'],
                "total_score": total_score,
                "pipeline_duration_seconds": pipeline_duration,
                "questions_expected": len(question_numbers),
                "questions_graded": len(all_problems),
                "completion_status": "SUCCESS" if problem_save_count == len(all_problems) else "PARTIAL"
            }
        )
        db.add(log_s3)
        db.commit()
        
        print(f"[Exam {task_id}] ✅ Pipeline completed in {pipeline_duration:.1f}s: {problem_save_count} problems saved, {mastery_update_summary['updated_mastery_count']} mastery records updated")
        
    except Exception as e:
        print(f"[Exam {task_id}] ❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            exam = db.query(ExamRecord).filter(ExamRecord.id == task_id).first()
            if exam:
                exam.status = "failed"
                exam.overall_evaluation = f"Pipeline Error: {str(e)}"
                db.commit()
                
            error_log = SystemLog(
                level="ERROR",
                category="teaching",
                message=f"Exam {task_id} pipeline failed",
                details={"error": str(e), "traceback": traceback.format_exc()[:500]}
            )
            db.add(error_log)
            db.commit()
        except:
            db.rollback()
    
    finally:
        db.close()


@router.post("/exams/upload_and_grade")
async def upload_and_grade_exam(
    background_tasks: BackgroundTasks,
    exam_mode: str = Form('separated'),
    exam_type: str = Form('custom'),
    question_images: List[UploadFile] = File(default=[]),
    answer_images: List[UploadFile] = File(default=[]),
    combined_images: List[UploadFile] = File(default=[]),
    paper_name: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import ExamRecord
    
    question_image_paths = []
    answer_image_paths = []
    combined_image_paths = []
    all_image_urls = []
    
    # Ensure exams subdir exists
    exams_dir = os.path.join(UPLOAD_DIR, "exams")
    os.makedirs(exams_dir, exist_ok=True)

    if exam_mode == 'separated':
        # ============================================================
        # SEPARATED MODE: Process question and answer images separately
        # ============================================================
        
        # Save question images
        for file in question_images:
            safe_filename = f"exam_{current_user.id}_{int(datetime.utcnow().timestamp())}_q_{file.filename}"
            file_location = os.path.join(exams_dir, safe_filename)

            with open(file_location, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            question_image_paths.append(file_location)
            # Build URL relative to UPLOAD_DIR (which is mounted at /static)
            rel_path = os.path.relpath(file_location, UPLOAD_DIR).replace('\\', '/')
            all_image_urls.append(f"/static/{rel_path}")

        # Save answer images
        for file in answer_images:
            safe_filename = f"exam_{current_user.id}_{int(datetime.utcnow().timestamp())}_a_{file.filename}"
            file_location = os.path.join(exams_dir, safe_filename)

            with open(file_location, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            answer_image_paths.append(file_location)
            # Build URL relative to UPLOAD_DIR (which is mounted at /static)
            rel_path = os.path.relpath(file_location, UPLOAD_DIR).replace('\\', '/')
            all_image_urls.append(f"/static/{rel_path}")
    
    elif exam_mode == 'combined':
        # ============================================================
        # COMBINED MODE: Process all images as combined (卷面作答)
        # ============================================================
        
        # Save combined mode images
        for file in combined_images:
            safe_filename = f"exam_{current_user.id}_{int(datetime.utcnow().timestamp())}_c_{file.filename}"
            file_location = os.path.join(exams_dir, safe_filename)

            with open(file_location, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            combined_image_paths.append(file_location)
            # Build URL relative to UPLOAD_DIR (which is mounted at /static)
            rel_path = os.path.relpath(file_location, UPLOAD_DIR).replace('\\', '/')
            all_image_urls.append(f"/static/{rel_path}")
        
        # For combined mode, treat combined images as both question and answer
        question_image_paths = combined_image_paths
        answer_image_paths = combined_image_paths
        
    else:
        raise ValueError(f"Invalid exam_mode: {exam_mode}")
        
    # Create Task Record
    from ..models import ExamType
    
    # Convert exam_type string to ExamType enum
    try:
        exam_type_enum = ExamType[exam_type.upper()]
    except (KeyError, AttributeError):
        exam_type_enum = ExamType.CUSTOM
    
    exam_record = ExamRecord(
        user_id=current_user.id,
        status="processing",
        exam_type=exam_type_enum,
        image_paths=question_image_paths + answer_image_paths,  # Store all paths for reference
        image_urls=all_image_urls,
        paper_name=(paper_name or f"摸底测试_{datetime.utcnow().strftime('%Y%m%d_%H%M')}")
    )
    db.add(exam_record)
    db.commit()
    db.refresh(exam_record)
    
    # Dispatch Async Task with separated image categories
    background_tasks.add_task(
        process_full_exam, 
        task_id=exam_record.id, 
        user_id=current_user.id, 
        question_image_paths=question_image_paths,
        answer_image_paths=answer_image_paths,
        image_urls=all_image_urls
    )
    
    return {"task_id": exam_record.id, "status": exam_record.status}


@router.get('/exams/history')
def exams_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ..models import ExamRecord
    exams = db.query(ExamRecord).filter(ExamRecord.user_id == current_user.id).order_by(ExamRecord.created_at.desc()).all()
    return [
        {
            'id': e.id,
            'paper_name': e.paper_name or f'试卷_{e.id}',
            'created_at': e.created_at,
            'ai_model': e.ai_model,
            'exam_type': e.exam_type.value if e.exam_type else 'custom',
            'total_score': e.total_score,
            'status': e.status
        } for e in exams
    ]


@router.get("/exams/task_status/{task_id}")
def get_exam_status(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ..models import ExamRecord, ExamProblemResult
    
    exam = db.query(ExamRecord).filter(
        ExamRecord.id == task_id,
        ExamRecord.user_id == current_user.id
    ).first()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    response = {
        "exam_id": exam.id,  # 新增：明确返回试卷 ID
        "id": exam.id,
        "status": exam.status,
        "total_score": exam.total_score,
        "overall_evaluation": exam.overall_evaluation,
        "image_urls": exam.image_urls or [],
        "created_at": exam.created_at,
        "results": []
    }
    
    if exam.status == "completed":
        results = db.query(ExamProblemResult).filter(ExamProblemResult.exam_id == exam.id).all()
        response["results"] = [
            {
                "problem_number": r.problem_number,
                "score": r.score,
                "max_score": r.max_score,
                "knowledge_tag": r.knowledge_tag,
                "feedback": r.feedback,
                "original_question_text": r.original_question_text,
                "user_answer_text": r.user_answer_text
            } for r in results
        ]
        
    return response


@router.get('/exams/{exam_id}')
def exam_detail(exam_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ..models import ExamRecord, ExamProblemResult
    exam = db.query(ExamRecord).filter(ExamRecord.id == exam_id, ExamRecord.user_id == current_user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail='Exam not found')

    results = db.query(ExamProblemResult).filter(ExamProblemResult.exam_id == exam.id).all()
    
    # Apply natural sorting by problem number (handles "1", "10", "2" → "1", "2", "10")
    def _natural_sort_key_query(result):
        num_str = str(result.problem_number).strip()
        numbers = re.findall(r'\d+', num_str)
        return tuple(int(n) for n in numbers) if numbers else (0, hash(num_str))
    
    results = sorted(results, key=_natural_sort_key_query)

    return {
        'id': exam.id,
        'paper_name': exam.paper_name,
        'created_at': exam.created_at,
        'ai_model': exam.ai_model,
        'exam_type': exam.exam_type.value if exam.exam_type else 'custom',
        'total_score': exam.total_score,
        'status': exam.status,
        'overall_feedback': exam.overall_feedback or exam.overall_evaluation,
        'image_urls': exam.image_urls or [],
        'results': [
            {
                'problem_number': r.problem_number,
                'score': r.score,
                'max_score': r.max_score,
                'knowledge_tag': r.knowledge_tag,
                'feedback': r.feedback,
                'original_question_text': r.original_question_text,
                'user_answer_text': r.user_answer_text
            } for r in results
        ]
    }

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

@router.get("/user/assessment_status")
def get_assessment_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ..models import AssessmentSession
    from datetime import datetime
    
    # Get the most recent completed assessment
    last_session = db.query(AssessmentSession).filter(
        AssessmentSession.user_id == current_user.id,
        AssessmentSession.status == "completed"
    ).order_by(AssessmentSession.id.desc()).first()

    if not last_session:
        return {"days_since_last_test": None}
    
    # Use completed_at if available, otherwise created_at
    ref_date = last_session.completed_at or last_session.created_at
    days = (datetime.utcnow() - ref_date).days
    
    return {"days_since_last_test": days}

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

    # 0. Check for existing uncompleted assessment paper session
    existing_session = db.query(AssessmentSession).filter(
        AssessmentSession.user_id == current_user.id,
        AssessmentSession.status == "paper_generated"
    ).order_by(AssessmentSession.id.desc()).first()

    if existing_session and existing_session.paper_snapshot:
        try:
            topic_names = list(set([q.get('knowledge_tag', '未知') for q in existing_session.paper_snapshot]))
        except:
            topic_names = []
            
        return {
            "status": "success",
            "session_id": existing_session.id,
            "paper": existing_session.paper_snapshot,
            "topics": topic_names
        }

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

    # 2. Get Mastery Scores and Build Difficulty Matrix
    from ..models import UserKnowledgeMastery
    difficulty_matrix = []
    topic_names = []
    
    for path, name in leaf_entries:
        topic_names.append(name)
        # Assuming knowledge_tag in UserKnowledgeMastery is the topic name
        mastery = db.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.user_id == current_user.id,
            UserKnowledgeMastery.knowledge_tag == name
        ).first()
        
        score = mastery.comprehensive_score if mastery and mastery.comprehensive_score else 0
        
        if score < 60:
            difficulty = "基础概念与简单计算 (Basic)"
        elif score <= 85:
            difficulty = "中等难度与标准题型 (Medium)"
        else:
            difficulty = "综合应用与压轴拔高 (Hard)"
            
        difficulty_matrix.append({
            "topic": name,
            "mastery_score": score,
            "target_difficulty": difficulty
        })

    difficulty_matrix_json = json.dumps(difficulty_matrix, ensure_ascii=False, indent=2)

    # 3. Ask Gemini to generate the full paper
    from ..main import ai_service
    
    prompt = f"""你是一个资深的数学教研专家。请根据以下【知识点及对应难度要求矩阵】，为学生生成一套定制化的摸底试卷：
{difficulty_matrix_json}

**出题规则**：
1. 必须为矩阵中的每个知识点各生成1道题（共 {len(topic_names)} 道）。
2. 对于要求【基础】的知识点，题目必须侧重单一公式或定义的直接套用，用于检测基础盲区。
3. 对于要求【中等】的知识点，题目需符合常见高考/模拟考的中档标准题型。
4. 对于要求【拔高】的知识点，题目需涉及知识交汇或复杂变形，以测试其真实上限。
5. 包含解答题（非选择题），需要学生写出完整解题过程。
6. 每道题必须有明确的标准答案和解析。

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
