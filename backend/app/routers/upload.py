from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import shutil
import os
import uuid
from typing import Optional
from ..database import get_db
from ..models import Problem, DifficultyLevel
from ..services.ai_service import AIService
from datetime import datetime

router = APIRouter()
ai_service = AIService()

UPLOAD_DIR = "uploads"
# Ensure absolute path for robustness or relative to running location
# For now, relative to where uvicorn runs is safer if consistent
# But let's verify if 'uploads' exists in root or backend/uploads.
# We created backend/uploads manually.
SCAN_DATA_DIR = "./backend/uploads"
if not os.path.exists(SCAN_DATA_DIR):
    os.makedirs(SCAN_DATA_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Generate unique filename
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(SCAN_DATA_DIR, unique_filename)
    
    # 2. Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # 3. Call AI Service (Immediate processing)
    try:
        # Note: analyze_image is async
        analysis_result = await ai_service.analyze_image(file_path)
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        analysis_result = {
            "latex_content": "\\text{Analysis Failed}",
            "ai_analysis": {"error": str(e)},
            "difficulty": 1,
            "knowledge_points": []
        }

    # 4. Save to Database
    # Merge knowledge_points into ai_analysis since we don't have a dedicated column yet
    ai_data = analysis_result.get("ai_analysis", {})
    if "knowledge_points" in analysis_result:
        ai_data["knowledge_points"] = analysis_result["knowledge_points"]

    new_problem = Problem(
        user_id=current_user.id,
        image_path=file_path,
        latex_content=analysis_result.get("latex_content"),
        ai_analysis=ai_data,
        difficulty=analysis_result.get("difficulty", 1),
        created_at=datetime.utcnow()
    )
    
    db.add(new_problem)
    db.commit()
    db.refresh(new_problem)
    
    return {"id": new_problem.id, "message": "File processed successfully"}
