"""
routers/reviews.py
------------------
MathRob API - 复习系统路由。

从原 api.py（3140 行单文件）拆分而来，零行为变更。
涵盖：每日复习生成、复习历史、每日个性化练习生成。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import random

from ..database import get_db
from ..models import (Problem, KnowledgeNode, LearningRecord, User,
                      DailyReview, UserKnowledgeMastery)
from ..services.upload_service import get_accessible_image_url
from ..auth_deps import get_current_user
from ._common import ai_service

router = APIRouter(dependencies=[Depends(get_current_user)])


class DailyReviewSchema(BaseModel):
    id: int
    review_date: str
    problem_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MasteryUpdateSchema(BaseModel):
    mastery_level: int


@router.get("/reviews/today")
def get_today_reviews(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get problems due for review today with rich formatting for the review page.
    """
    from sqlalchemy import and_, or_

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
                        "image_path": get_accessible_image_url(p.image_path),
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
            "image_path": get_accessible_image_url(p.image_path),
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
                db.flush()  # Flush to get the ID
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
            pass  # Keep going with whatever problems we did find

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
