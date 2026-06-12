#!/usr/bin/env python3
"""
knowledge_base.py — 知识库
正财主理固化，提供轻量级知识图谱与查询能力。
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class KnowledgeNode:
    """知识节点"""
    id: str
    name: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class KnowledgeEdge:
    """知识边（关系）"""
    source: str
    target: str
    relation: str
    weight: float = 1.0


class KnowledgeBase:
    """知识库 — 固化之库

    管理节点、关系，支持基本查询与遍历。
    """

    def __init__(self):
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: List[KnowledgeEdge] = []

    def add_node(
        self,
        name: str,
        node_type: str = "default",
        properties: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> KnowledgeNode:
        """添加节点"""
        nid = node_id or str(uuid.uuid4())[:8]
        node = KnowledgeNode(
            id=nid,
            name=name,
            node_type=node_type,
            properties=properties or {},
        )
        self._nodes[nid] = node
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        weight: float = 1.0,
    ) -> Optional[KnowledgeEdge]:
        """添加边"""
        if source not in self._nodes or target not in self._nodes:
            return None
        edge = KnowledgeEdge(source=source, target=target, relation=relation, weight=weight)
        self._edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取节点"""
        return self._nodes.get(node_id)

    def find_by_name(self, name: str) -> List[KnowledgeNode]:
        """按名称查找"""
        return [n for n in self._nodes.values() if n.name == name]

    def neighbors(self, node_id: str, relation: Optional[str] = None) -> List[KnowledgeNode]:
        """获取邻居节点"""
        if node_id not in self._nodes:
            return []
        result_ids = set()
        for edge in self._edges:
            if relation and edge.relation != relation:
                continue
            if edge.source == node_id:
                result_ids.add(edge.target)
            elif edge.target == node_id:
                result_ids.add(edge.source)
        return [self._nodes[nid] for nid in result_ids if nid in self._nodes]

    def stats(self) -> Dict[str, int]:
        """统计信息"""
        type_count: Dict[str, int] = {}
        for n in self._nodes.values():
            type_count[n.node_type] = type_count.get(n.node_type, 0) + 1
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "node_types": len(type_count),
        }

    def export(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.node_type,
                    "properties": n.properties,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "weight": e.weight,
                }
                for e in self._edges
            ],
        }
