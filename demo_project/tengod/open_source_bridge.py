"""
open_source_bridge.py — 开源方案集成桥接层 v3.1.0
=====================================================
道曰："工欲善其事，必先利其器。"

开源层集成（真实调用 + Mock fallback）：
  - ThreeFSClient      — 分布式文件系统 chunk 存储与检索
  - DeepSeekR1Client   — 推理链验证（因果门禁）
  - DSparkScheduler    — 推测解码节奏控制
  - GateCognitiveEngine — 门禁认知引擎总控入口

依赖策略：
  - 开源包可用 → 真实集成
  - 开源包不可用 → Mock 实现（功能等价，可测试）
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# ── 现有门禁模块 ──────────────────────────────────────────────────
from .tbce_unit import TBCECoordinates, CognitiveUnit, GateState
from .gate_torch import (
    TBCESixDimProjector,
    GateFilter,
    RhythmScheduler,
    ZuowangAttentionTorch,
    IntentDisambiguator,
    retrieve_with_gates,
    geodesic_distance,
    _HAS_TORCH,
)
from .local_embedding import LocalEmbedder, create_embedder

# ── 可选开源包导入 ────────────────────────────────────────────────
_HAS_THREEFS = False
_HAS_DEEPSEEK = False
_HAS_DSPARK = False

try:
    from deepseek_ai import ThreeFSClient as _RealThreeFSClient
    _HAS_THREEFS = True
except ImportError:
    pass

try:
    from deepseek_ai import DeepSeekR1Client as _RealR1Client
    _HAS_DEEPSEEK = True
except ImportError:
    pass

try:
    from deepseek_ai import DSparkScheduler as _RealDSparkScheduler
    _HAS_DSPARK = True
except ImportError:
    pass


# ============================================================================
# Mock 数据存储
# ============================================================================

@dataclass
class MockChunk:
    """Mock chunk 数据结构"""
    chunk_id: str
    text: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 1. ThreeFS 客户端（分布式文件系统 chunk 存储）
# ============================================================================

class ThreeFSClient:
    """3FS 分布式文件系统客户端

    真实模式：通过 deepseek_ai.ThreeFSClient 连接 3FS 集群
    Mock 模式：内存 dict 存储，用于测试
    """

    def __init__(self, endpoint: str = "http://3fs-cluster:8080"):
        self.endpoint = endpoint
        self._use_real = _HAS_THREEFS

        if self._use_real:
            self._client = _RealThreeFSClient(endpoint=endpoint)
        else:
            self._chunks: Dict[str, MockChunk] = {}
            # 预置一些 mock 数据
            self._seed_mock_data()

    def _seed_mock_data(self) -> None:
        """预置 mock 知识库数据"""
        mock_texts = [
            ("八字排盘 年柱月柱日柱时柱 天干地支六十甲子 五行生克 十神定位 大运流年", "八字命理"),
            ("紫微斗数十二宫 命宫兄弟宫夫妻宫 星曜分布 四化飞星 三方四正", "紫微斗数"),
            ("六爻起卦方法 三枚铜钱摇六次 本卦变卦互卦 世爻应爻动爻", "六爻占卜"),
            ("玄空飞星风水 九宫飞布 山向两星 旺山旺向 三元九运", "风水堪舆"),
            ("姓名学五格数理 天格人格地格外格总格 三才配置 81数理吉凶", "姓名学"),
        ]
        for i, (text, topic) in enumerate(mock_texts):
            cid = f"chunk_{i:04d}"
            # 使用文本 hash 生成确定性 embedding（384维）
            seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            emb = rng.randn(384).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            self._chunks[cid] = MockChunk(
                chunk_id=cid,
                text=text,
                embedding=emb,
                metadata={"topic": topic, "source": "mock"},
            )

    def read_all_embeddings(self) -> List[Tuple[str, np.ndarray]]:
        """读取所有 chunk 的 embeddings"""
        if self._use_real:
            return self._client.read_all_embeddings()
        return [(cid, c.embedding) for cid, c in self._chunks.items()]

    def read_embeddings_by_topic(self, topic: str) -> List[Tuple[str, np.ndarray]]:
        """按主题读取 embeddings"""
        if self._use_real:
            return self._client.read_embeddings_by_topic(topic)
        return [
            (cid, c.embedding)
            for cid, c in self._chunks.items()
            if c.metadata.get("topic") == topic
        ]

    def read_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """读取单个 chunk"""
        if self._use_real:
            return self._client.read_chunk(chunk_id)
        c = self._chunks.get(chunk_id)
        if c is None:
            return None
        return {
            "chunk_id": c.chunk_id,
            "text": c.text,
            "embedding": c.embedding,
            "metadata": c.metadata,
        }

    def write_chunk(self, text: str, embedding: np.ndarray, metadata: Dict[str, Any] = None) -> str:
        """写入 chunk"""
        cid = f"chunk_{uuid.uuid4().hex[:8]}"
        if self._use_real:
            return self._client.write_chunk(text, embedding, metadata)
        self._chunks[cid] = MockChunk(
            chunk_id=cid,
            text=text,
            embedding=embedding.astype(np.float32),
            metadata=metadata or {},
        )
        return cid

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        if self._use_real:
            return self._client.get_stats()
        return {
            "total_chunks": len(self._chunks),
            "topics": list(set(c.metadata.get("topic", "unknown") for c in self._chunks.values())),
            "mode": "mock",
        }


# ============================================================================
# 2. DeepSeek-R1 客户端（推理链验证）
# ============================================================================

class DeepSeekR1Client:
    """DeepSeek-R1 推理链客户端

    用于因果门禁的推理链验证 —— 判断候选意图是否因果自洽。
    """

    def __init__(self, api_key: str = "", endpoint: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "mock_key")
        self.endpoint = endpoint
        self._use_real = _HAS_DEEPSEEK and self.api_key != "mock_key"

        if self._use_real:
            self._client = _RealR1Client(api_key=self.api_key)
        else:
            self._mock_cache: Dict[str, str] = {}

    def generate_reasoning(self, prompt: str, max_tokens: int = 256) -> str:
        """生成推理链

        Args:
            prompt: 推理提示
            max_tokens: 最大 token 数

        Returns:
            推理链文本
        """
        if self._use_real:
            return self._client.generate_reasoning(prompt, max_tokens=max_tokens)

        # Mock: 基于 prompt 内容生成确定性推理
        cache_key = prompt[:100]
        if cache_key in self._mock_cache:
            return self._mock_cache[cache_key]

        # 简单的 mock 推理
        if "八字" in prompt or "命理" in prompt:
            reasoning = "推理链：用户提及八字相关术语 → 意图为命理查询 → 建议展示八字排盘结果。置信度：高。"
        elif "紫微" in prompt or "斗数" in prompt:
            reasoning = "推理链：用户提及紫微斗数 → 意图为星盘查询 → 建议展示十二宫分析。置信度：高。"
        elif "六爻" in prompt or "占卜" in prompt:
            reasoning = "推理链：用户提及六爻占卜 → 意图为预测咨询 → 建议展示起卦结果。置信度：中。"
        elif "风水" in prompt or "堪舆" in prompt:
            reasoning = "推理链：用户提及风水堪舆 → 意图为环境分析 → 建议展示方位吉凶。置信度：中。"
        elif "姓名" in prompt or "取名" in prompt:
            reasoning = "推理链：用户提及姓名学 → 意图为命名分析 → 建议展示五格数理。置信度：中。"
        else:
            reasoning = f"推理链：用户查询'{prompt[:50]}...' → 意图需要进一步澄清。置信度：低。"

        self._mock_cache[cache_key] = reasoning
        return reasoning

    def causal_gate(self, reasoning: str) -> float:
        """因果门禁：基于推理链判断因果自洽性

        Args:
            reasoning: R1 生成的推理链

        Returns:
            因果接受度 [0, 1]
        """
        if self._use_real:
            return self._client.causal_gate(reasoning)

        # Mock: 基于推理链中的关键词判断
        if "置信度：高" in reasoning:
            return 0.85
        elif "置信度：中" in reasoning:
            return 0.65
        elif "置信度：低" in reasoning:
            return 0.35
        else:
            return 0.5


# ============================================================================
# 3. DSpark 调度器（推测解码节奏控制）
# ============================================================================

class DSparkScheduler:
    """推测解码节奏调度器

    根据系统负载动态调整 tau（检索深度），tau ∈ [2, 6]。
    """

    def __init__(self, tau_min: int = 2, tau_max: int = 6):
        self.tau_min = tau_min
        self.tau_max = tau_max
        self._use_real = _HAS_DSPARK

        if self._use_real:
            self._scheduler = _RealDSparkScheduler(tau_range=(tau_min, tau_max))
        else:
            self._scheduler = RhythmScheduler(tau_min=tau_min, tau_max=tau_max)

    def adjust_tau(self, system_load: float) -> int:
        """调整检索深度"""
        if self._use_real:
            return self._scheduler.adjust_tau(system_load)
        return self._scheduler.adjust_tau(system_load)

    def get_load_trend(self) -> str:
        """获取负载趋势"""
        if self._use_real:
            return self._scheduler.get_load_trend()
        return self._scheduler.get_load_trend()


# ============================================================================
# 4. 门禁认知引擎总控
# ============================================================================

class GateCognitiveEngine:
    """门禁认知引擎总控 v3.1.0

    三链合一：
      1. 语义向量检索：六维投影 + 测地线门禁
      2. RAG 增强：门禁预过滤 + 节奏采样
      3. 多轮对话：坐忘门禁 + 主动澄清

    用法：
        engine = GateCognitiveEngine()
        result = engine.process("帮我算一下八字", history=[], system_load=0.3)
    """

    def __init__(
        self,
        embed_dim: int = 384,
        fs_endpoint: str = "http://3fs-cluster:8080",
        deepseek_api_key: str = "",
    ):
        self.embed_dim = embed_dim

        # 嵌入层：优先 SentenceTransformer → TF-IDF+SVD → 随机投影
        self._embedder = create_embedder(dim=embed_dim, mode="auto", fit_corpus=True)
        self.embed_dim = self._embedder.get_dim()  # 可能与输入不同

        # 门禁层（维度对齐嵌入器输出）
        self.projector = TBCESixDimProjector(dim=self.embed_dim)
        self.gate_filter = GateFilter(dim=self.embed_dim)
        self.disambiguator = IntentDisambiguator(
            embed_dim=self.embed_dim, num_intents=5, confidence_threshold=0.4,
        )

        # 开源层
        self.fs = ThreeFSClient(endpoint=fs_endpoint)
        self.r1_client = DeepSeekR1Client(api_key=deepseek_api_key)
        self.scheduler = DSparkScheduler(tau_min=2, tau_max=6)

        # 对话状态
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._embedding_fn: Optional[Callable] = None

    def set_embedding_fn(self, fn: Callable[[str], np.ndarray]) -> None:
        """设置 embedding 函数（如 SentenceTransformer.encode）

        Args:
            fn: 接受文本，返回 (dim,) numpy 向量
        """
        self._embedding_fn = fn

    def _embed(self, text: str) -> np.ndarray:
        """文本 → embedding"""
        if self._embedding_fn is not None:
            emb = self._embedding_fn(text)
            return _ensure_numpy(emb)
        # Fallback: 随机投影（确定性，基于文本 hash）
        import hashlib
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        return rng.randn(self.embed_dim).astype(np.float32)

    def process(
        self,
        query: str,
        history: Optional[List[str]] = None,
        system_load: float = 0.5,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """认知引擎主入口

        Args:
            query: 用户查询文本
            history: 历史对话列表（最近 N 条）
            system_load: 系统负载 [0, 1]
            session_id: 会话 ID，None 则自动创建

        Returns:
            处理结果字典
        """
        session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        history = history or []

        # 初始化会话
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "created_at": time.time(),
                "message_count": 0,
                "topics_covered": set(),
            }
        session = self._sessions[session_id]
        session["message_count"] += 1

        # Step 1: 多轮意图消解
        query_emb = self._embed(query)
        history_embs = np.stack([self._embed(h) for h in history[-10:]]) if history else np.zeros((1, self.embed_dim), dtype=np.float32)

        intent_action, intent_result = self.disambiguator.forward(query_emb, history_embs, query_text=query)

        if intent_action == "澄清":
            return {
                "session_id": session_id,
                "action": "clarify",
                "message": intent_result.get("message", "请澄清您的意图"),
                "candidates": intent_result.get("candidates", []),
                "reason": intent_result.get("reason", "坐忘门禁"),
            }

        # Step 2: RAG 门禁预过滤
        gate_state, gate_details = self.gate_filter.forward(
            query_emb, query_text=query, system_load=system_load,
        )

        if gate_state == GateState.CLOSED:
            return {
                "session_id": session_id,
                "action": "reject",
                "message": "门禁拒绝当前请求",
                "gate_details": gate_details,
            }
        elif gate_state == GateState.PENDING:
            return {
                "session_id": session_id,
                "action": "pending",
                "message": "请求已挂起，等待人工确认",
                "gate_details": gate_details,
            }

        # Step 3: 节奏检索 + 测地线排序
        tau = self.scheduler.adjust_tau(system_load)
        all_chunks = self.fs.read_all_embeddings()
        retrieved = retrieve_with_gates(
            query_emb, all_chunks,
            projector=self.projector,
            threshold=0.5,
            top_k=tau,
        )

        # Step 4: 因果门禁验证（R1 推理链）
        if intent_result.get("intent_name"):
            # 用 R1 验证候选意图的因果合理性
            reasoning = self.r1_client.generate_reasoning(
                f"如果用户意图是{intent_result['intent_name']}，"
                f"查询'{query[:100]}'的后继对话应该是什么？"
            )
            causal_acceptance = self.r1_client.causal_gate(reasoning)
        else:
            causal_acceptance = 0.5

        # Step 5: 构建结构化 Prompt
        retrieved_texts = []
        for cid, dist in retrieved:
            chunk = self.fs.read_chunk(cid)
            if chunk:
                retrieved_texts.append(f"- [{dist:.3f}] {chunk['text']}")

        prompt = self._build_prompt(query, retrieved_texts, intent_result)

        # 更新会话
        if intent_result.get("intent_name"):
            session["topics_covered"].add(intent_result["intent_name"])

        return {
            "session_id": session_id,
            "action": "generate",
            "intent": intent_result,
            "gate_state": gate_state,
            "gate_details": gate_details,
            "retrieved_count": len(retrieved),
            "retrieved": retrieved,
            "tau": tau,
            "causal_acceptance": round(causal_acceptance, 3),
            "prompt": prompt,
            "system_load": system_load,
            "session_stats": {
                "message_count": session["message_count"],
                "topics_covered": list(session["topics_covered"]),
            },
        }

    def _build_prompt(
        self,
        query: str,
        retrieved_texts: List[str],
        intent_result: Dict[str, Any],
    ) -> str:
        """构建结构化 RAG Prompt"""
        retrieved_block = "\n".join(retrieved_texts) if retrieved_texts else "（无相关检索结果）"

        intent_name = intent_result.get("intent_name", "综合")
        confidence = intent_result.get("confidence", 0.5)

        return f"""系统角色：门禁认知系统 · {intent_name}（置信度 {confidence:.0%}）

检索结果（共 {len(retrieved_texts)} 条）：
{retrieved_block}

用户问题：{query}

请基于以上检索结果生成答案。若检索结果不足以回答问题，请明确说明。"""

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self._sessions.get(session_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计"""
        return {
            "active_sessions": len(self._sessions),
            "torch_available": _HAS_TORCH,
            "threefs_available": _HAS_THREEFS,
            "deepseek_available": _HAS_DEEPSEEK,
            "dspark_available": _HAS_DSPARK,
            "storage_stats": self.fs.get_stats(),
        }


# ============================================================================
# 工具函数
# ============================================================================

def _ensure_numpy(x: Any) -> np.ndarray:
    """确保 numpy 数组"""
    if isinstance(x, np.ndarray):
        return x.astype(np.float32)
    if hasattr(x, 'detach'):  # torch tensor
        return x.detach().cpu().numpy().astype(np.float32)
    return np.array(x, dtype=np.float32)


# ============================================================================
# 自检
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  门禁认知引擎 v3.1.0 — 三链合一自检")
    print("=" * 60)

    # 创建引擎（默认 384 维，与 TF-IDF+SVD 对齐）
    engine = GateCognitiveEngine(embed_dim=384)
    stats = engine.get_stats()
    print(f"\n  引擎状态: torch={stats['torch_available']}, "
          f"3FS={stats['threefs_available']}, "
          f"R1={stats['deepseek_available']}, "
          f"DSpark={stats['dspark_available']}")
    print(f"  存储: {stats['storage_stats']}")

    # 测试 1: 正常查询
    print("\n── 测试 1: 八字命理查询 ──")
    result = engine.process("帮我算一下八字", system_load=0.3)
    print(f"  action={result['action']}")
    if result.get("gate_details"):
        gd = result["gate_details"]
        print(f"  gates: auth={gd['auth_gate']}, resource={gd['resource_gate']}, causal={gd['causal_score']:.3f}→{gd['causal_gate']}")
    if result.get("retrieved"):
        print(f"  retrieved={result['retrieved_count']}, tau={result['tau']}")
        print(f"  causal_acceptance={result['causal_acceptance']}")

    # 测试 2: 多轮对话
    print("\n── 测试 2: 多轮对话（歧义消解）──")
    result2 = engine.process("这个命怎么样", history=["帮我算一下八字"], system_load=0.3)
    print(f"  action={result2['action']}")
    if result2['action'] == 'clarify':
        print(f"  message={result2.get('message', '')[:80]}...")

    # 测试 3: 门禁拒绝
    print("\n── 测试 3: 高负载拒绝 ──")
    result3 = engine.process("测试查询", system_load=0.95)
    print(f"  action={result3['action']}, gate={result3.get('gate_state')}")

    print("\n" + "=" * 60)
    print("  自检完成")
    print("=" * 60)