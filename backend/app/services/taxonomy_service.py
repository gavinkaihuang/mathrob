"""
services/taxonomy_service.py
----------------------------
MathRob - 知识点大纲服务 (Taxonomy Service) 业务逻辑层。

当前阶段使用写死的 Mock 数据模拟数据库查询结果，
后续可替换为 SQLAlchemy / 外部 API 调用。
Mock 数据覆盖上海高中数学考纲的核心知识点，
包含「函数」「解析几何」两个典型一级目录及其完整子树。
"""

from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# 内部 Mock 数据（模拟 DB 返回的嵌套字典结构）
# ---------------------------------------------------------------------------

_MOCK_TAXONOMY: List[Dict[str, Any]] = [
    {
        "id": 101,
        "name": "函数",
        "level": 1,
        "is_leaf": False,
        "children": [
            {
                "id": 10101,
                "name": "函数的概念与性质",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1010101, "name": "函数的单调性", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010102, "name": "奇偶性",       "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010103, "name": "周期性",       "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010104, "name": "有界性",       "level": 3, "is_leaf": True, "children": None},
                ],
            },
            {
                "id": 10102,
                "name": "基本初等函数",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1010201, "name": "指数函数",     "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010202, "name": "对数函数",     "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010203, "name": "幂函数",       "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010204, "name": "三角函数",     "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010205, "name": "反三角函数",   "level": 3, "is_leaf": True, "children": None},
                ],
            },
            {
                "id": 10103,
                "name": "函数的应用",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1010301, "name": "函数零点与方程根", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010302, "name": "函数的最值",       "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010303, "name": "复合函数",         "level": 3, "is_leaf": True, "children": None},
                    {"id": 1010304, "name": "反函数",           "level": 3, "is_leaf": True, "children": None},
                ],
            },
        ],
    },
    {
        "id": 102,
        "name": "解析几何",
        "level": 1,
        "is_leaf": False,
        "children": [
            {
                "id": 10201,
                "name": "直线与圆",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1020101, "name": "直线的斜率与方程",   "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020102, "name": "两直线的位置关系",   "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020103, "name": "点到直线的距离",     "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020104, "name": "圆的方程",           "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020105, "name": "直线与圆的位置关系", "level": 3, "is_leaf": True, "children": None},
                ],
            },
            {
                "id": 10202,
                "name": "椭圆",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1020201, "name": "椭圆的标准方程与定义", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020202, "name": "椭圆的焦点",           "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020203, "name": "椭圆的离心率",         "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020204, "name": "椭圆的焦点弦",         "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020205, "name": "椭圆与直线的位置关系", "level": 3, "is_leaf": True, "children": None},
                ],
            },
            {
                "id": 10203,
                "name": "双曲线",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1020301, "name": "双曲线的标准方程与定义", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020302, "name": "双曲线的渐近线",         "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020303, "name": "双曲线的离心率",         "level": 3, "is_leaf": True, "children": None},
                ],
            },
            {
                "id": 10204,
                "name": "抛物线",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1020401, "name": "抛物线的标准方程与定义", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020402, "name": "抛物线的焦点与准线",     "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020403, "name": "抛物线的焦点弦",         "level": 3, "is_leaf": True, "children": None},
                    {"id": 1020404, "name": "抛物线与直线的位置关系", "level": 3, "is_leaf": True, "children": None},
                ],
            },
        ],
    },
    {
        "id": 103,
        "name": "数列",
        "level": 1,
        "is_leaf": False,
        "children": [
            {
                "id": 10301,
                "name": "等差数列",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1030101, "name": "等差数列的通项公式", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1030102, "name": "等差数列的前n项和", "level": 3, "is_leaf": True, "children": None},
                ],
            },
            {
                "id": 10302,
                "name": "等比数列",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1030201, "name": "等比数列的通项公式", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1030202, "name": "等比数列的前n项和", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1030203, "name": "等比数列的无穷级数", "level": 3, "is_leaf": True, "children": None},
                ],
            },
            {
                "id": 10303,
                "name": "数列的综合应用",
                "level": 2,
                "is_leaf": False,
                "children": [
                    {"id": 1030301, "name": "递推数列", "level": 3, "is_leaf": True, "children": None},
                    {"id": 1030302, "name": "数学归纳法", "level": 3, "is_leaf": True, "children": None},
                ],
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# TaxonomyService
# ---------------------------------------------------------------------------

class TaxonomyService:
    """
    知识点大纲服务。

    封装对知识点数据的访问逻辑，对调用方屏蔽底层存储细节。
    当前实现以内存 Mock 数据为数据源，接口签名已为后续切换 DB 预留。
    """

    def __init__(self) -> None:
        pass  # 移除内部级联状态，改为函数级获取以保持无状态

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def get_taxonomy_tree(self, db: Session) -> List[Dict[str, Any]]:
        """
        从数据库动态查询并构建完整知识点树（嵌套字典结构）。

        结构与 :class:`~app.schemas.taxonomy.TaxonomyNode` 的字段
        完全对应，包含从 DB 查出的真实 ltree path。
        """
        from ..models import KnowledgeNode
        
        # 按 ltree 字符串排序能天生保证 DFS 的遍历顺序
        nodes = db.query(KnowledgeNode).order_by(KnowledgeNode.path).all()
        
        node_dict: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            node_dict[node.path] = {
                "id": node.id,
                "name": node.name,
                "path": node.path,
                "level": len(node.path.split('.')),
                "is_leaf": True,  # 默认全是叶子，遇到子节点再改成 False
                "children": []
            }
        
        root_nodes: List[Dict[str, Any]] = []
        for node in nodes:
            path = node.path
            parts = path.split('.')
            parent_path = '.'.join(parts[:-1])
            
            node_data = node_dict[path]
            
            if parent_path and parent_path in node_dict:
                node_dict[parent_path]["children"].append(node_data)
                node_dict[parent_path]["is_leaf"] = False
            else:
                root_nodes.append(node_data)
                
        # 修正叶子节点的 children 字段（严格遵守 Schema 遇到 null 的情形）
        for dict_node in node_dict.values():
            if dict_node["is_leaf"]:
                dict_node["children"] = None
                
        return root_nodes

    def _collect_leaves(self, nodes: List[Dict[str, Any]], result: List[str]) -> None:
        """深度优先遍历，将所有 `is_leaf=True` 节点的名称追加到 `result`。"""
        for node in nodes:
            if node.get("is_leaf"):
                result.append(node["name"])
            children = node.get("children")
            if children:
                self._collect_leaves(children, result)

    def get_flat_leaf_tags(self, db: Session) -> List[str]:
        """
        从数据库查询，返回所有叶子节点（最末级知识点）的名称列表。
        """
        tree = self.get_taxonomy_tree(db)
        leaves: List[str] = []
        self._collect_leaves(tree, leaves)
        return leaves

# ---------------------------------------------------------------------------
# 模块级单例（可被路由层直接依赖注入）
# ---------------------------------------------------------------------------

taxonomy_service = TaxonomyService()
