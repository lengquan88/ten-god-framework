"""
test_knowledge_evolution.py — 知识进化引擎测试 v2.9
=====================================================
测试覆盖：
- FeedbackRecord: 创建/综合评分/序列化
- ConfidenceProfile: 创建/序列化
- KnowledgeNode: 创建/序列化
- KnowledgeEdge: 创建/序列化
- EvolutionResult: 创建/序列化
- KnowledgeEvolution 初始化与种子知识图谱
- 反馈收集: collect_feedback / 标签提取
- 置信度调整: 贝叶斯式更新 / 手动调整
- 知识图谱操作: 添加节点/边/邻居查询
- 知识图谱自动补全: 传递推理/对称补全/跨域关联
- 进化主循环: evolve 方法
- 统计与查询: 进化统计/反馈趋势/图谱统计
- 重置: reset 方法
"""

import pytest
from dataclasses import asdict

from tengod.knowledge_evolution import (
    FeedbackRecord,
    ConfidenceProfile,
    KnowledgeNode,
    KnowledgeEdge,
    EvolutionResult,
    KnowledgeEvolution,
    KNOWLEDGE_DOMAINS,
    WUXING_SHENG,
    WUXING_KE,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def ke():
    """创建 KnowledgeEvolution 实例。"""
    return KnowledgeEvolution()


# ============================================================================
# FeedbackRecord 测试
# ============================================================================

class TestFeedbackRecord:
    def test_create_feedback(self):
        """创建反馈记录"""
        record = FeedbackRecord(
            session_id="session_001",
            domain="bazi",
            accuracy=4,
            satisfaction=5,
            usefulness=4,
            comment="很准确",
            analysis_type="bazi_analysis",
        )
        assert record.session_id == "session_001"
        assert record.domain == "bazi"
        assert record.accuracy == 4
        assert record.satisfaction == 5
        assert record.usefulness == 4

    def test_overall_score(self):
        """综合评分计算"""
        record = FeedbackRecord(
            session_id="s1",
            accuracy=3, satisfaction=4, usefulness=5,
        )
        expected = (3 + 4 + 5) / 3.0
        assert abs(record.overall_score() - expected) < 0.001

    def test_overall_score_min(self):
        """最低评分"""
        record = FeedbackRecord(
            session_id="s1",
            accuracy=1, satisfaction=1, usefulness=1,
        )
        assert record.overall_score() == 1.0

    def test_overall_score_max(self):
        """最高评分"""
        record = FeedbackRecord(
            session_id="s1",
            accuracy=5, satisfaction=5, usefulness=5,
        )
        assert record.overall_score() == 5.0

    def test_to_dict(self):
        """反馈记录序列化"""
        record = FeedbackRecord(
            session_id="s1", domain="bazi",
            accuracy=4, satisfaction=3, usefulness=5,
            comment="test",
        )
        d = record.to_dict()
        assert d["session_id"] == "s1"
        assert d["domain"] == "bazi"
        assert d["accuracy"] == 4
        assert isinstance(d["corrections"], list)
        assert isinstance(d["tags"], list)


# ============================================================================
# ConfidenceProfile 测试
# ============================================================================

class TestConfidenceProfile:
    def test_create_profile(self):
        """创建置信度配置"""
        profile = ConfidenceProfile(domain="bazi")
        assert profile.domain == "bazi"
        assert profile.base_confidence == 0.5
        assert profile.current_confidence == 0.5
        assert profile.feedback_count == 0
        assert profile.positive_count == 0

    def test_to_dict(self):
        """置信度配置序列化"""
        profile = ConfidenceProfile(domain="ziwei", current_confidence=0.75)
        d = profile.to_dict()
        assert d["domain"] == "ziwei"
        assert d["current_confidence"] == 0.75
        assert "adjustments" in d


# ============================================================================
# KnowledgeNode 测试
# ============================================================================

class TestKnowledgeNode:
    def test_create_node(self):
        """创建知识节点"""
        node = KnowledgeNode(
            id="node_001",
            domain="bazi",
            concept="十天干",
            confidence=0.9,
            properties={"values": ["甲", "乙"]},
        )
        assert node.id == "node_001"
        assert node.domain == "bazi"
        assert node.concept == "十天干"
        assert node.confidence == 0.9

    def test_to_dict(self):
        """节点序列化"""
        node = KnowledgeNode(
            id="n1", domain="ziwei", concept="紫微星",
            confidence=0.85,
        )
        d = node.to_dict()
        assert d["id"] == "n1"
        assert d["domain"] == "ziwei"
        assert d["confidence"] == 0.85


# ============================================================================
# KnowledgeEdge 测试
# ============================================================================

class TestKnowledgeEdge:
    def test_create_edge(self):
        """创建知识边"""
        edge = KnowledgeEdge(
            source_id="src",
            target_id="tgt",
            relation="correlates",
            weight=0.7,
            confidence=0.8,
        )
        assert edge.source_id == "src"
        assert edge.target_id == "tgt"
        assert edge.relation == "correlates"
        assert edge.weight == 0.7
        assert edge.confidence == 0.8

    def test_to_dict(self):
        """边序列化"""
        edge = KnowledgeEdge(
            source_id="a", target_id="b",
            relation="supports", weight=0.9, confidence=0.85,
        )
        d = edge.to_dict()
        assert d["source_id"] == "a"
        assert d["target_id"] == "b"
        assert d["relation"] == "supports"


# ============================================================================
# EvolutionResult 测试
# ============================================================================

class TestEvolutionResult:
    def test_create_result(self):
        """创建进化结果"""
        result = EvolutionResult(
            domain="bazi",
            action="adjusted",
            before_confidence=0.5,
            after_confidence=0.6,
            description="置信度上调",
        )
        assert result.domain == "bazi"
        assert result.action == "adjusted"
        assert result.before_confidence == 0.5
        assert result.after_confidence == 0.6

    def test_to_dict(self):
        """进化结果序列化"""
        result = EvolutionResult(
            domain="fusion",
            action="discovered",
            before_confidence=0.0,
            after_confidence=0.5,
            new_nodes=["n1"],
            new_edges=[("a", "b", "correlates")],
            description="发现新关联",
        )
        d = result.to_dict()
        assert d["domain"] == "fusion"
        assert d["action"] == "discovered"
        assert d["new_nodes"] == ["n1"]
        assert len(d["new_edges"]) == 1
        assert d["new_edges"][0]["source"] == "a"


# ============================================================================
# KnowledgeEvolution 初始化测试
# ============================================================================

class TestKnowledgeEvolutionInit:
    def test_init_creates_domains(self, ke):
        """初始化创建所有领域置信度配置"""
        for domain in KNOWLEDGE_DOMAINS:
            assert domain in ke._confidence_profiles

    def test_init_seed_nodes(self, ke):
        """初始化种子知识节点"""
        assert len(ke._nodes) > 0
        assert "bazi_gan" in ke._nodes
        assert "bazi_zhi" in ke._nodes
        assert "bazi_wuxing" in ke._nodes
        assert "zw_stars" in ke._nodes
        assert "qm_men" in ke._nodes
        assert "ly_bagua" in ke._nodes

    def test_init_seed_edges(self, ke):
        """初始化种子知识边"""
        assert len(ke._edges) > 0

    def test_init_empty_feedback(self, ke):
        """初始无反馈"""
        assert len(ke._feedbacks) == 0

    def test_init_empty_evolution_history(self, ke):
        """初始无进化历史"""
        assert len(ke._evolution_history) == 0


# ============================================================================
# 反馈收集测试
# ============================================================================

class TestFeedbackCollection:
    def test_collect_feedback_basic(self, ke):
        """基本反馈收集"""
        record = ke.collect_feedback(
            session_id="s1",
            ratings={"accuracy": 4, "satisfaction": 5, "usefulness": 4},
            domain="bazi",
        )
        assert record.session_id == "s1"
        assert record.domain == "bazi"
        assert len(ke._feedbacks) == 1

    def test_collect_feedback_default_values(self, ke):
        """默认评分值"""
        record = ke.collect_feedback(
            session_id="s1",
            ratings={},
            domain="bazi",
        )
        assert record.accuracy == 3
        assert record.satisfaction == 3
        assert record.usefulness == 3

    def test_collect_feedback_with_corrections(self, ke):
        """带用户纠正的反馈"""
        corrections = [{"field": "dayun", "correct": "甲子"}]
        record = ke.collect_feedback(
            session_id="s1",
            ratings={"accuracy": 2},
            domain="bazi",
            corrections=corrections,
        )
        assert len(record.corrections) == 1
        assert record.corrections[0]["field"] == "dayun"

    def test_collect_feedback_updates_confidence(self, ke):
        """反馈收集实时更新置信度"""
        old_conf = ke.get_confidence("bazi")
        ke.collect_feedback(
            session_id="s1",
            ratings={"accuracy": 5, "satisfaction": 5, "usefulness": 5},
            domain="bazi",
        )
        new_conf = ke.get_confidence("bazi")
        assert new_conf != old_conf

    def test_collect_multiple_feedbacks(self, ke):
        """收集多条反馈"""
        for i in range(5):
            ke.collect_feedback(
                session_id=f"s{i}",
                ratings={"accuracy": 4, "satisfaction": 4, "usefulness": 4},
                domain="bazi",
            )
        assert len(ke._feedbacks) == 5
        profile = ke._confidence_profiles["bazi"]
        assert profile.feedback_count == 5

    def test_extract_tags_accurate(self, ke):
        """提取准确标签"""
        record = ke.collect_feedback(
            session_id="s1",
            ratings={},
            domain="general",
            comment="很准确，很有用",
        )
        assert "accurate" in record.tags
        assert "useful" in record.tags

    def test_extract_tags_inaccurate(self, ke):
        """提取不准确标签"""
        record = ke.collect_feedback(
            session_id="s1",
            ratings={},
            domain="general",
            comment="不准，没用",
        )
        assert "inaccurate" in record.tags
        assert "useless" in record.tags

    def test_extract_tags_complex(self, ke):
        """提取复杂标签"""
        record = ke.collect_feedback(
            session_id="s1",
            ratings={},
            domain="general",
            comment="太复杂了，难懂",
        )
        assert "too_complex" in record.tags
        assert "hard_to_understand" in record.tags

    def test_extract_tags_empty_comment(self, ke):
        """空评论无标签"""
        record = ke.collect_feedback(
            session_id="s1",
            ratings={},
            domain="general",
            comment="",
        )
        assert len(record.tags) == 0


# ============================================================================
# 置信度调整测试
# ============================================================================

class TestConfidenceAdjustment:
    def test_get_confidence_known_domain(self, ke):
        """获取已知领域置信度"""
        conf = ke.get_confidence("bazi")
        assert conf == 0.5

    def test_get_confidence_unknown_domain(self, ke):
        """获取未知领域置信度返回默认值"""
        conf = ke.get_confidence("unknown_domain")
        assert conf == 0.5

    def test_get_all_confidences(self, ke):
        """获取所有领域置信度"""
        all_conf = ke.get_all_confidences()
        assert len(all_conf) == len(KNOWLEDGE_DOMAINS)
        for domain in KNOWLEDGE_DOMAINS:
            assert domain in all_conf

    def test_positive_feedback_increases_confidence(self, ke):
        """正面反馈提升置信度"""
        old_conf = ke.get_confidence("bazi")
        for i in range(10):
            ke.collect_feedback(
                session_id=f"s{i}",
                ratings={"accuracy": 5, "satisfaction": 5, "usefulness": 5},
                domain="bazi",
            )
        new_conf = ke.get_confidence("bazi")
        assert new_conf > old_conf

    def test_negative_feedback_decreases_confidence(self, ke):
        """负面反馈降低置信度"""
        old_conf = ke.get_confidence("bazi")
        for i in range(10):
            ke.collect_feedback(
                session_id=f"s{i}",
                ratings={"accuracy": 1, "satisfaction": 1, "usefulness": 1},
                domain="bazi",
            )
        new_conf = ke.get_confidence("bazi")
        assert new_conf < old_conf

    def test_adjust_confidence_manual(self, ke):
        """手动调整置信度"""
        profile = ke.adjust_confidence("bazi", 0.2, "测试上调")
        assert profile.current_confidence > 0.5
        assert len(profile.adjustments) > 0

    def test_adjust_confidence_clamps_upper(self, ke):
        """置信度上限钳位 (1.0)"""
        ke.adjust_confidence("bazi", 1.0)
        conf = ke.get_confidence("bazi")
        assert conf <= 1.0
        assert conf >= 0.0

    def test_adjust_confidence_clamps_lower(self, ke):
        """置信度下限钳位 (0.0)"""
        ke.adjust_confidence("bazi", -1.0)
        conf = ke.get_confidence("bazi")
        assert conf >= 0.0

    def test_adjust_confidence_new_domain(self, ke):
        """为新领域调整置信度"""
        conf_before = ke.get_confidence("new_domain")
        ke.adjust_confidence("new_domain", 0.3, "新领域")
        conf_after = ke.get_confidence("new_domain")
        assert conf_after > conf_before
        assert "new_domain" in ke._confidence_profiles

    def test_bayesian_update_calculation(self, ke):
        """贝叶斯式更新计算正确性"""
        profile = ke._confidence_profiles["bazi"]
        old_conf = profile.current_confidence
        alpha = 0.1
        score = 5.0
        target = score / 5.0
        expected = old_conf * (1 - alpha) + target * alpha

        ke.collect_feedback(
            session_id="s1",
            ratings={"accuracy": 5, "satisfaction": 5, "usefulness": 5},
            domain="bazi",
        )

        new_conf = ke.get_confidence("bazi")
        assert abs(new_conf - expected) < 0.01


# ============================================================================
# 知识图谱操作测试
# ============================================================================

class TestKnowledgeGraphOps:
    def test_add_node(self, ke):
        """添加知识节点"""
        node = ke.add_node(
            node_id="custom_node",
            domain="bazi",
            concept="自定义概念",
            confidence=0.85,
            properties={"key": "value"},
        )
        assert node.id == "custom_node"
        assert "custom_node" in ke._nodes
        assert ke._nodes["custom_node"].confidence == 0.85

    def test_add_edge_valid(self, ke):
        """添加有效边"""
        edge = ke.add_edge(
            source_id="bazi_gan",
            target_id="bazi_zhi",
            relation="correlates",
            weight=0.7,
            confidence=0.8,
        )
        assert edge is not None
        assert edge.relation == "correlates"

    def test_add_edge_invalid_source(self, ke):
        """源节点不存在时返回 None"""
        edge = ke.add_edge(
            source_id="nonexistent",
            target_id="bazi_gan",
            relation="test",
        )
        assert edge is None

    def test_add_edge_invalid_target(self, ke):
        """目标节点不存在时返回 None"""
        edge = ke.add_edge(
            source_id="bazi_gan",
            target_id="nonexistent",
            relation="test",
        )
        assert edge is None

    def test_get_node(self, ke):
        """获取节点"""
        node = ke.get_node("bazi_gan")
        assert node is not None
        assert node.id == "bazi_gan"

    def test_get_node_nonexistent(self, ke):
        """获取不存在的节点返回 None"""
        node = ke.get_node("nonexistent")
        assert node is None

    def test_get_neighbors(self, ke):
        """获取节点邻居"""
        neighbors = ke.get_neighbors("bazi_gan")
        assert len(neighbors) > 0
        for neighbor, edge in neighbors:
            assert isinstance(neighbor, KnowledgeNode)
            assert isinstance(edge, KnowledgeEdge)

    def test_get_neighbors_no_edges(self, ke):
        """无关联节点的邻居为空"""
        ke.add_node("isolated", "bazi", "孤立节点")
        neighbors = ke.get_neighbors("isolated")
        assert len(neighbors) == 0


# ============================================================================
# 知识图谱自动补全测试
# ============================================================================

class TestAutoComplete:
    def test_transitive_inference(self, ke):
        """传递推理：A→B 且 B→C → A→C"""
        ke.add_node("A", "test", "A")
        ke.add_node("B", "test", "B")
        ke.add_node("C", "test", "C")
        ke.add_edge("A", "B", "test_rel", weight=0.9, confidence=0.9)
        ke.add_edge("B", "C", "test_rel", weight=0.9, confidence=0.9)

        edge_before = len(ke._edges)
        results = ke._transitive_inference()
        edge_after = len(ke._edges)

        assert edge_after > edge_before
        assert len(results) > 0
        assert results[0].action == "discovered"
        assert len(results[0].new_edges) == 1

    def test_transitive_inference_no_self_loop(self, ke):
        """传递推理不产生自环"""
        ke.add_node("A", "test", "A")
        ke.add_node("B", "test", "B")
        ke.add_edge("A", "B", "r", weight=0.9, confidence=0.9)
        ke.add_edge("B", "A", "r", weight=0.9, confidence=0.9)

        results = ke._transitive_inference()
        for r in results:
            for src, tgt, rel in r.new_edges:
                assert src != tgt

    def test_symmetry_completion(self, ke):
        """对称补全：A correlates B → B correlates A"""
        ke.add_node("X", "test", "X")
        ke.add_node("Y", "test", "Y")
        ke.add_edge("X", "Y", "correlates", weight=0.8, confidence=0.8)

        before = len(ke._edges)
        results = ke._symmetry_completion()
        after = len(ke._edges)

        assert after > before
        assert len(results) > 0

        reverse_exists = any(
            e.source_id == "Y" and e.target_id == "X" and e.relation == "correlates"
            for e in ke._edges
        )
        assert reverse_exists

    def test_symmetry_no_duplicate(self, ke):
        """对称补全不产生重复（使用唯一关系名避免种子边干扰）"""
        unique_rel = "test_sym_no_dup_rel"
        ke.add_node("A", "test", "A")
        ke.add_node("B", "test", "B")
        ke.add_edge("A", "B", unique_rel, weight=0.8, confidence=0.8)
        ke.add_edge("B", "A", unique_rel, weight=0.8, confidence=0.8)

        before_symmetric = sum(
            1 for e in ke._edges if e.relation == unique_rel
        )
        ke._symmetry_completion()
        after_symmetric = sum(
            1 for e in ke._edges if e.relation == unique_rel
        )

        assert after_symmetric == before_symmetric

    def test_cross_domain_inference(self, ke):
        """跨域关联推理"""
        ke.add_node("node_wood_bazi", "bazi", "木属性八字节点",
                    properties={"wuxing": ["木"]})
        ke.add_node("node_wood_ziwei", "ziwei", "木属性紫微节点",
                    properties={"wuxing": ["木"]})

        before = len(ke._edges)
        results = ke._cross_domain_inference()
        after = len(ke._edges)

        assert after > before

        cross_exists = any(
            (e.source_id == "node_wood_bazi" and e.target_id == "node_wood_ziwei")
            or (e.source_id == "node_wood_ziwei" and e.target_id == "node_wood_bazi")
            for e in ke._edges
        )
        assert cross_exists

    def test_auto_complete_returns_all_types(self, ke):
        """auto_complete 返回多种进化结果"""
        ke.add_node("A", "fusion", "A", properties={"wuxing": ["木"]})
        ke.add_node("B", "fusion", "B", properties={"wuxing": ["木"]})
        ke.add_node("C", "bazi", "C", properties={"wuxing": ["火"]})
        ke.add_edge("A", "B", "correlates", weight=0.9, confidence=0.9)
        ke.add_edge("B", "C", "derived_from", weight=0.9, confidence=0.9)

        results = ke.auto_complete_knowledge()
        assert len(results) >= 1
        actions = set(r.action for r in results)
        assert "discovered" in actions

    def test_transitive_weight_decay(self, ke):
        """传递推理的权重衰减"""
        ke.add_node("A", "test", "A")
        ke.add_node("B", "test", "B")
        ke.add_node("C", "test", "C")
        ke.add_edge("A", "B", "r", weight=0.8, confidence=0.8)
        ke.add_edge("B", "C", "r", weight=0.8, confidence=0.8)

        results = ke._transitive_inference()
        if results:
            for r in results:
                assert r.after_confidence < 0.8 * 0.8 + 0.01

    def test_transitive_minimum_weight_threshold(self, ke):
        """传递推理有最低权重阈值（使用唯一关系名避免种子边干扰）"""
        unique_rel = "test_trans_min_weight_rel"
        ke.add_node("A", "test", "A")
        ke.add_node("B", "test", "B")
        ke.add_node("C", "test", "C")
        ke.add_edge("A", "B", unique_rel, weight=0.3, confidence=0.3)
        ke.add_edge("B", "C", unique_rel, weight=0.3, confidence=0.3)

        before_trans = sum(
            1 for e in ke._edges if e.relation == unique_rel
        )
        ke._transitive_inference()
        after_trans = sum(
            1 for e in ke._edges if e.relation == unique_rel
        )

        derived_weight = 0.3 * 0.3 * 0.7
        if derived_weight < 0.2:
            assert after_trans == before_trans


# ============================================================================
# 进化主循环测试
# ============================================================================

class TestEvolve:
    def test_evolve_with_feedback(self, ke):
        """带反馈的进化"""
        for i in range(5):
            ke.collect_feedback(
                session_id=f"s{i}",
                ratings={"accuracy": 4, "satisfaction": 5, "usefulness": 4},
                domain="bazi",
            )

        results = ke.evolve()
        assert len(results) > 0
        actions = set(r.action for r in results)
        assert "adjusted" in actions or "discovered" in actions

    def test_evolve_without_feedback(self, ke):
        """无反馈的进化（仅图谱补全）"""
        results = ke.evolve()
        assert len(results) >= 0

    def test_evolve_records_history(self, ke):
        """进化结果记录到历史"""
        before = len(ke._evolution_history)
        ke.evolve()
        after = len(ke._evolution_history)
        assert after >= before


# ============================================================================
# 统计与查询测试
# ============================================================================

class TestStatsAndQueries:
    def test_get_evolution_stats_initial(self, ke):
        """初始进化统计"""
        stats = ke.get_evolution_stats()
        assert stats["total_feedback"] == 0
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0
        assert "domains" in stats
        assert "recent_evolutions" in stats

    def test_get_evolution_stats_with_feedback(self, ke):
        """带反馈的进化统计"""
        ke.collect_feedback(
            session_id="s1",
            ratings={"accuracy": 4, "satisfaction": 5, "usefulness": 4},
            domain="bazi",
        )
        stats = ke.get_evolution_stats()
        assert stats["total_feedback"] == 1
        assert stats["average_score"] > 0
        assert "bazi" in stats["domains"]

    def test_get_feedback_trend(self, ke):
        """反馈趋势"""
        for i in range(5):
            ke.collect_feedback(
                session_id=f"s{i}",
                ratings={"accuracy": i % 5 + 1},
                domain="bazi",
            )
        trend = ke.get_feedback_trend(domain="bazi", limit=3)
        assert len(trend) == 3
        for item in trend:
            assert "score" in item
            assert "timestamp" in item
            assert item["domain"] == "bazi"

    def test_get_feedback_trend_all_domains(self, ke):
        """全领域反馈趋势"""
        ke.collect_feedback(session_id="s1", ratings={}, domain="bazi")
        ke.collect_feedback(session_id="s2", ratings={}, domain="ziwei")
        trend = ke.get_feedback_trend(limit=10)
        assert len(trend) >= 2

    def test_get_knowledge_graph_stats(self, ke):
        """知识图谱统计"""
        stats = ke.get_knowledge_graph_stats()
        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "nodes_by_domain" in stats
        assert "edges_by_relation" in stats
        assert "avg_confidence" in stats
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0


# ============================================================================
# 重置测试
# ============================================================================

class TestReset:
    def test_reset_clears_feedback(self, ke):
        """重置清空反馈"""
        ke.collect_feedback(session_id="s1", ratings={}, domain="bazi")
        assert len(ke._feedbacks) == 1
        ke.reset()
        assert len(ke._feedbacks) == 0

    def test_reset_restores_seeds(self, ke):
        """重置恢复种子知识"""
        ke._nodes.clear()
        ke._edges.clear()
        ke.reset()
        assert len(ke._nodes) > 0
        assert "bazi_gan" in ke._nodes

    def test_reset_clears_evolution_history(self, ke):
        """重置清空进化历史"""
        ke.evolve()
        assert len(ke._evolution_history) > 0
        ke.reset()
        assert len(ke._evolution_history) == 0

    def test_reset_resets_confidence(self, ke):
        """重置重置置信度"""
        ke.adjust_confidence("bazi", 0.3)
        assert ke.get_confidence("bazi") > 0.5
        ke.reset()
        assert ke.get_confidence("bazi") == 0.5
