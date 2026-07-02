#!/usr/bin/env python3
"""
knowledge_fusion.py — 命理知识融合引擎 v4.6.0
第二阶段：知识图谱 + 向量存储 + Deepseek AI 推理融合

功能：
  1. 知识链推理：八字 → 五行 → 神煞 → 格局 → 古籍条文
  2. 向量搜索 + 图邻居搜索 混合召回
  3. 图谱可视化 JSON 生成（供前端 D3.js/ECharts 渲染）
  4. 命理经典条文批量向量化入库（《三命通会》《渊海子平》）

架构：
  KnowledgeFusionEngine =
    graph_db (KnowledgeGraphDB)
    + vector_store (VectorStore)
    + deepseek_client (DeepseekClient)
    + search_rank (混合排序)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .graph_engine import KnowledgeGraphDB, GraphNode, GraphEdge, get_graph_db
from .vector_store import VectorStore, get_vector_store
from .deepseek_adapter import DeepseekClient, DeepseekResponse, Message


__all__ = [
    "KnowledgeFusionEngine",
    "FusedKnowledge",
    "KnowledgeGraphVisualization",
    "get_fusion_engine",
    "inject_classic_text",
]

# 全局单例
_fusion_engine: Optional[KnowledgeFusionEngine] = None


# ============================================================================
# 融合结果数据结构
# ============================================================================

@dataclass
class FusedKnowledge:
    """融合后的知识结果"""
    query: str                                   # 用户查询
    nodes: List[Dict[str, Any]]                 # 命中节点
    edges: List[Dict[str, Any]]                 # 命中边
    text_chunks: List[str]                      # 经典文本片段
    reasoning_chain: str                        # AI 推理链结果
    relevance_scores: Dict[str, float]         # 相关性分数
    depth: int = 2                              # 搜索深度

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "nodes": self.nodes,
            "edges": self.edges,
            "text_chunks": self.text_chunks,
            "reasoning_chain": self.reasoning_chain,
            "relevance_scores": self.relevance_scores,
            "depth": self.depth,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================================
# 知识融合引擎主类
# ============================================================================

class KnowledgeFusionEngine:
    """知识融合引擎 —— 向量检索 + 图遍历 + AI推理 三层融合"""

    def __init__(
        self,
        graph_db: Optional[KnowledgeGraphDB] = None,
        vector_store: Optional[VectorStore] = None,
        deepseek_client: Optional[DeepseekClient] = None,
    ):
        self.graph_db = graph_db or get_graph_db()
        self.vector_store = vector_store or get_vector_store()
        self.deepseek_client = deepseek_client

    async def deepseek_chat(self, messages: list[Message]) -> DeepseekResponse:
        """调用 Deepseek AI"""
        if self.deepseek_client is None:
            from .deepseek_adapter import get_client
            self.deepseek_client = get_client()
        return await self.deepseek_client.chat(messages)

    def hybrid_search(
        self,
        query: str,
        query_embedding: Optional[list[float]] = None,
        top_k: int = 10,
        graph_depth: int = 2,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """混合搜索：向量搜索 + 图邻接扩展"""
        # 1. 向量初始召回
        if query_embedding is None:
            query_embedding = self.vector_store.embed(query)

        vector_results = self.vector_store.search(query_embedding, top_k=top_k)
        initial_node_ids = [r["metadata"].get("node_id") for r in vector_results if "node_id" in r["metadata"]]

        # 2. 图遍历扩展
        expanded_nodes: set[str] = set(initial_node_ids)
        expanded_edges: list[GraphEdge] = []

        current_nodes = set(initial_node_ids)
        for depth in range(graph_depth):
            next_nodes: set[str] = set()
            for node_id in current_nodes:
                neighbors = self.graph_db.get_neighbors(node_id)
                for neighbor in neighbors:
                    if neighbor.target not in expanded_nodes:
                        next_nodes.add(neighbor.target)
                        expanded_edges.append(neighbor)
                        expanded_nodes.add(neighbor.target)
            current_nodes = next_nodes
            if not current_nodes:
                break

        # 3. 收集所有节点
        all_nodes: list[GraphNode] = []
        for node_id in expanded_nodes:
            node = self.graph_db.get_node(node_id)
            if node:
                all_nodes.append(node)

        return all_nodes, expanded_edges

    async def reason(
        self,
        bazi_data: Dict[str, Any],
        query: str = "请进行命理推理",
    ) -> FusedKnowledge:
        """基于八字进行知识融合推理"""
        # 1. 从八字提取关键词
        keywords = self._extract_keywords(bazi_data)
        combined_query = " ".join(keywords) + " " + query

        # 2. 混合知识搜索
        nodes, edges = self.hybrid_search(combined_query, top_k=15, graph_depth=2)

        # 3. 检索相关经典文本
        text_chunks = self._search_classic_texts(combined_query)

        # 4. AI 推理生成
        prompt = self._build_reasoning_prompt(bazi_data, nodes, text_chunks, query)
        response = await self.deepseek_chat([
            Message(role="system", content="你是一位精通中国传统命理的资深大师，请结合提供的经典命理知识进行精准推理。"),
            Message(role="user", content=prompt),
        ])

        # 5. 计算相关性分数
        scores = self._compute_relevance(nodes, text_chunks)

        # 6. 构建结果
        result = FusedKnowledge(
            query=query,
            nodes=[n.to_dict() for n in nodes],
            edges=[e.to_dict() for e in edges],
            text_chunks=text_chunks,
            reasoning_chain=response.content,
            relevance_scores=scores,
            depth=2,
        )

        return result

    def _extract_keywords(self, bazi_data: Dict[str, Any]) -> list[str]:
        """从八字数据提取搜索关键词"""
        keywords = []
        pillars = bazi_data.get("pillars", {})
        for p in pillars.values():
            if isinstance(p, str):
                keywords.extend(list(p))

        if "wuxing" in bazi_data and isinstance(bazi_data["wuxing"], dict):
            for wuxing, count in bazi_data["wuxing"].items():
                if count > 0:
                    keywords.append(wuxing)

        if "geju" in bazi_data:
            geju = bazi_data["geju"]
            if isinstance(geju, str) and geju:
                keywords.append(geju)

        if "shensha" in bazi_data and isinstance(bazi_data["shensha"], list):
            for s in bazi_data["shensha"]:
                if isinstance(s, str):
                    keywords.append(s)

        return list(set(keywords))  # 去重

    def _search_classic_texts(self, query: str, top_k: int = 5) -> list[str]:
        """搜索经典文本片段"""
        results = self.vector_store.search_text(query, top_k=top_k)
        chunks = []
        for r in results:
            if "text" in r:
                chunks.append(r["text"])
            elif "content" in r:
                chunks.append(r["content"])
        return chunks[:top_k]

    def _build_reasoning_prompt(
        self,
        bazi_data: Dict[str, Any],
        nodes: list[GraphNode],
        text_chunks: list[str],
        query: str,
    ) -> str:
        """构建推理提示词"""
        pillars = bazi_data.get("pillars", {})
        lines = [
            "### 八字命盘",
            f"年柱：{pillars.get('year', '')}",
            f"月柱：{pillars.get('month', '')}",
            f"日柱：{pillars.get('day', '')}",
            f"时柱：{pillars.get('hour', '')}",
            "",
            "### 命中相关知识",
        ]
        for node in nodes[:8]:
            props = node.properties
            desc = props.get("description", props.get("content", ""))
            if desc:
                lines.append(f"- {node.name}：{desc[:150]}")
        lines.append("")
        lines.append("### 经典命理文献")
        for i, chunk in enumerate(text_chunks):
            lines.append(f"[{i+1}] {chunk[:200]}")
        lines.append("")
        lines.append(f"### 用户问题\n{query}")
        lines.append("")
        lines.append("请结合以上知识，进行命理推理，给出清晰、准确、有深度的分析。")
        return "\n".join(lines)

    def _compute_relevance(self, nodes: list[GraphNode], text_chunks: list[str]) -> Dict[str, float]:
        """计算各节点相关性分数（简化版）"""
        scores: Dict[str, float] = {}
        for i, node in enumerate(nodes):
            # 越靠前分数越高
            scores[node.id] = max(0.0, 1.0 - i * 0.1)
        return scores

    def export_graph_visualization(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> Dict[str, Any]:
        """导出图谱可视化 JSON（适合 D3.js force-directed 或 ECharts 关系图）"""
        vis_nodes = []
        node_map: Dict[str, int] = {}
        for i, node in enumerate(nodes):
            node_map[node.id] = i
            label = node.properties.get("label", node.name)
            vis_nodes.append({
                "id": node.id,
                "name": node.name,
                "label": label,
                "category": node.label,
                "symbolSize": 10 + len(node.name) * 3,
            })

        vis_links = []
        for edge in edges:
            if edge.source in node_map and edge.target in node_map:
                vis_links.append({
                    "source": edge.source,
                    "target": edge.target,
                    "relation": edge.relation,
                    "value": max(1, int(edge.weight * 2)),
                })

        return {
            "nodes": vis_nodes,
            "links": vis_links,
            "categories": sorted(list(set(n.label for n in nodes))),
        }


# ============================================================================
# 可视化导出工具
# ============================================================================

class KnowledgeGraphVisualization:
    """图谱可视化导出工具"""

    @staticmethod
    def to_echarts_json(engine: KnowledgeFusionEngine, nodes, edges) -> str:
        """导出为 ECharts 关系图 JSON 格式"""
        data = engine.export_graph_visualization(nodes, edges)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_d3_json(engine: KnowledgeFusionEngine, nodes, edges) -> str:
        """导出为 D3.js force-directed JSON 格式"""
        exp = engine.export_graph_visualization(nodes, edges)
        d3_data = {
            "nodes": [
                {"id": n["id"], "group": n["category"], "name": n["name"]}
                for n in exp["nodes"]
            ],
            "links": [
                {"source": link["source"], "target": link["target"], "value": link["value"]}
                for link in exp["links"]
            ],
        }
        return json.dumps(d3_data, ensure_ascii=False, indent=2)


# ============================================================================
# 便捷接口与单例
# ============================================================================

def get_fusion_engine() -> KnowledgeFusionEngine:
    """获取知识融合引擎单例"""
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = KnowledgeFusionEngine()
    return _fusion_engine


def inject_classic_text(
    engine: KnowledgeFusionEngine,
    classic_name: str,
    content: str,
    chunk_size: int = 200,
    overlap: int = 20,
) -> int:
    """将经典命理文献分段向量化注入到向量存储

    Args:
        engine: 知识融合引擎
        classic_name: 经典名称 (如 "三命通会", "渊海子平")
        content: 全文内容
        chunk_size: 分段大小
        overlap: 重叠字符数

    Returns:
        注入分段数
    """
    # 简单分段
    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunk = content[start:end].strip()
        if len(chunk) > 50:  # 跳过过短片段
            chunks.append(f"[{classic_name}] {chunk}")
        start = end - overlap
        if start >= end:
            break

    # 注入向量存储
    for chunk in chunks:
        engine.vector_store.add_text(chunk, metadata={
            "source": classic_name,
            "type": "classic_text",
        })

    # 注入知识图谱
    node_id = f"classic:{classic_name}"
    existing = engine.graph_db.get_node(node_id)
    if not existing:
        engine.graph_db.add_node(node_id, "classic", classic_name, properties={"total_chunks": len(chunks)})

    return len(chunks)


# ============================================================================
# 预初始化基础命理知识图谱
# ============================================================================

def init_base_knowledge(engine: KnowledgeFusionEngine) -> int:
    """初始化基础命理知识（天干/地支/五行/十神）到图谱

    Returns:
        注入节点数
    """
    base_nodes = [
        # 五行
        ("wood", "木", "element", "木曰曲直，生长生发"),
        ("fire", "火", "element", "火曰炎上，温热上升"),
        ("earth", "土", "element", "土爰稼穑，生化万物"),
        ("metal", "金", "element", "金曰从革，肃杀收敛"),
        ("water", "水", "element", "水曰润下，寒凉滋润"),
        # 天干
        ("jia", "甲", "gan", "甲木，阳木"),
        ("yi", "乙", "gan", "乙木，阴木"),
        ("bing", "丙", "gan", "丙火，阳火"),
        ("ding", "丁", "gan", "丁火，阴火"),
        ("wu", "戊", "gan", "戊土，阳土"),
        ("ji", "己", "gan", "己土，阴土"),
        ("geng", "庚", "gan", "庚金，阳金"),
        ("xin", "辛", "gan", "辛金，阴金"),
        ("ren", "壬", "gan", "壬水，阳水"),
        ("gui", "癸", "gan", "癸水，阴水"),
        # 地支
        ("zi", "子", "zhi", "子水，正北，冬至"),
        ("chou", "丑", "zhi", "丑土，东北，小寒"),
        ("yin", "寅", "zhi", "寅木，东北，立春"),
        ("mao", "卯", "zhi", "卯木，正东，惊蛰"),
        ("chen", "辰", "zhi", "辰土，东南，清明"),
        ("si", "巳", "zhi", "巳火，东南，立夏"),
        ("wu", "午", "zhi", "午火，正南，芒种"),
        ("wei", "未", "zhi", "未土，西南，小暑"),
        ("shen", "申", "zhi", "申金，西南，立秋"),
        ("you", "酉", "zhi", "酉金，正西，白露"),
        ("xu", "戌", "zhi", "戌土，西北，寒露"),
        ("hai", "亥", "zhi", "亥水，西北，立冬"),
    ]

    count = 0
    for node_id, name, label, desc in base_nodes:
        engine.graph_db.add_node(node_id, label, name, properties={"description": desc})
        count += 1

    # 添加五行相生关系
    relations = [
        ("wood", "fire", "生"),
        ("fire", "earth", "生"),
        ("earth", "metal", "生"),
        ("metal", "water", "生"),
        ("water", "wood", "生"),
        ("wood", "earth", "克"),
        ("earth", "water", "克"),
        ("water", "fire", "克"),
        ("fire", "metal", "克"),
        ("metal", "wood", "克"),
    ]
    for src, tgt, rel in relations:
        engine.graph_db.add_edge(src, tgt, rel)
        count += 1

    return count
