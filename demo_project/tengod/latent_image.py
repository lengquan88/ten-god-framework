"""
latent_image.py — 潜影门禁与记忆固化 v4.6.0
=================================================
道曰："知不知，上；不知知，病。"

潜影（Latent Image）：
- HDR多帧合成 → 门禁检测
- 记忆固化（Engram）
- 推理回头看（Retrospection）
- 验证门禁裁决

映射仓库：
  - Engram：记忆固化框架
  - profile-data：推理性能画像
  - Math/Math-V2：数学验证
  - Prover-V1.5/V2：证明验证

核心模块：
  1. MemoryTrace      — 记忆痕迹
  2. VerificationGate — 验证门禁
  3. Retrospection    — 推理回头看
  4. LatentImageEngine — 潜影引擎
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import time
import hashlib

from .tbce_unit import TBCECoordinates, CognitiveUnit, GateState


# ============================================================================
# 记忆痕迹
# ============================================================================

@dataclass
class MemoryTrace:
    """记忆痕迹 —— Engram 映射

    记忆固化的三个层次：
    1. 短时记忆：当前推理上下文
    2. 工作记忆：会话内活跃知识
    3. 长期记忆：固化到知识库
    """
    trace_id: str
    content: Dict[str, Any]
    confidence: float
    source: str          # 来源推理步骤
    trace_level: int     # 1=短时, 2=工作, 3=长期
    verification_count: int = 0
    verified: bool = False
    consolidated: bool = False
    timestamp: float = field(default_factory=time.time)

    def compute_hash(self) -> str:
        """计算内容哈希"""
        content_str = str(sorted(self.content.items()))
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]


@dataclass
class VerificationResult:
    """验证结果"""
    verified: bool
    confidence: float
    method: str          # 验证方法
    evidence: List[str]  # 验证证据
    contradictions: List[str]  # 矛盾点
    retrospection_score: float  # 回头看评分
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 验证门禁
# ============================================================================

class VerificationGate:
    """验证门禁 —— 潜影阶段裁决

    裁决逻辑：
    - 推理/数学/证明结果可复现 → 开
    - 需要多实例验证 → 徘徊
    - 不可复现/矛盾 → 关

    验证方法：
    1. 自洽性验证：推理过程无矛盾
    2. 多实例验证：多个独立实例得到相同结果
    3. 形式化验证：数学证明的形式化检查
    4. 回溯验证：从结论反推前提
    """

    VERIFICATION_METHODS = [
        "self_consistency",    # 自洽性
        "multi_instance",      # 多实例
        "formal_proof",        # 形式化证明
        "backward_reasoning",  # 回溯推理
        "cross_validation",    # 交叉验证
    ]

    def __init__(self, required_methods: int = 2):
        self.required_methods = required_methods

    def verify(
        self,
        trace: MemoryTrace,
        verification_results: List[VerificationResult],
        retrospection: Optional["RetrospectionResult"] = None,
    ) -> VerificationResult:
        """综合验证

        Args:
            trace: 记忆痕迹
            verification_results: 各验证方法的结果
            retrospection: 回头看结果

        Returns:
            综合验证结果
        """
        if not verification_results:
            return VerificationResult(
                verified=False,
                confidence=0.0,
                method="none",
                evidence=[],
                contradictions=["未执行任何验证"],
                retrospection_score=0.0,
            )

        # 统计通过的方法
        passed = [r for r in verification_results if r.verified]
        failed = [r for r in verification_results if not r.verified]

        all_evidence = []
        all_contradictions = []

        for r in verification_results:
            all_evidence.extend(r.evidence)
            all_contradictions.extend(r.contradictions)

        # 综合置信度
        if verification_results:
            avg_confidence = sum(r.confidence for r in verification_results) / len(verification_results)
        else:
            avg_confidence = 0.0

        # 回头看评分
        retro_score = retrospection.score if retrospection else 0.5

        # 至少需要 required_methods 种方法通过
        verified = len(passed) >= self.required_methods

        # 综合置信度 = 验证通过率 * 平均置信度 * 回头看评分
        pass_rate = len(passed) / max(1, len(verification_results))
        final_confidence = pass_rate * avg_confidence * retro_score

        return VerificationResult(
            verified=verified,
            confidence=final_confidence,
            method="+".join(r.method for r in verification_results),
            evidence=all_evidence,
            contradictions=all_contradictions,
            retrospection_score=retro_score,
        )

    def judge(
        self,
        trace: MemoryTrace,
        final_verification: VerificationResult,
    ) -> Tuple[str, str]:
        """验证门禁裁决

        Returns:
            (门禁状态, 理由)
        """
        if not final_verification.verified:
            return GateState.CLOSED, f"验证未通过({len(final_verification.contradictions)}个矛盾)"

        if final_verification.confidence >= 0.9:
            return GateState.OPEN, "高置信度验证通过"

        if final_verification.confidence >= 0.6:
            return GateState.PENDING, "验证通过但置信度中等，建议多实例复核"

        return GateState.CLOSED, f"验证置信度过低({final_verification.confidence:.2f})"


# ============================================================================
# 推理回头看
# ============================================================================

@dataclass
class RetrospectionResult:
    """推理回头看结果"""
    original_chain: List[str]     # 原始推理链
    retrospected_chain: List[str]  # 回头看后的推理链
    consistency_score: float       # 一致性评分
    gaps_found: List[str]          # 发现的推理断层
    corrections: List[str]         # 修正建议
    score: float = 0.5             # 综合回头看评分


class Retrospection:
    """推理回头看 —— 从结论反推前提

    HDR多帧合成：多次推理结果的叠加验证
    通过回溯推理链，发现潜在的逻辑断层和跳跃。
    """

    def retrospect(
        self,
        reasoning_chain: List[str],
        conclusion: str,
        premises: List[str],
    ) -> RetrospectionResult:
        """推理回头看

        Args:
            reasoning_chain: 推理链步骤
            conclusion: 结论
            premises: 前提

        Returns:
            回头看结果
        """
        gaps = []
        corrections = []
        retrospected = list(reasoning_chain)

        # 检查1：推理链是否完整（无断层）
        for i in range(len(reasoning_chain) - 1):
            step = reasoning_chain[i]
            next_step = reasoning_chain[i + 1]
            if not self._is_connected(step, next_step):
                gaps.append(f"步骤{i}→步骤{i+1}存在逻辑断层: {step[:30]}... → {next_step[:30]}...")

        # 检查2：结论是否可以从推理链推导
        if reasoning_chain and not self._leads_to(reasoning_chain[-1], conclusion):
            gaps.append(f"推理链最后一步与结论不符")
            corrections.append("建议增加结论推导步骤")

        # 检查3：前提是否在推理链中被使用
        used_premises = []
        for premise in premises:
            for step in reasoning_chain:
                if self._contains_keyword(step, premise):
                    used_premises.append(premise)
                    break

        unused = [p for p in premises if p not in used_premises]
        if unused:
            gaps.append(f"未使用的前提: {', '.join(unused)}")
            corrections.append("检查是否遗漏了关键前提")

        # 一致性评分
        consistency = 1.0
        if gaps:
            consistency -= len(gaps) * 0.15
        if corrections:
            consistency -= len(corrections) * 0.05
        consistency = max(0.0, min(1.0, consistency))

        # 综合评分 = 一致性 * 前置条件使用率
        premise_usage = len(used_premises) / max(1, len(premises))
        score = consistency * 0.6 + premise_usage * 0.4

        return RetrospectionResult(
            original_chain=reasoning_chain,
            retrospected_chain=retrospected,
            consistency_score=consistency,
            gaps_found=gaps,
            corrections=corrections,
            score=score,
        )

    def _is_connected(self, step_a: str, step_b: str) -> bool:
        """判断两个推理步骤是否关联"""
        # 简化的相关性检查：共享关键词
        words_a = set(step_a.lower().split())
        words_b = set(step_b.lower().split())
        common = words_a & words_b
        # 排除停用词
        stopwords = {'的', '了', '是', '在', '和', 'a', 'the', 'is', 'of', 'to', 'in', 'and'}
        meaningful = common - stopwords
        return len(meaningful) >= 1

    def _leads_to(self, last_step: str, conclusion: str) -> bool:
        """判断推理步骤是否导向结论"""
        return self._contains_keyword(last_step, conclusion)

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """检查文本是否包含关键词"""
        if not keyword:
            return False
        kw_words = set(keyword.lower().split())
        text_words = set(text.lower().split())
        return len(kw_words & text_words) >= max(1, len(kw_words) * 0.3)


# ============================================================================
# 潜影引擎
# ============================================================================

class LatentImageEngine:
    """潜影引擎 —— 记忆固化 + 验证 + 回头看

    流程：
    1. 接收推理结果 → 创建记忆痕迹
    2. 多方法验证 → 自洽性/多实例/形式化
    3. 推理回头看 → 发现逻辑断层
    4. 验证门禁裁决 → 开/徘徊/关
    5. 记忆固化 → 写入长期记忆
    """

    def __init__(self, required_verification_methods: int = 2):
        self.verification_gate = VerificationGate(required_methods=required_verification_methods)
        self.retrospection = Retrospection()
        self._memory_store: Dict[str, MemoryTrace] = {}
        self._verification_log: List[VerificationResult] = []

    def process(
        self,
        content: Dict[str, Any],
        reasoning_chain: List[str],
        conclusion: str,
        premises: List[str],
        confidence: float = 0.5,
        source: str = "inference",
        trace_level: int = 1,
        verification_results: Optional[List[VerificationResult]] = None,
    ) -> Tuple[MemoryTrace, VerificationResult, str]:
        """潜影处理

        Returns:
            (记忆痕迹, 验证结果, 门禁状态)
        """
        # 1. 创建记忆痕迹
        trace = MemoryTrace(
            trace_id=f"trace_{int(time.time()*1000)}",
            content=content,
            confidence=confidence,
            source=source,
            trace_level=trace_level,
        )
        trace.compute_hash()

        # 2. 推理回头看
        retro = self.retrospection.retrospect(
            reasoning_chain, conclusion, premises
        )

        # 3. 综合验证
        if verification_results is None:
            verification_results = self._default_verification(trace, retro)

        final_verification = self.verification_gate.verify(
            trace, verification_results, retro
        )
        trace.verified = final_verification.verified
        trace.verification_count = len(verification_results)

        # 4. 门禁裁决
        gate_state, reason = self.verification_gate.judge(trace, final_verification)

        # 5. 记忆固化（仅门禁通过时）
        if gate_state == GateState.OPEN:
            trace.consolidated = True
            trace.trace_level = max(trace.trace_level, 3)  # 长期记忆
        elif gate_state == GateState.PENDING:
            trace.trace_level = max(trace.trace_level, 2)  # 工作记忆

        self._memory_store[trace.trace_id] = trace
        self._verification_log.append(final_verification)

        return trace, final_verification, gate_state

    def _default_verification(
        self, trace: MemoryTrace, retro: RetrospectionResult
    ) -> List[VerificationResult]:
        """默认验证方法"""
        results = []

        # 自洽性验证
        sc_verified = retro.consistency_score >= 0.7
        results.append(VerificationResult(
            verified=sc_verified,
            confidence=retro.consistency_score,
            method="self_consistency",
            evidence=["推理链一致性检查通过"] if sc_verified else [],
            contradictions=retro.gaps_found if not sc_verified else [],
            retrospection_score=retro.score,
        ))

        # 回溯推理验证
        bw_verified = retro.score >= 0.6
        results.append(VerificationResult(
            verified=bw_verified,
            confidence=retro.score,
            method="backward_reasoning",
            evidence=["回溯推理通过"] if bw_verified else [],
            contradictions=retro.corrections if not bw_verified else [],
            retrospection_score=retro.score,
        ))

        return results

    def consolidate(
        self, trace_id: str, force: bool = False
    ) -> Tuple[bool, str]:
        """记忆固化到长期记忆

        Returns:
            (是否成功, 理由)
        """
        if trace_id not in self._memory_store:
            return False, "记忆痕迹不存在"

        trace = self._memory_store[trace_id]

        if not trace.verified and not force:
            return False, "未通过验证，需要 force=True"

        trace.consolidated = True
        trace.trace_level = 3
        return True, "已固化到长期记忆"

    def get_consolidated_memories(self) -> List[MemoryTrace]:
        """获取已固化的长期记忆"""
        return [
            t for t in self._memory_store.values()
            if t.consolidated and t.trace_level >= 3
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """获取潜影统计"""
        total = len(self._memory_store)
        verified = sum(1 for t in self._memory_store.values() if t.verified)
        consolidated = sum(1 for t in self._memory_store.values() if t.consolidated)
        return {
            "total_traces": total,
            "verified": verified,
            "consolidated": consolidated,
            "verification_rate": verified / max(1, total),
            "consolidation_rate": consolidated / max(1, total),
        }

    def get_memory(self, trace_id: str) -> Optional[MemoryTrace]:
        """获取指定记忆痕迹"""
        return self._memory_store.get(trace_id)


__all__ = [
    "MemoryTrace", "VerificationResult", "VerificationGate",
    "Retrospection", "RetrospectionResult", "LatentImageEngine",
]