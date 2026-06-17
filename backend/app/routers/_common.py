"""
routers/_common.py
------------------
MathRob API 路由层的公共依赖与共享定义。

拆分自原 api.py（3140 行单文件），本模块集中放置：
- 共享的 Pydantic schemas（Problem / SolutionAttempt / API调用日志 等）
- 单例 ai_service 实例（所有路由复用同一个 AIService）
- 通用的工具函数与常量

注意：保持零行为变更，仅做物理拆分。
"""
import os
from datetime import datetime
from typing import List, Optional, Union, Any

from pydantic import BaseModel

from ..models import Problem
from ..services.ai_service import AIService
from ..services.upload_service import get_accessible_image_url

# 单例：所有路由复用同一个 AI 服务实例（与原 api.py 行为一致）
ai_service = AIService()

# 上传目录常量（向后兼容，部分历史代码仍引用）
UPLOAD_DIR = "backend/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _hydrate_problem_images(problem: Problem):
    """把 Problem 及其 SolutionAttempt 的 image_path 转成可访问的预签名 URL。"""
    problem.image_path = get_accessible_image_url(problem.image_path)
    if getattr(problem, "solution_attempts", None):
        for attempt in problem.solution_attempts:
            attempt.image_path = get_accessible_image_url(attempt.image_path)


# ---------------------------------------------------------------------------
# 共享 Pydantic Schemas
# ---------------------------------------------------------------------------

class SolutionAttemptSchema(BaseModel):
    id: int
    image_path: str
    ai_model_used: Optional[str] = None
    ai_score: Optional[float] = None
    ai_evaluation: Optional[Union[dict, str]] = None
    formatting_feedback: Optional[str] = None
    feedback_json: Optional[Union[dict, str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class APICallLogSchema(BaseModel):
    id: int
    category: str
    action_type: str
    target_id: Optional[int] = None
    model_used: str
    token_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProblemSchema(BaseModel):
    id: int
    image_path: str
    latex_content: Optional[str] = None
    difficulty: Optional[int] = None
    ai_analysis: Optional[Union[dict, str]] = None
    created_at: datetime
    current_mastery_level: Optional[int] = None
    ai_model: Optional[str] = None
    solution_attempts: List[SolutionAttemptSchema] = []

    class Config:
        from_attributes = True


class PaginatedProblemsResponse(BaseModel):
    items: List[ProblemSchema]
    total: int
    page: int
    page_size: int
    total_pages: int


class KnowledgePointSchema(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    children: List['KnowledgePointSchema'] = []

    class Config:
        from_attributes = True
