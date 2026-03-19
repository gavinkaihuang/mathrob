"""
MathRob 两阶段批阅管道 - 代码快速参考
===================================

关键函数速查表
"""

# ============================================================================
# STAGE 1: 轻量级结构提取
# ============================================================================
async def _extract_exam_structure(image_paths: List[str], ai_service):
    """
    第一阶段：仅返回题号索引，token 消耗最少
    
    输入：图片路径列表
    输出：{'paper_title', 'question_numbers', 'total_question_count', 'model', 'page_count'}
    
    特点：
    - Prompt 仅 100-200 行
    - AI 只需返回 JSON，无需详细批改
    - 并发第一个 API 调用
    """
    pass


# ============================================================================
# STAGE 2: 并发分块批改（核心改进）
# ============================================================================
async def _grade_exam_batch(
    batch_numbers: List[str],           # 这批需要批改的题号，如 ["1", "2", "3"]
    image_paths: List[str],             # 所有图片（保持完整上下文）
    standard_tags_list: List[str],      # 知识点标签限制列表
    ai_service,                         # AI 服务实例
    batch_index: int,                   # 批次编号 0, 1, 2...
    total_batches: int                  # 总批数，用于 prompt 提示
):
    """
    第二阶段：对单个批次进行深度批改
    
    输入：特定批次的题号 + 全部图片 + 配置
    输出：{'batch_index', 'problems', 'model', 'tokens_used', 'graded_count'}
    
    特点：
    - 带所有图片发送（Gemini 需要全局上下文）
    - Prompt 明确指定题号范围
    - 返回 problems 数组
    
    这个函数会被多个实例并发调用。
    """
    pass


# ============================================================================
# STAGE 2 并发执行示例
# ============================================================================
async def example_concurrent_execution():
    """
    展示如何使用 asyncio.gather 并发执行多个批改任务
    """
    # 假设我们有 8 道题，按 3 题/批分割成 3 批
    question_numbers = ["1", "2", "3", "4", "5", "6", "7", "8"]
    batch_size = 3
    
    # 创建批次
    batches = [
        question_numbers[i:i+batch_size]
        for i in range(0, len(question_numbers), batch_size)
    ]
    # batches = [["1", "2", "3"], ["4", "5", "6"], ["7", "8"]]
    
    # 为每个批次创建任务（这里是示例，实际使用会立即被 asyncio.gather 执行）
    batch_tasks = [
        _grade_exam_batch(
            batch_numbers=batch,
            image_paths=image_paths,  # 所有图片
            standard_tags_list=tags,
            ai_service=ai_service,
            batch_index=idx,
            total_batches=len(batches)
        )
        for idx, batch in enumerate(batches)
    ]
    
    # 关键：并发执行所有任务
    # 如果单个批次耗时 15s，3 批：
    #   - 串行：15+15+15 = 45s
    #   - 并发：15s（最慢的批次的耗时）
    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
    
    # batch_results 是一个列表，包含每个批次的结果
    all_problems = []
    for result in batch_results:
        if isinstance(result, Exception):
            print(f"错误: {result}")
            continue
        
        problems = result.get('problems', [])
        all_problems.extend(problems)
        print(f"Batch {result['batch_index']}: {result['graded_count']} 题")


# ============================================================================
# STAGE 3: 结果聚合与落库
# ============================================================================
async def example_aggregation_and_persistence():
    """
    第三阶段：合并批改结果，计算总分，生成反馈，落库
    
    流程：
    1. 等待所有异步任务完成（已在 stage 2 的 gather() 中完成）
    2. 合并 all_problems 数组
    3. 计算 total_score
    4. 调用 AI 生成总体反馈
    5. 持久化到数据库
    """
    
    # 所有批改结果合并
    all_problems = []
    for batch_result in batch_results:
        all_problems.extend(batch_result.get('problems', []))
    
    # 计算总分
    total_score = sum(p.get('score', 0) for p in all_problems)
    
    # 生成学情分析反馈
    overall_feedback = await _generate_overall_feedback(
        all_problems=all_problems,
        paper_title=paper_title,
        total_score=total_score,
        ai_service=ai_service
    )
    
    # 保存到数据库
    exam.total_score = total_score
    exam.overall_feedback = overall_feedback
    exam.status = "completed"
    
    for problem in all_problems:
        prob_res = ExamProblemResult(
            exam_id=exam.id,
            problem_number=str(problem.get("problem_number")),
            score=problem.get("score", 0),
            max_score=problem.get("max_score", 10),
            knowledge_tag=problem.get("knowledge_tag", "未知"),
            feedback=problem.get("feedback", ""),
            original_question_text=problem.get("original_question_text"),
            user_answer_text=problem.get("user_answer_text")
        )
        db.add(prob_res)
    
    db.commit()


# ============================================================================
# Prompt 对比
# ============================================================================
"""
【Stage 1 Prompt】轻量级

你是一个试卷结构分析助手。请浏览提供的所有试卷和答题纸图片，
识别出图片中包含的所有"独立数学大题"的题号。

你不需要批改，只需要告诉我一共有哪些题。

严格输出 JSON 格式，不要任何额外文本：
{
    "paper_title": "提取的试卷标题或名称",
    "total_question_count": 8,
    "question_numbers": ["1", "2", "3", "4", "5", "6", "7", "8"],
    "notes": "如果有任何题号缺失或不清楚的地方，请说明"
}

✓ 简单、快速、清晰
✓ Token 消耗：~500-1000
✓ 成功率极高（只识别题号，无需复杂推理）
"""

"""
【Stage 2 Prompt】聚焦型（每批 2-3 题）

你是一位严格的高中数学阅卷专家。请在提供的试卷和答卷图片中，
**仅仅寻找并批改第 1, 2, 3 题**。

请忽略其他题号的内容。对这几道题进行深度 OCR 提取、数学逻辑研判，
并给出最终得分。

## 重要提示
- 这是批改任务的第 1/3 批
- 题号列表：1, 2, 3
- 每题必须包含完整的原题文本、学生答案和批改反馈

## 知识点标签限制
**只能**从以下列表中选择：[完整列表...]

## 输出格式（严格JSON）
{
    "batch_index": 0,
    "graded_question_count": 3,
    "problems": [
        {
            "problem_number": "1",
            "original_question_text": "完整原题文本",
            "user_answer_text": "学生手写答案",
            "score": 10,
            "max_score": 10,
            "knowledge_tag": "知识点名称",
            "feedback": "批改反馈"
        },
        ...
    ]
}

✓ 明确指定题号和批次
✓ 聚焦少量题目，深度分析
✓ Token 消耗：~3000-5000 per batch
✓ 准确度高
✓ 可以并发执行多个批次
"""

# ============================================================================
# 关键性能数据
# ============================================================================
"""
性能对比（以 8 道题为例）

【原方案】单次调用
- API 调用：1 次
- 单次 Input Token：~15000 (所有图片 + 复杂 prompt)
- 耗时：~60 秒
- 准确性：62.5% (遗漏 3 题)
- 问题：Gemini 一次处理过多内容，OCR 准确度下降

【新方案】两阶段管道
- API 调用：5 次 (1 个 Stage 1 + 3 个 Stage 2 + 1 个反馈)
- 单次 Input Token：更均衡（Stage 1: 5000 + 每个 Batch: 3000-5000）
- 耗时：~45 秒（并发，不是叠加）
- 准确性：>95% (预期)
- 优势：
  * 分治降低复杂度
  * 并发提升吞吐
  * Prompt 清晰，减少 AI 幻觉
"""

# ============================================================================
# 监控和调试
# ============================================================================
"""
【查看 SystemLog】

SELECT level, created_at, message, details 
FROM system_logs 
WHERE category = 'teaching' 
  AND message LIKE 'Exam %Stage%'
ORDER BY created_at DESC 
LIMIT 20;

预期日志流：
- [INFO] Exam 5 Stage 1: Extracted 8 questions
- [INFO] Exam 5 Stage 2: Batch grading completed
- [INFO] Exam 5 Stage 3: Aggregating results...
- [INFO] Exam 5 completed via two-stage pipeline

【标准输出日志】

[Exam 5] Stage 1: Extracting exam structure from 8 images...
[Exam 5] Stage 1 Complete: Found 8 questions: ['1', '2', '3', '4', '5', '6', '7', '8']
[Exam 5] Stage 2: Processing 3 batches with asyncio.gather...
[Exam 5] Batch 0: Graded 3 questions
[Exam 5] Batch 1: Graded 3 questions
[Exam 5] Batch 2: Graded 2 questions
[Exam 5] Stage 2 Complete: Total 8 problems graded
[Exam 5] Stage 3: Aggregating results and saving to database...
[Exam 5] ✅ Pipeline completed in 45.3s: 8 problems saved
"""

# ============================================================================
# 参数调优
# ============================================================================
"""
batch_size = 3  # 可改为 2-4

- batch_size = 2：
  * 批次数更多，并发度高
  * 单批 token 更少
  * 轻量级模型（如 flash）友好
  * 需要更多 API 调用

- batch_size = 3：
  * 平衡方案（推荐）
  * 吞吐和准确度均衡

- batch_size = 4+：
  * 批次数少，API 调用少
  * 单批 token 多
  * 对大模型（如 Pro）友好
  * 可能降低准确度
"""
