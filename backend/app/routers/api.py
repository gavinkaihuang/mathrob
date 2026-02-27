from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from pydantic import BaseModel
from ..database import get_db
from ..models import Problem, KnowledgePoint, LearningRecord, SolutionAttempt, User, PracticeProblem
import os
from datetime import datetime
from ..services.ai_service import AIService

UPLOAD_DIR = "backend/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
from datetime import datetime
from ..services.ai_service import AIService
from ..auth_deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])
ai_service = AIService()

class ProblemSchema(BaseModel):
    id: int
    image_path: str
    latex_content: Optional[str] = None
    difficulty: Optional[int] = None
    ai_analysis: Optional[Union[dict, str]] = None
    created_at: datetime
    current_mastery_level: Optional[int] = None
    ai_model: Optional[str] = None
    
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
    record.created_at = datetime.utcnow() # Last activity time
    
    # Update legacy status field for compatibility
    if request.level == 3:
        record.status = "correct"
    else:
        record.status = "wrong"
        
    db.commit()
    
    return {
        "message": "Mastery updated", 
        "level": request.level, 
        "next_review": record.review_date,
        "days_until_next": interval
    }

@router.get("/daily-review", response_model=List[ProblemSchema])
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
    record.mastery_level = score # Sync with UI selection
    record.status = "correct" if score == 2 else "wrong" # Basic status sync
    
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
    
    # Call AI with rich context
    result = await ai_service.generate_similar_problems(
        original_latex=latex, 
        knowledge_points=kps, 
        difficulty=difficulty,
        knowledge_path_name=knowledge_path_name
    )
    
    # Extract problems from result
    similar_problems = result.get("problems", [])
    
    saved_problems = []
    for sp in similar_problems:
        new_prob = PracticeProblem(
            user_id=current_user.id,
            latex_content=sp.get("latex", ""),
            difficulty=difficulty,
            knowledge_path=problem.knowledge_path,
            ai_model=result.get("ai_model", "Utility Model"),
            source_problem_id=problem.id,
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
    for sp in saved_problems:
        db.refresh(sp)
        
    # We return the schemas so frontend receives the newly generated DB IDs.
    return saved_problems

@router.get("/problems/{problem_id}/similar")
def get_similar_practice(problem_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetches previously generated practice problems linked to a specific source problem."""
    # Ensure source problem is owned by user (or at least the children are)
    practice_problems = db.query(PracticeProblem).filter(
        PracticeProblem.source_problem_id == problem_id,
        PracticeProblem.user_id == current_user.id
    ).order_by(PracticeProblem.created_at.asc()).all()
    
    # We can return them directly since their structure maps well to the frontend expectations 
    return practice_problems

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
        feedback = await ai_service.analyze_solution(problem_latex, standard_solution, file_location)
    except Exception as e:
        print(f"AI Practice Analysis failed: {e}")
        feedback = {"score": 0, "error": str(e)}
        
    # Return directly, no need to clutter DB with solution attempts for practice
    return {"feedback_json": feedback}

@router.post("/problems/{problem_id}/submit_solution")
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
        feedback = await ai_service.analyze_solution(problem_latex, standard_solution, file_location)
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        feedback = {"score": 0, "error": str(e)}
        
    # Save Attempt
    attempt = SolutionAttempt(
        problem_id=problem_id,
        user_id=current_user.id,
        image_path=safe_filename,
        feedback_json=feedback
    )
    db.add(attempt)
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
async def get_today_reviews(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from datetime import datetime
    from sqlalchemy import and_, or_
    import random
    
    today = datetime.utcnow()
    
    # 1. Query problems due for review
    # We join Problem with LearningRecord to find due items
    due_records = db.query(LearningRecord).join(Problem).filter(
        and_(
            LearningRecord.user_id == current_user.id,
            LearningRecord.review_date <= today
        )
    ).all()
    
    if not due_records:
        return []

    # 2. Extract problem data with rich context
    raw_list = []
    for rec in due_records:
        p = rec.problem
        item = {
            "id": p.id,
            "latex_content": p.latex_content,
            "difficulty": p.difficulty,
            "knowledge_path": p.knowledge_path,
            "ai_analysis": p.ai_analysis,
            "ai_model": p.ai_model,
            "ease_factor": rec.ease_factor,
            # If ease_factor is high (e.g. > 2.8), suggest a variant instead of the original
            "trigger_variant": rec.ease_factor >= 2.8
        }
        raw_list.append(item)

    # 3. Intelligent Shuffling & Grouping
    # Group by knowledge_path
    by_kp = {}
    for item in raw_list:
        kp = item["knowledge_path"] or "unknown"
        if kp not in by_kp:
            by_kp[kp] = []
        by_kp[kp].append(item)
    
    # Interleave them to avoid same KP appearing > 3 times consecutively
    final_selection = []
    kps = list(by_kp.keys())
    
    while kps and len(final_selection) < 15:
        # Pick a random KP that wasn't just used 3 times
        # (Simplified: just shuffle the list of KPs and pull one)
        random.shuffle(kps)
        target_kp = kps[0]
        
        # Add up to 1-2 items from this KP then rotate
        batch_size = min(len(by_kp[target_kp]), random.randint(1, 2))
        for _ in range(batch_size):
            if len(final_selection) < 15:
                final_selection.append(by_kp[target_kp].pop(0))
        
        if not by_kp[target_kp]:
            kps.remove(target_kp)

    return final_selection

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
