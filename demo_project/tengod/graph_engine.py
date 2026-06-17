#!/usr/bin/env python3
"""
graph_engine.py — 命理知识图谱引擎 v1.0.0

阶段十四：命理知识图谱

功能：
  1. 图数据模型（节点 Node + 边 Edge + 标签 Label）
  2. 图查询（邻居/最短路径/子图/模式匹配/全文本搜索）
  3. 命理知识入库（天干/地支/五行/八卦/十神/神煞/格局/64卦）
  4. Cypher-like 查询接口（简化版）
  5. 图导出（前端可视化 JSON 格式）

设计原则：
  - 纯标准库实现，无外部依赖（不依赖 Neo4j）
  - 兼容 Neo4j 数据模型，便于未来迁移
  - 内存图 + 索引加速
"""

from __future__ import annotations
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Iterator
from functools import lru_cache


__all__ = [
    "GraphNode", "GraphEdge", "KnowledgeGraphDB",
    "get_graph_db",
]
__version__ = "1.0.0"


# ============================================================================
# 图数据模型
# ============================================================================

@dataclass
class GraphNode:
    """图节点"""
    id: str                              # 唯一标识
    label: str                           # 节点标签（类别）
    name: str                            # 显示名
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "name": self.name,
            "properties": self.properties,
        }


@dataclass
class GraphEdge:
    """图边（有向）"""
    source: str                          # 源节点 ID
    target: str                          # 目标节点 ID
    relation: str                        # 关系类型
    weight: float = 1.0                  # 权重
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "properties": self.properties,
        }


# ============================================================================
# 知识图谱数据库
# ============================================================================

class KnowledgeGraphDB:
    """命理知识图谱数据库（内存图）"""

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        # 索引：邻接表（出边 + 入边）
        self._out_edges: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._in_edges: Dict[str, List[GraphEdge]] = defaultdict(list)
        # 索引：按标签分组
        self._label_index: Dict[str, List[str]] = defaultdict(list)
        # 索引：按关系类型分组
        self._relation_index: Dict[str, List[GraphEdge]] = defaultdict(list)
        # 索引：名称 → 节点 ID（支持别名）
        self._name_index: Dict[str, str] = {}
        # 全文索引：关键词 → 节点 ID 集合
        self._text_index: Dict[str, Set[str]] = defaultdict(set)
        # 是否已初始化
        self._initialized = False

    # ── 节点管理 ────────────────────────────────────────────────────

    def add_node(self, node_id: str, label: str, name: str,
                 properties: Optional[Dict[str, Any]] = None,
                 aliases: Optional[List[str]] = None) -> GraphNode:
        """添加节点"""
        if node_id in self._nodes:
            # 更新属性
            if properties:
                self._nodes[node_id].properties.update(properties)
            return self._nodes[node_id]

        node = GraphNode(id=node_id, label=label, name=name,
                         properties=properties or {})
        self._nodes[node_id] = node
        self._label_index[label].append(node_id)
        self._name_index[name] = node_id

        # 别名索引
        if aliases:
            for alias in aliases:
                self._name_index[alias] = node_id

        # 全文索引
        self._index_text(node_id, name)
        if properties:
            for v in properties.values():
                if isinstance(v, str):
                    self._index_text(node_id, v)
        return node

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """按 ID 获取节点"""
        return self._nodes.get(node_id)

    def find_node_by_name(self, name: str) -> Optional[GraphNode]:
        """按名称/别名查找节点"""
        node_id = self._name_index.get(name)
        if node_id:
            return self._nodes[node_id]
        return None

    def get_nodes_by_label(self, label: str) -> List[GraphNode]:
        """按标签获取所有节点"""
        return [self._nodes[nid] for nid in self._label_index.get(label, [])]

    # ── 边管理 ────────────────────────────────────────────────────

    def add_edge(self, source: str, target: str, relation: str,
                 weight: float = 1.0,
                 properties: Optional[Dict[str, Any]] = None) -> Optional[GraphEdge]:
        """添加有向边"""
        if source not in self._nodes or target not in self._nodes:
            return None

        # 去重（同源同目同关系只保留一条，合并属性）
        for e in self._out_edges[source]:
            if e.target == target and e.relation == relation:
                if properties:
                    e.properties.update(properties)
                return e

        edge = GraphEdge(source=source, target=target, relation=relation,
                         weight=weight, properties=properties or {})
        self._edges.append(edge)
        self._out_edges[source].append(edge)
        self._in_edges[target].append(edge)
        self._relation_index[relation].append(edge)
        return edge

    def add_edge_undirected(self, source: str, target: str, relation: str,
                            weight: float = 1.0,
                            properties: Optional[Dict[str, Any]] = None):
        """添加无向边（双向）"""
        self.add_edge(source, target, relation, weight, properties)
        self.add_edge(target, source, relation, weight, properties)

    # ── 查询：邻居 ────────────────────────────────────────────────

    def neighbors(self, node_id: str, direction: str = "both",
                  relation: Optional[str] = None,
                  limit: int = 100) -> List[GraphNode]:
        """获取邻居节点

        Args:
            node_id: 节点 ID
            direction: "out"（出边）/ "in"（入边）/ "both"（双向）
            relation: 关系类型过滤
            limit: 返回数量上限
        """
        if node_id not in self._nodes:
            return []

        neighbor_ids: Set[str] = set()
        if direction in ("out", "both"):
            for e in self._out_edges.get(node_id, []):
                if relation is None or e.relation == relation:
                    neighbor_ids.add(e.target)
        if direction in ("in", "both"):
            for e in self._in_edges.get(node_id, []):
                if relation is None or e.relation == relation:
                    neighbor_ids.add(e.source)

        result = [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]
        return result[:limit]

    def neighbor_edges(self, node_id: str, direction: str = "both",
                       relation: Optional[str] = None) -> List[GraphEdge]:
        """获取邻居边"""
        if node_id not in self._nodes:
            return []
        result = []
        if direction in ("out", "both"):
            for e in self._out_edges.get(node_id, []):
                if relation is None or e.relation == relation:
                    result.append(e)
        if direction in ("in", "both"):
            for e in self._in_edges.get(node_id, []):
                if relation is None or e.relation == relation:
                    result.append(e)
        return result

    # ── 查询：最短路径（BFS） ────────────────────────────────────

    def shortest_path(self, source: str, target: str,
                      max_depth: int = 10) -> Optional[List[str]]:
        """最短路径（BFS，无权图）

        Returns:
            节点 ID 列表，或 None（不可达）
        """
        if source not in self._nodes or target not in self._nodes:
            return None
        if source == target:
            return [source]

        visited = {source}
        queue = deque([(source, [source])])

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for e in self._out_edges.get(current, []):
                if e.target in visited:
                    continue
                new_path = path + [e.target]
                if e.target == target:
                    return new_path
                visited.add(e.target)
                queue.append((e.target, new_path))
        return None

    def shortest_path_with_edges(self, source: str, target: str,
                                 max_depth: int = 10) -> Optional[Dict[str, Any]]:
        """最短路径（含边信息）"""
        path = self.shortest_path(source, target, max_depth)
        if path is None:
            return None

        edges = []
        for i in range(len(path) - 1):
            # 找到第一条连接边
            for e in self._out_edges.get(path[i], []):
                if e.target == path[i + 1]:
                    edges.append(e.to_dict())
                    break

        return {
            "path": [self._nodes[nid].to_dict() for nid in path],
            "edges": edges,
            "length": len(path) - 1,
        }

    # ── 查询：子图提取 ───────────────────────────────────────────

    def subgraph(self, node_ids: List[str], hops: int = 1) -> Dict[str, Any]:
        """提取以指定节点为中心、N 跳范围内的子图"""
        included: Set[str] = set(node_ids)
        frontier = set(node_ids)

        for _ in range(hops):
            new_frontier = set()
            for nid in frontier:
                for e in self._out_edges.get(nid, []):
                    if e.target not in included:
                        included.add(e.target)
                        new_frontier.add(e.target)
                for e in self._in_edges.get(nid, []):
                    if e.source not in included:
                        included.add(e.source)
                        new_frontier.add(e.source)
            frontier = new_frontier
            if not frontier:
                break

        nodes = [self._nodes[nid].to_dict() for nid in included if nid in self._nodes]
        edges = []
        seen = set()
        for e in self._edges:
            if e.source in included and e.target in included:
                key = (e.source, e.target, e.relation)
                if key not in seen:
                    edges.append(e.to_dict())
                    seen.add(key)

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # ── 查询：模式匹配 ───────────────────────────────────────────

    def match_pattern(self, label: Optional[str] = None,
                      properties: Optional[Dict[str, Any]] = None,
                      limit: int = 50) -> List[GraphNode]:
        """按标签和属性匹配节点

        Args:
            label: 节点标签（None 表示不限）
            properties: 属性键值对（全部匹配）
            limit: 返回上限
        """
        candidates = []
        if label:
            candidates = [self._nodes[nid] for nid in self._label_index.get(label, [])]
        else:
            candidates = list(self._nodes.values())

        if properties:
            result = []
            for node in candidates:
                if all(node.properties.get(k) == v for k, v in properties.items()):
                    result.append(node)
            candidates = result

        return candidates[:limit]

    def match_relation(self, source_label: Optional[str] = None,
                       relation: str = None,
                       target_label: Optional[str] = None,
                       limit: int = 50) -> List[GraphEdge]:
        """按关系类型匹配边"""
        if relation is None:
            edges = list(self._edges)
        else:
            edges = list(self._relation_index.get(relation, []))

        result = []
        for e in edges:
            src = self._nodes.get(e.source)
            tgt = self._nodes.get(e.target)
            if src is None or tgt is None:
                continue
            if source_label and src.label != source_label:
                continue
            if target_label and tgt.label != target_label:
                continue
            result.append(e)
            if len(result) >= limit:
                break
        return result

    # ── 查询：全文搜索 ───────────────────────────────────────────

    def search(self, keyword: str, limit: int = 20) -> List[GraphNode]:
        """全文搜索节点"""
        keyword = keyword.strip().lower()
        if not keyword:
            return []

        # 精确名称匹配优先
        exact = self.find_node_by_name(keyword)
        if exact:
            return [exact]

        # 关键词索引
        result_ids: Set[str] = set()
        for k, ids in self._text_index.items():
            if keyword in k:
                result_ids.update(ids)

        # 名称模糊匹配
        for name, nid in self._name_index.items():
            if keyword in name.lower():
                result_ids.add(nid)

        return [self._nodes[nid] for nid in result_ids if nid in self._nodes][:limit]

    def _index_text(self, node_id: str, text: str):
        """建立全文索引"""
        for token in re.split(r"[\s·，,。/、]+", text.lower()):
            if token:
                self._text_index[token].add(node_id)

    # ── 统计与导出 ───────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """图统计信息"""
        label_counts = {l: len(ids) for l, ids in self._label_index.items()}
        relation_counts = {r: len(es) for r, es in self._relation_index.items()}
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "labels": label_counts,
            "relations": relation_counts,
        }

    def export_graph(self, limit: int = 500) -> Dict[str, Any]:
        """导出全图（前端可视化用）"""
        nodes = [n.to_dict() for n in list(self._nodes.values())[:limit]]
        node_id_set = {n["id"] for n in nodes}
        edges = [e.to_dict() for e in self._edges
                 if e.source in node_id_set and e.target in node_id_set]
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": self.stats(),
        }

    def export_subgraph_by_label(self, labels: List[str], max_nodes: int = 200) -> Dict[str, Any]:
        """按标签导出子图"""
        node_ids = set()
        for label in labels:
            for nid in self._label_index.get(label, []):
                node_ids.add(nid)
                if len(node_ids) >= max_nodes:
                    break

        nodes = [self._nodes[nid].to_dict() for nid in node_ids][:max_nodes]
        edges = [e.to_dict() for e in self._edges
                 if e.source in node_ids and e.target in node_ids]
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "labels": labels,
            },
        }

    # ========================================================================
    # 命理知识入库
    # ========================================================================

    def initialize(self):
        """初始化命理知识图谱"""
        if self._initialized:
            return
        self._init_elements()
        self._init_tiangan()
        self._init_dizhi()
        self._init_trigrams()
        self._init_shigan()
        self._init_shensha()
        self._init_geju()
        self._init_64gua()
        self._initialized = True

    def _init_elements(self):
        """五行"""
        elements = {
            "金": {"color": "白", "direction": "西", "season": "秋",
                    "nature": "燥", "number": 9, "organs": "肺/大肠",
                    "emotion": "悲", "flavor": "辛", "description": "从革，清洁肃杀"},
            "木": {"color": "青", "direction": "东", "season": "春",
                    "nature": "温", "number": 8, "organs": "肝/胆",
                    "emotion": "怒", "flavor": "酸", "description": "曲直，生长升发"},
            "水": {"color": "黑", "direction": "北", "season": "冬",
                    "nature": "寒", "number": 6, "organs": "肾/膀胱",
                    "emotion": "恐", "flavor": "咸", "description": "润下，闭藏静谧"},
            "火": {"color": "赤", "direction": "南", "season": "夏",
                    "nature": "热", "number": 7, "organs": "心/小肠",
                    "emotion": "喜", "flavor": "苦", "description": "炎上，光明温热"},
            "土": {"color": "黄", "direction": "中", "season": "长夏",
                    "nature": "平", "number": 5, "organs": "脾/胃",
                    "emotion": "思", "flavor": "甘", "description": "稼穑，承载化育"},
        }
        for name, props in elements.items():
            self.add_node(f"elem_{name}", "五行", name, props,
                          aliases=[name])

        # 五行生克关系
        sheng = [("木", "火"), ("火", "土"), ("土", "金"), ("金", "水"), ("水", "木")]
        ke = [("木", "土"), ("土", "水"), ("水", "火"), ("火", "金"), ("金", "木")]
        for src, tgt in sheng:
            self.add_edge(f"elem_{src}", f"elem_{tgt}", "相生", 1.0,
                          {"type": "生", "desc": f"{src}生{tgt}"})
        for src, tgt in ke:
            self.add_edge(f"elem_{src}", f"elem_{tgt}", "相克", 1.0,
                          {"type": "克", "desc": f"{src}克{tgt}"})

    def _init_tiangan(self):
        """天干"""
        tiangan_data = [
            ("甲", "木", "阳", "参天大树"),
            ("乙", "木", "阴", "花草藤蔓"),
            ("丙", "火", "阳", "太阳烈火"),
            ("丁", "火", "阴", "灯烛星火"),
            ("戊", "土", "阳", "城墙高山"),
            ("己", "土", "阴", "田园沃土"),
            ("庚", "金", "阳", "刀剑矿石"),
            ("辛", "金", "阴", "珠玉首饰"),
            ("壬", "水", "阳", "江河大海"),
            ("癸", "水", "阴", "雨露溪流"),
        ]
        for name, wuxing, yinyang, xiang in tiangan_data:
            self.add_node(f"tg_{name}", "天干", name,
                          {"wuxing": wuxing, "yinyang": yinyang, "xiang": xiang},
                          aliases=[name])

            # 关联到五行
            self.add_edge(f"tg_{name}", f"elem_{wuxing}", "属五行")

        # 天干五合：甲己合化土、乙庚合化金、丙辛合化水、丁壬合化木、戊癸合化火
        wuhe = [("甲", "己", "土"), ("乙", "庚", "金"),
                ("丙", "辛", "水"), ("丁", "壬", "木"),
                ("戊", "癸", "火")]
        for a, b, hua in wuhe:
            self.add_edge_undirected(f"tg_{a}", f"tg_{b}", "五合", 1.0,
                                     {"hua": hua, "desc": f"{a}{b}合化{hua}"})
            # 合化后的五行
            self.add_edge(f"tg_{a}", f"elem_{hua}", "合化")
            self.add_edge(f"tg_{b}", f"elem_{hua}", "合化")

        # 天干相冲：甲庚冲、乙辛冲、丙壬冲、丁癸冲
        chong = [("甲", "庚"), ("乙", "辛"), ("丙", "壬"), ("丁", "癸")]
        for a, b in chong:
            self.add_edge_undirected(f"tg_{a}", f"tg_{b}", "相冲", 1.0,
                                     {"desc": f"{a}{b}相冲"})

    def _init_dizhi(self):
        """地支"""
        dizhi_data = [
            ("子", "水", "阳", "鼠", "冬", "正", "23-1"),
            ("丑", "土", "阴", "牛", "冬", "腊", "1-3"),
            ("寅", "木", "阳", "虎", "春", "正", "3-5"),
            ("卯", "木", "阴", "兔", "春", "二", "5-7"),
            ("辰", "土", "阳", "龙", "春", "三", "7-9"),
            ("巳", "火", "阴", "蛇", "夏", "四", "9-11"),
            ("午", "火", "阳", "马", "夏", "五", "11-13"),
            ("未", "土", "阴", "羊", "夏", "六", "13-15"),
            ("申", "金", "阳", "猴", "秋", "七", "15-17"),
            ("酉", "金", "阴", "鸡", "秋", "八", "17-19"),
            ("戌", "土", "阳", "狗", "秋", "九", "19-21"),
            ("亥", "水", "阴", "猪", "冬", "十", "21-23"),
        ]
        for name, wuxing, yinyang, zodiac, season, month, hour in dizhi_data:
            self.add_node(f"dz_{name}", "地支", name,
                          {"wuxing": wuxing, "yinyang": yinyang,
                           "zodiac": zodiac, "season": season,
                           "month": month, "hour": hour},
                          aliases=[name, zodiac])
            self.add_edge(f"dz_{name}", f"elem_{wuxing}", "属五行")

        # 地支六合：子丑合土、寅亥合木、卯戌合火、辰酉合金、巳申合水、午未合火
        liuhe = [("子", "丑", "土"), ("寅", "亥", "木"), ("卯", "戌", "火"),
                 ("辰", "酉", "金"), ("巳", "申", "水"), ("午", "未", "火")]
        for a, b, hua in liuhe:
            self.add_edge_undirected(f"dz_{a}", f"dz_{b}", "六合", 1.0,
                                     {"hua": hua, "desc": f"{a}{b}合化{hua}"})

        # 地支三合局：申子辰合水、亥卯未合木、寅午戌合火、巳酉丑合金
        sanhe = [
            (["申", "子", "辰"], "水"),
            (["亥", "卯", "未"], "木"),
            (["寅", "午", "戌"], "火"),
            (["巳", "酉", "丑"], "金"),
        ]
        for branches, hua in sanhe:
            for i in range(len(branches)):
                for j in range(i + 1, len(branches)):
                    self.add_edge_undirected(
                        f"dz_{branches[i]}", f"dz_{branches[j]}",
                        "三合", 0.8, {"hua": hua})

        # 地支六冲：子午冲、丑未冲、寅申冲、卯酉冲、辰戌冲、巳亥冲
        liuchong = [("子", "午"), ("丑", "未"), ("寅", "申"),
                    ("卯", "酉"), ("辰", "戌"), ("巳", "亥")]
        for a, b in liuchong:
            self.add_edge_undirected(f"dz_{a}", f"dz_{b}", "相冲", 1.0)

        # 地支三刑：寅巳申、丑戌未、子卯
        xing = [("寅", "巳"), ("巳", "申"), ("寅", "申"),
                ("丑", "戌"), ("戌", "未"), ("丑", "未"),
                ("子", "卯")]
        for a, b in xing:
            self.add_edge_undirected(f"dz_{a}", f"dz_{b}", "相刑", 0.7)

        # 地支六害：子未、丑午、寅巳、卯辰、申亥、酉戌
        liuhai = [("子", "未"), ("丑", "午"), ("寅", "巳"),
                  ("卯", "辰"), ("申", "亥"), ("酉", "戌")]
        for a, b in liuhai:
            self.add_edge_undirected(f"dz_{a}", f"dz_{b}", "相害", 0.6)

        # 地支藏干
        canggan = {
            "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
            "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
            "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
            "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
        }
        for dz, gans in canggan.items():
            for i, gan in enumerate(gans):
                self.add_edge(f"dz_{dz}", f"tg_{gan}", "藏干",
                              1.0 - i * 0.2,  # 本气 > 中气 > 余气
                              {"qi": ["本气", "中气", "余气"][i] if i < 3 else "余气"})

    def _init_trigrams(self):
        """八卦"""
        trigram_data = [
            ("乾", 1, "☰", "金", "西北", "天", "健", "父亲", "首", "秋冬"),
            ("兑", 2, "☱", "金", "西", "泽", "悦", "少女", "口", "秋"),
            ("离", 3, "☲", "火", "南", "火", "丽", "中女", "目", "夏"),
            ("震", 4, "☳", "木", "东", "雷", "动", "长男", "足", "春"),
            ("巽", 5, "☴", "木", "东南", "风", "入", "长女", "股", "春夏"),
            ("坎", 6, "☵", "水", "北", "水", "陷", "中男", "耳", "冬"),
            ("艮", 7, "☶", "土", "东北", "山", "止", "少男", "手", "冬春"),
            ("坤", 8, "☷", "土", "西南", "地", "顺", "母亲", "腹", "夏秋"),
        ]
        for name, num, symbol, elem, direction, nature, attr, role, body, season in trigram_data:
            self.add_node(f"tri_{name}", "八卦", name,
                          {"number": num, "symbol": symbol, "wuxing": elem,
                           "direction": direction, "nature": nature,
                           "attribute": attr, "family_role": role,
                           "body_part": body, "season": season},
                          aliases=[name, symbol])
            self.add_edge(f"tri_{name}", f"elem_{elem}", "属五行")

        # 先天八卦对：乾对坤、坎对离、震对巽、艮对兑
        duigua = [("乾", "坤"), ("坎", "离"), ("震", "巽"), ("艮", "兑")]
        for a, b in duigua:
            self.add_edge_undirected(f"tri_{a}", f"tri_{b}", "对待", 1.0,
                                     {"desc": f"{a}{b}对待"})

    def _init_shigan(self):
        """十神"""
        shigan_data = [
            ("比肩", "同我", "助", "同类同性", "独立竞争"),
            ("劫财", "同我", "助", "同类异性", "争夺合作"),
            ("食神", "我生", "泄", "我生同性", "才华福禄"),
            ("伤官", "我生", "泄", "我生异性", "聪明叛逆"),
            ("偏财", "我克", "耗", "我克同性", "意外之财"),
            ("正财", "我克", "耗", "我克异性", "正当之财"),
            ("七杀", "克我", "克", "克我同性", "权威压力"),
            ("正官", "克我", "克", "克我异性", "约束管理"),
            ("偏印", "生我", "生", "生我同性", "孤僻学问"),
            ("正印", "生我", "生", "生我异性", "慈爱庇护"),
        ]
        for name, relation, action, nature, meaning in shigan_data:
            self.add_node(f"sg_{name}", "十神", name,
                          {"relation": relation, "action": action,
                           "nature": nature, "meaning": meaning},
                          aliases=[name])

        # 十神生克关系
        # 生：官杀生印、印生比劫、比劫生食伤、食伤生财、财生官杀
        sheng_chain = [
            ("正官", "正印"), ("七杀", "偏印"),
            ("正印", "比肩"), ("偏印", "劫财"),
            ("比肩", "食神"), ("劫财", "伤官"),
            ("食神", "正财"), ("伤官", "偏财"),
            ("正财", "正官"), ("偏财", "七杀"),
        ]
        for src, tgt in sheng_chain:
            self.add_edge(f"sg_{src}", f"sg_{tgt}", "相生", 1.0)

        # 十神相克
        ke_chain = [
            ("正官", "比肩"), ("七杀", "劫财"),
            ("比肩", "正财"), ("劫财", "偏财"),
            ("正财", "正印"), ("偏财", "偏印"),
            ("正印", "食神"), ("偏印", "伤官"),
            ("食神", "七杀"), ("伤官", "正官"),
        ]
        for src, tgt in ke_chain:
            self.add_edge(f"sg_{src}", f"sg_{tgt}", "相克", 1.0)

    def _init_shensha(self):
        """神煞（部分重要神煞）"""
        shensha_data = [
            ("天乙贵人", "吉神", "至尊吉神，逢凶化吉"),
            ("文昌", "吉神", "聪明好学，文采斐然"),
            ("天德贵人", "吉神", "仁慈祥和，逢凶化吉"),
            ("月德贵人", "吉神", "慈祥仁善，福泽深厚"),
            ("太极贵人", "吉神", "神秘玄学，洞察力强"),
            ("驿马", "动星", "奔波走动，变动迁移"),
            ("桃花", "感情", "异性缘佳，风流浪漫"),
            ("华盖", "孤星", "聪明孤僻，宗教艺术"),
            ("将星", "权力", "掌权统帅，领导才能"),
            ("禄神", "财禄", "衣食丰足，财禄充盈"),
            ("羊刃", "凶星", "刚强好斗，易有灾祸"),
            ("空亡", "凶星", "落空无成，虚耗损失"),
        ]
        for name, category, meaning in shensha_data:
            self.add_node(f"ss_{name}", "神煞", name,
                          {"category": category, "meaning": meaning},
                          aliases=[name])

    def _init_geju(self):
        """格局（部分重要格局）"""
        geju_data = [
            ("正官格", "贵格", "官星得令，主权贵"),
            ("七杀格", "权格", "杀星有制，主将帅"),
            ("正财格", "富格", "财星得地，主富裕"),
            ("偏财格", "富格", "偏财得地，主横财"),
            ("正印格", "文格", "印星得令，主学问"),
            ("食神格", "福格", "食神得令，主福禄"),
            ("伤官格", "才格", "伤官得令，主才华"),
            ("建禄格", "身格", "日干得禄，主自立"),
            ("羊刃格", "刚格", "刃星当权，主刚强"),
            ("从格", "变格", "从势从旺，弃命相从"),
        ]
        for name, category, meaning in geju_data:
            self.add_node(f"gj_{name}", "格局", name,
                          {"category": category, "meaning": meaning},
                          aliases=[name])

        # 格局与十神关联
        geju_shigan = [
            ("正官格", "正官"), ("七杀格", "七杀"),
            ("正财格", "正财"), ("偏财格", "偏财"),
            ("正印格", "正印"), ("食神格", "食神"),
            ("伤官格", "伤官"),
        ]
        for gj, sg in geju_shigan:
            self.add_edge(f"gj_{gj}", f"sg_{sg}", "以十神为用")

    def _init_64gua(self):
        """六十四卦（八宫归属）"""
        # 八宫卦序：乾宫八卦、坎宫八卦、艮宫八卦、震宫八卦、
        #          巽宫八卦、离宫八卦、坤宫八卦、兑宫八卦
        bagong = [
            ("乾", ["乾为天", "天风姤", "天山遁", "天地否", "风地观", "山地剥", "火地晋", "火天大有"]),
            ("坎", ["坎为水", "水泽节", "水雷屯", "水火既济", "泽火革", "雷火丰", "地火明夷", "地水师"]),
            ("艮", ["艮为山", "山火贲", "山天大畜", "山泽损", "火泽睽", "天泽履", "风泽中孚", "风山渐"]),
            ("震", ["震为雷", "雷地豫", "雷水解", "雷风恒", "地风升", "水风井", "泽风大过", "泽雷随"]),
            ("巽", ["巽为风", "风天小畜", "风水涣", "风泽中孚", "天泽履", "水泽节", "山泽损", "山风蛊"]),
            ("离", ["离为火", "火山旅", "火风鼎", "火水未济", "山水蒙", "风水涣", "天水讼", "天火同人"]),
            ("坤", ["坤为地", "地雷复", "地泽临", "地天泰", "雷天大壮", "泽天夬", "水天需", "水地比"]),
            ("兑", ["兑为泽", "泽水困", "泽地萃", "泽山咸", "水山蹇", "地山谦", "雷山小过", "雷泽归妹"]),
        ]
        for gong, guas in bagong:
            for i, gua_name in enumerate(guas):
                node_id = f"gua_{gong}_{i}"
                self.add_node(node_id, "六十四卦", gua_name,
                              {"gong": gong, "index_in_gong": i,
                               "upper": gua_name[0] if len(gua_name) > 0 else "",
                               "desc": f"{gong}宫第{i+1}卦"},
                              aliases=[gua_name])
                # 归属八宫
                self.add_edge(node_id, f"tri_{gong}", "属宫")


# ============================================================================
# 单例
# ============================================================================

_graph_db: Optional[KnowledgeGraphDB] = None


def get_graph_db() -> KnowledgeGraphDB:
    """获取知识图谱数据库单例"""
    global _graph_db
    if _graph_db is None:
        _graph_db = KnowledgeGraphDB()
        _graph_db.initialize()
    return _graph_db


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    db = get_graph_db()
    print("=== 知识图谱统计 ===")
    print(json.dumps(db.stats(), ensure_ascii=False, indent=2))

    print("\n=== 五行 '木' 的邻居 ===")
    node = db.find_node_by_name("木")
    if node:
        print(f"节点: {node.to_dict()}")
        neighbors = db.neighbors(node.id, direction="both")
        for n in neighbors:
            print(f"  - {n.label}·{n.name}")

    print("\n=== 天干 '甲' → 五行 '火' 的最短路径 ===")
    path = db.shortest_path_with_edges("tg_甲", "elem_火")
    if path:
        print(f"路径长度: {path['length']}")
        for n in path["path"]:
            print(f"  → {n['label']}·{n['name']}")
        for e in path["edges"]:
            print(f"    [{e['relation']}]")

    print("\n=== 搜索 '财' ===")
    results = db.search("财")
    for r in results:
        print(f"  - {r.label}·{r.name}: {r.properties}")

    print("\n=== 子图（以 '木' 为中心，2 跳） ===")
    sub = db.subgraph(["elem_木"], hops=2)
    print(f"节点数: {sub['node_count']}, 边数: {sub['edge_count']}")
