"""
从 api.py 拆分出的题目管理路由 (Problems Router)。

包含以下端点组：
- 题目列表与详情 (get_problems / get_wrong_problems / get_problem)
- 知识节点与掌握度 (knowledge-nodes / update_mastery)
- 每日复习 (daily-review)
- 复习打分 (review_problem)
- 重新分析 (reanalyze_problem)
- 相似题练习 (generate / get similar practice)
- 练习历史与会话详情 (practice history / session detail)
- 练习题提交 (submit_practice_solution)
- 解答提交 (submit_solution / submit_homework)

所有函数体从原 api.py 原样照搬，保持零行为变更。
"""

# 1. 导入区
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import datetime, timedelta

from ..database import get_db
from ..models import (Problem, KnowledgePoint, KnowledgeNode, LearningRecord,
                      SolutionAttempt, User, PracticeProblem, PracticeSession,
                      UserProgress, UserKnowledgeMastery)
from ..services.ai_service import AIService, AIServiceException
from ..services.upload_service import upload_to_s3, get_accessible_image_url
from ..auth_deps import get_current_user
from ._common import (ai_service, _hydrate_problem_images,
                      SolutionAttemptSchema, ProblemSchema,
                      PaginatedProblemsResponse, KnowledgePointSchema)

# 2. 创建 router
router = APIRouter(dependencies=[Depends(get_current_user)])

# 3. 本地 schemas（在原文件中定义在端点附近的）
class KnowledgeNodeSchema(BaseModel):
    id: int
    name: str
    path: str
    class Config:
        from_attributes = True

class MasteryRequest(BaseModel):
    level: int

class PracticeSessionSchema(BaseModel):
    id: int
    source_problem_id: Optional[int] = None
    ai_model: Optional[str] = None
    problem_count: int
    created_at: datetime
    class Config:
        from_attributes = True

# 4. 所有端点函数，原样照搬，不做任何逻辑修改

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
        problem.image_path = get_accessible_image_url(problem.image_path)
        problems.append(problem)
        
    return problems


@router.get("/problems/wrong", response_model=PaginatedProblemsResponse)
def get_wrong_problems(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    mastery: Optional[int] = None,
    recent_days: Optional[int] = Query(default=None, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated wrong-answer notebook problems.

    Returns a standardized payload with pagination metadata for frontend pagination UI.
    """
    from datetime import timedelta
    from sqlalchemy import or_

    base_query = db.query(Problem, LearningRecord).outerjoin(
        LearningRecord,
        (Problem.id == LearningRecord.problem_id) & (LearningRecord.user_id == current_user.id)
    ).filter(
        Problem.user_id == current_user.id,
        or_(LearningRecord.id == None, LearningRecord.status != "correct")
    )

    if mastery is not None:
        base_query = base_query.filter(LearningRecord.mastery_level == mastery)

    if recent_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=recent_days)
        base_query = base_query.filter(LearningRecord.last_reviewed_at != None).filter(LearningRecord.last_reviewed_at >= cutoff)

    total_count = base_query.count()
    skip = (page - 1) * page_size

    results = base_query.order_by(Problem.created_at.desc()).offset(skip).limit(page_size).all()

    problems: List[Problem] = []
    for problem, record in results:
        problem.current_mastery_level = record.mastery_level if record else None
        problem.image_path = get_accessible_image_url(problem.image_path)
        problems.append(problem)

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return {
        "items": problems,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

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

    _hydrate_problem_images(problem)
        
    return problem

# Knowledge Nodes Endpoints (Using ltree paths)
from ..models import KnowledgeNode

@router.get("/knowledge-nodes", response_model=List[KnowledgeNodeSchema])
def get_knowledge_nodes(db: Session = Depends(get_db)):
    return db.query(KnowledgeNode).order_by(KnowledgeNode.path).all()


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
        # 注意：以下 prompt 字符串是历史遗留的死代码，不应在此处，保留以维持零行为变更
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
        
    saved_upload = upload_to_s3(file, prefix="practice-solutions")
        
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
        feedback_data = await ai_service.analyze_solution(problem_latex, standard_solution, saved_upload.s3_uri, target_id=problem_id, user_id=current_user.id)
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
        
    saved_upload = upload_to_s3(file, prefix="solutions")
        
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
        ai_response = await ai_service.analyze_solution(problem_latex, standard_solution, saved_upload.s3_uri, target_id=problem_id, user_id=current_user.id)
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
        image_path=saved_upload.public_url,
        ai_model_used=used_model,
        ai_score=feedback.get("score") if isinstance(feedback, dict) else None,
        ai_evaluation=feedback,
        feedback_json=feedback
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    attempt.image_path = get_accessible_image_url(attempt.image_path)
    
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
        
    saved_upload = upload_to_s3(file, prefix="homework")
        
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
        ai_response = await ai_service.analyze_solution(problem_latex, standard_solution, saved_upload.s3_uri, target_id=problem_id, user_id=current_user.id)
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
        image_path=saved_upload.public_url,
        ai_model_used=used_model,
        ai_score=feedback.get("score") if isinstance(feedback, dict) else None,
        ai_evaluation=feedback,
        formatting_feedback=feedback.get("formatting_feedback") if isinstance(feedback, dict) else None,
        feedback_json=feedback
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    attempt.image_path = get_accessible_image_url(attempt.image_path)
    
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
