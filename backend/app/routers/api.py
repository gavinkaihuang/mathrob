"""
routers/api.py
--------------
MathRob API - 兼容性聚合路由（Shim）。

历史说明：
  本文件曾是 3140 行的单体路由文件，包含全部 40 个业务端点。
  已于 2026-06-17 按业务域拆分为 5 个独立模块：

    - problems.py     题目管理（列表/错题本/详情/掌握度/AI分析/相似题/解答提交）
    - reviews.py      复习系统（每日复习/复习历史/每日练习生成）
    - exams.py        整卷智能批阅（上传/流水线/历史/状态/详情）
    - assessment.py   诊断评测（生成试卷/提交/批改/报告）
    - misc.py         杂项（周报/学习进度/日志/解题尝试管理）

  公共依赖（schemas / ai_service 实例 / 工具函数）抽取至 _common.py。

兼容性设计：
  main.py 中仍以 `app.include_router(api.router, prefix="/api")` 注册，
  本 shim 将所有子路由的端点合并到一个 router 下，保持 URL 路径零变更。
  main.py 无需任何改动。
"""
from fastapi import APIRouter

from .problems import router as problems_router
from .reviews import router as reviews_router
from .exams import router as exams_router
from .assessment import router as assessment_router
from .misc import router as misc_router

# 创建聚合 router，将所有子路由的端点合并注册
router = APIRouter()

for _sub in (problems_router, reviews_router, exams_router, assessment_router, misc_router):
    router.include_router(_sub)
