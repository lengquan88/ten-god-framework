"""
test_archive.py — 时空索引与语义归档测试 v2.27.0
"""
import pytest
import hashlib

from tengod.tbce_unit import GateState
from tengod.archive import (
    ArchiveType, SpatioTemporalIndex, SemanticBinding, SemanticBinder,
    ArchiveGate, ArchiveEngine,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def binder():
    return SemanticBinder()


@pytest.fixture
def engine():
    return ArchiveEngine()


# ── 1. ArchiveType ────────────────────────────────────────

class TestArchiveType:
    def test_values(self):
        assert ArchiveType.INTEGRATION.value == "integration"
        assert ArchiveType.KNOWLEDGE.value == "knowledge"


# ── 2. SpatioTemporalIndex ────────────────────────────────

class TestSpatioTemporalIndex:
    def test_create(self):
        index = SpatioTemporalIndex(
            index_id="test",
            archive_type=ArchiveType.INTEGRATION,
            temporal_coord=0.5,
            spatial_coords=[0.8, 0.7, 0.8, 0.7, 0.8, 0.2],
            semantic_tags=["deepseek", "integration"],
            cognitive_layer=5,
            palace_id=1,
        )
        assert index.index_id == "test"
        assert len(index.spatial_coords) == 6
        assert len(index.semantic_tags) == 2

    def test_compute_hash(self):
        index = SpatioTemporalIndex(
            index_id="test",
            archive_type=ArchiveType.INTEGRATION,
            temporal_coord=0.5,
            spatial_coords=[0.5]*6,
            semantic_tags=[],
            cognitive_layer=1,
        )
        h = index.compute_hash({"key": "value"})
        assert len(h) == 16

    def test_to_dict(self):
        index = SpatioTemporalIndex(
            index_id="test",
            archive_type=ArchiveType.INTEGRATION,
            temporal_coord=0.5,
            spatial_coords=[0.5]*6,
            semantic_tags=["tag1", "tag2"],
            cognitive_layer=1,
        )
        d = index.to_dict()
        assert d["index_id"] == "test"
        assert d["archive_type"] == "integration"
        assert len(d["semantic_tags"]) == 2


# ── 3. SemanticBinder ─────────────────────────────────────

class TestSemanticBinder:
    def test_bind(self, binder):
        binding = binder.bind("a", "b", "reference", 0.7)
        assert binding.source_id == "a"
        assert binding.target_id == "b"
        assert binder.binding_count() == 1

    def test_get_bindings(self, binder):
        binder.bind("a", "b", "reference", 0.7)
        binder.bind("a", "c", "similarity", 0.5)
        bindings = binder.get_bindings("a")
        assert len(bindings) == 2

    def test_find_related(self, binder):
        binder.bind("a", "b", "reference", 0.8)
        binder.bind("a", "c", "reference", 0.2)
        related = binder.find_related("a", min_strength=0.5)
        assert related == ["b"]

    def test_get_binding_graph(self, binder):
        binder.bind("a", "b", "reference", 0.7)
        binder.bind("a", "c", "reference", 0.5)
        graph = binder.get_binding_graph()
        assert "a" in graph
        assert len(graph["a"]) == 2


# ── 4. ArchiveGate ────────────────────────────────────────

class TestArchiveGate:
    def test_quality_high_open(self):
        gate = ArchiveGate()
        index = SpatioTemporalIndex(
            index_id="test",
            archive_type=ArchiveType.INTEGRATION,
            temporal_coord=0.5,
            spatial_coords=[0.5]*6,
            semantic_tags=["t1", "t2", "t3"],
            cognitive_layer=5,
            reference_count=5,
            content_hash="abc123",
        )
        state, reason = gate.judge(index, binding_count=3)
        assert state == GateState.OPEN

    def test_quality_medium_pending(self):
        gate = ArchiveGate()
        index = SpatioTemporalIndex(
            index_id="test",
            archive_type=ArchiveType.INTEGRATION,
            temporal_coord=0.5,
            spatial_coords=[0.5]*6,
            semantic_tags=["t1"],
            cognitive_layer=5,
            reference_count=0,
        )
        state, reason = gate.judge(index, binding_count=1)
        assert state == GateState.PENDING

    def test_quality_low_closed(self):
        gate = ArchiveGate()
        index = SpatioTemporalIndex(
            index_id="test",
            archive_type=ArchiveType.INTEGRATION,
            temporal_coord=0.5,
            spatial_coords=[],  # 缺少TBCE坐标
            semantic_tags=[],
            cognitive_layer=1,
        )
        state, reason = gate.judge(index, binding_count=0)
        assert state == GateState.CLOSED


# ── 5. ArchiveEngine ─────────────────────────────────────

class TestArchiveEngine:
    def test_archive(self, engine):
        idx, gate, reason = engine.archive(
            archive_type=ArchiveType.INTEGRATION,
            spatial_coords=[0.8, 0.7, 0.8, 0.7, 0.8, 0.2],
            semantic_tags=["deepseek", "integration", "TBCE"],
            cognitive_layer=5,
            content={"description": "test"},
            related_ids=["prev1"],
        )
        assert isinstance(idx, SpatioTemporalIndex)
        assert gate in (GateState.OPEN, GateState.PENDING, GateState.CLOSED)
        assert engine.get_content(idx.index_id)["description"] == "test"

    def test_search_by_type(self, engine):
        engine.archive(
            archive_type=ArchiveType.INTEGRATION,
            spatial_coords=[0.5]*6,
            semantic_tags=["a"],
            cognitive_layer=5,
            content={},
        )
        engine.archive(
            archive_type=ArchiveType.KNOWLEDGE,
            spatial_coords=[0.5]*6,
            semantic_tags=["b"],
            cognitive_layer=3,
            content={},
        )
        results = engine.search(archive_type=ArchiveType.INTEGRATION)
        assert len(results) == 1

    def test_search_by_tags(self, engine):
        engine.archive(
            archive_type=ArchiveType.INTEGRATION,
            spatial_coords=[0.5]*6,
            semantic_tags=["deepseek", "holographic"],
            cognitive_layer=5,
            content={},
        )
        results = engine.search(tags=["deepseek"])
        assert len(results) == 1

    def test_get_related(self, engine):
        idx1, _, _ = engine.archive(
            archive_type=ArchiveType.INTEGRATION,
            spatial_coords=[0.5]*6,
            semantic_tags=["a"],
            cognitive_layer=5,
            content={},
        )
        idx2, _, _ = engine.archive(
            archive_type=ArchiveType.INTEGRATION,
            spatial_coords=[0.5]*6,
            semantic_tags=["b"],
            cognitive_layer=5,
            content={},
            related_ids=[idx1.index_id],
        )
        related = engine.get_related(idx2.index_id)
        assert len(related) == 1
        assert related[0].index_id == idx1.index_id

    def test_get_statistics(self, engine):
        idx1, _, _ = engine.archive(
            archive_type=ArchiveType.INTEGRATION,
            spatial_coords=[0.5]*6,
            semantic_tags=["a"],
            cognitive_layer=5,
            content={},
        )
        engine.archive(
            archive_type=ArchiveType.KNOWLEDGE,
            spatial_coords=[0.5]*6,
            semantic_tags=["b"],
            cognitive_layer=3,
            content={},
            related_ids=[idx1.index_id],
        )
        stats = engine.get_statistics()
        assert stats["total_archives"] == 2
        assert "integration" in stats["type_distribution"]
        assert stats["total_bindings"] > 0


# ── 6. Integration ───────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self):
        engine = ArchiveEngine()

        # 归档第一个条目
        idx1, gate1, _ = engine.archive(
            archive_type=ArchiveType.INTEGRATION,
            spatial_coords=[0.8, 0.7, 0.8, 0.7, 0.8, 0.2],
            semantic_tags=["deepseek", "cognitive", "TBCE"],
            cognitive_layer=5,
            content={"description": "DeepSeek全息认知系统"},
        )

        # 归档第二个条目，关联第一个
        idx2, gate2, _ = engine.archive(
            archive_type=ArchiveType.KNOWLEDGE,
            spatial_coords=[0.9, 0.8, 0.8, 0.8, 0.7, 0.1],
            semantic_tags=["deepseek", "knowledge", "archeology"],
            cognitive_layer=8,
            content={"description": "知识库归档"},
            related_ids=[idx1.index_id],
        )

        # 搜索
        results = engine.search(tags=["deepseek"])
        assert len(results) == 2

        # 获取相关
        related = engine.get_related(idx2.index_id)
        assert len(related) == 1

        # 统计
        stats = engine.get_statistics()
        assert stats["total_archives"] == 2
        assert stats["total_bindings"] == 1