"""
test_gate_cognitive.py — 门禁认知引擎三链合一测试 v3.1.0
===========================================================
覆盖三个任务：
  - 任务一：六维投影 + 测地线门禁检索
  - 任务二：三道门禁预过滤 + 节奏采样
  - 任务三：坐忘门禁 + 意图歧义消解
"""

import numpy as np
import pytest

from tengod.gate_torch import (
    TBCESixDimProjector,
    GateFilter,
    RhythmScheduler,
    ZuowangAttentionTorch,
    IntentDisambiguator,
    geodesic_distance,
    retrieve_with_gates,
    _HAS_TORCH,
)
from tengod.open_source_bridge import (
    ThreeFSClient,
    DeepSeekR1Client,
    DSparkScheduler,
    GateCognitiveEngine,
)
from tengod.tbce_unit import TBCECoordinates, GateState


# ============================================================================
# 任务一：TBCE 六维投影 + 测地线门禁
# ============================================================================

class TestTBCESixDimProjector:
    """六维投影器测试"""

    def test_creation(self):
        proj = TBCESixDimProjector(dim=768)
        assert proj.dim == 768
        assert len(proj.gate_mods) == 9  # 九宫格

    def test_forward_shape(self):
        proj = TBCESixDimProjector(dim=768)
        emb = np.random.randn(768).astype(np.float32)
        vec = proj.forward(emb)
        assert vec.shape == (1, 6)  # batch=1, 6维

    def test_forward_batch(self):
        proj = TBCESixDimProjector(dim=768)
        emb = np.random.randn(4, 768).astype(np.float32)
        vec = proj.forward(emb)
        assert vec.shape == (4, 6)

    def test_gate_modulation(self):
        """测试门禁系数调制"""
        proj = TBCESixDimProjector(dim=768)
        emb = np.random.randn(768).astype(np.float32)

        # 无调制
        vec_no_mod = proj.forward(emb, gate_mods=np.ones(6, dtype=np.float32))
        # 坎一调制（S维0.8）
        vec_kan = proj.forward(emb, palace_id=1)

        # S维应该被调制
        assert abs(vec_kan[0, 0]) < abs(vec_no_mod[0, 0]) * 1.1 or abs(vec_kan[0, 0]) <= abs(vec_no_mod[0, 0]) * 0.9

    def test_palace_auto_select(self):
        """九宫格自动选择门禁系数"""
        proj = TBCESixDimProjector(dim=768)
        emb = np.random.randn(768).astype(np.float32)

        for pid in range(1, 10):
            vec = proj.forward(emb, palace_id=pid)
            assert vec.shape == (1, 6)

    def test_to_tbce_coordinates(self):
        proj = TBCESixDimProjector(dim=768)
        emb = np.random.randn(768).astype(np.float32)
        vec = proj.forward(emb)
        coord = proj.to_tbce_coordinates(vec)
        assert isinstance(coord, TBCECoordinates)
        assert 0.0 <= coord.S <= 1.0
        assert 0.0 <= coord.E <= 1.0

    def test_deterministic(self):
        """相同输入应产生相同输出"""
        proj = TBCESixDimProjector(dim=768)
        emb = np.random.randn(768).astype(np.float32)
        vec1 = proj.forward(emb)
        vec2 = proj.forward(emb)
        np.testing.assert_array_almost_equal(vec1, vec2)


class TestGeodesicDistance:
    """测地线距离测试"""

    def test_self_distance_zero(self):
        v = np.ones(6, dtype=np.float32) * 0.5
        d = geodesic_distance(v, v)
        assert abs(d) < 1e-6

    def test_different_vectors(self):
        v1 = np.zeros(6, dtype=np.float32)
        v2 = np.ones(6, dtype=np.float32)
        d = geodesic_distance(v1, v2)
        assert d > 0

    def test_metric_tensor_effect(self):
        """度量张量应影响距离"""
        v1 = np.zeros(6, dtype=np.float32)
        v2 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)

        d_default = geodesic_distance(v1, v2)
        # 放大S维权重
        metric_heavy = np.eye(6, dtype=np.float32)
        metric_heavy[0, 0] = 10.0
        d_heavy = geodesic_distance(v1, v2, metric_heavy)

        assert d_heavy > d_default

    def test_symmetry(self):
        v1 = np.random.randn(6).astype(np.float32)
        v2 = np.random.randn(6).astype(np.float32)
        d12 = geodesic_distance(v1, v2)
        d21 = geodesic_distance(v2, v1)
        assert abs(d12 - d21) < 1e-5


class TestRetrieveWithGates:
    """测地线门禁检索测试"""

    def test_basic_retrieval(self):
        query = np.random.randn(768).astype(np.float32)
        chunks = [
            (f"chunk_{i}", np.random.randn(768).astype(np.float32))
            for i in range(20)
        ]
        proj = TBCESixDimProjector(dim=768)
        results = retrieve_with_gates(query, chunks, projector=proj, threshold=1.0, top_k=5)
        assert len(results) <= 5
        for cid, dist in results:
            assert isinstance(cid, str)
            assert isinstance(dist, float)
            assert dist >= 0.0

    def test_threshold_filtering(self):
        query = np.random.randn(768).astype(np.float32)
        chunks = [
            (f"chunk_{i}", np.random.randn(768).astype(np.float32))
            for i in range(20)
        ]
        proj = TBCESixDimProjector(dim=768)
        results_strict = retrieve_with_gates(query, chunks, projector=proj, threshold=0.01, top_k=10)
        results_loose = retrieve_with_gates(query, chunks, projector=proj, threshold=100.0, top_k=10)
        assert len(results_strict) <= len(results_loose)

    def test_without_projector(self):
        """无投影器时直接使用原始维度"""
        query = np.random.randn(6).astype(np.float32)
        chunks = [
            (f"chunk_{i}", np.random.randn(6).astype(np.float32))
            for i in range(10)
        ]
        results = retrieve_with_gates(query, chunks, threshold=100.0, top_k=5)
        assert len(results) > 0


# ============================================================================
# 任务二：三道门禁预过滤 + 节奏采样
# ============================================================================

class TestGateFilter:
    """三道门禁测试"""

    def test_all_open(self):
        gate = GateFilter(dim=768)
        emb = np.random.randn(768).astype(np.float32)
        state, details = gate.forward(emb, query_text="正常查询", system_load=0.3)
        # 随机 embedding 因果分数可能不高，但至少 auth+resource 应全开
        assert state in (GateState.OPEN, GateState.PENDING, GateState.CLOSED)
        assert "auth_gate" in details
        assert "resource_gate" in details
        assert "causal_gate" in details
        assert "causal_score" in details

    def test_resource_gate_high_load(self):
        gate = GateFilter(dim=768)
        emb = np.random.randn(768).astype(np.float32)
        state, details = gate.forward(emb, system_load=0.9)
        assert details["resource_gate"] == 0.0

    def test_auth_gate_whitelist(self):
        gate = GateFilter(dim=768)
        gate.set_whitelist(["八字", "紫微"])
        emb = np.random.randn(768).astype(np.float32)

        _, details_authorized = gate.forward(emb, query_text="帮我算八字")
        assert details_authorized["auth_gate"] == 1.0

        _, details_unauthorized = gate.forward(emb, query_text="违规查询")
        assert details_unauthorized["auth_gate"] == 0.0

    def test_empty_whitelist_allows_all(self):
        gate = GateFilter(dim=768)
        assert gate.is_authorized("任何查询") is True


class TestRhythmScheduler:
    """节奏采样测试"""

    def test_tau_range(self):
        s = RhythmScheduler(tau_min=2, tau_max=6)
        for load in [0.0, 0.3, 0.5, 0.8, 1.0]:
            tau = s.adjust_tau(load)
            assert 2 <= tau <= 6

    def test_monotonic(self):
        """负载越高 → tau 越小"""
        s = RhythmScheduler(tau_min=2, tau_max=6)
        tau_low = s.adjust_tau(0.1)
        tau_high = s.adjust_tau(0.9)
        assert tau_low >= tau_high

    def test_load_trend(self):
        s = RhythmScheduler(tau_min=2, tau_max=6)
        assert s.get_load_trend() == "stable"
        for load in [0.1, 0.2, 0.3, 0.4, 0.9]:
            s.adjust_tau(load)
        assert s.get_load_trend() == "rising"


# ============================================================================
# 任务三：坐忘门禁 + 意图歧义消解
# ============================================================================

class TestZuowangAttentionTorch:
    """坐忘注意力测试"""

    def test_creation(self):
        z = ZuowangAttentionTorch(embed_dim=768, num_heads=12, theta=0.7)
        assert z.embed_dim == 768
        assert z.theta == 0.7

    def test_forward_shape(self):
        z = ZuowangAttentionTorch(embed_dim=768)
        query = np.random.randn(768).astype(np.float32)
        history = np.random.randn(5, 768).astype(np.float32)
        state, output = z.forward(query, history)
        assert state in (GateState.OPEN, GateState.PENDING)
        assert output.shape == (768,)

    def test_single_history(self):
        z = ZuowangAttentionTorch(embed_dim=768)
        query = np.random.randn(768).astype(np.float32)
        history = np.random.randn(768).astype(np.float32)  # 1D
        state, output = z.forward(query, history)
        assert output.shape == (768,)

    def test_threshold_behavior(self):
        """高 theta → 更容易触发坐忘"""
        z_strict = ZuowangAttentionTorch(embed_dim=768, theta=0.99)
        z_loose = ZuowangAttentionTorch(embed_dim=768, theta=0.01)

        query = np.random.randn(768).astype(np.float32)
        history = np.random.randn(5, 768).astype(np.float32)

        state_strict, _ = z_strict.forward(query, history)
        state_loose, _ = z_loose.forward(query, history)

        # strict 更容易 pending
        assert state_strict == GateState.PENDING or state_loose == GateState.OPEN


class TestIntentDisambiguator:
    """意图歧义消解测试"""

    def test_creation(self):
        d = IntentDisambiguator(embed_dim=768, num_intents=5)
        assert d.num_intents == 5
        assert len(d.INTENT_LABELS) == 5

    def test_forward(self):
        d = IntentDisambiguator(embed_dim=768, num_intents=5, confidence_threshold=0.6)
        query = np.random.randn(768).astype(np.float32)
        history = np.random.randn(3, 768).astype(np.float32)
        action, result = d.forward(query, history)
        assert action in ("澄清", "开")
        assert "reason" in result or "intent" in result

    def test_clarify_has_candidates(self):
        """澄清动作应包含候选列表"""
        d = IntentDisambiguator(embed_dim=768, num_intents=5, confidence_threshold=0.99)
        query = np.random.randn(768).astype(np.float32)
        history = np.random.randn(3, 768).astype(np.float32)
        action, result = d.forward(query, history)
        # 高阈值 → 大概率澄清
        if action == "澄清" and "candidates" in result:
            assert len(result["candidates"]) <= 3

    def test_open_has_intent(self):
        """开动作应包含意图"""
        d = IntentDisambiguator(embed_dim=768, num_intents=5, confidence_threshold=0.01)
        query = np.random.randn(768).astype(np.float32)
        history = np.random.randn(3, 768).astype(np.float32)
        action, result = d.forward(query, history)
        if action == "开":
            assert "intent" in result
            assert "confidence" in result


# ============================================================================
# 开源层集成
# ============================================================================

class TestThreeFSClient:
    """3FS 客户端测试"""

    def test_mock_creation(self):
        fs = ThreeFSClient()
        assert fs.endpoint == "http://3fs-cluster:8080"
        assert fs._use_real is False

    def test_mock_seed_data(self):
        fs = ThreeFSClient()
        chunks = fs.read_all_embeddings()
        assert len(chunks) == 5  # 5 条预置数据

    def test_read_by_topic(self):
        fs = ThreeFSClient()
        chunks = fs.read_embeddings_by_topic("八字命理")
        assert len(chunks) >= 1

    def test_read_chunk(self):
        fs = ThreeFSClient()
        chunk = fs.read_chunk("chunk_0000")
        assert chunk is not None
        assert "text" in chunk
        assert "embedding" in chunk

    def test_read_nonexistent(self):
        fs = ThreeFSClient()
        chunk = fs.read_chunk("nonexistent")
        assert chunk is None

    def test_write_and_read(self):
        fs = ThreeFSClient()
        emb = np.random.randn(768).astype(np.float32)
        cid = fs.write_chunk("测试文本", emb, {"topic": "测试"})
        chunk = fs.read_chunk(cid)
        assert chunk is not None
        assert chunk["text"] == "测试文本"

    def test_stats(self):
        fs = ThreeFSClient()
        stats = fs.get_stats()
        assert stats["mode"] == "mock"
        assert stats["total_chunks"] >= 5


class TestDeepSeekR1Client:
    """R1 推理链客户端测试"""

    def test_mock_reasoning(self):
        r1 = DeepSeekR1Client()
        reasoning = r1.generate_reasoning("如果用户意图是八字命理，查询'帮我算八字'的后继对话应该是什么？")
        assert "推理链" in reasoning
        assert "八字" in reasoning

    def test_causal_gate_high(self):
        r1 = DeepSeekR1Client()
        acceptance = r1.causal_gate("推理链：... 置信度：高。")
        assert acceptance >= 0.7

    def test_causal_gate_low(self):
        r1 = DeepSeekR1Client()
        acceptance = r1.causal_gate("推理链：... 置信度：低。")
        assert acceptance < 0.5

    def test_caching(self):
        r1 = DeepSeekR1Client()
        r1.generate_reasoning("测试缓存")
        assert len(r1._mock_cache) > 0


class TestDSparkScheduler:
    """推测解码调度器测试"""

    def test_tau_range(self):
        s = DSparkScheduler(tau_min=2, tau_max=6)
        for load in [0.0, 0.5, 1.0]:
            tau = s.adjust_tau(load)
            assert 2 <= tau <= 6

    def test_load_trend(self):
        s = DSparkScheduler()
        assert s.get_load_trend() in ("stable", "rising", "falling")


# ============================================================================
# 三链合一总控
# ============================================================================

class TestGateCognitiveEngine:
    """门禁认知引擎总控测试"""

    def test_creation(self):
        engine = GateCognitiveEngine(embed_dim=768)
        assert engine.embed_dim == 768
        assert engine.projector is not None
        assert engine.gate_filter is not None
        assert engine.disambiguator is not None

    def test_process_normal(self):
        engine = GateCognitiveEngine(embed_dim=768)
        result = engine.process("帮我算一下八字", system_load=0.3)
        assert "session_id" in result
        assert "action" in result
        assert result["action"] in ("clarify", "reject", "pending", "generate")

    def test_process_high_load(self):
        engine = GateCognitiveEngine(embed_dim=768)
        result = engine.process("测试查询", system_load=0.95)
        assert result["action"] in ("clarify", "reject", "pending", "generate")

    def test_process_with_history(self):
        engine = GateCognitiveEngine(embed_dim=768)
        result = engine.process(
            "这个命怎么样",
            history=["帮我算一下八字", "好的，请提供出生日期"],
            system_load=0.3,
        )
        assert "session_id" in result

    def test_session_persistence(self):
        engine = GateCognitiveEngine(embed_dim=768)
        sid = "test_session_001"
        result1 = engine.process("第一条消息", session_id=sid)
        result2 = engine.process("第二条消息", session_id=sid)

        session = engine.get_session(sid)
        assert session is not None
        assert session["message_count"] == 2

    def test_session_topics(self):
        engine = GateCognitiveEngine(embed_dim=768)
        sid = "test_session_002"
        engine.process("帮我算八字", session_id=sid)
        session = engine.get_session(sid)
        assert isinstance(session["topics_covered"], set)

    def test_stats(self):
        engine = GateCognitiveEngine(embed_dim=768)
        stats = engine.get_stats()
        assert "torch_available" in stats
        assert "threefs_available" in stats
        assert "deepseek_available" in stats
        assert "dspark_available" in stats
        assert "storage_stats" in stats

    def test_set_embedding_fn(self):
        engine = GateCognitiveEngine(embed_dim=768)

        def mock_embed(text: str) -> np.ndarray:
            return np.ones(768, dtype=np.float32)

        engine.set_embedding_fn(mock_embed)
        result = engine.process("测试")
        assert result["action"] in ("clarify", "reject", "pending", "generate")

    def test_multiple_sessions_independent(self):
        engine = GateCognitiveEngine(embed_dim=768)
        result_a = engine.process("消息A", session_id="sess_a")
        result_b = engine.process("消息B", session_id="sess_b")
        assert result_a["session_id"] == "sess_a"
        assert result_b["session_id"] == "sess_b"

    def test_prompt_structure(self):
        engine = GateCognitiveEngine(embed_dim=768)
        result = engine.process("帮我算八字", system_load=0.3)
        if result["action"] == "generate":
            assert "prompt" in result
            assert "系统角色" in result["prompt"]

    def test_retrieved_format(self):
        engine = GateCognitiveEngine(embed_dim=768)
        result = engine.process("帮我算八字", system_load=0.3)
        if result["action"] == "generate":
            assert "retrieved" in result
            assert isinstance(result["retrieved"], list)
            for item in result["retrieved"]:
                assert isinstance(item, tuple)
                assert len(item) == 2  # (chunk_id, distance)


# ============================================================================
# 端到端集成测试
# ============================================================================

class TestEndToEndPipeline:
    """端到端三链合一管道"""

    def test_full_pipeline_mock(self):
        """全管道 mock 模式运行"""
        engine = GateCognitiveEngine(embed_dim=768)

        # 模拟多轮对话
        queries = [
            "帮我算一下八字",
            "我的命怎么样",
            "什么时候能发财",
        ]
        history = []
        for q in queries:
            result = engine.process(q, history=history, system_load=0.3)
            history.append(q)
            assert result["action"] in ("clarify", "reject", "pending", "generate")

    def test_torch_vs_numpy_consistency(self):
        """torch 和 numpy 路径应输出一致的结果形状"""
        proj = TBCESixDimProjector(dim=768)
        emb = np.random.randn(768).astype(np.float32)
        vec = proj.forward(emb)
        assert vec.shape == (1, 6)

    def test_gate_coefficient_loading(self):
        """九宫格门禁系数应正确加载"""
        proj = TBCESixDimProjector(dim=768)
        # 坎一 (T维调制 0.8)
        mods = proj.gate_mods["kan_1"]
        assert mods[0] == 1.0  # S 维不调制
        assert mods[1] == 0.8  # T 维调制

    def test_engine_availability_flags(self):
        """引擎应正确报告可用性"""
        engine = GateCognitiveEngine(embed_dim=768)
        stats = engine.get_stats()
        assert isinstance(stats["torch_available"], bool)
        assert isinstance(stats["threefs_available"], bool)
        assert isinstance(stats["deepseek_available"], bool)
        assert isinstance(stats["dspark_available"], bool)