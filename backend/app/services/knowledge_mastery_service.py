"""
Knowledge Mastery Weighted Calculation Service

This module provides functions to update user knowledge mastery based on exam results
using a weighted moving average algorithm that accounts for exam type importance.
"""

import logging
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from ..models import UserKnowledgeMastery, ExamType

logger = logging.getLogger(__name__)

# Weight coefficients for different exam types
EXAM_TYPE_WEIGHTS = {
    ExamType.CUSTOM: 1.0,           # 日常练习
    ExamType.DIAGNOSTIC: 2.0,       # 摸底评测
    ExamType.MIDTERM: 3.0,          # 期中评测
    ExamType.FINAL: 3.0,            # 期末评测
}


def get_weight_for_exam_type(exam_type: ExamType) -> float:
    """
    Get the weight coefficient for a given exam type.
    
    Args:
        exam_type: ExamType enum value
        
    Returns:
        Weight coefficient (float)
        
    Raises:
        ValueError: If exam type not found in weights mapping
    """
    if exam_type not in EXAM_TYPE_WEIGHTS:
        raise ValueError(f"Unknown exam type: {exam_type}")
    
    return EXAM_TYPE_WEIGHTS[exam_type]


def calculate_weighted_mastery(
    db: Session,
    user_id: int,
    knowledge_tag: str,
    new_score: float,
    max_score: float,
    exam_type: ExamType
) -> Tuple[float, float]:
    """
    Calculate and update weighted mastery score for a knowledge point.
    
    Uses a weighted moving average algorithm:
    - If no prior record: use new score directly
    - If prior record exists: weighted_avg = (current_score * current_weight + new_score * exam_weight) / (current_weight + exam_weight)
    
    Args:
        db: SQLAlchemy session
        user_id: User ID
        knowledge_tag: Knowledge point name
        new_score: Score achieved in current exam (0-100, or 0-max_score)
        max_score: Maximum score for the problem
        exam_type: Type of exam (determines weight)
        
    Returns:
        Tuple of (new_ai_assessed_rating, new_total_weight)
    """
    if max_score <= 0:
        raise ValueError(f"max_score must be > 0, got {max_score}")
    
    # Normalize new score to 0-10 scale (AI assessment scale)
    normalized_new_score = round((new_score / max_score) * 10, 2)
    
    # Get exam type weight
    exam_weight = get_weight_for_exam_type(exam_type)
    
    # Fetch existing mastery record
    mastery_record: Optional[UserKnowledgeMastery] = (
        db.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.user_id == user_id,
            UserKnowledgeMastery.knowledge_tag == knowledge_tag
        ).first()
    )
    
    if not mastery_record:
        # New knowledge point: direct assignment
        new_rating = normalized_new_score
        new_total_weight = exam_weight
        logger.info(
            f"[NewMastery] User {user_id}, Tag '{knowledge_tag}': "
            f"Initial rating={new_rating:.2f}, weight={new_total_weight:.2f}"
        )
    else:
        # Existing knowledge point: weighted moving average
        current_rating = mastery_record.ai_assessed_rating or 0.0
        current_weight = mastery_record.total_weight or 0.0
        
        if current_weight == 0:
            # Fallback to direct assignment if weight is 0
            new_rating = normalized_new_score
            new_total_weight = exam_weight
        else:
            # Weighted average formula
            weighted_sum = (current_rating * current_weight) + (normalized_new_score * exam_weight)
            new_total_weight = current_weight + exam_weight
            new_rating = round(weighted_sum / new_total_weight, 2)
        
        logger.info(
            f"[UpdateMastery] User {user_id}, Tag '{knowledge_tag}': "
            f"Previous: rating={current_rating:.2f}, weight={current_weight:.2f} | "
            f"New Score: {normalized_new_score:.2f} (raw: {new_score}/{max_score}), exam_weight={exam_weight} | "
            f"Updated: rating={new_rating:.2f}, total_weight={new_total_weight:.2f}"
        )
    
    return new_rating, new_total_weight


def update_user_knowledge_mastery(
    db: Session,
    user_id: int,
    knowledge_tag: str,
    new_score: float,
    max_score: float,
    exam_type: ExamType
) -> Optional[UserKnowledgeMastery]:
    """
    Update user knowledge mastery record in the database using weighted algorithm.
    
    This function:
    1. Calculates the new weighted rating and total weight
    2. Updates or creates the mastery record
    3. Commits changes to database
    
    Args:
        db: SQLAlchemy session
        user_id: User ID
        knowledge_tag: Knowledge point name
        new_score: Score achieved in current exam
        max_score: Maximum score for the problem
        exam_type: Type of exam (for weight calculation)
        
    Returns:
        Updated or created UserKnowledgeMastery record
        
    Raises:
        ValueError: If parameters are invalid
    """
    if max_score <= 0:
        raise ValueError(f"max_score must be positive, got {max_score}")
    
    # Calculate new values using weighted algorithm
    new_rating, new_total_weight = calculate_weighted_mastery(
        db=db,
        user_id=user_id,
        knowledge_tag=knowledge_tag,
        new_score=new_score,
        max_score=max_score,
        exam_type=exam_type
    )
    
    # Fetch or create mastery record
    mastery_record: Optional[UserKnowledgeMastery] = (
        db.query(UserKnowledgeMastery).filter(
            UserKnowledgeMastery.user_id == user_id,
            UserKnowledgeMastery.knowledge_tag == knowledge_tag
        ).first()
    )
    
    if mastery_record:
        # Update existing record
        mastery_record.ai_assessed_rating = new_rating
        mastery_record.total_weight = new_total_weight
    else:
        # Create new record
        mastery_record = UserKnowledgeMastery(
            user_id=user_id,
            knowledge_tag=knowledge_tag,
            ai_assessed_rating=new_rating,
            total_weight=new_total_weight,
            comprehensive_score=new_rating  # Initialize comprehensive score with AI rating
        )
        db.add(mastery_record)
    
    db.flush()
    
    logger.info(
        f"[DBUpdate] User {user_id}, Tag '{knowledge_tag}': "
        f"Persisted rating={new_rating:.2f}, weight={new_total_weight:.2f}"
    )
    
    return mastery_record


def batch_update_knowledge_mastery(
    db: Session,
    user_id: int,
    problems: list,
    exam_type: ExamType,
    standard_tags_list: list
) -> dict:
    """
    Batch update knowledge mastery for multiple problems from a single exam.
    
    Args:
        db: SQLAlchemy session
        user_id: User ID
        problems: List of problem dicts with keys: problem_number, score, max_score, knowledge_tag
        exam_type: Type of the exam
        standard_tags_list: List of valid knowledge tags (for filtering)
        
    Returns:
        Dict with summary of updates:
        {
            'total_problems': int,
            'updated_mastery_count': int,
            'skipped': list of reasons,
            'exam_weight': float,
            'mastery_updates': list of tuples (knowledge_tag, new_rating, new_weight)
        }
    """
    updates_summary = {
        'total_problems': len(problems),
        'updated_mastery_count': 0,
        'skipped': [],
        'exam_weight': get_weight_for_exam_type(exam_type),
        'mastery_updates': []
    }
    
    for problem in problems:
        knowledge_tag = problem.get('knowledge_tag', '未知')
        score = problem.get('score', 0)
        max_score = problem.get('max_score', 10)
        problem_num = problem.get('problem_number', '?')
        
        # Validation checks
        if not knowledge_tag or knowledge_tag not in standard_tags_list:
            updates_summary['skipped'].append(
                f"Problem {problem_num}: Invalid or unknown tag '{knowledge_tag}'"
            )
            continue
        
        if max_score <= 0:
            updates_summary['skipped'].append(
                f"Problem {problem_num}: Invalid max_score {max_score}"
            )
            continue
        
        # Update mastery for this problem
        try:
            mastery_record = update_user_knowledge_mastery(
                db=db,
                user_id=user_id,
                knowledge_tag=knowledge_tag,
                new_score=score,
                max_score=max_score,
                exam_type=exam_type
            )
            
            updates_summary['updated_mastery_count'] += 1
            updates_summary['mastery_updates'].append((
                knowledge_tag,
                mastery_record.ai_assessed_rating,
                mastery_record.total_weight
            ))
            
        except Exception as e:
            updates_summary['skipped'].append(
                f"Problem {problem_num}, Tag '{knowledge_tag}': {str(e)}"
            )
            logger.error(f"Failed to update mastery for {knowledge_tag}: {e}")
    
    logger.info(
        f"[BatchUpdate] User {user_id}: Updated {updates_summary['updated_mastery_count']}/{updates_summary['total_problems']} mastery records. "
        f"Exam weight: {updates_summary['exam_weight']}"
    )
    
    return updates_summary
