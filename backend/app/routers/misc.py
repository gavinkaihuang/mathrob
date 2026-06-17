"""
routers/misc.py
--------------
MathRob API - 杂项路由：周报、学习进度、日志、解题尝试管理。

从原 api.py（3140 行单文件）拆分而来，零行为变更。
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from pydantic import BaseModel

from ..database import get_db
from ..models import (Problem, SolutionAttempt, User, WeeklyReport,
                      UserProgress, APICallLog, SystemLog)
from ..services.ai_service import AIService, AIServiceException
from ..services.upload_service import upload_to_s3, delete_uploaded_object, get_accessible_image_url
from ..services.report_service import ReportService
from ..auth_deps import get_current_user
from ._common import (ai_service, UPLOAD_DIR, SolutionAttemptSchema,
                      APICallLogSchema)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ---------------------------------------------------------------------------
# 解题尝试管理 (Solution Attempts)
# ---------------------------------------------------------------------------

@router.delete("/solution-attempts/{attempt_id}")
async def delete_solution_attempt(attempt_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attempt = db.query(SolutionAttempt).filter(SolutionAttempt.id == attempt_id, SolutionAttempt.user_id == current_user.id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Solution attempt not found")

    # Optional: Delete file from disk
    try:
        if attempt.image_path:
            delete_uploaded_object(attempt.image_path)
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

    file_location = attempt.image_path
    if file_location and not (
        file_location.startswith("s3://")
        or file_location.startswith("http://")
        or file_location.startswith("https://")
        or os.path.isabs(file_location)
    ):
        file_location = os.path.join(UPLOAD_DIR, file_location)

    if not file_location:
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
        ai_response = await ai_service.analyze_solution(problem_latex, standard_solution, file_location, target_id=problem.id, user_id=current_user.id)
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
    attempt.image_path = get_accessible_image_url(attempt.image_path)

    return attempt


# ---------------------------------------------------------------------------
# 周报 (Reports)
# ---------------------------------------------------------------------------

@router.post("/reports/generate")
def generate_weekly_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ReportService(db)
    try:
        report = service.generate_weekly_report(user_id=current_user.id)
        return report
    except Exception as e:
        print(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    file_path = os.path.join(base_path, report.pdf_path)  # report.pdf_path includes "reports/" prefix

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(file_path, filename=os.path.basename(file_path), media_type='application/pdf')


# ---------------------------------------------------------------------------
# 学习进度 (Progress)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 日志 (Logs)
# ---------------------------------------------------------------------------

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
