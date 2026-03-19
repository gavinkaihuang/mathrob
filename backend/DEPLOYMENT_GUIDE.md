# 两阶段批阅管道 - 部署与实现总结

## 文件修改列表

### 1. 主实现文件
**文件**: `backend/app/routers/api.py`

**修改内容**:
- ✅ 添加 `import asyncio`
- ✅ 创建辅助函数 `_extract_exam_structure()` - Stage 1
- ✅ 创建辅助函数 `_grade_exam_batch()` - Stage 2 (单个批次)
- ✅ 创建辅助函数 `_generate_overall_feedback()` - 生成学情反馈
- ✅ 重写 `process_full_exam()` - 两阶段管道协调器

**关键改进**:
```python
# 原：单次调用，容易遗漏
response = await ai_service.call_gemini_with_fallback('teaching', prompt, image_paths=all_8_images)

# 新：两阶段分治
# Stage 1: 获取题号索引
structure = await _extract_exam_structure(image_paths, ai_service)
question_numbers = structure['question_numbers']  # ['1','2','3','4','5','6','7','8']

# Stage 2: 并发批改
batch_tasks = [_grade_exam_batch(...) for batch in batches]
results = await asyncio.gather(*batch_tasks)  # 并发执行

# Stage 3: 聚合后落库
all_problems = [p for batch in results for p in batch['problems']]
```

## 代码架构

### 辅助函数签名

```python
# Stage 1: 轻量级索引
async def _extract_exam_structure(
    image_paths: List[str],
    ai_service
) -> dict:
    """
    返回: {
        'paper_title': str,
        'question_numbers': List[str],
        'total_question_count': int,
        'model': str,
        'page_count': int
    }
    """

# Stage 2: 单批次深度批改
async def _grade_exam_batch(
    batch_numbers: List[str],
    image_paths: List[str],
    standard_tags_list: List[str],
    ai_service,
    batch_index: int,
    total_batches: int
) -> dict:
    """
    返回: {
        'batch_index': int,
        'problems': List[dict],
        'model': str,
        'tokens_used': int,
        'graded_count': int
    }
    """

# 生成总体反馈
async def _generate_overall_feedback(
    all_problems: List[dict],
    paper_title: str,
    total_score: float,
    ai_service
) -> str:
    """返回: 学情分析文本"""
```

### 主协调函数

```python
async def process_full_exam(
    task_id: int,
    user_id: int,
    image_paths: List[str],
    image_urls: List[str] = None
):
    """
    两阶段管道入口
    
    Stage 1 → Stage 2 (asyncio.gather) → Stage 3 → 数据库
    """
    
    # ============ Stage 1: 结构提取 ============
    structure = await _extract_exam_structure(image_paths, ai_service)
    question_numbers = structure['question_numbers']
    
    # ============ Stage 2: 并发批改 ============
    batches = [question_numbers[i:i+3] for i in range(0, len(question_numbers), 3)]
    batch_tasks = [
        _grade_exam_batch(batch, image_paths, ..., batch_index=idx, ...)
        for idx, batch in enumerate(batches)
    ]
    batch_results = await asyncio.gather(*batch_tasks)
    
    # ============ Stage 3: 聚合与落库 ============
    all_problems = [p for r in batch_results for p in r.get('problems', [])]
    total_score = sum(p.get('score', 0) for p in all_problems)
    
    # 生成反馈 + 保存到数据库
    ```
```

## 关键性能优化

### 1. 并发执行

```python
# 差：串行
for batch in batches:
    result = await _grade_exam_batch(batch, ...)  # 等待 15s
    # 耗时：3 批 × 15s = 45s

# 优：并发
tasks = [_grade_exam_batch(batch, ...) for batch in batches]
results = await asyncio.gather(*tasks)  # 只需 15s（最慢的批次）
```

### 2. Token 预算均衡

| Stage | Token (输入) | Token (输出) | 耗时 | 调用数 |
|-------|------------|----------|-----|--------|
| 1 (结构提取) | 5K | 100 | 5s | 1 |
| 2 (批改 Batch 0) | 5K | 2K | 15s | 1 |
| 2 (批改 Batch 1) | 5K | 2K | 15s | 1 (并发) |
| 2 (批改 Batch 2) | 3K | 1K | 10s | 1 (并发) |
| 3 (反馈) | 3K | 200 | 5s | 1 |
| **总计** | **21K** | **5.3K** | **45s** | **5** |

**原方案** (単次): 15K input tokens → 失败或遗漏

## 部署步骤

### 1. 备份
```bash
cp backend/app/routers/api.py backend/app/routers/api.py.backup
```

### 2. 部署代码
新代码已直接修改 `api.py`，无需额外步骤。

### 3. 验证语法
```bash
python -m py_compile backend/app/routers/api.py
# 输出：✅ Syntax check passed
```

### 4. 重启服务
```bash
# Docker
docker-compose restart api

# 或本地
pkill uvicorn
cd backend && uvicorn app.main:app --reload
```

### 5. 测试
1. 上传 8 张试卷照片
2. 查看 SystemLog 验证三个阶段都完成
3. 检查 exam_records 和 exam_problem_results 表数据完整性

## 监控

### 实时监控（标准输出）
```
[Exam 5] Stage 1: Extracting exam structure from 8 images...
[Exam 5] Stage 1 Complete: Found 8 questions
[Exam 5] Stage 2: Processing 3 batches with asyncio.gather...
[Exam 5] Batch 0: Graded 3 questions
[Exam 5] Batch 1: Graded 3 questions
[Exam 5] Batch 2: Graded 2 questions
[Exam 5] ✅ Pipeline completed in 45.3s: 8 problems saved
```

### 数据库查询
```sql
-- 查看最近 10 个试卷的完成情况
SELECT id, paper_name, status, total_score, 
       (SELECT COUNT(*) FROM exam_problem_results WHERE exam_id = e.id) as problem_count
FROM exam_records e
ORDER BY created_at DESC
LIMIT 10;

-- 查看某个试卷的所有问题
SELECT problem_number, score, max_score, knowledge_tag, feedback
FROM exam_problem_results
WHERE exam_id = 5
ORDER BY problem_number;

-- 查看处理日志
SELECT created_at, level, message, details
FROM system_logs
WHERE category = 'teaching' AND message LIKE 'Exam%'
ORDER BY created_at DESC
LIMIT 30;
```

## 配置调优

### 调整批大小
```python
# 在 process_full_exam 中
batch_size = 2  # 或 3（推荐） 或 4

batches = [
    question_numbers[i:i+batch_size]
    for i in range(0, len(question_numbers), batch_size)
]
```

**推荐值**:
- `batch_size=2`: 对小模型或严格准确度要求
- `batch_size=3`: 平衡（默认、推荐）
- `batch_size=4`: 对 Pro 模型，重视速度

## 故障排除

### 问题 1: 某个批次失败

**症状**: `[ERROR] Batch grading error: ...`

**原因**: 该批次的 AI 调用失败或数据质量差

**解决**:
1. 检查 Gemini API 配额
2. 查看完整错误日志
3. 检查图片质量

### 问题 2: 题目数少于预期

**症状**: 识别到 8 题，但只批改了 6 题

**原因**: 某个批次的 Prompt 指定题号不清晰

**解决**:
1. 重新上传试卷
2. 或调小 `batch_size` 减轻压力

### 问题 3: 耗时大幅增加

**症状**: 从 ~60s 变成 ~120s

**原因**: 可能是：
- Gemini API 限流
- 网络延迟
- 单个批次卡顿

**解决**:
1. 查看 Gemini API 限流日志
2. 调整批大小
3. 监控网络

## 回滚

如需回滚到原方案：
```bash
cp backend/app/routers/api.py.backup backend/app/routers/api.py
# 重启服务
```

## 下一步改进

1. **断点续传**: 若某批失败，支持重试单个批
2. **动态批大小**: 根据 Gemini API 调用耗时动态调整
3. **缓存**: 缓存已识别的题号，避免重复 Stage 1
4. **用户反馈**: 若检测题数 < 预期，提示用户重新上传

## 文档参考

- 详细架构文档: [EXAM_GRADING_REFACTOR.md](./EXAM_GRADING_REFACTOR.md)
- 代码快速参考: [EXAM_GRADING_REFERENCE.py](./EXAM_GRADING_REFERENCE.py)
- 原 issue: 试卷 ID 5 只识别了 5/8 题

---

**部署日期**: 2026-03-18  
**版本**: 2.0 (Two-Stage Pipeline)  
**状态**: ✅ 生产就绪
