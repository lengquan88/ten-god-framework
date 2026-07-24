"""
imaging.py — 认知成像融合引擎 v4.6.0
===========================================
道曰："大象无形，道隐无名。"

成像（Imaging）：
- 传感器曝光 → 多模态认知融合
- 文本/视觉/代码/3D 多模态输出
- 输出门禁裁决（徘徊：需要人工判断）

映射仓库：
  - VL/VL2：视觉语言模型
  - Janus：统一多模态架构
  - OCR/OCR-2：文档理解
  - Coder/Coder-V2：代码生成
  - DreamCraft3D：3D 生成

核心模块：
  1. CognitiveImage   — 认知成像结果
  2. ModalityFuser    — 多模态融合器
  3. ImageQualityGate — 成像质量门禁
  4. ImagingEngine    — 成像引擎
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import time

from .tbce_unit import TBCECoordinates, CognitiveUnit, GateState


# ============================================================================
# 模态类型
# ============================================================================

class Modality(Enum):
    """认知模态"""
    TEXT = "text"          # 文本
    VISION = "vision"      # 视觉
    CODE = "code"          # 代码
    MATH = "math"          # 数学
    REASONING = "reasoning"  # 推理
    THREED = "3d"          # 3D生成
    DOCUMENT = "document"  # 文档理解
    MULTIMODAL = "multimodal"  # 多模态融合


# ============================================================================
# 认知成像结果
# ============================================================================

@dataclass
class CognitiveImage:
    """认知成像结果 —— 多模态融合输出"""
    image_id: str
    modalities: List[Modality]
    content: Dict[str, Any]     # 模态 → 内容
    confidence: float           # 整体置信度
    quality_score: float        # 质量评分 [0, 1]
    coherence: float            # 模态间一致性 [0, 1]
    hallucination_risk: float   # 幻觉风险 [0, 1]
    fusion_weights: Dict[str, float]  # 融合权重
    gate_state: str = GateState.PENDING
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "modalities": [m.value for m in self.modalities],
            "confidence": round(self.confidence, 3),
            "quality_score": round(self.quality_score, 3),
            "coherence": round(self.coherence, 3),
            "hallucination_risk": round(self.hallucination_risk, 3),
            "fusion_weights": {k: round(v, 3) for k, v in self.fusion_weights.items()},
            "gate_state": self.gate_state,
        }


# ============================================================================
# 多模态融合器
# ============================================================================

class ModalityFuser:
    """多模态融合器 —— 传感器曝光 → 认知成像

    融合策略：
    1. 加权平均融合：各模态按置信度加权
    2. 注意力融合：高相关模态互相增强
    3. 交叉验证：多模态互相验证降低幻觉
    4. 缺失补全：缺失模态从相关模态推断
    """

    # 模态间相关性矩阵
    MODALITY_CORRELATION = {
        (Modality.TEXT, Modality.VISION): 0.7,
        (Modality.TEXT, Modality.CODE): 0.8,
        (Modality.TEXT, Modality.MATH): 0.6,
        (Modality.TEXT, Modality.REASONING): 0.9,
        (Modality.VISION, Modality.DOCUMENT): 0.8,
        (Modality.CODE, Modality.REASONING): 0.7,
        (Modality.MATH, Modality.REASONING): 0.8,
        (Modality.THREED, Modality.VISION): 0.6,
    }

    # 默认融合权重
    DEFAULT_WEIGHTS = {
        Modality.TEXT: 0.3,
        Modality.VISION: 0.2,
        Modality.CODE: 0.2,
        Modality.MATH: 0.1,
        Modality.REASONING: 0.1,
        Modality.THREED: 0.05,
        Modality.DOCUMENT: 0.05,
    }

    def fuse(
        self,
        modal_contents: Dict[Modality, Dict[str, Any]],
        base_confidence: float = 0.5,
    ) -> CognitiveImage:
        """多模态融合

        Args:
            modal_contents: 模态 → 内容映射
            base_confidence: 基础置信度

        Returns:
            认知成像结果
        """
        modalities = list(modal_contents.keys())

        if not modalities:
            return CognitiveImage(
                image_id=f"img_{int(time.time()*1000)}",
                modalities=[],
                content={},
                confidence=0.0,
                quality_score=0.0,
                coherence=0.0,
                hallucination_risk=1.0,
                fusion_weights={},
            )

        # 计算融合权重
        weights = self._compute_fusion_weights(modalities)

        # 加权融合置信度
        confidence = self._fuse_confidence(modal_contents, weights, base_confidence)

        # 模态间一致性
        coherence = self._compute_coherence(modalities)

        # 幻觉风险（更多模态交叉验证 → 更低风险）
        hallucination_risk = self._compute_hallucination_risk(
            modalities, confidence, coherence
        )

        # 质量评分
        quality_score = self._compute_quality(confidence, coherence, hallucination_risk)

        return CognitiveImage(
            image_id=f"img_{int(time.time()*1000)}",
            modalities=modalities,
            content={m.value: c for m, c in modal_contents.items()},
            confidence=confidence,
            quality_score=quality_score,
            coherence=coherence,
            hallucination_risk=hallucination_risk,
            fusion_weights={m.value: w for m, w in weights.items()},
        )

    def _compute_fusion_weights(
        self, modalities: List[Modality]
    ) -> Dict[Modality, float]:
        """计算融合权重：考虑模态间相关性"""
        if not modalities:
            return {}

        # 基础权重
        weights = {
            m: self.DEFAULT_WEIGHTS.get(m, 0.1)
            for m in modalities
        }

        # 相关性增强：有相关模态的获得更高权重
        for m in modalities:
            for other in modalities:
                if m == other:
                    continue
                corr = self.MODALITY_CORRELATION.get((m, other), 0.0)
                corr = max(corr, self.MODALITY_CORRELATION.get((other, m), 0.0))
                weights[m] += corr * 0.05

        # 归一化
        total = sum(weights.values())
        if total > 0:
            for m in weights:
                weights[m] /= total

        return weights

    def _fuse_confidence(
        self,
        modal_contents: Dict[Modality, Dict],
        weights: Dict[Modality, float],
        base: float,
    ) -> float:
        """加权融合置信度"""
        total = 0.0
        total_weight = 0.0

        for m, content in modal_contents.items():
            w = weights.get(m, 0.1)
            c = content.get("confidence", base)
            total += c * w
            total_weight += w

        if total_weight > 0:
            return total / total_weight
        return base

    def _compute_coherence(self, modalities: List[Modality]) -> float:
        """计算模态间一致性"""
        if len(modalities) <= 1:
            return 1.0

        total_corr = 0.0
        count = 0
        for i, m1 in enumerate(modalities):
            for m2 in modalities[i+1:]:
                corr = self.MODALITY_CORRELATION.get((m1, m2), 0.0)
                corr = max(corr, self.MODALITY_CORRELATION.get((m2, m1), 0.0))
                total_corr += corr
                count += 1

        if count == 0:
            return 1.0
        return total_corr / count

    def _compute_hallucination_risk(
        self,
        modalities: List[Modality],
        confidence: float,
        coherence: float,
    ) -> float:
        """计算幻觉风险

        多模态交叉验证 → 降低幻觉风险
        低置信度 + 低一致性 → 高幻觉风险
        """
        n_modalities = len(modalities)
        if n_modalities <= 1:
            # 单模态：高风险
            return 1.0 - confidence * 0.5

        # 多模态交叉验证降低风险
        cross_validation = min(1.0, n_modalities / 4.0)  # 4模态以上 → 完全交叉验证
        risk = (1.0 - confidence) * 0.5 + (1.0 - coherence) * 0.3
        risk *= (1.0 - cross_validation * 0.5)
        return min(1.0, max(0.0, risk))

    def _compute_quality(
        self, confidence: float, coherence: float, hallucination_risk: float
    ) -> float:
        """计算整体质量评分"""
        quality = confidence * 0.4 + coherence * 0.3 + (1.0 - hallucination_risk) * 0.3
        return min(1.0, max(0.0, quality))


# ============================================================================
# 成像质量门禁
# ============================================================================

class ImageQualityGate:
    """成像质量门禁 —— 输出门禁裁决

    裁决逻辑（成像阶段为"徘徊"）：
    - 质量高 + 一致性高 → 开
    - 质量中 + 有交叉验证 → 徘徊（需要人工判断）
    - 质量低 + 幻觉高风险 → 关
    - 视觉/代码/3D 生成 → 倾向徘徊（需要人工判断）

    这与路线图一致：成像阶段为"徘徊"，因为视觉/代码/3D
    生成类仓库的输出质量评估需要人工判断。
    """

    QUALITY_OPEN_THRESHOLD = 0.8
    QUALITY_CLOSED_THRESHOLD = 0.4
    HALLUCINATION_CLOSED_THRESHOLD = 0.6
    COHERENCE_OPEN_THRESHOLD = 0.7

    # 需要人工判断的模态
    HUMAN_JUDGMENT_MODALITIES = {
        Modality.VISION, Modality.CODE, Modality.THREED,
    }

    def judge(self, image: CognitiveImage) -> Tuple[str, str]:
        """裁决成像质量

        Returns:
            (门禁状态, 裁决理由)
        """
        # 幻觉风险过高 → 关
        if image.hallucination_risk > self.HALLUCINATION_CLOSED_THRESHOLD:
            return GateState.CLOSED, f"幻觉风险过高({image.hallucination_risk:.2f})"

        # 质量过低 → 关
        if image.quality_score < self.QUALITY_CLOSED_THRESHOLD:
            return GateState.CLOSED, f"成像质量过低({image.quality_score:.2f})"

        # 包含需要人工判断的模态 → 徘徊
        human_modalities = [
            m for m in image.modalities
            if m in self.HUMAN_JUDGMENT_MODALITIES
        ]
        if human_modalities:
            names = ", ".join(m.value for m in human_modalities)
            return GateState.PENDING, f"需要人工判断: {names}"

        # 高质量 + 高一致性 → 开
        if (image.quality_score >= self.QUALITY_OPEN_THRESHOLD and
                image.coherence >= self.COHERENCE_OPEN_THRESHOLD):
            return GateState.OPEN, "成像质量高，一致性高"

        # 默认徘徊
        return GateState.PENDING, "成像质量中等，建议人工复核"


# ============================================================================
# 成像引擎
# ============================================================================

class ImagingEngine:
    """成像引擎 —— 认知成像主控

    流程：
    1. 接收多模态输入
    2. 融合模态 → 生成认知成像
    3. 质量门禁裁决
    4. 输出认知成像结果
    """

    def __init__(self):
        self.fuser = ModalityFuser()
        self.gate = ImageQualityGate()
        self._image_log: List[CognitiveImage] = []

    def image(
        self,
        modal_contents: Dict[Modality, Dict[str, Any]],
        base_confidence: float = 0.5,
        auto_judge: bool = True,
    ) -> Tuple[CognitiveImage, Tuple[str, str]]:
        """认知成像

        Args:
            modal_contents: 多模态内容
            base_confidence: 基础置信度
            auto_judge: 是否自动门禁裁决

        Returns:
            (认知成像结果, (门禁状态, 理由))
        """
        image = self.fuser.fuse(modal_contents, base_confidence)

        if auto_judge:
            gate_state, reason = self.gate.judge(image)
            image.gate_state = gate_state
        else:
            gate_state, reason = GateState.PENDING, "未裁决"

        self._image_log.append(image)
        return image, (gate_state, reason)

    def get_statistics(self) -> Dict[str, Any]:
        """获取成像统计"""
        if not self._image_log:
            return {}
        total = len(self._image_log)
        avg_quality = sum(i.quality_score for i in self._image_log) / total
        avg_confidence = sum(i.confidence for i in self._image_log) / total
        avg_hallucination = sum(i.hallucination_risk for i in self._image_log) / total
        gate_stats = {'open': 0, 'pending': 0, 'closed': 0}
        for i in self._image_log:
            gate_stats[i.gate_state] += 1
        return {
            'total_images': total,
            'avg_quality': round(avg_quality, 3),
            'avg_confidence': round(avg_confidence, 3),
            'avg_hallucination_risk': round(avg_hallucination, 3),
            'gate_stats': gate_stats,
        }


__all__ = [
    "Modality", "CognitiveImage", "ModalityFuser",
    "ImageQualityGate", "ImagingEngine",
]