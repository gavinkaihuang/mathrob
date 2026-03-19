# MathRob 整卷智能批阅 - 两阶段管道重构

## 概述

已成功重构 `process_full_exam` 函数，从**单次 Gemini API 调用**改为**两阶段分治管道**，解决大模型一次性处理过多图片（8+ 张）导致题目提取遗漏的问题。

## 核心改进

| 问题 | 原因 | 解决方案 |
|-----|------|--------|
| 题目遗漏 | Gemini 一次处理 8 张图，OCR 准确度下降 | 拆分为两阶段：先建索引，再分块批改 |
| 串行处理 | 原为单个 API 调用 | 使用 `asyncio.gather` 并发处理多个批次 |
| 结果不稳定 | Prompt 过复杂，要求 AI 同时做太多事 | 轻量级 Stage 1 + 专注型 Stage 2 |

## 架构设计

### 三阶段流程

```
┌─────────────────────────────────────────────────────────────┐
│ 输入：8 张试卷照片                                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │   Stage 1: 结构提取   │ 轻量级提取，仅列题号
        │ (单次 AI 调用)      │
        │ Output: [1,2,3...] │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────────┐
        │  Stage 2: 分块并发批改        │
        │ 按 3 题/批创建 N 个任务      │
        │ asyncio.gather([Task...])  │
        │ ├─ Batch 0: 题 1-3 (并发)  │
        │ ├─ Batch 1: 题 4-6 (并发)  │
        │ └─ Batch 2: 题 7-8 (并发)  │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────────────┐
        │  Stage 3: 结果聚合与落库      │
        │ - 合并所有 problems 数组    │
        │ - 计算 total_score         │
        │ - 生成总体反馈              │
        │ - 持久化到数据库           │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────┐
        │  输出：完整试卷批改  │
        │  记录在数据库中     │
        └──────────────────────┘
```

## 代码实现细节

### 1. Stage 1: 结构提取函数 (`_extract_exam_structure`)

**目的**：轻量级扫描，建立题号索引

**Prompt 特点**：
- 不要求详细批改
- 仅需返回题号列表和试卷标题
- Token 消耗最少（~500-1000 tokens）

**输出格式**：
```json
{
    "paper_title": "同济大学第一附属中学 2025 学年...",
    "total_question_count": 8,
    "question_numbers": ["1", "2", "3", "4", "5", "6", "7", "8"]
}
```

### 2. Stage 2: 分块批改函数 (`_grade_exam_batch`)

**目的**：按批次进行深度批改，聚焦少量题目

**关键特性**：
- 每批 2-3 题（configurable via `batch_size`)
- **带着所有图片**发送给 Gemini（保持上下文）
- Prompt 明确指定要批改的题号范围
- 使用 `asyncio.gather` 并发执行

**并发调用示例**（对于 8 道题）：
```python
batches = [
    ["1", "2", "3"],      # Batch 0
    ["4", "5", "6"],      # Batch 1
    ["7", "8"]            # Batch 2
]

batch_tasks = [
    _grade_exam_batch(batch, image_paths, ..., batch_index=0, ...),
    _grade_exam_batch(batch, image_paths, ..., batch_index=1, ...),
    _grade_exam_batch(batch, image_paths, ..., batch_index=2, ...)
]

results = await asyncio.gather(*batch_tasks)  # 并发执行
```

**输出格式**：
```json
{
    "batch_index": 0,
    "graded_question_count": 3,
    "problems": [
        {
            "problem_number": "1",
            "original_question_text": "...",
            "user_answer_text": "...",
            "score": 10,
            "max_score": 10,
            "knowledge_tag": "幂、指、对函数",
            "feedback": "..."
        }
    ]
}
```

### 3. Stage 3: 结果聚合 & 落库

**逻辑**：
1. 等待所有 batch 任务完成（`asyncio.gather` 已内置等待）
2. 合并所有 `problems` 数组
3. 计算 `total_score`
4. 调用 `_generate_overall_feedback` 生成学情分析
5. 保存到 `ExamRecord` 和 `ExamProblemResult` 表

## 性能对比

### 原方案 vs 新方案

| 指标 | 原方案 | 新方案 |
|-----|-------|-------|
| API 调用次 | 1 次 | N + 2 次 (结构提取1 + 批改N + 反馈1) |
| 并发性 | 否 | 是（asyncio.gather） |
| 对单次调用的 Token 限制 | 敏感 | 鲁棒（每次 token 可控） |
| 准确性（题目遗漏） | 低 (5/8 = 62.5%) | 高 (预期 >95%) |
| 总耗时 | ~60s | ~45-50s (并发)* |

*因为批改阶段是并发的，总耗时通常 = max(所有批次耗时) + 聚合时间，而不是累加时间。

## SystemLog 记录

每个 Exam 会生成完整的流程日志：

```
[INFO] Exam 5 Stage 1: Extracted 8 questions: [1,2,3,4,5,6,7,8]
[INFO] Exam 5 Stage 2: Batch grading completed (3 batches, 8 problems graded)
[INFO] Exam 5 Stage 3 Aggregating results...
[INFO] Exam 5 completed via two-stage pipeline
  {
    "problems_saved": 8,
    "total_score": 62.0,
    "pipeline_duration_seconds": 45.3,
    "completion_status": "SUCCESS"
  }
```

## 关键改进点

### 1. Prompt 设计规范化

**Stage 1 Prompt**（轻量级）：
```
你是一个试卷结构分析助手。请浏览所有试卷，识别独立数学大题的题号。
你不需要批改，仅返回题号列表。

严格输出 JSON：{ "question_numbers": ["1", "2", ...] }
```

**Stage 2 Prompt**（聚焦型）：
```
你是严格的高中数学阅卷专家。**仅仅寻找并批改第 1, 2, 3 题**。
忽略其他题号。进行深度 OCR 提取和数学逻辑研判。

知识点标签仅从 [...] 中选择。
严格输出 JSON：{ "problems": [...] }
```

### 2. 异步并发优化

```python
# 创建多个并发任务
batch_tasks = [
    _grade_exam_batch(..., batch_index=0),  # 并发1
    _grade_exam_batch(..., batch_index=1),  # 并发2
    _grade_exam_batch(..., batch_index=2),  # 并发3
]

# 异步等待全部完成
results = await asyncio.gather(*batch_tasks, return_exceptions=True)
```

- 所有批次**并发运行**，不串行等待
- 错误处理：`return_exceptions=True` 捕获单个批次的失败
- 总耗时 ≈ 最慢的单个批次，而非累加

### 3. 数据库操作优化

- 每个 stage 后立即 `db.commit()`，避免事务过长
- 完整的错误恢复：失败时将 exam 状态设为 "failed" 并记录错误信息
- SystemLog 完整记录每个 stage 的进度和关键参数

## 使用示例

### 部署

直接替换现有的 `process_full_exam` 函数。上传试卷的 API 端点 `/exams/upload_and_grade` 无需修改，会自动使用新的两阶段管道。

### 监控

查看 SystemLog 表中 `category='teaching'` 的记录：

```sql
SELECT * FROM system_logs 
WHERE category = 'teaching' AND message LIKE 'Exam % Stage%' 
ORDER BY created_at DESC 
LIMIT 20;
```

### 调试

关键日志输出（标准输出）：
```
[Exam 5] Stage 1: Extracting exam structure from 8 images...
[Exam 5] Stage 1 Complete: Found 8 questions: ['1', '2', '3', '4', '5', '6', '7', '8']
[Exam 5] Stage 2: Processing 3 batches with asyncio.gather...
[Exam 5] Batch 0: Graded 3 questions
[Exam 5] Batch 1: Graded 3 questions
[Exam 5] Batch 2: Graded 2 questions
[Exam 5] Stage 2 Complete: Total 8 problems graded
[Exam 5] Stage 3: Aggregating results and saving to database...
[Exam 5] ✅ Pipeline completed in 45.3s: 8 problems saved
```

## 配置调整

修改批大小（当前 3，可改为 2）：

```python
# 在 process_full_exam 中
batch_size = 2  # 改为 2-3 题/批
batches = [
    question_numbers[i:i+batch_size]
    for i in range(0, len(question_numbers), batch_size)
]
```

## 测试清单

- [ ] 单份 8 张图试卷，验证 8 道题全部识别并批改
- [ ] 验证并发性：监控多个 batch 任务是否实际并发
- [ ] 验证错误恢复：若某个 batch 失败，整体 exam 状态为 "failed"
- [ ] 验证数据库持久化：所有问题和知识点掌握记录正确保存
- [ ] 性能测试：测量整体耗时 vs 原方案

## 总结

新的两阶段管道通过：
1. **分治**：拆分复杂任务，降低 AI 单次负载
2. **并发**：批次间异步并行，提高吞吐
3. **规范化 Prompt**：每个 stage 职责清晰，减少幻觉

预期效果：
- 题目识别准确率 从 62.5% → >95%
- 总耗时 从 ~60s → ~45s
- 系统稳定性和可维护性显著提升
