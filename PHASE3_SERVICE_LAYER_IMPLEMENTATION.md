"""
=============================================================================
MathRob 整卷批阅服务层核心重构 - Phase 3 实现指南
=============================================================================

本文档展示了整卷批阅系统的核心改动，包括：
1. 动态模型路由（根据 exam_type）
2. 加权知识点掌握度计算算法
3. 服务层架构设计

=============================================================================
"""

# ============================================================================
# 1. 动态模型路由机制
# ============================================================================

"""
在 process_full_exam() 函数中，根据 exam 的 exam_type 字段动态选择教学模型。

执行流程：
  1. 从 database 获取 ExamRecord
  2. 读取 exam.exam_type （ExamType.CUSTOM | DIAGNOSTIC | MIDTERM | FINAL）
  3. 调用 model_manager.get_teaching_model_for_exam_type(db, exam_type)
  4. 根据 exam_type：
     - CUSTOM          → 使用 【日常批改模型】(Routine Teaching）
     - DIAGNOSTIC      → 使用 【高阶评测模型】(Advanced Assessment）
     - MIDTERM/FINAL   → 使用 【高阶评测模型】(Advanced Assessment）
  5. 将实际使用的模型名称保存到 exam.ai_model
"""

# 核心代码片段（来自 api.py process_full_exam）：
"""
    # Fetch exam and determine teaching model
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
        selected_teaching_model = None
    
    # [... grading pipeline stages ...]
    
    # Persist the actual teaching model used in this exam
    if selected_teaching_model:
        exam.ai_model = selected_teaching_model
    else:
        exam.ai_model = batch_models[0] if batch_models else "unknown"
    
    db.commit()
"""

# model_manager 实现（来自 services/model_manager.py）：
"""
def get_teaching_model_for_exam_type(self, db: Session, exam_type: ExamType) -> str:
    \"\"\"
    根据试卷类型动态选择模型。
    
    Logic:
    - exam_type == CUSTOM → routine_teaching（日常批改模型，推荐 Flash）
    - exam_type in [DIAGNOSTIC, MIDTERM, FINAL] → advanced_assessment（高阶评测模型，推荐 Pro）
    \"\"\"
    if exam_type == ExamType.CUSTOM:
        role = "routine_teaching"
    elif exam_type in [ExamType.DIAGNOSTIC, ExamType.MIDTERM, ExamType.FINAL]:
        role = "advanced_assessment"
    else:
        raise ValueError(f"Unknown exam type: {exam_type}")
    
    config = db.query(ModelConfig).filter(ModelConfig.role == role).first()
    if not config:
        raise ValueError(f"No model configuration found for role: '{role}'")
    
    logger.info(f"[ModelManager] Selected {role} model for exam_type: {exam_type.value}")
    return config.model_name
"""


# ============================================================================
# 2. 加权知识点掌握度计算算法
# ============================================================================

"""
核心算法：加权移动平均 (Weighted Moving Average)

权重系数定义（根据试卷类型）：
  - CUSTOM (日常练习)：       W = 1.0
  - DIAGNOSTIC (摸底评测)：   W = 2.0
  - MIDTERM (期中评测)：      W = 3.0
  - FINAL (期末评测)：        W = 3.0

计算公式：
  如果该知识点首次出现：
    new_rating = 当前题目的分数

  如果该知识点已有历史记录：
    weighted_sum = (current_rating * current_weight) + (new_score * exam_weight)
    new_total_weight = current_weight + exam_weight
    new_rating = weighted_sum / new_total_weight

数据库字段更新：
  - ai_assessed_rating: 保存新的加权平均分（0-10 scale）
  - total_weight: 累计权重总和
"""

# Stage 3 批量更新逻辑（来自 api.py process_full_exam）：
"""
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
"""

# 完整的加权计算函数（来自 services/knowledge_mastery_service.py）：
"""
def calculate_weighted_mastery(
    db: Session,
    user_id: int,
    knowledge_tag: str,
    new_score: float,
    max_score: float,
    exam_type: ExamType
) -> Tuple[float, float]:
    \"\"\"
    Calculate weighted mastery score using moving average algorithm.
    
    Returns:
        Tuple of (new_ai_assessed_rating, new_total_weight)
    \"\"\"
    # Normalize new score to 0-10 scale
    normalized_new_score = round((new_score / max_score) * 10, 2)
    
    # Get exam type weight
    exam_weight = get_weight_for_exam_type(exam_type)
    
    # Fetch existing mastery record
    mastery_record = db.query(UserKnowledgeMastery).filter(
        UserKnowledgeMastery.user_id == user_id,
        UserKnowledgeMastery.knowledge_tag == knowledge_tag
    ).first()
    
    if not mastery_record:
        # New knowledge point: direct assignment
        new_rating = normalized_new_score
        new_total_weight = exam_weight
    else:
        # Existing knowledge point: weighted moving average
        current_rating = mastery_record.ai_assessed_rating or 0.0
        current_weight = mastery_record.total_weight or 0.0
        
        if current_weight == 0:
            new_rating = normalized_new_score
            new_total_weight = exam_weight
        else:
            # Weighted average formula
            weighted_sum = (current_rating * current_weight) + (normalized_new_score * exam_weight)
            new_total_weight = current_weight + exam_weight
            new_rating = round(weighted_sum / new_total_weight, 2)
    
    logger.info(
        f"[UpdateMastery] User {user_id}, Tag '{knowledge_tag}': "
        f"New: {normalized_new_score:.2f} (raw: {new_score}/{max_score}), "
        f"exam_weight={exam_weight}, updated_rating={new_rating:.2f}"
    )
    
    return new_rating, new_total_weight


def batch_update_knowledge_mastery(
    db: Session,
    user_id: int,
    problems: list,
    exam_type: ExamType,
    standard_tags_list: list
) -> dict:
    \"\"\"
    Batch update knowledge mastery for all problems in the exam.
    
    Returns:
        Summary dict with update counts and any skip reasons
    \"\"\"
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
        
        # Validation
        if not knowledge_tag or knowledge_tag not in standard_tags_list:
            updates_summary['skipped'].append(f"Invalid tag: {knowledge_tag}")
            continue
        
        if max_score <= 0:
            updates_summary['skipped'].append(f"Invalid max_score: {max_score}")
            continue
        
        # Update mastery
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
            updates_summary['skipped'].append(f"Update failed: {str(e)}")
    
    return updates_summary
"""


# ============================================================================
# 3. 实际存储案例演示
# ============================================================================

"""
示例：用户李明参加了一次摸底测试（diagnostic），有两道题目

题目 1：【函数与极限】
  - 得分：8/10
  - 规范化到 10 分制：8.0
  - 考试权重：2.0（diagnostic）
  
  假设首次出现这个知识点：
    ai_assessed_rating = 8.0
    total_weight = 2.0

题目 2：【数列求和】
  - 得分：15/20
  - 规范化到 10 分制：7.5
  - 考试权重：2.0（diagnostic）
  
  假设数列求和已有历史记录：
    previous_rating = 6.0（之前的加权平均）
    previous_weight = 1.0（之前的累积权重，来自日常练习）
    
    weighted_sum = (6.0 * 1.0) + (7.5 * 2.0) = 6.0 + 15.0 = 21.0
    new_total_weight = 1.0 + 2.0 = 3.0
    new_rating = 21.0 / 3.0 = 7.0
    
  更新到数据库：
    ai_assessed_rating = 7.0 ✓
    total_weight = 3.0 ✓

后续：
  - 用户进行了一次日常练习（custom）
  - 数列求和得分 18/20 = 9.0 分，权重 1.0
  
    weighted_sum = (7.0 * 3.0) + (9.0 * 1.0) = 21.0 + 9.0 = 30.0
    new_total_weight = 3.0 + 1.0 = 4.0
    new_rating = 30.0 / 4.0 = 7.5
    
  更新到数据库：
    ai_assessed_rating = 7.5 ✓
    total_weight = 4.0 ✓
"""


# ============================================================================
# 4. 数据库表结构
# ============================================================================

"""
ExamRecord 表：
  - id: 主键
  - exam_type: ENUM('custom', 'diagnostic', 'midterm', 'final') ✓ NEW
  - ai_model: 实际使用的模型名称（如 'gemini-1.5-pro'）✓ 填充
  - status: 批改状态
  - total_score: 总分
  - [其他字段...]

UserKnowledgeMastery 表：
  - id: 主键
  - user_id: 用户 ID
  - knowledge_tag: 知识点标签
  - ai_assessed_rating: 加权平均分（0-10）
  - total_weight: 累积权重总和 ✓ NEW / NOW USED
  - user_self_rating: 用户自我评价
  - comprehensive_score: 综合分数
  - updated_at: 更新时间
"""


# ============================================================================
# 5. 集成检查清单
# ============================================================================

"""
前端改动（已完成）：
  ✓ FullExamUploader - 模式切换（separated/combined）
  ✓ Model Config 页面 - 分离日常/高阶教学模型

后端改动（已完成）：
  ✓ models.py - ExamType enum + exam_records.exam_type 字段
  ✓ models.py - UserKnowledgeMastery.total_weight 字段
  ✓ services/model_manager.py - get_teaching_model_for_exam_type() 方法
  ✓ services/knowledge_mastery_service.py - 新建，实现加权算法
  ✓ routers/api.py - upload_and_grade 接收 exam_mode
  ✓ routers/api.py - process_full_exam 集成模型路由和加权计算
  ✓ routers/settings.py - 模型配置路由更新

数据库迁移（已完成）：
  ✓ Alembic 迁移 10e51f0310a9 - 添加 exam_type 和 total_weight 字段
  ✓ 数据库已升级到最新 schema

部署检查：
  □ 运行 `npm run dev` 验证前端集成
  □ 运行后端，验证模型选择逻辑
  □ 上传试卷（分离或合一模式），检查 exam.ai_model
  □ 验证知识点更新：检查 total_weight 增长和 ai_assessed_rating 加权
  □ 查看日志，确认模型选择和加权计算的执行流程
"""

# ============================================================================
# 6. 关键文件列表
# ============================================================================

"""
新增文件：
  - backend/app/services/knowledge_mastery_service.py

修改的文件：
  - backend/app/models.py
  - backend/app/routers/api.py
  - backend/app/routers/settings.py
  - backend/app/services/model_manager.py
  - frontend/app/settings/page.tsx
  - frontend/components/FullExamUploader.tsx
  - frontend/hooks/useExamPolling.ts

迁移文件：
  - backend/alembic/versions/10e51f0310a9_add_exam_type_and_total_weight_fields.py
"""
