"""
schemas/taxonomy.py
-------------------
MathRob - 知识点大纲服务 (Taxonomy Service) 的 Pydantic 数据模型。

供 FastAPI 自动生成 OpenAPI / Swagger 文档使用。
"""

from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 通用响应包装字段
# ---------------------------------------------------------------------------

class _BaseResponse(BaseModel):
    """所有接口响应的公共包装字段。"""

    code: int = Field(
        default=200,
        description="业务状态码。`200` 表示成功，非 200 表示错误。",
        examples=[200],
    )
    message: str = Field(
        default="success",
        description="人类可读的状态描述。",
        examples=["success"],
    )


# ---------------------------------------------------------------------------
# 接口 1：扁平标签列表
# ---------------------------------------------------------------------------

class TaxonomyTagListResponse(_BaseResponse):
    """
    扁平化知识点标签列表响应体。

    `data` 数组仅包含叶子节点（最末级知识点）的名称，
    例如 `["椭圆的离心率", "函数的单调性", "等差数列的通项公式"]`。
    供 AI 提示词注入（RAG / few-shot）及 MathQBank 切题打标使用。
    """

    data: List[str] = Field(
        default_factory=list,
        description="所有最末级（`is_leaf=True`）知识点名称的有序列表。",
        examples=[["集合", "二次函数", "椭圆的离心率"]],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": 200,
                "message": "success",
                "data": [
                    "函数的单调性",
                    "奇偶性",
                    "反函数",
                    "椭圆的焦点",
                    "椭圆的离心率",
                    "双曲线的渐近线",
                    "抛物线的焦点弦",
                ],
            }
        }
    }


# ---------------------------------------------------------------------------
# 接口 2：树状知识点结构
# ---------------------------------------------------------------------------

class TaxonomyNode(BaseModel):
    """
    知识点树的单个节点。

    支持无限层级自嵌套（`children` 中的元素同为 `TaxonomyNode`）。
    当 `is_leaf=True` 时，`children` 为空列表或 `None`。
    """

    id: Union[int, str] = Field(
        description="节点唯一标识符（数据库主键或业务编码）。",
        examples=[101],
    )
    name: str = Field(
        description="知识点名称，对应教材章节或考纲条目。",
        examples=["函数"],
    )
    path: str = Field(
        description="节点在知识体系中的层级路径编码（例如 '101.10101'），可对应数据库中的 ltree 类型。",
        examples=["101"],
    )
    level: int = Field(
        description="节点所在层级（从 `1` 开始）。1=一级目录，2=二级目录，3=叶子节点，以此类推。",
        examples=[1],
        ge=1,
    )
    is_leaf: bool = Field(
        description="是否为叶子节点（最末级知识点）。叶子节点无子节点，可直接用于打标。",
        examples=[False],
    )
    children: Optional[List["TaxonomyNode"]] = Field(
        default=None,
        description="子节点列表。叶子节点该字段为 `null` 或空列表。",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 101,
                "name": "函数",
                "path": "101",
                "level": 1,
                "is_leaf": False,
                "children": [
                    {
                        "id": 10101,
                        "name": "函数的概念与性质",
                        "path": "101.10101",
                        "level": 2,
                        "is_leaf": False,
                        "children": [
                            {
                                "id": 1010101,
                                "name": "函数的单调性",
                                "path": "101.10101.1010101",
                                "level": 3,
                                "is_leaf": True,
                                "children": None,
                            }
                        ],
                    }
                ],
            }
        }
    }


# 让 Pydantic v2 完成自引用模型的 forward reference 解析
TaxonomyNode.model_rebuild()


class TaxonomyTreeResponse(_BaseResponse):
    """
    完整知识点树响应体。

    `data` 为顶层一级目录节点列表，每个节点递归嵌套其所有子节点。
    供管理后台渲染级联下拉菜单或可视化树状图使用。
    """

    data: List[TaxonomyNode] = Field(
        default_factory=list,
        description="顶层（`level=1`）知识点节点列表，含完整的嵌套子树。",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": 200,
                "message": "success",
                "data": [
                    {
                        "id": 101,
                        "name": "函数",
                        "path": "101",
                        "level": 1,
                        "is_leaf": False,
                        "children": [
                            {
                                "id": 10101,
                                "name": "函数的概念与性质",
                                "path": "101.10101",
                                "level": 2,
                                "is_leaf": False,
                                "children": [
                                    {
                                        "id": 1010101,
                                        "name": "函数的单调性",
                                        "path": "101.10101.1010101",
                                        "level": 3,
                                        "is_leaf": True,
                                        "children": None,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        }
    }
