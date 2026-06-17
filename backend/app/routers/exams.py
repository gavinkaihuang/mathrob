"""整卷智能批阅路由模块。

从原 api.py 拆分出的整卷批阅流水线相关代码：
- ExamSessionSchema 等本地 schema
- _sanitize_json_string / _extract_exam_structure / _grade_exam_batch /
  _generate_overall_feedback / _natural_sort_key / _normalize_paper_title /
  _is_similar_paper_title / _find_duplicate_exam_by_title 等辅助函数
- process_full_exam 核心异步流水线函数
- upload_and_grade_exam / exams_history / get_exam_status / exam_detail 路由端点

拆分原则：零行为变更，所有函数体原样照搬，仅做模块化整理。
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Union, Any
from pydantic import BaseModel
import os
import json
import re
import asyncio
from difflib import SequenceMatcher
from datetime import datetime

from ..database import get_db
from ..models import (Problem, KnowledgeNode, LearningRecord, SolutionAttempt,
                      User, ExamRecord, ExamProblemResult, UserKnowledgeMastery,
                      ExamType, SystemLog, OperationLog)
from ..services.ai_service import AIService, AIServiceException
from ..services.upload_service import upload_to_s3, get_accessible_image_url
from ..auth_deps import get_current_user
from ._common import ai_service

router = APIRouter(dependencies=[Depends(get_current_user)])


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
            img = ai_service._open_image_for_model(img_path)
            content.append(img)
        except Exception as e:
            print(f"Warning: failed to open answer image {img_path}: {e}")
    
    # Add question images second (with inline text labels)
    for i, img_path in enumerate(question_image_paths):
        try:
            img = ai_service._open_image_for_model(img_path)
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
            img = ai_service._open_image_for_model(img_path)
            content.append(img)
        except Exception as e:
            print(f"Warning: failed to open answer image {img_path}: {e}")
    
    # Add question images second (context only)
    for img_path in question_image_paths:
        try:
            img = ai_service._open_image_for_model(img_path)
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


def _normalize_paper_title(title: Optional[str]) -> str:
    if not title:
        return ""
    normalized = title.strip().lower()
    normalized = re.sub(r'\s+', '', normalized)
    normalized = re.sub(r'[\-—_·•,，。:：;；!！?？"“”\'‘’()（）\[\]{}<>《》]', '', normalized)
    return normalized


def _is_similar_paper_title(title_a: Optional[str], title_b: Optional[str]) -> bool:
    normalized_a = _normalize_paper_title(title_a)
    normalized_b = _normalize_paper_title(title_b)

    if not normalized_a or not normalized_b:
        return False

    if normalized_a == normalized_b:
        return True

    shorter, longer = (normalized_a, normalized_b) if len(normalized_a) <= len(normalized_b) else (normalized_b, normalized_a)
    if len(shorter) >= 6 and shorter in longer:
        return True

    return SequenceMatcher(None, normalized_a, normalized_b).ratio() >= 0.90


def _find_duplicate_exam_by_title(db: Session, user_id: int, paper_title: str, exclude_exam_id: Optional[int] = None):
    from ..models import ExamRecord

    if not paper_title:
        return None

    query = db.query(ExamRecord).filter(ExamRecord.user_id == user_id)
    if exclude_exam_id is not None:
        query = query.filter(ExamRecord.id != exclude_exam_id)

    candidates = query.order_by(ExamRecord.created_at.desc()).limit(200).all()
    for exam in candidates:
        if _is_similar_paper_title(paper_title, exam.paper_name or ""):
            return exam

    return None


async def process_full_exam(
    task_id: int, 
    user_id: int, 
    question_image_paths: List[str], 
    answer_image_paths: List[str],
    image_urls: List[str] = None,
    exam_mode: str = "separated",
    precomputed_question_numbers: Optional[List[str]] = None,
    precomputed_paper_title: Optional[str] = None,
    precomputed_stage1_model: Optional[str] = None
):
    """
    Two-Stage Exam Grading Pipeline with Image Separation & Dynamic Model Routing:
    Stage 1: Lightweight structure extraction (identify all question numbers from answer images)
    Stage 2: Parallel batch grading (2-3 questions per batch using asyncio.gather)
    Stage 3: Result aggregation, weighted knowledge mastery update, and database persistence
    
    CRITICAL: Database session is held ONLY during Stage 1 and Stage 3.
    During Stage 2 (long-running AI calls), the DB session is closed to prevent:
    - Connection timeouts from 5-10 minute AI requests
    - Database resource exhaustion
    - Firewall/proxy disconnection issues
    
    Key Improvements:
    - Dynamically routes to appropriate teaching model based on exam_type
    - Implements weighted moving average for knowledge mastery calculation
    - Explicitly separates question images from answer images
    - Lazy session pattern: DB connection only acquired when needed
    """
    from ..database import SessionLocal
    from ..models import ExamRecord, ExamProblemResult, KnowledgeNode, UserKnowledgeMastery, SystemLog, OperationLog, ExamType
    from ..main import ai_service
    from ..services.model_manager import model_manager
    from ..services.knowledge_mastery_service import batch_update_knowledge_mastery, get_weight_for_exam_type
    
    pipeline_start_time = datetime.utcnow()
    selected_teaching_model = None  # Will be set based on exam_type
    db = None  # Will be created when needed
    standard_tags_list = []  # Fetch early, before AI calls
    exam_type = None
    all_problems = []
    batch_models = []
    mastery_update_summary = {}
    
    try:
        # ============================================================
        # STAGE 1a: FETCH CONFIGURATION (Database only - quick)
        # Close DB immediately after fetching config
        # ============================================================
        db = SessionLocal()
        print(f"[Exam {task_id}] Stage 1a: Fetching exam configuration...")
        
        # FETCH EXAM RECORD & DETERMINE TEACHING MODEL
        exam = db.query(ExamRecord).filter(ExamRecord.id == task_id).first()
        if not exam:
            raise ValueError(f"Exam record {task_id} not found")
        
        exam_type = exam.exam_type or ExamType.CUSTOM
        print(f"[Exam {task_id}] Exam Type: {exam_type.value}")
        
        # Get the appropriate teaching model based on exam type
        try:
            selected_teaching_model = model_manager.get_teaching_model_for_exam_type(db, exam_type)
            print(f"[Exam {task_id}] Selected Teaching Model: {selected_teaching_model}")
        except Exception as e:
            print(f"[Exam {task_id}] ⚠️ Failed to fetch exam_type-specific model: {e}")
            selected_teaching_model = None
        
        # Get standard knowledge tags (fetch into memory BEFORE closing db)
        nodes = db.query(KnowledgeNode).all()
        standard_tags_list = [n.name for n in nodes]
        print(f"[Exam {task_id}] Fetched {len(standard_tags_list)} standard knowledge tags")
        
        # CLOSE DATABASE IMMEDIATELY after fetching config
        # This prevents holding a connection during long AI calls
        print(f"[Exam {task_id}] Closing DB session before Stage 1b (AI extraction)...")
        try:
            db.close()
        except Exception as e:
            print(f"[Exam {task_id}] Warning: Error closing DB after config fetch: {e}")
        db = None
        
        # ============================================================
        # STAGE 1b: STRUCTURE EXTRACTION (AI only - long-running)
        # Database connection is closed, preventing connection pooling issues
        # ============================================================
        print(f"[Exam {task_id}] Stage 1b: Extracting exam structure from {len(answer_image_paths)} answer images...")

        if precomputed_question_numbers is not None and precomputed_paper_title is not None:
            question_numbers = precomputed_question_numbers
            paper_title = precomputed_paper_title
            stage1_model_used = precomputed_stage1_model or "precomputed_stage1"
            structure = {
                "question_numbers": question_numbers,
                "paper_title": paper_title,
                "model": stage1_model_used
            }
            print(f"[Exam {task_id}] Stage 1b: Using precomputed structure from upload preflight")
        else:
            structure = await _extract_exam_structure(
                answer_image_paths=answer_image_paths,
                question_image_paths=question_image_paths,
                ai_service=ai_service
            )
            question_numbers = structure['question_numbers']
            paper_title = structure['paper_title']
        
        print(f"[Exam {task_id}] Stage 1b Complete: Found {len(question_numbers)} questions: {question_numbers}")
        
        if not question_numbers:
            raise ValueError("No questions detected in exam. OCR may have failed.")
        
        # ============================================================
        # Stage 1c: LOG EXTRACTION (Database only - post-AI)
        # Re-acquire DB session to log Stage 1 results
        # ============================================================
        print(f"[Exam {task_id}] Stage 1c: Re-acquiring DB session to log Stage 1 completion...")
        db = SessionLocal()
        
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
        
        # Attempt to commit with retry logic
        try:
            db.add(log_s1)
            db.commit()
            print(f"[Exam {task_id}] Stage 1 log saved successfully")
        except Exception as commit_error:
            print(f"[Exam {task_id}] ⚠️ Stage 1 commit failed: {commit_error}")
            try:
                db.rollback()
            except:
                pass
            # Reconnect and retry once
            print(f"[Exam {task_id}] Attempting to reconnect and retry...")
            try:
                db.close()
            except:
                pass
            db = SessionLocal()
            try:
                db.add(log_s1)
                db.commit()
                print(f"[Exam {task_id}] Stage 1 log saved successfully (after reconnect)")
            except Exception as retry_error:
                print(f"[Exam {task_id}] ⚠️ Stage 1 log save failed even after reconnect: {retry_error}")
                # Continue without logging - don't fail the entire pipeline
        
        # CLOSE DATABASE SESSION BEFORE STAGE 2
        # Stage 2 involves long-running AI calls (5-10 minutes)
        # Holding the DB connection open during this time risks:
        # - Connection timeouts and firewall disconnects
        # - Database resource exhaustion
        # Pattern: Lazy session - only hold connection when needed
        print(f"[Exam {task_id}] Closing DB session before Stage 2 to prevent long-held connections...")
        try:
            db.close()
        except Exception as e:
            print(f"[Exam {task_id}] Warning: Error closing DB after Stage 1: {e}")
        db = None  # Signal that session is closed
        
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
        
        # Limit concurrent AI calls to prevent connection pool exhaustion.
        # Each call_gemini_with_fallback briefly opens a DB session to fetch model/token
        # config; without a semaphore, all batches race at once and can saturate the pool.
        _batch_semaphore = asyncio.Semaphore(5)

        async def _bounded_batch(batch, idx):
            async with _batch_semaphore:
                return await _grade_exam_batch(
                    batch_numbers=batch,
                    question_image_paths=question_image_paths,
                    answer_image_paths=answer_image_paths,
                    standard_tags_list=standard_tags_list,
                    ai_service=ai_service,
                    batch_index=idx,
                    total_batches=len(batches)
                )

        batch_tasks = [_bounded_batch(batch, idx) for idx, batch in enumerate(batches)]
        
        # Execute all batches concurrently (max 5 at a time)
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
        
        # DO NOT log Stage 2 yet - wait until DB session is re-acquired in Stage 3
        # This keeps DB connection closed during the longest AI processing phase
        
        # ============================================================
        # STAGE 3: RESULT AGGREGATION & DATABASE PERSISTENCE
        # Re-acquire DB session for persistence operations only
        # ============================================================
        # All batch AI calls are done. Generate overall feedback BEFORE opening DB
        # so we don't hold a connection during another 1-3 min AI call.
        # Calculate total score first (needed by _generate_overall_feedback).
        total_score = sum(p.get('score', 0) for p in all_problems)
        print(f"[Exam {task_id}] Stage 3: Generating overall feedback (before DB open)...")
        overall_feedback = await _generate_overall_feedback(
            all_problems=all_problems,
            paper_title=paper_title,
            total_score=total_score,
            ai_service=ai_service
        )
        
        # All AI calls are now complete. Re-acquire DB connection for data persistence.
        db = SessionLocal()
        print(f"[Exam {task_id}] Stage 3: Re-acquired DB session for persistence layer")
        
        # Now log Stage 2 completion
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
        try:
            db.add(log_s2)
            db.commit()
        except Exception as e:
            print(f"[Exam {task_id}] ⚠️ Stage 2 log commit failed: {e}")
            try:
                db.rollback()
            except:
                pass
            # Don't fail the pipeline for logging errors
        
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
        
        # Persist exam record and results
        print(f"[Exam {task_id}] Stage 3: Aggregating results and saving to database...")
        
        exam = db.query(ExamRecord).filter(ExamRecord.id == task_id).first()
        if not exam:
            raise ValueError(f"Exam record {task_id} not found")
        
        # Set basic exam info
        exam.paper_name = paper_title
        exam.image_urls = image_urls
        
        # total_score and overall_feedback were computed before DB open (no AI call while holding connection)
        exam.total_score = total_score
        
        # Use the first batch model or the latest
        exam.ai_model = batch_models[0] if batch_models else "unknown"
        
        exam.overall_feedback = overall_feedback
        exam.overall_evaluation = f"Graded via two-stage pipeline on {datetime.utcnow().isoformat()}"
        exam.status = "completed"
        exam.completed_at = datetime.utcnow()
        
        # Persist the actual teaching model used in this exam
        if selected_teaching_model:
            exam.ai_model = selected_teaching_model
        else:
            exam.ai_model = batch_models[0] if batch_models else "unknown"
        
        # Build all problem objects in memory, then bulk-insert in one call.
        # This avoids N round-trips to Postgres (one per problem) and dramatically
        # reduces the time the DB session is held open.
        problem_objects = []
        for p in all_problems:
            if not p.get('problem_number'):
                continue
            problem_objects.append(ExamProblemResult(
                exam_id=exam.id,
                problem_number=str(p.get("problem_number", "未知")),
                score=p.get("score", 0),
                max_score=p.get("max_score", 10),
                knowledge_tag=p.get("knowledge_tag", "未知"),
                feedback=p.get("feedback", ""),
                original_question_text=p.get("original_question_text", None),
                user_answer_text=p.get("user_answer_text", None)
            ))
        problem_save_count = len(problem_objects)
        
        # Flush problem results (single bulk operation)
        try:
            db.bulk_save_objects(problem_objects)
            db.flush()
        except Exception as flush_error:
            print(f"[Exam {task_id}] ⚠️ Bulk flush error (connection may have been dropped): {flush_error}")
            try:
                db.rollback()
            except:
                pass
            try:
                db.close()
            except:
                pass
            db = SessionLocal()
            print(f"[Exam {task_id}] Reconnected after flush error, retrying bulk insert")
            db.bulk_save_objects(problem_objects)
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
        
        # Final commit with error handling
        try:
            db.commit()
        except Exception as commit_error:
            print(f"[Exam {task_id}] ⚠️ Final commit failed: {commit_error}")
            try:
                db.rollback()
            except:
                pass
            # Re-raise to trigger the except block for error logging
            raise
        
        pipeline_duration = (datetime.utcnow() - pipeline_start_time).total_seconds()

        # Business operation log (frontend-facing): write with short-lived session only.
        # Do NOT reuse the long-lived pipeline DB session to avoid pool pressure.
        operation_details = {
            "exam_id": task_id,
            "exam_type": exam_type.value if exam_type else "custom",
            "exam_mode": exam_mode,
            "model_used": selected_teaching_model or (batch_models[0] if batch_models else "unknown"),
            "weight_applied": mastery_update_summary.get("exam_weight", 1.0),
            "total_problems": len(all_problems),
            "cost_time_ms": round(pipeline_duration * 1000, 2)
        }
        try:
            with SessionLocal() as op_db:
                op_log = OperationLog(
                    user_id=user_id,
                    action_type="整卷智能批阅",
                    status="success",
                    details=operation_details,
                    created_at=datetime.utcnow()
                )
                op_db.add(op_log)
                op_db.commit()
        except Exception as op_log_error:
            print(f"[Exam {task_id}] ⚠️ Failed to write operation log: {op_log_error}")
        
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

        pipeline_duration = (datetime.utcnow() - pipeline_start_time).total_seconds()
        try:
            if exam_type:
                failure_weight_applied = get_weight_for_exam_type(exam_type)
            else:
                failure_weight_applied = 1.0
        except Exception:
            failure_weight_applied = 1.0

        failed_operation_details = {
            "exam_id": task_id,
            "exam_type": exam_type.value if exam_type else "custom",
            "exam_mode": exam_mode,
            "model_used": selected_teaching_model or (batch_models[0] if batch_models else "unknown"),
            "weight_applied": failure_weight_applied,
            "total_problems": len(all_problems),
            "cost_time_ms": round(pipeline_duration * 1000, 2),
            "error": str(e)
        }

        # Business operation log for failure (frontend-facing) with short-lived session
        try:
            with SessionLocal() as op_db:
                op_log = OperationLog(
                    user_id=user_id,
                    action_type="整卷智能批阅",
                    status="failed",
                    details=failed_operation_details,
                    created_at=datetime.utcnow()
                )
                op_db.add(op_log)
                op_db.commit()
        except Exception as op_log_error:
            print(f"[Exam {task_id}] ⚠️ Failed to write failed operation log: {op_log_error}")
        
        # Try to update exam status and log error
        # Note: db session may be None if error occurred during Stage 2 (AI calls)
        try:
            if db is None:
                print(f"[Exam {task_id}] DB session was None during error - creating new session for error logging")
                db = SessionLocal()
            
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
        except Exception as db_error:
            print(f"[Exam {task_id}] Error updating exam status: {db_error}")
            try:
                if db:
                    db.rollback()
            except:
                pass
    
    finally:
        try:
            if db:
                db.close()
                print(f"[Exam {task_id}] DB session closed successfully")
        except Exception as cleanup_error:
            print(f"[Exam {task_id}] Error closing DB session: {cleanup_error}")


@router.post("/exams/upload_and_grade")
async def upload_and_grade_exam(
    background_tasks: BackgroundTasks,
    exam_mode: str = Form('separated'),
    exam_type: str = Form('custom'),
    force_regrade: bool = Form(False),
    existing_exam_id: Optional[int] = Form(None),
    question_images: List[UploadFile] = File(default=[]),
    answer_images: List[UploadFile] = File(default=[]),
    combined_images: List[UploadFile] = File(default=[]),
    paper_name: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import ExamRecord, ExamProblemResult
    from ..main import ai_service as main_ai_service
    
    question_image_paths = []
    answer_image_paths = []
    combined_image_paths = []
    all_image_urls = []

    if exam_mode == 'separated':
        # ============================================================
        # SEPARATED MODE: Process question and answer images separately
        # ============================================================
        
        # Save question images
        for file in question_images:
            saved_upload = upload_to_s3(file, prefix="exams")
            question_image_paths.append(saved_upload.s3_uri)
            all_image_urls.append(saved_upload.public_url)

        # Save answer images
        for file in answer_images:
            saved_upload = upload_to_s3(file, prefix="exams")
            answer_image_paths.append(saved_upload.s3_uri)
            all_image_urls.append(saved_upload.public_url)
    
    elif exam_mode == 'combined':
        # ============================================================
        # COMBINED MODE: Process all images as combined (卷面作答)
        # ============================================================
        
        # Save combined mode images
        for file in combined_images:
            saved_upload = upload_to_s3(file, prefix="exams")
            combined_image_paths.append(saved_upload.s3_uri)
            all_image_urls.append(saved_upload.public_url)
        
        # For combined mode, treat combined images as both question and answer
        question_image_paths = combined_image_paths
        answer_image_paths = combined_image_paths
        
    else:
        raise ValueError(f"Invalid exam_mode: {exam_mode}")
        
    # Convert exam_type string to ExamType enum
    from ..models import ExamType
    try:
        exam_type_enum = ExamType[exam_type.upper()]
    except (KeyError, AttributeError):
        exam_type_enum = ExamType.CUSTOM

    # Stage 1 preflight: extract title/question numbers first, then run duplicate interception.
    # This avoids launching expensive map-reduce grading when same paper was already graded.
    try:
        structure = await _extract_exam_structure(
            answer_image_paths=answer_image_paths,
            question_image_paths=question_image_paths,
            ai_service=main_ai_service
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"试卷结构识别失败，请重试: {str(e)}")

    extracted_paper_title = (structure.get("paper_title") or paper_name or f"摸底测试_{datetime.utcnow().strftime('%Y%m%d_%H%M')}").strip()
    extracted_question_numbers = structure.get("question_numbers", [])
    extracted_stage1_model = structure.get("model", "unknown")

    duplicate_exam = _find_duplicate_exam_by_title(
        db=db,
        user_id=current_user.id,
        paper_title=extracted_paper_title
    )

    if duplicate_exam and not force_regrade:
        return {
            "status": "duplicate_found",
            "existing_exam_id": duplicate_exam.id,
            "title": duplicate_exam.paper_name or extracted_paper_title
        }

    exam_record = None
    target_exam = None

    # Force regrade path: update existing record in place (do not insert a new row)
    if force_regrade:
        if existing_exam_id is not None:
            target_exam = db.query(ExamRecord).filter(
                ExamRecord.id == existing_exam_id,
                ExamRecord.user_id == current_user.id
            ).first()
            if not target_exam:
                raise HTTPException(status_code=404, detail="指定的历史试卷不存在")
        elif duplicate_exam is not None:
            target_exam = duplicate_exam

    if target_exam:
        db.query(ExamProblemResult).filter(ExamProblemResult.exam_id == target_exam.id).delete(synchronize_session=False)

        target_exam.status = "processing"
        target_exam.exam_type = exam_type_enum
        target_exam.image_paths = question_image_paths + answer_image_paths
        target_exam.image_urls = all_image_urls
        target_exam.paper_name = extracted_paper_title
        target_exam.total_score = None
        target_exam.overall_feedback = None
        target_exam.overall_evaluation = None
        target_exam.ai_model = None
        target_exam.completed_at = None

        db.commit()
        db.refresh(target_exam)
        exam_record = target_exam
    else:
        exam_record = ExamRecord(
            user_id=current_user.id,
            status="processing",
            exam_type=exam_type_enum,
            image_paths=question_image_paths + answer_image_paths,
            image_urls=all_image_urls,
            paper_name=extracted_paper_title
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
        image_urls=all_image_urls,
        exam_mode=exam_mode,
        precomputed_question_numbers=extracted_question_numbers,
        precomputed_paper_title=extracted_paper_title,
        precomputed_stage1_model=extracted_stage1_model
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
    from ..database import db_retry, engine
    from sqlalchemy.exc import OperationalError
    
    # Wrap all DB operations with retry to handle transient connection drops
    # This endpoint is polled every 3-5 seconds during long exam processing
    try:
        @db_retry
        def _fetch_exam():
            return db.query(ExamRecord).filter(
                ExamRecord.id == task_id,
                ExamRecord.user_id == current_user.id
            ).first()
        
        exam = _fetch_exam()
    except OperationalError:
        engine.dispose()
        raise HTTPException(status_code=503, detail="Database connection temporarily unavailable, please retry")
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    response = {
        "exam_id": exam.id,
        "id": exam.id,
        "status": exam.status,
        "total_score": exam.total_score,
        "overall_evaluation": exam.overall_evaluation,
        "image_urls": [get_accessible_image_url(url) for url in (exam.image_urls or [])],
        "created_at": exam.created_at,
        "results": []
    }
    
    if exam.status == "completed":
        try:
            @db_retry
            def _fetch_results():
                return db.query(ExamProblemResult).filter(ExamProblemResult.exam_id == exam.id).all()
            
            results = _fetch_results()
        except OperationalError:
            engine.dispose()
            raise HTTPException(status_code=503, detail="Database connection temporarily unavailable, please retry")
        
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
        'image_urls': [get_accessible_image_url(url) for url in (exam.image_urls or [])],
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

