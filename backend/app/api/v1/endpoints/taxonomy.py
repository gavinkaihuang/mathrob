"""
api/v1/endpoints/taxonomy.py
-----------------------------
MathRob - 知识点大纲服务 (Taxonomy Service) API 路由层。

对外暴露标准化 RESTful 接口，供 MathQBank 等外部系统调用。
所有端点均附有完整的 OpenAPI / Swagger 文档注解。

使用方式（在 FastAPI 主应用中注册）：

    from app.api.v1.endpoints.taxonomy import router as taxonomy_router
    app.include_router(taxonomy_router, prefix="/api/v1/taxonomy")
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ....database import get_db

from ....schemas.taxonomy import TaxonomyTagListResponse, TaxonomyTreeResponse
from ....services.taxonomy_service import taxonomy_service

# ---------------------------------------------------------------------------
# 路由实例
# ---------------------------------------------------------------------------

router = APIRouter(
    tags=["知识点大纲 (Taxonomy)"],
)

# ---------------------------------------------------------------------------
# GET /tags  —  扁平叶子标签库
# ---------------------------------------------------------------------------

@router.get(
    "/tags",
    response_model=TaxonomyTagListResponse,
    summary="获取打标用扁平标签库",
    description="""
## 接口说明

返回知识点体系中所有 **最末级叶子节点** 的名称列表（扁平数组）。

### 典型使用场景

| 系统 | 用途 |
|------|------|
| **MathQBank 切题打标** | 将返回列表直接注入 AI 提示词，作为合法标签候选集（tag constraint），避免模型幻觉出不存在的知识点 |
| **RAG / Few-Shot** | 构建向量索引，用于语义匹配题目与知识点 |
| **题库审题面板** | 渲染多选下拉的候选选项 |

### 返回说明

- `data[]` 中每个字符串即为一个可直接打标的知识点名称（`is_leaf=True`）。
- 顺序按深度优先遍历（DFS）从知识树中提取，与 `/tree` 接口的树形结构一一对应。
- 当前版本返回上海高中数学考纲核心知识点（共覆盖函数、解析几何、数列三大板块）。

### 错误码

| code | 含义 |
|------|------|
| 200 | 成功 |
| 500 | 服务器内部错误 |
""",
    response_description="包含所有最末级知识点名称的扁平数组。",
    status_code=status.HTTP_200_OK,
)
def get_flat_tags(db: Session = Depends(get_db)) -> TaxonomyTagListResponse:
    """
    获取所有叶子节点（最末级知识点）名称，以扁平字符串数组返回。

    供 MathQBank 切题打标时注入 AI 提示词，作为合法知识点标签的候选集合使用。
    """
    try:
        tags = taxonomy_service.get_flat_leaf_tags(db)
        return TaxonomyTagListResponse(
            code=200,
            message="success",
            data=tags,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取标签列表失败：{exc}",
        ) from exc


# ---------------------------------------------------------------------------
# GET /tree  —  完整知识点树
# ---------------------------------------------------------------------------

@router.get(
    "/tree",
    response_model=TaxonomyTreeResponse,
    summary="获取完整知识点树",
    description="""
## 接口说明

以 **嵌套树形结构** 返回完整知识点体系，每个节点包含 `id`、`name`、`level`、
`is_leaf` 及递归的 `children` 列表。

### 典型使用场景

| 系统 | 用途 |
|------|------|
| **MathQBank 管理后台** | 渲染级联下拉菜单（Cascader）或交互式树状图（Tree），供教研人员浏览/筛选题目 |
| **课程编排系统** | 基于 `level` 字段绑定章节层级，自动生成课程目录骨架 |
| **诊断报告引擎** | 以树形路径（如「解析几何 > 椭圆 > 椭圆的离心率」）展示学生薄弱知识点 |

### 节点字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int \\| str | 节点唯一标识符 |
| `name` | str | 知识点名称 |
| `level` | int | 层级深度，从 `1` 开始（1=一级目录，2=二级，3=叶子…） |
| `is_leaf` | bool | 是否为最末级节点，叶子节点 `children` 为 `null` |
| `children` | array \\| null | 子节点列表，叶子节点为 `null` |

### 错误码

| code | 含义 |
|------|------|
| 200 | 成功 |
| 500 | 服务器内部错误 |
""",
    response_description="以顶层节点列表为根的完整知识点嵌套树。",
    status_code=status.HTTP_200_OK,
)
def get_taxonomy_tree(db: Session = Depends(get_db)) -> TaxonomyTreeResponse:
    """
    获取完整知识点树，以嵌套结构返回，支持管理后台渲染级联下拉菜单或树状图。
    """
    try:
        tree_data: Any = taxonomy_service.get_taxonomy_tree(db)
        return TaxonomyTreeResponse(
            code=200,
            message="success",
            data=tree_data,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识点树失败：{exc}",
        ) from exc
