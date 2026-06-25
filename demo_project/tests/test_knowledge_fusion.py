#!/usr/bin/env python3
"""
test_knowledge_fusion.py — 命理知识融合引擎单元测试
覆盖：FusedKnowledge, KnowledgeFusionEngine, KnowledgeGraphVisualization,
       get_fusion_engine, inject_classic_text, init_base_knowledge
"""
import os
import sys
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.knowledge_fusion import (
    FusedKnowledge,
    KnowledgeFusionEngine,
    KnowledgeGraphVisualization,
    get_fusion_engine,
    inject_classic_text,
    init_base_knowledge,
)
from tengod.graph_engine import GraphNode, GraphEdge, KnowledgeGraphDB
from tengod.deepseek_adapter import DeepseekClient, DeepseekResponse, Message


# ============================================================================
# 共享引擎实例 — 避免每个测试都创建 VectorStore（FAISS 初始化很慢）
# ============================================================================

@pytest.fixture(scope="module")
def engine():
    """模块级共享的 KnowledgeFusionEngine 实例"""
    return KnowledgeFusionEngine()


# ============================================================================
# 辅助工厂函数
# ============================================================================

def make_graph_node(node_id: str, node_label: str, name: str, **props) -> GraphNode:
    """创建 GraphNode 辅助函数"""
    return GraphNode(id=node_id, label=node_label, name=name, properties=props)


def make_graph_edge(source: str, target: str, relation: str, weight: float = 1.0) -> GraphEdge:
    """创建 GraphEdge 辅助函数"""
    return GraphEdge(source=source, target=target, relation=relation, weight=weight)


def make_full_bazi_data() -> dict:
    """构造完整的八字数据"""
    return {
        "pillars": {
            "year": "甲子",
            "month": "丙寅",
            "day": "戊辰",
            "hour": "壬申",
        },
        "wuxing": {"木": 2, "火": 1, "土": 3, "金": 1, "水": 1},
        "geju": "正官格",
        "shensha": ["天乙贵人", "文昌", "桃花"],
    }


def make_mock_graph(**kwargs) -> MagicMock:
    """创建 mock KnowledgeGraphDB（不限制 spec 以允许 get_neighbors）"""
    mock = MagicMock()
    for k, v in kwargs.items():
        setattr(mock, k, v)
    return mock


# ============================================================================
# 1. FusedKnowledge 数据类
# ============================================================================

class TestFusedKnowledge:
    """FusedKnowledge 数据类测试"""

    def test_create_default(self):
        fk = FusedKnowledge(
            query="测试",
            nodes=[],
            edges=[],
            text_chunks=[],
            reasoning_chain="",
            relevance_scores={},
        )
        assert fk.query == "测试"
        assert fk.nodes == []
        assert fk.edges == []
        assert fk.text_chunks == []
        assert fk.reasoning_chain == ""
        assert fk.relevance_scores == {}
        assert fk.depth == 2

    def test_create_with_data(self):
        nodes = [{"id": "n1", "name": "节点1"}]
        edges = [{"source": "n1", "target": "n2"}]
        fk = FusedKnowledge(
            query="八字分析",
            nodes=nodes,
            edges=edges,
            text_chunks=["古籍片段"],
            reasoning_chain="推理结果",
            relevance_scores={"n1": 0.9},
            depth=3,
        )
        assert fk.query == "八字分析"
        assert fk.nodes == nodes
        assert fk.edges == edges
        assert fk.text_chunks == ["古籍片段"]
        assert fk.reasoning_chain == "推理结果"
        assert fk.relevance_scores == {"n1": 0.9}
        assert fk.depth == 3

    def test_to_dict(self):
        fk = FusedKnowledge(
            query="q",
            nodes=[{"a": 1}],
            edges=[{"b": 2}],
            text_chunks=["t1"],
            reasoning_chain="推理",
            relevance_scores={"k": 0.5},
            depth=1,
        )
        d = fk.to_dict()
        assert d["query"] == "q"
        assert d["nodes"] == [{"a": 1}]
        assert d["edges"] == [{"b": 2}]
        assert d["text_chunks"] == ["t1"]
        assert d["reasoning_chain"] == "推理"
        assert d["relevance_scores"] == {"k": 0.5}
        assert d["depth"] == 1

    def test_to_json(self):
        fk = FusedKnowledge(
            query="测试查询",
            nodes=[{"id": "n1", "name": "木"}],
            edges=[],
            text_chunks=[],
            reasoning_chain="分析结果",
            relevance_scores={"n1": 1.0},
        )
        json_str = fk.to_json()
        data = json.loads(json_str)
        assert data["query"] == "测试查询"
        assert data["nodes"][0]["name"] == "木"
        assert data["reasoning_chain"] == "分析结果"
        assert "测试查询" in json_str
        assert "木" in json_str

    def test_to_json_roundtrip(self):
        fk = FusedKnowledge(
            query="x",
            nodes=[{"k": "v"}],
            edges=[],
            text_chunks=["chunk"],
            reasoning_chain="rc",
            relevance_scores={"a": 0.7},
            depth=2,
        )
        data = json.loads(fk.to_json())
        assert data == fk.to_dict()


# ============================================================================
# 2. KnowledgeFusionEngine 初始化
# ============================================================================

class TestKnowledgeFusionEngineInit:
    """KnowledgeFusionEngine 初始化测试"""

    def test_init_with_mocks(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_deepseek = MagicMock(spec=DeepseekClient)
        engine = KnowledgeFusionEngine(
            graph_db=mock_graph,
            vector_store=mock_vector,
            deepseek_client=mock_deepseek,
        )
        assert engine.graph_db is mock_graph
        assert engine.vector_store is mock_vector
        assert engine.deepseek_client is mock_deepseek

    def test_init_defaults(self, engine):
        """默认初始化（使用共享 fixture）"""
        assert engine.graph_db is not None
        assert engine.vector_store is not None
        assert engine.deepseek_client is None

    def test_init_partial(self):
        mock_graph = make_mock_graph()
        engine = KnowledgeFusionEngine(graph_db=mock_graph)
        assert engine.graph_db is mock_graph
        assert engine.vector_store is not None
        assert engine.deepseek_client is None


# ============================================================================
# 3. _extract_keywords
# ============================================================================

class TestExtractKeywords:
    """_extract_keywords 方法测试"""

    def test_full_bazi_data(self, engine):
        bazi = make_full_bazi_data()
        keywords = engine._extract_keywords(bazi)
        for ch in ["甲", "子", "丙", "寅", "戊", "辰", "壬", "申"]:
            assert ch in keywords
        for w in ["木", "火", "土", "金", "水"]:
            assert w in keywords
        assert "正官格" in keywords
        for s in ["天乙贵人", "文昌", "桃花"]:
            assert s in keywords

    def test_empty_bazi(self, engine):
        keywords = engine._extract_keywords({})
        assert keywords == []

    def test_no_pillars(self, engine):
        keywords = engine._extract_keywords({"wuxing": {"木": 1}})
        assert "木" in keywords
        assert len(keywords) == 1

    def test_no_wuxing(self, engine):
        keywords = engine._extract_keywords({
            "pillars": {"year": "甲子", "month": "乙丑"},
        })
        assert "甲" in keywords
        assert "子" in keywords
        assert "乙" in keywords
        assert "丑" in keywords

    def test_no_geju(self, engine):
        bazi = make_full_bazi_data()
        del bazi["geju"]
        keywords = engine._extract_keywords(bazi)
        assert "正官格" not in keywords

    def test_no_shensha(self, engine):
        bazi = make_full_bazi_data()
        del bazi["shensha"]
        keywords = engine._extract_keywords(bazi)
        assert "天乙贵人" not in keywords

    def test_geju_empty_string(self, engine):
        keywords = engine._extract_keywords({"geju": ""})
        assert "正官格" not in keywords

    def test_geju_not_string(self, engine):
        keywords = engine._extract_keywords({"geju": 123})
        assert 123 not in keywords

    def test_shensha_contains_non_string(self, engine):
        keywords = engine._extract_keywords({"shensha": ["天乙贵人", 123, "文昌"]})
        assert "天乙贵人" in keywords
        assert "文昌" in keywords
        assert 123 not in keywords

    def test_wuxing_zero_count(self, engine):
        keywords = engine._extract_keywords({"wuxing": {"木": 0, "火": 1, "土": 0}})
        assert "木" not in keywords
        assert "火" in keywords
        assert "土" not in keywords

    def test_wuxing_not_dict(self, engine):
        keywords = engine._extract_keywords({"wuxing": "invalid"})
        assert isinstance(keywords, list)

    def test_pillars_value_not_string(self, engine):
        keywords = engine._extract_keywords({"pillars": {"year": 123, "month": None}})
        assert isinstance(keywords, list)

    def test_deduplication(self, engine):
        bazi = {
            "pillars": {"year": "甲甲甲"},
            "wuxing": {"木": 1},
            "geju": "木",
            "shensha": ["甲", "木"],
        }
        keywords = engine._extract_keywords(bazi)
        assert keywords.count("甲") <= 1
        assert keywords.count("木") <= 1

    def test_shensha_not_list(self, engine):
        keywords = engine._extract_keywords({"shensha": "not_a_list"})
        assert isinstance(keywords, list)


# ============================================================================
# 4. _build_reasoning_prompt
# ============================================================================

class TestBuildReasoningPrompt:
    """_build_reasoning_prompt 方法测试"""

    def test_basic_prompt(self, engine):
        bazi = make_full_bazi_data()
        nodes = [
            make_graph_node("n1", "wuxing", "木", description="木曰曲直，生长生发"),
        ]
        prompt = engine._build_reasoning_prompt(bazi, nodes, ["古籍内容"], "测试查询")
        assert "八字命盘" in prompt
        assert "年柱：甲子" in prompt
        assert "月柱：丙寅" in prompt
        assert "日柱：戊辰" in prompt
        assert "时柱：壬申" in prompt
        assert "命中相关知识" in prompt
        assert "木" in prompt
        assert "经典命理文献" in prompt
        assert "古籍内容" in prompt
        assert "用户问题" in prompt
        assert "测试查询" in prompt

    def test_empty_nodes(self, engine):
        bazi = make_full_bazi_data()
        prompt = engine._build_reasoning_prompt(bazi, [], [], "查询")
        assert "命中相关知识" in prompt
        assert "经典命理文献" in prompt
        assert "查询" in prompt

    def test_nodes_without_description(self, engine):
        bazi = make_full_bazi_data()
        node = make_graph_node("n1", "test", "测试")
        node.properties = {}
        prompt = engine._build_reasoning_prompt(bazi, [node], [], "查询")
        assert isinstance(prompt, str)

    def test_nodes_with_content_instead_of_description(self, engine):
        bazi = make_full_bazi_data()
        node = make_graph_node("n1", "test", "测试", content="内容文本")
        prompt = engine._build_reasoning_prompt(bazi, [node], [], "查询")
        assert "内容文本" in prompt

    def test_nodes_truncated_at_8(self, engine):
        bazi = make_full_bazi_data()
        nodes = [
            make_graph_node(f"n{i}", "test", f"节点{i}", description=f"描述{i}")
            for i in range(15)
        ]
        prompt = engine._build_reasoning_prompt(bazi, nodes, [], "查询")
        assert "描述0" in prompt
        assert "描述7" in prompt
        assert "描述8" not in prompt

    def test_description_truncated_at_150(self, engine):
        bazi = make_full_bazi_data()
        long_desc = "X" * 200
        node = make_graph_node("n1", "test", "测试", description=long_desc)
        prompt = engine._build_reasoning_prompt(bazi, [node], [], "查询")
        assert long_desc[:150] in prompt
        assert long_desc not in prompt

    def test_empty_pillars(self, engine):
        bazi = {"pillars": {}}
        prompt = engine._build_reasoning_prompt(bazi, [], [], "查询")
        assert "年柱：" in prompt
        assert "月柱：" in prompt

    def test_multiple_text_chunks(self, engine):
        bazi = make_full_bazi_data()
        chunks = ["片段1", "片段2", "片段3"]
        prompt = engine._build_reasoning_prompt(bazi, [], chunks, "查询")
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "[3]" in prompt
        assert "片段1" in prompt
        assert "片段2" in prompt

    def test_text_chunk_truncated_at_200(self, engine):
        bazi = make_full_bazi_data()
        long_text = "Y" * 250
        prompt = engine._build_reasoning_prompt(bazi, [], [long_text], "查询")
        assert long_text[:200] in prompt
        assert long_text not in prompt


# ============================================================================
# 5. _compute_relevance
# ============================================================================

class TestComputeRelevance:
    """_compute_relevance 方法测试"""

    def test_empty_nodes(self, engine):
        scores = engine._compute_relevance([], [])
        assert scores == {}

    def test_single_node(self, engine):
        node = make_graph_node("n1", "test", "测试")
        scores = engine._compute_relevance([node], [])
        assert scores["n1"] == 1.0

    def test_two_nodes(self, engine):
        nodes = [
            make_graph_node("n1", "test", "A"),
            make_graph_node("n2", "test", "B"),
        ]
        scores = engine._compute_relevance(nodes, [])
        assert scores["n1"] == 1.0
        assert scores["n2"] == 0.9

    def test_ten_nodes(self, engine):
        nodes = [make_graph_node(f"n{i}", "test", f"节点{i}") for i in range(10)]
        scores = engine._compute_relevance(nodes, [])
        assert scores["n0"] == 1.0
        assert scores["n9"] == pytest.approx(0.1)

    def test_eleven_nodes_min_score_zero(self, engine):
        nodes = [make_graph_node(f"n{i}", "test", f"节点{i}") for i in range(15)]
        scores = engine._compute_relevance(nodes, [])
        assert scores["n0"] == 1.0
        assert scores["n10"] == 0.0
        assert scores["n14"] == 0.0

    def test_text_chunks_ignored(self, engine):
        node = make_graph_node("n1", "test", "测试")
        scores = engine._compute_relevance([node], ["chunk1", "chunk2"])
        assert scores["n1"] == 1.0


# ============================================================================
# 6. export_graph_visualization
# ============================================================================

class TestExportGraphVisualization:
    """export_graph_visualization 方法测试"""

    def test_basic_export(self, engine):
        nodes = [
            make_graph_node("n1", "wuxing", "木", label="五行"),
            make_graph_node("n2", "gan", "甲", label="天干"),
        ]
        edges = [make_graph_edge("n1", "n2", "关联")]
        result = engine.export_graph_visualization(nodes, edges)
        assert "nodes" in result
        assert "links" in result
        assert "categories" in result
        assert len(result["nodes"]) == 2
        assert len(result["links"]) == 1
        assert result["categories"] == ["gan", "wuxing"]

    def test_nodes_with_different_labels(self, engine):
        nodes = [
            make_graph_node("n1", "element", "木", label="五行"),
            make_graph_node("n2", "gan", "甲", label="天干"),
            make_graph_node("n3", "zhi", "子", label="地支"),
        ]
        result = engine.export_graph_visualization(nodes, [])
        assert len(result["nodes"]) == 3
        assert result["categories"] == ["element", "gan", "zhi"]

    def test_node_without_label_property(self, engine):
        node = make_graph_node("n1", "test", "测试节点")
        node.properties = {}
        result = engine.export_graph_visualization([node], [])
        assert result["nodes"][0]["label"] == "测试节点"

    def test_symbol_size_calculation(self, engine):
        short_node = make_graph_node("n1", "t", "短")
        long_node = make_graph_node("n2", "t", "很长的名字")
        result = engine.export_graph_visualization([short_node, long_node], [])
        sizes = [n["symbolSize"] for n in result["nodes"]]
        assert sizes[0] == 10 + len("短") * 3
        assert sizes[1] == 10 + len("很长的名字") * 3
        assert sizes[1] > sizes[0]

    def test_empty_nodes(self, engine):
        result = engine.export_graph_visualization([], [])
        assert result["nodes"] == []
        assert result["links"] == []
        assert result["categories"] == []

    def test_empty_edges(self, engine):
        nodes = [make_graph_node("n1", "test", "测试")]
        result = engine.export_graph_visualization(nodes, [])
        assert len(result["links"]) == 0

    def test_edges_referencing_non_existent_nodes(self, engine):
        nodes = [make_graph_node("n1", "test", "A")]
        edges = [
            make_graph_edge("n1", "n2", "关联"),
            make_graph_edge("n3", "n1", "关联"),
        ]
        result = engine.export_graph_visualization(nodes, edges)
        assert len(result["links"]) == 0

    def test_edge_weight_value(self, engine):
        nodes = [
            make_graph_node("n1", "test", "A"),
            make_graph_node("n2", "test", "B"),
        ]
        edges = [make_graph_edge("n1", "n2", "关联", weight=0.4)]
        result = engine.export_graph_visualization(nodes, edges)
        assert result["links"][0]["value"] == max(1, int(0.4 * 2))

    def test_edge_weight_high_value(self, engine):
        nodes = [
            make_graph_node("n1", "test", "A"),
            make_graph_node("n2", "test", "B"),
        ]
        edges = [make_graph_edge("n1", "n2", "关联", weight=5.0)]
        result = engine.export_graph_visualization(nodes, edges)
        assert result["links"][0]["value"] == 10

    def test_export_relation_field(self, engine):
        nodes = [
            make_graph_node("n1", "test", "A"),
            make_graph_node("n2", "test", "B"),
        ]
        edges = [make_graph_edge("n1", "n2", "相生")]
        result = engine.export_graph_visualization(nodes, edges)
        assert result["links"][0]["relation"] == "相生"


# ============================================================================
# 7. hybrid_search
# ============================================================================

class TestHybridSearch:
    """hybrid_search 方法测试"""

    def test_basic_search(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.1, 0.2, 0.3]
        mock_vector.search.return_value = [
            {"metadata": {"node_id": "n1"}},
            {"metadata": {"node_id": "n2"}},
        ]
        mock_graph.get_neighbors.return_value = []
        n1 = make_graph_node("n1", "test", "节点1")
        n2 = make_graph_node("n2", "test", "节点2")
        mock_graph.get_node.side_effect = lambda nid: {"n1": n1, "n2": n2}.get(nid)

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        nodes, edges = engine.hybrid_search("测试查询", top_k=10, graph_depth=2)

        assert len(nodes) == 2
        node_ids = {n.id for n in nodes}
        assert node_ids == {"n1", "n2"}
        assert edges == []

    def test_search_with_query_embedding_provided(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.search.return_value = []
        mock_graph.get_neighbors.return_value = []

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        engine.hybrid_search("查询", query_embedding=[0.5, 0.6], top_k=5)

        mock_vector.embed.assert_not_called()
        mock_vector.search.assert_called_once_with([0.5, 0.6], top_k=5)

    def test_search_with_no_query_embedding(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.7, 0.8]
        mock_vector.search.return_value = []
        mock_graph.get_neighbors.return_value = []

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        engine.hybrid_search("查询", top_k=5)

        mock_vector.embed.assert_called_once_with("查询")
        mock_vector.search.assert_called_once_with([0.7, 0.8], top_k=5)

    def test_empty_vector_results(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = []

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        nodes, edges = engine.hybrid_search("查询")

        assert nodes == []
        assert edges == []

    def test_vector_results_without_node_id(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = [
            {"metadata": {}},
            {"metadata": {"node_id": "n1"}},
            {"metadata": {"other": "val"}},
        ]
        mock_graph.get_neighbors.return_value = []
        n1 = make_graph_node("n1", "test", "节点1")
        mock_graph.get_node.return_value = n1

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        nodes, edges = engine.hybrid_search("查询")

        assert len(nodes) == 1
        assert nodes[0].id == "n1"

    def test_graph_expansion(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = [{"metadata": {"node_id": "n1"}}]

        edge_n1_n2 = make_graph_edge("n1", "n2", "关联")
        mock_graph.get_neighbors.side_effect = lambda nid: (
            [edge_n1_n2] if nid == "n1" else []
        )

        n1 = make_graph_node("n1", "test", "节点1")
        n2 = make_graph_node("n2", "test", "节点2")
        mock_graph.get_node.side_effect = lambda nid: {"n1": n1, "n2": n2}.get(nid)

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        nodes, edges = engine.hybrid_search("查询", graph_depth=2)

        assert len(nodes) == 2
        node_ids = {n.id for n in nodes}
        assert node_ids == {"n1", "n2"}
        assert len(edges) == 1
        assert edges[0].source == "n1"
        assert edges[0].target == "n2"

    def test_graph_expansion_depth_1(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = [{"metadata": {"node_id": "n1"}}]
        mock_graph.get_neighbors.return_value = []
        n1 = make_graph_node("n1", "test", "节点1")
        mock_graph.get_node.return_value = n1

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        nodes, edges = engine.hybrid_search("查询", graph_depth=1)

        assert len(nodes) == 1
        assert nodes[0].id == "n1"
        assert mock_graph.get_neighbors.call_count == 1

    def test_graph_expansion_duplicate_prevention(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = [
            {"metadata": {"node_id": "n1"}},
            {"metadata": {"node_id": "n2"}},
        ]

        edge = make_graph_edge("n1", "n2", "关联")
        mock_graph.get_neighbors.side_effect = lambda nid: (
            [edge] if nid == "n1" else []
        )

        n1 = make_graph_node("n1", "test", "A")
        n2 = make_graph_node("n2", "test", "B")
        mock_graph.get_node.side_effect = lambda nid: {"n1": n1, "n2": n2}.get(nid)

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        nodes, edges = engine.hybrid_search("查询", graph_depth=2)

        assert len(nodes) == 2

    def test_graph_expansion_no_neighbors(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = [{"metadata": {"node_id": "n1"}}]
        mock_graph.get_neighbors.return_value = []
        n1 = make_graph_node("n1", "test", "A")
        mock_graph.get_node.return_value = n1

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        nodes, edges = engine.hybrid_search("查询", graph_depth=3)

        assert len(nodes) == 1
        assert mock_graph.get_neighbors.call_count == 1

    def test_hybrid_search_returns_graph_nodes(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = [{"metadata": {"node_id": "n1"}}]
        mock_graph.get_neighbors.return_value = []
        n1 = make_graph_node("n1", "test", "A")
        mock_graph.get_node.return_value = n1

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        nodes, edges = engine.hybrid_search("查询")

        assert isinstance(nodes, list)
        assert isinstance(edges, list)
        assert isinstance(nodes[0], GraphNode)


# ============================================================================
# 8. deepseek_chat
# ============================================================================

class TestDeepseekChat:
    """deepseek_chat 方法测试"""

    @pytest.mark.asyncio
    async def test_chat_with_client(self):
        mock_client = MagicMock(spec=DeepseekClient)
        mock_client.chat = AsyncMock(return_value=DeepseekResponse(
            content="推理结果",
            model="test-model",
            usage={"tokens": 10},
            finish_reason="stop",
        ))
        engine = KnowledgeFusionEngine(deepseek_client=mock_client)
        messages = [Message(role="user", content="测试")]
        response = await engine.deepseek_chat(messages)
        assert response.content == "推理结果"
        assert response.model == "test-model"
        mock_client.chat.assert_called_once_with(messages)

    @pytest.mark.asyncio
    async def test_chat_lazy_init(self):
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value=DeepseekResponse(
            content="惰性初始化结果",
            model="test-model",
            usage={"tokens": 5},
            finish_reason="stop",
        ))

        with patch("tengod.deepseek_adapter.get_client", return_value=mock_client):
            engine = KnowledgeFusionEngine()
            assert engine.deepseek_client is None
            messages = [Message(role="user", content="测试")]
            response = await engine.deepseek_chat(messages)
            assert response.content == "惰性初始化结果"
            assert engine.deepseek_client is mock_client
            mock_client.chat.assert_called_once_with(messages)

    @pytest.mark.asyncio
    async def test_chat_multiple_messages(self):
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value=DeepseekResponse(
            content="多轮结果",
            model="test",
            usage={"tokens": 20},
            finish_reason="stop",
        ))
        engine = KnowledgeFusionEngine(deepseek_client=mock_client)
        messages = [
            Message(role="system", content="你是大师"),
            Message(role="user", content="分析八字"),
        ]
        response = await engine.deepseek_chat(messages)
        assert response.content == "多轮结果"
        mock_client.chat.assert_called_once_with(messages)


# ============================================================================
# 9. reason (端到端)
# ============================================================================

class TestReason:
    """reason 融合推理管道测试"""

    @pytest.mark.asyncio
    async def test_reason_end_to_end(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_client = MagicMock()

        mock_vector.embed.return_value = [0.1, 0.2]
        mock_vector.search.return_value = [{"metadata": {"node_id": "n1"}}]
        mock_vector.search_text.return_value = [
            {"text": "古籍片段1"},
            {"text": "古籍片段2"},
        ]
        mock_graph.get_neighbors.return_value = []
        n1 = make_graph_node("n1", "wuxing", "木", description="木曰曲直")
        mock_graph.get_node.return_value = n1

        mock_client.chat = AsyncMock(return_value=DeepseekResponse(
            content="命理推理结果",
            model="test",
            usage={"tokens": 50},
            finish_reason="stop",
        ))

        engine = KnowledgeFusionEngine(
            graph_db=mock_graph,
            vector_store=mock_vector,
            deepseek_client=mock_client,
        )
        result = await engine.reason(make_full_bazi_data(), "测试查询")

        assert isinstance(result, FusedKnowledge)
        assert result.query == "测试查询"
        assert result.reasoning_chain == "命理推理结果"
        assert len(result.nodes) == 1
        assert result.nodes[0]["id"] == "n1"
        assert len(result.text_chunks) == 2
        assert result.depth == 2
        assert "n1" in result.relevance_scores

    @pytest.mark.asyncio
    async def test_reason_default_query(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_client = MagicMock()

        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = []
        mock_vector.search_text.return_value = []
        mock_graph.get_neighbors.return_value = []
        mock_client.chat = AsyncMock(return_value=DeepseekResponse(
            content="默认推理",
            model="test",
            usage={"tokens": 10},
            finish_reason="stop",
        ))

        engine = KnowledgeFusionEngine(
            graph_db=mock_graph,
            vector_store=mock_vector,
            deepseek_client=mock_client,
        )
        result = await engine.reason(make_full_bazi_data())
        assert result.query == "请进行命理推理"

    @pytest.mark.asyncio
    async def test_reason_with_empty_bazi(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_client = MagicMock()

        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = []
        mock_vector.search_text.return_value = []
        mock_graph.get_neighbors.return_value = []
        mock_client.chat = AsyncMock(return_value=DeepseekResponse(
            content="空数据推理",
            model="test",
            usage={"tokens": 5},
            finish_reason="stop",
        ))

        engine = KnowledgeFusionEngine(
            graph_db=mock_graph,
            vector_store=mock_vector,
            deepseek_client=mock_client,
        )
        result = await engine.reason({}, "查询")
        assert isinstance(result, FusedKnowledge)
        assert result.reasoning_chain == "空数据推理"


# ============================================================================
# 10. KnowledgeGraphVisualization
# ============================================================================

class TestKnowledgeGraphVisualization:
    """KnowledgeGraphVisualization 测试"""

    def test_to_echarts_json(self):
        mock_engine = MagicMock(spec=KnowledgeFusionEngine)
        mock_engine.export_graph_visualization.return_value = {
            "nodes": [{"id": "n1", "name": "木", "label": "五行", "category": "wuxing", "symbolSize": 20}],
            "links": [{"source": "n1", "target": "n2", "relation": "生", "value": 2}],
            "categories": ["wuxing"],
        }
        nodes = [make_graph_node("n1", "wuxing", "木")]
        edges = [make_graph_edge("n1", "n2", "生")]
        result = KnowledgeGraphVisualization.to_echarts_json(mock_engine, nodes, edges)
        data = json.loads(result)
        assert data["nodes"][0]["id"] == "n1"
        assert data["categories"] == ["wuxing"]

    def test_to_d3_json(self):
        mock_engine = MagicMock(spec=KnowledgeFusionEngine)
        mock_engine.export_graph_visualization.return_value = {
            "nodes": [
                {"id": "n1", "name": "木", "label": "五行", "category": "wuxing", "symbolSize": 20},
                {"id": "n2", "name": "火", "label": "五行", "category": "wuxing", "symbolSize": 20},
            ],
            "links": [{"source": "n1", "target": "n2", "relation": "生", "value": 2}],
            "categories": ["wuxing"],
        }
        nodes = [
            make_graph_node("n1", "wuxing", "木"),
            make_graph_node("n2", "wuxing", "火"),
        ]
        edges = [make_graph_edge("n1", "n2", "生")]
        result = KnowledgeGraphVisualization.to_d3_json(mock_engine, nodes, edges)
        data = json.loads(result)
        assert data["nodes"][0]["group"] == "wuxing"
        assert data["nodes"][0]["name"] == "木"
        assert "category" not in data["nodes"][0]
        assert len(data["links"]) == 1
        assert data["links"][0]["source"] == "n1"
        assert data["links"][0]["target"] == "n2"

    def test_to_d3_json_empty(self):
        mock_engine = MagicMock(spec=KnowledgeFusionEngine)
        mock_engine.export_graph_visualization.return_value = {
            "nodes": [],
            "links": [],
            "categories": [],
        }
        result = KnowledgeGraphVisualization.to_d3_json(mock_engine, [], [])
        data = json.loads(result)
        assert data["nodes"] == []
        assert data["links"] == []


# ============================================================================
# 11. get_fusion_engine 单例
# ============================================================================

class TestGetFusionEngine:
    """get_fusion_engine 单例测试"""

    def test_singleton_same_instance(self):
        import tengod.knowledge_fusion as kf
        kf._fusion_engine = None
        engine1 = get_fusion_engine()
        engine2 = get_fusion_engine()
        assert engine1 is engine2
        assert isinstance(engine1, KnowledgeFusionEngine)

    def test_singleton_returns_engine(self):
        import tengod.knowledge_fusion as kf
        kf._fusion_engine = None
        engine = get_fusion_engine()
        assert isinstance(engine, KnowledgeFusionEngine)


# ============================================================================
# 12. inject_classic_text
# ============================================================================

class TestInjectClassicText:
    """inject_classic_text 测试 — 注意：overlap=0 避免死循环"""

    def test_basic_injection(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        count = inject_classic_text(mock_engine, "三命通会", "命" * 300, chunk_size=100, overlap=0)

        assert count > 0
        assert mock_engine.vector_store.add_text.call_count == count
        mock_engine.graph_db.add_node.assert_called_once()

    def test_injection_node_already_exists(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = MagicMock()

        count = inject_classic_text(mock_engine, "三命通会", "命" * 300, chunk_size=100, overlap=0)

        assert count > 0
        mock_engine.vector_store.add_text.assert_called()
        mock_engine.graph_db.add_node.assert_not_called()

    def test_short_content(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        count = inject_classic_text(mock_engine, "短篇", "短内容", chunk_size=200, overlap=0)

        assert count == 0
        mock_engine.vector_store.add_text.assert_not_called()

    def test_chunk_prefix(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        inject_classic_text(mock_engine, "渊海子平", "X" * 200, chunk_size=60, overlap=0)

        calls = mock_engine.vector_store.add_text.call_args_list
        for call in calls:
            args, _ = call
            assert "[渊海子平]" in args[0]

    def test_metadata_passed(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        inject_classic_text(mock_engine, "三命通会", "X" * 200, chunk_size=60, overlap=0)

        calls = mock_engine.vector_store.add_text.call_args_list
        for call in calls:
            _, kwargs = call
            assert kwargs["metadata"]["source"] == "三命通会"
            assert kwargs["metadata"]["type"] == "classic_text"

    def test_default_chunk_params(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        content = "X" * 500
        count = inject_classic_text(mock_engine, "经典", content, chunk_size=200, overlap=0)

        # overlap=0 时每个 chunk 后 start=end，只生成一个 chunk
        assert count > 0

    def test_graph_node_properties(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        count = inject_classic_text(mock_engine, "三命通会", "X" * 200, chunk_size=60, overlap=0)

        mock_engine.graph_db.add_node.assert_called_once_with(
            "classic:三命通会", "classic", "三命通会", properties={"total_chunks": count}
        )


# ============================================================================
# 13. init_base_knowledge
# ============================================================================

class TestInitBaseKnowledge:
    """init_base_knowledge 测试"""

    def test_init_base_knowledge(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)

        count = init_base_knowledge(mock_engine)

        # 5 (五行) + 10 (天干) + 12 (地支) = 27 节点 + 10 边 = 37
        assert count == 37
        assert mock_engine.graph_db.add_node.call_count == 27
        assert mock_engine.graph_db.add_edge.call_count == 10

    def test_init_node_calls(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)

        init_base_knowledge(mock_engine)

        first_call = mock_engine.graph_db.add_node.call_args_list[0]
        args, kwargs = first_call
        assert args[0] == "wood"
        assert args[1] == "element"
        assert args[2] == "木"
        assert "description" in kwargs["properties"]

    def test_init_edge_calls(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)

        init_base_knowledge(mock_engine)

        first_edge = mock_engine.graph_db.add_edge.call_args_list[0]
        args, _ = first_edge
        assert args[0] == "wood"
        assert args[1] == "fire"
        assert args[2] == "生"


# ============================================================================
# 14. 边界情况与异常处理
# ============================================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_bazi_all_fields(self, engine):
        keywords = engine._extract_keywords({})
        assert keywords == []

    def test_hybrid_search_no_embedding(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_vector.embed.return_value = [0.0]
        mock_vector.search.return_value = []
        mock_graph.get_neighbors.return_value = []

        engine = KnowledgeFusionEngine(graph_db=mock_graph, vector_store=mock_vector)
        engine.hybrid_search("查询", query_embedding=None)

        mock_vector.embed.assert_called_once_with("查询")

    def test_export_empty_nodes(self, engine):
        result = engine.export_graph_visualization([], [])
        assert result == {"nodes": [], "links": [], "categories": []}

    def test_export_edges_non_existent_nodes(self, engine):
        nodes = [make_graph_node("n1", "test", "A")]
        edges = [
            make_graph_edge("n1", "missing", "关联"),
            make_graph_edge("missing", "n1", "关联"),
        ]
        result = engine.export_graph_visualization(nodes, edges)
        assert len(result["links"]) == 0

    def test_inject_short_content(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        content = "X" * 45
        count = inject_classic_text(mock_engine, "短篇", content, chunk_size=200, overlap=0)

        assert count == 0
        mock_engine.vector_store.add_text.assert_not_called()

    def test_inject_exact_boundary_content(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        content = "X" * 51
        count = inject_classic_text(mock_engine, "边界测试", content, chunk_size=200, overlap=0)

        assert count == 1
        mock_engine.vector_store.add_text.assert_called_once()

    def test_inject_normal_boundary(self):
        mock_engine = MagicMock()
        mock_engine.graph_db = MagicMock(spec=KnowledgeGraphDB)
        mock_engine.graph_db.get_node.return_value = None

        content = "X" * 250
        count = inject_classic_text(mock_engine, "边界测试", content, chunk_size=100, overlap=0)

        # overlap=0 时只生成一个 chunk: content[0:100]
        assert count == 1

    def test_fused_knowledge_mutable(self):
        fk = FusedKnowledge(
            query="q",
            nodes=[],
            edges=[],
            text_chunks=[],
            reasoning_chain="",
            relevance_scores={},
        )
        fk.query = "modified"
        assert fk.query == "modified"

    @pytest.mark.asyncio
    async def test_reason_empty_results(self):
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_client = MagicMock()

        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = []
        mock_vector.search_text.return_value = []
        mock_graph.get_neighbors.return_value = []
        mock_client.chat = AsyncMock(return_value=DeepseekResponse(
            content="无知识推理",
            model="test",
            usage={"tokens": 5},
            finish_reason="stop",
        ))

        engine = KnowledgeFusionEngine(
            graph_db=mock_graph,
            vector_store=mock_vector,
            deepseek_client=mock_client,
        )
        result = await engine.reason(make_full_bazi_data(), "查询")

        assert result.nodes == []
        assert result.edges == []
        assert result.text_chunks == []
        assert result.relevance_scores == {}
        assert result.reasoning_chain == "无知识推理"

    @pytest.mark.asyncio
    async def test_reason_search_text_returns_content_key(self):
        """_search_classic_texts 处理 'content' 键（覆盖 elif 分支）"""
        mock_graph = make_mock_graph()
        mock_vector = MagicMock()
        mock_client = MagicMock()

        mock_vector.embed.return_value = [0.1]
        mock_vector.search.return_value = []
        mock_vector.search_text.return_value = [
            {"content": "古籍内容A"},
            {"content": "古籍内容B"},
        ]
        mock_graph.get_neighbors.return_value = []
        mock_client.chat = AsyncMock(return_value=DeepseekResponse(
            content="推理结果",
            model="test",
            usage={"tokens": 10},
            finish_reason="stop",
        ))

        engine = KnowledgeFusionEngine(
            graph_db=mock_graph,
            vector_store=mock_vector,
            deepseek_client=mock_client,
        )
        result = await engine.reason(make_full_bazi_data(), "查询")

        assert len(result.text_chunks) == 2
        assert "古籍内容A" in result.text_chunks
        assert "古籍内容B" in result.text_chunks