"""
routers/assessment.py
---------------------
MathRob API - 诊断评测路由。

从原 api.py（3140 行单文件）拆分而来，零行为变更。
涵盖：评测状态查询、诊断试卷生成、整卷提交批改、
诊断测试生成、会话查询、单题提交批改、评测终结。
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Union, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import asyncio

from ..database import get_db
from ..models import (Problem, KnowledgeNode, LearningRecord, SolutionAttempt,
                      User, PracticeProblem, PracticeSession, UserProgress,
                      UserKnowledgeMastery, AssessmentSession, AssessmentProblem,
                      ExamType)
from ..services.ai_service import AIService, AIServiceException
from ..services.upload_service import upload_to_s3, get_accessible_image_url
from ..auth_deps import get_current_user
from ._common import ai_service

router = APIRouter(dependencies=[Depends(get_current_user)])


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
    image_paths = []
    paper_image_urls = []
    for i, file in enumerate(files):
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        saved_upload = upload_to_s3(file, prefix=f"assessments/{session_id}")
        image_paths.append(saved_upload.s3_uri)
        paper_image_urls.append(saved_upload.public_url)

    if not image_paths:
        raise HTTPException(status_code=400, detail="请至少上传一张答卷图片")

    # 2. Call AI to grade
    from ..main import ai_service
    try:
        grading_result = await ai_service.grade_full_paper(
            paper_snapshot=session.paper_snapshot,
            image_paths=image_paths,
            session_id=session_id,
            user_id=current_user.id,
            exam_type="DIAGNOSTIC",
            exam_mode="combined",
            weight_applied=1.0
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
    session.paper_image_paths = paper_image_urls
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
        
    saved_upload = upload_to_s3(file, prefix=f"assessments/{session_id}/problems/{problem_id}")
        
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
        ai_response = await ai_service.analyze_solution(problem_latex, standard_solution, saved_upload.s3_uri, target_id=problem.id, user_id=current_user.id)
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
    ap.image_path = saved_upload.public_url
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
