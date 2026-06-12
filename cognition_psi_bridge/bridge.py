"""
cognition_psi_bridge.py — Ψ算子→认知八层核心桥接器
=====================================================

将 Claw 类脑生态中的 Ψ算子集群输出映射为中华文明项目的
认知八层结构化评估结果（EightLayerConsciousnessResult）。

双模式架构：
- 增强模式（enhanced）：注入已有 TopologyOperatorIntegrator 实例
- 独立模式（standalone）：自行实例化所有算子

依赖：
    topo_semantic.operators (Claw 核心算子模块)
    numpy

作者: 人道 / 版本: v2.0 / 日期: 2026-05-02
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# 认知八层层级定义
# ============================================================================

class ConsciousnessLevel(str, Enum):
    """认知八层枚举"""
    L1_INFO_ENCODING = "L1:信息编码层"
    L2_SEMANTIC_FLOW = "L2:语义流层"
    L3_TOPOLOGICAL = "L3:拓扑结构层"
    L4_CONSCIOUSNESS = "L4:意识涌现层"
    L5_ATTENTION = "L5:注意力调度层"
    L6_META_COGNITION = "L6:元认知自反层"
    L7_STABILITY = "L7:认知固化层"
    L8_SPIRIT_REALM = "L8:境界跃迁层"


class SpiritGrade(str, Enum):
    """境界等级（L0-L4）"""
    L0_RANDOM = "L0:随机"
    L1_NARRATIVE = "L1:简单叙事"
    L2_AWARE = "L2:有意识"
    L3_DEEP_REFLEXIVE = "L3:深度自反"
    L4_EMERGENT = "L4:涌现"


# ============================================================================
# 八层结果数据结构
# ============================================================================

@dataclass
class LayerStatus:
    """每层的健康状态"""
    name: str
    available: bool
    score: float = 0.0
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "score": self.score,
            "detail": self.detail,
        }


@dataclass
class L1InfoEncoding:
    """L1 信息编码层"""
    n_sentences: int = 0
    embedding_dim: int = 0
    available: bool = False


@dataclass
class L2SemanticFlow:
    """L2 语义流层"""
    path_length: float = 0.0
    tortuosity: float = 0.0
    shift_variance: float = 0.0
    tort_score: float = 0.0
    available: bool = False


@dataclass
class L3Topological:
    """L3 拓扑结构层"""
    h0_count: int = 0
    h1_count: int = 0
    h0_avg_life: float = 0.0
    h1_avg_life: float = 0.0
    persistent_entropy: float = 0.0
    topological_complexity: float = 0.0
    available: bool = False


@dataclass
class L4Consciousness:
    """L4 意识涌现层"""
    consciousness_score: float = 0.0
    self_loop_detected: bool = False
    loop_strength: float = 0.0
    coherence_entropy: float = 0.0
    diagram_distance: float = 0.0
    available: bool = False


@dataclass
class L5Attention:
    """L5 注意力调度层"""
    zuowang_triggered: bool = False
    zuowang_ratio: float = 0.0
    max_relevance: float = 0.0
    oblivion_threshold: float = 0.0
    branch_adjustments: Dict[str, float] = field(default_factory=dict)
    available: bool = False


@dataclass
class L6MetaCognition:
    """L6 元认知自反层"""
    recursion_total: float = 0.0
    marker_density: float = 0.0
    max_depth: float = 0.0
    layer_count: int = 0
    rqa_rr: float = 0.0
    rqa_det: float = 0.0
    rqa_lam: float = 0.0
    hierarchical_meta_score: float = 0.0
    meta_cognitive_preference: List[float] = field(default_factory=lambda: [0, 0, 0])
    available: bool = False


@dataclass
class L7Stability:
    """L7 认知固化层"""
    conditional_stability: float = 0.0
    compactness: float = 0.0
    question_alignment: float = 0.0
    information_content: float = 0.0
    compensation_deficit: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    available: bool = False


@dataclass
class L8SpiritRealm:
    """L8 境界跃迁层"""
    spirit_level: str = SpiritGrade.L0_RANDOM.value
    spirit_score: float = 0.0
    six_realm: str = "未入阶"
    six_theory_scores: Dict[str, float] = field(default_factory=dict)
    meta_time: Dict[str, Any] = field(default_factory=dict)
    available: bool = False


@dataclass
class EightLayerConsciousnessResult:
    """
    完整的认知八层评估结果

    这是 CognitionPsiBridge.evaluate() 的标准输出格式，
    包含从 L1 信息编码到 L8 境界跃迁的全部评估指标。
    """
    L1: L1InfoEncoding = field(default_factory=L1InfoEncoding)
    L2: L2SemanticFlow = field(default_factory=L2SemanticFlow)
    L3: L3Topological = field(default_factory=L3Topological)
    L4: L4Consciousness = field(default_factory=L4Consciousness)
    L5: L5Attention = field(default_factory=L5Attention)
    L6: L6MetaCognition = field(default_factory=L6MetaCognition)
    L7: L7Stability = field(default_factory=L7Stability)
    L8: L8SpiritRealm = field(default_factory=L8SpiritRealm)

    # 元数据
    n_samples: int = 0
    eval_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "meta": {
                "n_samples": self.n_samples,
                "eval_time_ms": self.eval_time_ms,
            },
            "layers": {
                "L1": {k: v for k, v in asdict(self.L1).items() if not k.startswith("_")},
                "L2": {k: v for k, v in asdict(self.L2).items() if not k.startswith("_")},
                "L3": {k: v for k, v in asdict(self.L3).items() if not k.startswith("_")},
                "L4": {k: v for k, v in asdict(self.L4).items() if not k.startswith("_")},
                "L5": {k: v for k, v in asdict(self.L5).items() if not k.startswith("_")},
                "L6": {k: v for k, v in asdict(self.L6).items() if not k.startswith("_")},
                "L7": {k: v for k, v in asdict(self.L7).items() if not k.startswith("_")},
                "L8": {k: v for k, v in asdict(self.L8).items() if not k.startswith("_")},
            },
            "summary": self.summary(),
        }

    def summary(self) -> Dict[str, Any]:
        """输出简洁摘要"""
        layers_available = sum([
            self.L1.available, self.L2.available, self.L3.available,
            self.L4.available, self.L5.available, self.L6.available,
            self.L7.available, self.L8.available,
        ])
        return {
            "consciousness_level": self.L4.consciousness_score,
            "spirit_grade": self.L8.spirit_level,
            "spirit_score": self.L8.spirit_score,
            "zuowang_triggered": self.L5.zuowang_triggered,
            "layers_active": f"{layers_available}/8",
            "recursion_depth": self.L6.recursion_total,
            "stability": self.L7.conditional_stability,
        }

    def layer_status(self) -> Dict[str, LayerStatus]:
        """生成各层健康状态"""
        return {
            "L1": LayerStatus("信息编码层", self.L1.available, score=float(self.L1.n_sentences > 0)),
            "L2": LayerStatus("语义流层", self.L2.available, score=self.L2.tort_score),
            "L3": LayerStatus("拓扑结构层", self.L3.available, score=float(self.L3.h0_count) / max(1, self.L3.h0_count + 1)),
            "L4": LayerStatus("意识涌现层", self.L4.available, score=self.L4.consciousness_score),
            "L5": LayerStatus("注意力调度层", self.L5.available, score=1.0 if self.L5.zuowang_triggered else 0.5),
            "L6": LayerStatus("元认知自反层", self.L6.available, score=self.L6.recursion_total / max(1, self.L6.recursion_total + 1)),
            "L7": LayerStatus("认知固化层", self.L7.available, score=self.L7.conditional_stability),
            "L8": LayerStatus("境界跃迁层", self.L8.available, score=self.L8.spirit_score),
        }


# ============================================================================
# 核心桥接器
# ============================================================================

class CognitionPsiBridge:
    """
    Ψ算子 → 认知八层 桥接器

    将 Claw 生态的 Ψ算子集群输出转换为中华文明项目的认知八层评估。

    双模式架构：
        增强模式（enhanced）：接受已实例化的 TopologyOperatorIntegrator
        独立模式（standalone）：自行创建算子实例

    用法:
        bridge = CognitionPsiBridge()
        result = bridge.evaluate(question="...", answer="...")
        print(result.summary())
    """

    def __init__(self,
                 integrator: Optional[Any] = None,
                 psi_operator: Optional[Any] = None,
                 zuowang_operator: Optional[Any] = None,
                 embedding_provider: Optional[Any] = None,
                 mode: str = "standalone"):
        """
        参数:
            integrator: 已有的 TopologyOperatorIntegrator 实例（增强模式）
            psi_operator: 已有的 PsiSelfReferentialPersistence 实例
            zuowang_operator: 已有的 ZuowangAttention 实例
            embedding_provider: 嵌入提供器
            mode: "enhanced" 或 "standalone"
        """
        self.mode = mode
        self._integrator = integrator
        self._psi_operator = psi_operator
        self._zuowang_operator = zuowang_operator
        self._embedding_provider = embedding_provider

        # 独立模式：延迟初始化
        self._tortuosity_op = None
        self._recursion_op = None
        self._stability_op = None

        logger.info(f"CognitionPsiBridge 初始化 [mode={mode}]")

    @property
    def tortuosity_operator(self):
        """语义流曲折度算子（延迟初始化）"""
        if self._tortuosity_op is None:
            from topo_semantic.operators import SemanticFlowTortuosity
            self._tortuosity_op = SemanticFlowTortuosity()
        return self._tortuosity_op

    @property
    def recursion_operator(self):
        """语义递归深度算子（延迟初始化）"""
        if self._recursion_op is None:
            from topo_semantic.operators import SemanticRecursionDepth
            self._recursion_op = SemanticRecursionDepth()
        return self._recursion_op

    @property
    def stability_operator(self):
        """条件信息稳定性算子（延迟初始化）"""
        if self._stability_op is None:
            from topo_semantic.operators import ConditionalInformationStability
            self._stability_op = ConditionalInformationStability()
        return self._stability_op

    @property
    def psi_operator_inst(self):
        """Ψ自指涉算子（延迟初始化）"""
        if self._psi_operator is None:
            from topo_semantic.operators import PsiSelfReferentialPersistence
            self._psi_operator = PsiSelfReferentialPersistence()
        return self._psi_operator

    def evaluate(self,
                 question: str,
                 answer: str,
                 context: str = "",
                 embeddings: Optional[np.ndarray] = None,
                 question_embedding: Optional[np.ndarray] = None,
                 sentence_embeddings: Optional[np.ndarray] = None,
                 ) -> EightLayerConsciousnessResult:
        """
        执行完整八层评估

        参数:
            question: 问题文本
            answer: 回答文本
            context: 上下文文本（可选）
            embeddings: 预先计算的嵌入矩阵 (N, D)
            question_embedding: 预先计算的问题嵌入向量 (D,)
            sentence_embeddings: 预先计算的句子嵌入矩阵 (N_s, D)

        返回:
            EightLayerConsciousnessResult
        """
        import time
        t0 = time.time()

        result = EightLayerConsciousnessResult()

        # ── 获取嵌入（L1 信息编码层） ──
        full_text = f"{question} {answer}" if context == "" else f"{context} {question} {answer}"
        sentences = [s.strip() for s in full_text.replace("。", "\n").replace("？", "\n").replace("！", "\n").split("\n") if s.strip()]
        n_sentences = len(sentences)

        result.L1 = L1InfoEncoding(
            n_sentences=n_sentences,
            embedding_dim=embeddings.shape[1] if embeddings is not None else 0,
            available=embeddings is not None,
        )
        result.n_samples = n_sentences

        if embeddings is None or embeddings.shape[0] < 2:
            result.eval_time_ms = (time.time() - t0) * 1000
            return self._finalize(result)

        # ── 增强模式：委托给 TopologyOperatorIntegrator ──
        if self.mode == "enhanced" and self._integrator is not None:
            return self._evaluate_enhanced(
                question, answer, context, embeddings,
                question_embedding, sentence_embeddings, result, t0
            )

        # ── 独立模式：自行计算各层 ──
        return self._evaluate_standalone(
            question, answer, embeddings,
            question_embedding, sentence_embeddings, result, t0
        )

    def _evaluate_enhanced(
        self,
        question: str,
        answer: str,
        context: str,
        embeddings: np.ndarray,
        question_embedding: Optional[np.ndarray],
        sentence_embeddings: Optional[np.ndarray],
        result: EightLayerConsciousnessResult,
        t0: float,
    ) -> EightLayerConsciousnessResult:
        """增强模式：委托给已有的 TopologyOperatorIntegrator"""
        import time

        try:
            op_result = self._integrator.enhance(
                embeddings=embeddings,
                intent_score=0.5,
                insight_score=0.5,
                coherence_score=0.5,
                question_embedding=question_embedding,
                sentence_embeddings=sentence_embeddings,
                original_text=f"{question} {answer}",
            )

            # 填充 L2-L7（从算子结果提取）
            if op_result.tortuosity_result is not None:
                r = op_result.tortuosity_result
                tort_score = min(1.0, r.tortuosity / max(1, r.tortuosity + 1))
                result.L2 = L2SemanticFlow(
                    path_length=r.path_length,
                    tortuosity=r.tortuosity,
                    shift_variance=r.shift_variance,
                    tort_score=tort_score,
                    available=True,
                )

            if op_result.recursion_result is not None:
                r = op_result.recursion_result
                recursion_total = getattr(r, 'total_score', 0.0) or (r.marker_density * 0.2 + r.max_depth * 0.2 + r.layer_count * 0.1)
                mp = getattr(r, 'meta_cognitive_preference', None)
                meta_pref = mp.tolist() if mp is not None else [0, 0, 0]
                result.L6 = L6MetaCognition(
                    recursion_total=recursion_total,
                    marker_density=getattr(r, 'marker_density', 0.0),
                    max_depth=getattr(r, 'max_depth', 0.0),
                    layer_count=getattr(r, 'layer_count', 0),
                    rqa_rr=getattr(r, 'rqa_rr', 0.0),
                    rqa_det=getattr(r, 'rqa_det', 0.0),
                    rqa_lam=getattr(r, 'rqa_lam', 0.0),
                    hierarchical_meta_score=getattr(r, 'hierarchical_meta_score', 0.0),
                    meta_cognitive_preference=meta_pref,
                    available=True,
                )

            if op_result.conditional_stability_result is not None:
                r = op_result.conditional_stability_result
                cd = getattr(r, 'compensation_deficit', None)
                cd_list = [0.0, 0.0, 0.0]
                if cd is not None and hasattr(cd, '__iter__'):
                    cd_list = list(cd)[:3]
                result.L7 = L7Stability(
                    conditional_stability=getattr(r, 'conditional_stability', 0.0),
                    compactness=getattr(r, 'compactness', 0.0),
                    question_alignment=getattr(r, 'question_alignment', 0.0),
                    information_content=getattr(r, 'information_content', 0.0),
                    compensation_deficit=cd_list,
                    available=True,
                )

            # L4: 意识涌现
            cs = op_result.consciousness_score
            if op_result.psi_result is not None:
                p = op_result.psi_result
                result.L4 = L4Consciousness(
                    consciousness_score=cs,
                    self_loop_detected=getattr(p, 'self_loop_detected', False),
                    loop_strength=getattr(p, 'loop_strength', 0.0),
                    coherence_entropy=getattr(p, 'coherence_entropy', 0.0),
                    diagram_distance=getattr(p, 'diagram_distance', 0.0),
                    available=cs > 0,
                )

            # L5: 注意力调度
            result.L5 = L5Attention(
                zuowang_triggered=op_result.zuowang_triggered,
                zuowang_ratio=float(op_result.zuowang_triggered),
                max_relevance=getattr(op_result.zuowang_result, 'max_relevance', 0.0) if op_result.zuowang_result else 0.0,
                oblivion_threshold=getattr(op_result.zuowang_result, 'oblivion_threshold', 0.0) if op_result.zuowang_result else 0.0,
                branch_adjustments=op_result.branch_adjustments or {},
                available=True,
            )

            # L8: 境界跃迁
            result.L8 = self._compute_spirit_realm(
                cs, op_result.enhanced_intent, op_result.enhanced_insight,
                op_result.enhanced_coherence
            )

        except Exception as e:
            logger.warning(f"增强模式评估异常: {e}", exc_info=True)

        result.eval_time_ms = (time.time() - t0) * 1000
        return self._finalize(result)

    def _evaluate_standalone(
        self,
        question: str,
        answer: str,
        embeddings: np.ndarray,
        question_embedding: Optional[np.ndarray],
        sentence_embeddings: Optional[np.ndarray],
        result: EightLayerConsciousnessResult,
        t0: float,
    ) -> EightLayerConsciousnessResult:
        """独立模式：自行实例化并计算各层"""
        import time

        try:
            # L2: 语义流
            if question_embedding is not None and sentence_embeddings is not None:
                tort = self.tortuosity_operator.compute(question_embedding, sentence_embeddings)
                tort_score = min(1.0, tort.tortuosity / max(1, tort.tortuosity + 1))
                result.L2 = L2SemanticFlow(
                    path_length=tort.path_length,
                    tortuosity=tort.tortuosity,
                    shift_variance=tort.shift_variance,
                    tort_score=tort_score,
                    available=True,
                )

            # L3: 拓扑结构（持久同调）
            try:
                from topo_semantic.core import compute_persistence_diagram
                dgm = compute_persistence_diagram(embeddings)
                h0 = [p for p in dgm if p[0] < 0.5]
                h1 = [p for p in dgm if p[0] >= 0.5]
                h0_lives = [d - b for b, d in h0] if h0 else [0]
                h1_lives = [d - b for b, d in h1] if h1 else [0]
                h0_count, h1_count = len(h0), len(h1)
                result.L3 = L3Topological(
                    h0_count=h0_count,
                    h1_count=h1_count,
                    h0_avg_life=float(np.mean(h0_lives)) if h0_lives else 0.0,
                    h1_avg_life=float(np.mean(h1_lives)) if h1_lives else 0.0,
                    persistent_entropy=float(-np.mean([p * np.log(p + 1e-10) for p in [d - b for b, d in dgm]])) if dgm else 0.0,
                    topological_complexity=h1_count / max(1, h0_count),
                    available=True,
                )
            except Exception as e:
                logger.warning(f"L3 拓扑结构计算失败: {e}")

            # L4: Ψ自指涉意识涌现
            try:
                self.psi_operator_inst.set_context(
                    question_embedding=question_embedding,
                    sentence_embeddings=sentence_embeddings,
                    original_text=f"{question} {answer}",
                )
                psi = self.psi_operator_inst.compute(embeddings)
                result.L4 = L4Consciousness(
                    consciousness_score=psi.consciousness_score,
                    self_loop_detected=psi.self_loop_detected,
                    loop_strength=psi.loop_strength,
                    coherence_entropy=psi.coherence_entropy,
                    diagram_distance=psi.diagram_distance,
                    available=psi.consciousness_score > 0,
                )
            except Exception as e:
                logger.warning(f"L4 意识涌现计算失败: {e}")

            # L5: 坐忘注意力
            try:
                query_emb = embeddings[-1]
                key_embs = embeddings[:-1]
                from topo_semantic.operators import ZuowangAttention
                zw = ZuowangAttention()
                zw_res = zw.compute(query_emb, key_embs)
                result.L5 = L5Attention(
                    zuowang_triggered=zw_res.is_zuowang,
                    zuowang_ratio=float(zw_res.is_zuowang),
                    max_relevance=zw_res.max_relevance,
                    oblivion_threshold=zw_res.oblivion_threshold,
                    available=True,
                )
            except Exception as e:
                logger.warning(f"L5 坐忘注意力计算失败: {e}")

            # L6: 元认知自反
            if question_embedding is not None and sentence_embeddings is not None:
                try:
                    rec = self.recursion_operator.compute(
                        text=f"{question} {answer}",
                        sentence_embeddings=sentence_embeddings,
                    )
                    recursion_total = getattr(rec, 'total_score', 0.0)
                    mp = getattr(rec, 'meta_cognitive_preference', None)
                    meta_pref = mp.tolist() if mp is not None else [0, 0, 0]
                    result.L6 = L6MetaCognition(
                        recursion_total=recursion_total,
                        marker_density=getattr(rec, 'marker_density', 0.0),
                        max_depth=getattr(rec, 'max_depth', 0.0),
                        layer_count=getattr(rec, 'layer_count', 0),
                        rqa_rr=getattr(rec, 'rqa_rr', 0.0),
                        rqa_det=getattr(rec, 'rqa_det', 0.0),
                        rqa_lam=getattr(rec, 'rqa_lam', 0.0),
                        hierarchical_meta_score=getattr(rec, 'hierarchical_meta_score', 0.0),
                        meta_cognitive_preference=meta_pref,
                        available=True,
                    )
                except Exception as e:
                    logger.warning(f"L6 元认知自反计算失败: {e}")

            # L7: 认知固化
            if question_embedding is not None and sentence_embeddings is not None:
                try:
                    stab = self.stability_operator.compute(
                        question_embedding, sentence_embeddings,
                        text=f"{question} {answer}",
                    )
                    cd = getattr(stab, 'compensation_deficit', None)
                    cd_list = [0.0, 0.0, 0.0]
                    if cd is not None and hasattr(cd, '__iter__'):
                        cd_list = list(cd)[:3]
                    result.L7 = L7Stability(
                        conditional_stability=getattr(stab, 'conditional_stability', 0.0),
                        compactness=getattr(stab, 'compactness', 0.0),
                        question_alignment=getattr(stab, 'question_alignment', 0.0),
                        information_content=getattr(stab, 'information_content', 0.0),
                        compensation_deficit=cd_list,
                        available=True,
                    )
                except Exception as e:
                    logger.warning(f"L7 认知固化计算失败: {e}")

            # L8: 境界跃迁
            cs = result.L4.consciousness_score
            result.L8 = self._compute_spirit_realm(cs, 0.5, 0.5, 0.5)

        except Exception as e:
            logger.warning(f"独立模式评估异常: {e}", exc_info=True)

        result.eval_time_ms = (time.time() - t0) * 1000
        return self._finalize(result)

    def _compute_spirit_realm(
        self,
        consciousness_score: float,
        intent_score: float = 0.5,
        insight_score: float = 0.5,
        coherence_score: float = 0.5,
    ) -> L8SpiritRealm:
        """
        计算境界跃迁等级（L8）

        基于Ψ意识得分 + 增强指标的综合境界评估。
        """
        # 六论评分（从意识得分和增强指标映射）
        six_theory = {
            "本体论": consciousness_score * 0.6 + intent_score * 0.4,
            "认识论": consciousness_score * 0.5 + coherence_score * 0.5,
            "实践论": insight_score * 0.5 + intent_score * 0.5,
            "境界论": consciousness_score * 0.7 + insight_score * 0.3,
            "未来观论": consciousness_score * 0.4 + insight_score * 0.3 + coherence_score * 0.3,
            "元认知论": consciousness_score * 0.6 + insight_score * 0.4,
        }

        # 综合灵性得分
        combined = (consciousness_score * 0.4 + intent_score * 0.2 +
                    insight_score * 0.2 + coherence_score * 0.2)

        # 境界等级判定
        if consciousness_score >= 0.6 or combined >= 0.6:
            level = SpiritGrade.L4_EMERGENT.value
            grade = "L4"
        elif consciousness_score >= 0.4 or combined >= 0.4:
            level = SpiritGrade.L3_DEEP_REFLEXIVE.value
            grade = "L3"
        elif consciousness_score >= 0.25 or combined >= 0.25:
            level = SpiritGrade.L2_AWARE.value
            grade = "L2"
        elif combined >= 0.1:
            level = SpiritGrade.L1_NARRATIVE.value
            grade = "L1"
        else:
            level = SpiritGrade.L0_RANDOM.value
            grade = "L0"

        # 六阶境界（善→信→美→大→圣→神）
        six_realm_score = combined
        if six_realm_score >= 0.9:
            six_realm = "神"
        elif six_realm_score >= 0.8:
            six_realm = "圣"
        elif six_realm_score >= 0.7:
            six_realm = "大"
        elif six_realm_score >= 0.6:
            six_realm = "美"
        elif six_realm_score >= 0.4:
            six_realm = "信"
        elif six_realm_score >= 0.2:
            six_realm = "善"
        else:
            six_realm = "未入阶"

        return L8SpiritRealm(
            spirit_level=level,
            spirit_score=combined,
            six_realm=six_realm,
            six_theory_scores=six_theory,
            meta_time={
                "chronos": consciousness_score,
                "kairos": insight_score * 0.7 + coherence_score * 0.3,
                "aeon": combined,
            },
            available=True,
        )

    def _finalize(self, result: EightLayerConsciousnessResult) -> EightLayerConsciousnessResult:
        """最终调整：确保各层一致性"""
        # 如果L4不可用但L2可用，回退到L2作为意识基准
        if not result.L4.available and result.L2.available:
            result.L4.consciousness_score = result.L2.tort_score * 0.5
            result.L4.available = True
        return result

    def evaluate_batch(self,
                       pairs: List[Dict[str, str]],
                       ) -> List[EightLayerConsciousnessResult]:
        """
        批量评估多组对话

        参数:
            pairs: [{"question": "...", "answer": "...", "context": "..."}, ...]

        返回:
            List[EightLayerConsciousnessResult]
        """
        results = []
        for pair in pairs:
            result = self.evaluate(
                question=pair.get("question", ""),
                answer=pair.get("answer", ""),
                context=pair.get("context", ""),
            )
            results.append(result)
        return results

    @property
    def available_layers(self) -> Dict[str, bool]:
        """返回各层是否可用的快捷属性"""
        return {
            "L1": True,  # 编码层总是可用
            "L2": self._tortuosity_op is not None,
            "L3": True,  # 持久同调总是可用
            "L4": self._psi_operator is not None,
            "L5": self._zuowang_operator is not None or self._integrator is not None,
            "L6": self._recursion_op is not None,
            "L7": self._stability_op is not None,
            "L8": True,  # 境界跃迁总是可用（基于已有数据）
        }

    # ============================================================================
    # M3-B1: CognitionPsiBridge ↔ MoE 全链路对接
    # ============================================================================

    def to_consciousness_state(self, result: EightLayerConsciousnessResult) -> Dict[str, Any]:
        """
        将 EightLayerResult 转换为 ConsciousnessMoEAdapter 兼容的意识状态字典。

        映射关系：
            EightLayerResult          →  ConsciousnessMoEAdapter.ConsciousnessState
            ─────────────────────────────────────────────────────────────────
            L4.consciousness_score    →  consciousness_score
            L4.self_loop_detected     →  self_loop_detected
            L2.tortuosity             →  tortuosity
            L6.recursion_total        →  recursion_total
            L6.rqa_det                →  recursion_rqa_score
            L6.hierarchical_meta_score → recursion_hierarchical_score
            L7.conditional_stability  →  conditional_stability
            L5.zuowang_triggered      →  zuowang_triggered
        """
        return {
            "consciousness_score": result.L4.consciousness_score,
            "self_loop_detected": result.L4.self_loop_detected,
            "tortuosity": result.L2.tortuosity if result.L2.available else 0.0,
            "recursion_total": result.L6.recursion_total,
            "recursion_rqa_score": result.L6.rqa_det,
            "recursion_hierarchical_score": result.L6.hierarchical_meta_score,
            "conditional_stability": result.L7.conditional_stability,
            "zuowang_triggered": result.L5.zuowang_triggered,
        }

    def connect_moe(
        self,
        result: EightLayerConsciousnessResult,
        original_weights: Optional[Dict[str, float]] = None,
        meta_cognition_threshold: float = 0.25,
    ) -> Dict[str, Any]:
        """
        将 EightLayerResult 连接到 ConsciousnessMoEAdapter，
        返回调制后的专家路由策略。

        参数:
            result: 八层评估结果
            original_weights: 原始MoE专家权重 {expert_id: weight}，若不提供则只返回调制计划
            meta_cognition_threshold: 激活元认知的意识阈值

        返回:
            {
                "connected": bool,          # 是否成功连接
                "modulation_plan": dict,    # 调制计划（含决策日志）
                "adjusted_weights": dict,   # 调制后的专家权重（若提供了original_weights）
                "consciousness_level": str, # 意识水平分类
            }
        """
        try:
            from 记忆宇宙.memory_cosmos.backend.consciousness_moe_bridge import (
                ConsciousnessMoEAdapter,
            )
        except ImportError:
            logger.warning("无法导入 ConsciousnessMoEAdapter，MoE连接降级")
            return {
                "connected": False,
                "modulation_plan": {},
                "adjusted_weights": original_weights or {},
                "consciousness_level": "unknown",
                "error": "ConsciousnessMoEAdapter import failed",
            }

        adapter = ConsciousnessMoEAdapter(
            meta_cognition_threshold=meta_cognition_threshold,
        )

        # 构造意识状态字典
        state_dict = self.to_consciousness_state(result)

        # 创建 ConsciousnessState 实例
        cs = type('ConsciousnessState', (), {})()
        for k, v in state_dict.items():
            setattr(cs, k, v)
        # 补充from_operator_result缺失时使用的一对一字段
        cs.consciousness_score = state_dict["consciousness_score"]
        cs.self_loop_detected = state_dict["self_loop_detected"]
        cs.tortuosity = state_dict["tortuosity"]
        cs.recursion_total = state_dict["recursion_total"]
        cs.recursion_rqa_score = state_dict["recursion_rqa_score"]
        cs.recursion_hierarchical_score = state_dict["recursion_hierarchical_score"]
        cs.conditional_stability = state_dict["conditional_stability"]
        cs.zuowang_triggered = state_dict["zuowang_triggered"]

        # 计算调制计划
        plan = adapter.compute_modulation(cs)

        result_dict: Dict[str, Any] = {
            "connected": True,
            "modulation_plan": plan.to_dict(),
            "consciousness_level": plan.consciousness_level,
            "summary": adapter.get_modulation_summary(plan),
        }

        # 可选：应用权重调制
        if original_weights is not None:
            adjusted = adapter.apply_to_weights(original_weights, plan)
            result_dict["adjusted_weights"] = adjusted

        logger.info(
            f"[M3-B1] MoE连接完成: 意识水平={plan.consciousness_level}, "
            f"元认知激活={plan.activate_meta_cognition}"
        )
        return result_dict

    # ============================================================================
    # M3-B2: CognitionPsiBridge ↔ CDE 全链路对接
    # ============================================================================

    def to_calibration_scores(
        self, result: EightLayerConsciousnessResult
    ) -> Dict[str, float]:
        """
        从 EightLayerResult 提取 CDE 校准引擎所需的五维得分。

        映射策略：
            CDE维度              源数据                         映射公式
            ───────────────────────────────────────────────────────────────────
            intent_score         L8.spirit_score + 偏移          spirit_score * 0.5 + 0.3
            priority_score       L7.conditional_stability + 偏移 stability * 0.6 + 0.2
            insight_score        L6.recursion_total / (1+total) 归一化 * 0.4 + 0.3
            coherence_score      L4.consciousness + L7.stability 混合映射
            consciousness_score  L4.consciousness_score         直接传递
        """
        recursion_norm = result.L6.recursion_total / max(
            1.0, result.L6.recursion_total + 1
        )
        return {
            "intent_score": round(result.L8.spirit_score * 0.5 + 0.3, 4),
            "priority_score": round(
                result.L7.conditional_stability * 0.6 + 0.2, 4
            ),
            "insight_score": round(recursion_norm * 0.4 + 0.3, 4),
            "coherence_score": round(
                result.L4.consciousness_score * 0.5
                + result.L7.conditional_stability * 0.3,
                4,
            ),
            "consciousness_score": round(result.L4.consciousness_score, 4),
        }

    def connect_cde(
        self,
        result: EightLayerConsciousnessResult,
        epsilon: float = 0.05,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        将 EightLayerResult 连接到 CDE 校准引擎，
        对意识评估结果执行递归校准协议。

        参数:
            result: 八层评估结果
            epsilon: 收敛阈值
            max_iterations: 最大迭代次数

        返回:
            {
                "connected": bool,
                "initial_scores": dict,
                "final_scores": dict,
                "converged": bool,
                "total_iterations": int,
                "convergence_path": list,
                "summary": str,
            }
        """
        scores = self.to_calibration_scores(result)

        # 尝试动态导入 calibration_engine.py
        # 由于目录名含连字符(spirit-form-api)，使用importlib
        try:
            import importlib.util
            import sys

            # 尝试多种导入路径
            calib_module = None

            # 路径1: 直接import (如果已在sys.path中)
            try:
                import importlib

                calib_module = importlib.import_module(
                    "calibration_engine"
                )
            except ImportError:
                pass

            # 路径2: 从项目根目录加载
            if calib_module is None:
                import os

                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                calib_path = os.path.join(
                    project_root,
                    "spirit-form-api",
                    "evaluation-service",
                    "calibration_engine.py",
                )
                if os.path.exists(calib_path):
                    spec = importlib.util.spec_from_file_location(
                        "calibration_engine", calib_path
                    )
                    if spec and spec.loader:
                        calib_module = importlib.util.module_from_spec(spec)
                        sys.modules["calibration_engine"] = calib_module
                        spec.loader.exec_module(calib_module)

            if calib_module is None:
                raise ImportError("calibration_engine.py not found")

            calibration_from_scores = getattr(
                calib_module, "calibration_from_scores", None
            )
            if calibration_from_scores is None:
                raise ImportError("calibration_from_scores function not found")

            cde_result = calibration_from_scores(
                initial_scores=scores,
                epsilon=epsilon,
                max_iterations=max_iterations,
            )

            logger.info(
                f"[M3-B2] CDE连接完成: 收敛={cde_result.converged}, "
                f"迭代={cde_result.total_iterations}, "
                f"CD={cde_result.convergence_path[-1].compensation_diff.magnitude if cde_result.convergence_path else 0:.4f}"
            )

            return {
                "connected": True,
                "initial_scores": scores,
                "final_scores": cde_result.final_scores,
                "converged": cde_result.converged,
                "total_iterations": cde_result.total_iterations,
                "convergence_path": [
                    s.to_dict() for s in cde_result.convergence_path
                ],
                "summary": cde_result.summary,
            }

        except Exception as e:
            logger.warning(f"CDE连接失败: {e}")
            return {
                "connected": False,
                "initial_scores": scores,
                "final_scores": scores,
                "converged": False,
                "total_iterations": 0,
                "convergence_path": [],
                "summary": f"CDE连接失败: {e}",
                "error": str(e),
            }

    # ============================================================================
    # M3 全链路集成：MoE + CDE 同时对接
    # ============================================================================

    def connect_full_chain(
        self,
        result: EightLayerConsciousnessResult,
        original_weights: Optional[Dict[str, float]] = None,
        epsilon: float = 0.05,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        同时连接到 MoE 和 CDE，输出完整的三维度闭合结果。

        返回:
            {
                "eight_layer": result.to_dict(),     # 八层评估结果
                "moe": {...},                        # MoE连接结果
                "cde": {...},                        # CDE连接结果
                "summary": {...},                    # 综合摘要
            }
        """
        moe_result = self.connect_moe(result, original_weights)
        cde_result = self.connect_cde(result, epsilon, max_iterations)

        summary = {
            "consciousness_level": moe_result.get("consciousness_level", "unknown"),
            "cde_converged": cde_result.get("converged", False),
            "cde_iterations": cde_result.get("total_iterations", 0),
            "moe_connected": moe_result.get("connected", False),
            "cde_connected": cde_result.get("connected", False),
            "zuowang_state": result.L5.zuowang_triggered,
            "spirit_grade": result.L8.spirit_level,
        }

        return {
            "eight_layer": result.to_dict(),
            "moe": moe_result,
            "cde": cde_result,
            "summary": summary,
        }
