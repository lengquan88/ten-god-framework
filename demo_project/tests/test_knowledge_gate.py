"""
test_knowledge_gate.py — 知识门禁专用测试 v1.0
====================================================
知识门禁（正财·偏财/土）核心逻辑补充测试。
之前仅在 test_twelve_gods.py 中有极少覆盖，本文件重点覆盖：

1. KnowledgeEntry: compute_hash 确定性、is_stale 边界
2. store_knowledge: 冲突检测、版本递增、created_at 继承
3. _evaluate_knowledge 正财 vs 偏财的权重差异
4. 冲突惩罚对 score 的影响
5. get_knowledge_stats 新鲜度比例计算
6. 无 metadata content_hash 时 integrity *= 0.9 惩罚
7. 过期知识 (freshness T < 0.3) 的 issue 记录
8. 偏财（PIANCAI）更偏重 evolution 维度的评分
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tengod.tbce_unit import TBCECoordinates, CognitiveUnit, GateState
from tengod.twelve_gods_base import TwelveGods, FiveElements, GateVerdict
from tengod.knowledge_gate import KnowledgeEntry, KnowledgeGate


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def zhengcai_gate():
    """正财·知识固化门禁。"""
    return KnowledgeGate(god=TwelveGods.ZHENGCAI)


@pytest.fixture
def piancai_gate():
    """偏财·奇招演化门禁。"""
    return KnowledgeGate(god=TwelveGods.PIANCAI)


@pytest.fixture
def high_quality_unit():
    """高质量认知单元：完整、一致、新鲜、稳定。"""
    return CognitiveUnit(
        unit_id="know.good",
        name="好知识",
        module_path="know.good",
        coordinates=TBCECoordinates(S=0.9, T=0.85, P=0.8, C=0.9, I=0.9, E=0.1),
        cognitive_layer=3,
        psi_operator="EmbeddingProvider",
        metadata={"content_hash": "abc123def456"},
    )


@pytest.fixture
def low_quality_unit():
    """低质量认知单元：不完整、过期、不稳定。"""
    return CognitiveUnit(
        unit_id="know.bad",
        name="坏知识",
        module_path="know.bad",
        coordinates=TBCECoordinates(S=0.2, T=0.15, P=0.3, C=0.25, I=0.2, E=0.8),
        cognitive_layer=1,
        psi_operator="EmbeddingProvider",
        # 无 content_hash → integrity 惩罚
    )


# ========================================================================
# 1. KnowledgeEntry 数据对象
# ========================================================================

class TestKnowledgeEntry:
    def test_compute_hash_is_deterministic(self):
        """相同内容必须产生相同哈希。"""
        content = {"answer": 42, "question": "life"}
        e1 = KnowledgeEntry(
            entry_id="e1", content=dict(content), source="src", confidence=0.8,
        )
        e2 = KnowledgeEntry(
            entry_id="e2", content=dict(content), source="src", confidence=0.8,
        )
        assert e1.compute_hash() == e2.compute_hash()

    def test_compute_hash_differs_for_different_content(self):
        """不同内容必须产生不同哈希。"""
        e1 = KnowledgeEntry(entry_id="a", content={"x": 1}, source="s", confidence=0.5)
        e2 = KnowledgeEntry(entry_id="a", content={"x": 2}, source="s", confidence=0.5)
        assert e1.compute_hash() != e2.compute_hash()

    def test_compute_hash_length(self):
        """哈希截取前 16 位十六进制。"""
        e = KnowledgeEntry(entry_id="a", content={"k": "v"}, source="s", confidence=0.5)
        h = e.compute_hash()
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_is_stale_false_for_fresh(self):
        """刚创建的知识绝不过期。"""
        e = KnowledgeEntry(entry_id="a", content={}, source="s", confidence=0.5)
        assert e.is_stale() is False
        assert e.is_stale(max_age_days=0.000001) is False  # 几乎零秒也算新鲜

    def test_is_stale_true_for_old(self):
        """长时间未更新的知识视为过期。"""
        e = KnowledgeEntry(entry_id="a", content={}, source="s", confidence=0.5)
        # 人工把 updated_at 推到 100 天前
        e.updated_at = time.time() - 100 * 86400
        assert e.is_stale() is True
        assert e.is_stale(max_age_days=50) is True
        # 阈值极大，仍算新鲜
        assert e.is_stale(max_age_days=500) is False

    def test_is_stale_boundary_one_second_before(self):
        """正好比阈值早 1 秒 → 算过期。"""
        e = KnowledgeEntry(entry_id="a", content={}, source="s", confidence=0.5)
        e.updated_at = time.time() - (86400 * 30 + 1)
        assert e.is_stale(max_age_days=30) is True

    def test_is_stale_boundary_one_second_after(self):
        """正好比阈值晚 1 秒 → 仍算新鲜。"""
        e = KnowledgeEntry(entry_id="a", content={}, source="s", confidence=0.5)
        e.updated_at = time.time() - (86400 * 30 - 1)
        assert e.is_stale(max_age_days=30) is False


# ========================================================================
# 2. store_knowledge — 冲突检测与版本递增
# ========================================================================

class TestStoreKnowledge:
    def test_store_new_entry_version_1(self, zhengcai_gate):
        entry = zhengcai_gate.store_knowledge(
            entry_id="k1",
            content={"a": 1},
            source="test",
            confidence=0.9,
            tags=["tag1"],
            dependencies=["dep1"],
        )
        assert entry.version == 1
        assert entry.content_hash != ""
        assert zhengcai_gate.get_knowledge("k1") is entry

    def test_store_same_content_increments_version_no_conflict(self, zhengcai_gate):
        """相同内容再次存储 → 版本递增，但冲突 log 不增加。"""
        e1 = zhengcai_gate.store_knowledge("k1", {"a": 1}, "s", 0.9)
        created = e1.created_at
        time.sleep(0.001)
        e2 = zhengcai_gate.store_knowledge("k1", {"a": 1}, "s", 0.9)
        # 版本递增
        assert e2.version == 2
        # created_at 继承
        assert e2.created_at == created
        # 无冲突
        assert len(zhengcai_gate.get_conflicts()) == 0

    def test_store_different_content_logs_conflict(self, zhengcai_gate):
        """不同内容覆盖 → 冲突 log +1。"""
        zhengcai_gate.store_knowledge("k1", {"a": 1}, "s", 0.9)
        zhengcai_gate.store_knowledge("k1", {"a": 2}, "s", 0.9)
        conflicts = zhengcai_gate.get_conflicts()
        assert len(conflicts) == 1
        assert conflicts[0]["entry_id"] == "k1"
        assert conflicts[0]["old_hash"] != conflicts[0]["new_hash"]

    def test_get_knowledge_missing_returns_none(self, zhengcai_gate):
        assert zhengcai_gate.get_knowledge("nope") is None


# ========================================================================
# 3. _evaluate_knowledge 正财 vs 偏财权重差异
# ========================================================================

class TestEvaluateKnowledgeWeightDifference:
    def test_high_quality_zhengcai_score_is_high(self, zhengcai_gate, high_quality_unit):
        score, issues, evidence = zhengcai_gate._evaluate_knowledge(high_quality_unit)
        assert score >= 0.8
        assert any("内容哈希一致" in e for e in evidence)
        assert any("知识新鲜" in e for e in evidence)
        assert issues == []

    def test_low_quality_zhengcai_score_is_low(self, zhengcai_gate, low_quality_unit):
        score, issues, evidence = zhengcai_gate._evaluate_knowledge(low_quality_unit)
        # 无哈希 → integrity 惩罚 0.9；过期 → issue；冲突 0
        assert score < 0.5
        assert any("过期" in i for i in issues)

    def test_no_hash_penalizes_integrity(self, zhengcai_gate, high_quality_unit):
        """移除 metadata.content_hash → integrity 乘 0.9。"""
        # 有哈希
        s1, _, _ = zhengcai_gate._evaluate_knowledge(high_quality_unit)
        # 无哈希
        no_hash = CognitiveUnit(
            unit_id="nohash", name="n", module_path="n",
            coordinates=TBCECoordinates(S=0.9, T=0.85, P=0.8, C=0.9, I=0.9, E=0.1),
            cognitive_layer=3, psi_operator="EmbeddingProvider",
            metadata={},  # 无 content_hash
        )
        s2, _, _ = zhengcai_gate._evaluate_knowledge(no_hash)
        # integrity 占 0.35，差异 = 0.35 * 0.9 * (1 - 0.9) ≈ 0.0315
        # 但还有 evidence 影响；只要求 s2 < s1
        assert s2 < s1

    def test_conflict_penalty(self, zhengcai_gate, high_quality_unit):
        """存在冲突 → score 降低。

        注意：N 次 store_knowledge (同一 entry_id) 产生 N-1 个冲突（第一次不算冲突）。
        所以要得到 3 个冲突，需要 store 4 次：a:1, a:2, a:3, a:4。
        """
        clean, _, _ = zhengcai_gate._evaluate_knowledge(high_quality_unit)
        # 制造 3 个冲突（需要 4 次 store）
        zhengcai_gate.store_knowledge(high_quality_unit.unit_id, {"a": 1}, "s")
        zhengcai_gate.store_knowledge(high_quality_unit.unit_id, {"a": 2}, "s")
        zhengcai_gate.store_knowledge(high_quality_unit.unit_id, {"a": 3}, "s")
        zhengcai_gate.store_knowledge(high_quality_unit.unit_id, {"a": 4}, "s")
        # 3 次冲突
        with_conflict, issues, _ = zhengcai_gate._evaluate_knowledge(high_quality_unit)
        assert with_conflict < clean
        # 真实源码格式：f"知识冲突({conflicts}个)"
        assert any("知识冲突(3个)" in i for i in issues)

    def test_zhengcai_prioritizes_integrity_over_evolution(self):
        """正财：integrity+consistency > evolution+freshness。
        通过两个单元对比：
          Unit A: S=0.95 C=0.95 (高完整性)，I=0.4 (演化弱)
          Unit B: I=0.95 E=低 (高演化)，S=0.4 C=0.4 (完整性差)
        正财必须给 A 更高评分。
        """
        gate = KnowledgeGate(god=TwelveGods.ZHENGCAI)
        unit_a = CognitiveUnit(
            unit_id="a", name="a", module_path="a",
            coordinates=TBCECoordinates(S=0.95, T=0.5, P=0.5, C=0.95, I=0.4, E=0.2),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
            metadata={"content_hash": "x"},
        )
        unit_b = CognitiveUnit(
            unit_id="b", name="b", module_path="b",
            coordinates=TBCECoordinates(S=0.4, T=0.5, P=0.5, C=0.4, I=0.95, E=0.2),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
            metadata={"content_hash": "y"},
        )
        sa, _, _ = gate._evaluate_knowledge(unit_a)
        sb, _, _ = gate._evaluate_knowledge(unit_b)
        assert sa > sb

    def test_piancai_prioritizes_evolution_over_integrity(self):
        """偏财：evolution+consistency > integrity。
        相同 A/B 单元下，偏财给 B (高 I 演化) 更高评分。
        """
        gate = KnowledgeGate(god=TwelveGods.PIANCAI)
        unit_a = CognitiveUnit(
            unit_id="a", name="a", module_path="a",
            coordinates=TBCECoordinates(S=0.95, T=0.5, P=0.5, C=0.5, I=0.3, E=0.2),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
            metadata={"content_hash": "x"},
        )
        unit_b = CognitiveUnit(
            unit_id="b", name="b", module_path="b",
            coordinates=TBCECoordinates(S=0.5, T=0.5, P=0.5, C=0.5, I=0.95, E=0.2),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
            metadata={"content_hash": "y"},
        )
        sa, _, _ = gate._evaluate_knowledge(unit_a)
        sb, _, _ = gate._evaluate_knowledge(unit_b)
        # 偏财中 evolution (I) 权重 0.30，integrity 0.15，所以 B 应该更高
        assert sb > sa


# ========================================================================
# 4. judge 裁决三态
# ========================================================================

class TestKnowledgeGateJudge:
    def test_judge_high_quality_open(self, zhengcai_gate, high_quality_unit):
        v = zhengcai_gate.judge(high_quality_unit)
        assert isinstance(v, GateVerdict)
        assert v.state in (GateState.OPEN, GateState.PENDING)

    def test_judge_low_quality_closed(self, zhengcai_gate, low_quality_unit):
        v = zhengcai_gate.judge(low_quality_unit)
        # 分很低 → 关
        assert v.state == GateState.CLOSED

    def test_judge_scores_clamped_0_1(self, zhengcai_gate):
        """极端冲突 + 极低坐标 → score 仍在 [0,1]。"""
        unit = CognitiveUnit(
            unit_id="x", name="x", module_path="x",
            coordinates=TBCECoordinates(S=0.0, T=0.0, P=0.0, C=0.0, I=0.0, E=1.0),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        # 制造大量冲突（每次 -0.05，再乘内部 0.1 + 惩罚）
        for i in range(5):
            zhengcai_gate.store_knowledge("x", {"v": i}, "s")
        v = zhengcai_gate.judge(unit)
        assert 0.0 <= v.score <= 1.0

    def test_judge_applies_wuxing_boost(self):
        """palace_id=3(震三=木) → 克土。偏财/正财都属土，被木克 → -0.05。
        通过 metadata 或 palace_id 触发 boost 机制（在 TwelveGodsGate.judge 模板方法）。
        """
        gate_wood_palace = KnowledgeGate(god=TwelveGods.ZHENGCAI)
        unit_wood_palace = CognitiveUnit(
            unit_id="w", name="w", module_path="w",
            coordinates=TBCECoordinates(S=0.8, T=0.8, P=0.7, C=0.8, I=0.8, E=0.1),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
            palace_id=3,  # 震三木，克土（门禁本神是土）
            metadata={"content_hash": "h"},
        )
        # 原始分：_judge_impl 先算纯内部分 → TwelveGodsGate.judge 模板方法再叠加生克
        # 直接调用 _judge_impl 拿"纯评分"，再和 judge() 的最终分比较
        v_impl = gate_wood_palace._judge_impl(unit_wood_palace)
        v = gate_wood_palace.judge(unit_wood_palace)
        # 宫位木克土 → boost = -0.05 → 最终分应低于或等于_impl分
        assert v.score <= v_impl.score


# ========================================================================
# 5. get_knowledge_stats 统计
# ========================================================================

class TestKnowledgeStats:
    def test_empty_stats(self, zhengcai_gate):
        s = zhengcai_gate.get_knowledge_stats()
        assert s["total_entries"] == 0
        assert s["stale_entries"] == 0
        assert s["conflicts"] == 0
        assert s["freshness_ratio"] == 0.0  # 0/0 → 0（max(1,total)）

    def test_mixed_stats(self, zhengcai_gate):
        # 新鲜知识 2 条
        zhengcai_gate.store_knowledge("fresh1", {"a": 1}, "s", 0.8)
        zhengcai_gate.store_knowledge("fresh2", {"b": 2}, "s", 0.8)
        # 过期知识 1 条
        stale = zhengcai_gate.store_knowledge("stale", {"c": 3}, "s", 0.8)
        stale.updated_at = time.time() - 60 * 86400
        # 1 次冲突
        zhengcai_gate.store_knowledge("fresh1", {"a": 999}, "s", 0.8)

        s = zhengcai_gate.get_knowledge_stats()
        assert s["total_entries"] == 3
        assert s["stale_entries"] == 1
        assert s["conflicts"] == 1
        assert s["freshness_ratio"] == pytest.approx(2 / 3)


# ========================================================================
# 6. TwelveGodsGate 继承：元素映射正确
# ========================================================================

class TestElementMapping:
    def test_zhengcai_is_earth(self):
        g = KnowledgeGate(TwelveGods.ZHENGCAI)
        assert g.element == FiveElements.EARTH

    def test_piancai_is_earth(self):
        g = KnowledgeGate(TwelveGods.PIANCAI)
        assert g.element == FiveElements.EARTH

    def test_gate_type_is_knowledge(self):
        g = KnowledgeGate(TwelveGods.ZHENGCAI)
        assert g.gate_type == "knowledge"
