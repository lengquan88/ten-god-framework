"""
test_imaging.py — 认知成像融合引擎测试 v2.25.0
"""
import pytest
import math

from tengod.tbce_unit import GateState
from tengod.imaging import (
    Modality, CognitiveImage, ModalityFuser, ImageQualityGate, ImagingEngine,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def fuser():
    return ModalityFuser()


@pytest.fixture
def engine():
    return ImagingEngine()


# ── 1. Modality ────────────────────────────────────────────

class TestModality:
    def test_modality_values(self):
        assert Modality.TEXT.value == "text"
        assert Modality.VISION.value == "vision"
        assert Modality.CODE.value == "code"
        assert Modality.MULTIMODAL.value == "multimodal"


# ── 2. CognitiveImage ──────────────────────────────────────

class TestCognitiveImage:
    def test_create(self):
        image = CognitiveImage(
            image_id="test",
            modalities=[Modality.TEXT, Modality.CODE],
            content={"text": "hello"},
            confidence=0.8,
            quality_score=0.7,
            coherence=0.8,
            hallucination_risk=0.2,
            fusion_weights={"text": 0.6},
        )
        assert image.image_id == "test"
        assert len(image.modalities) == 2
        assert isinstance(image.fusion_weights, dict)

    def test_to_dict(self):
        image = CognitiveImage(
            image_id="test",
            modalities=[Modality.TEXT],
            content={},
            confidence=0.5,
            quality_score=0.5,
            coherence=0.5,
            hallucination_risk=0.5,
            fusion_weights={},
        )
        d = image.to_dict()
        assert d["image_id"] == "test"
        assert "confidence" in d


# ── 3. ModalityFuser ───────────────────────────────────────

class TestModalityFuser:
    def test_fuse_single_modality(self, fuser):
        content = {Modality.TEXT: {"confidence": 0.8}}
        image = fuser.fuse(content)
        assert len(image.modalities) == 1
        assert image.confidence == 0.8

    def test_fuse_multimodal(self, fuser):
        content = {
            Modality.TEXT: {"confidence": 0.9},
            Modality.CODE: {"confidence": 0.85},
        }
        image = fuser.fuse(content)
        assert len(image.modalities) == 2
        assert 0.8 < image.confidence < 0.9
        assert image.coherence > 0.7  # text+code 高相关性

    def test_fuse_empty(self, fuser):
        image = fuser.fuse({})
        assert len(image.modalities) == 0
        assert image.confidence == 0.0
        assert image.hallucination_risk == 1.0

    def test_coherence_calculation(self, fuser):
        # text+vision → 0.7 相关性
        modalities = [Modality.TEXT, Modality.VISION]
        coherence = fuser._compute_coherence(modalities)
        assert math.isclose(coherence, 0.7, rel_tol=1e-9)

    def test_hallucination_risk_multimodal(self, fuser):
        modalities = [Modality.TEXT, Modality.VISION, Modality.CODE]
        risk = fuser._compute_hallucination_risk(modalities, 0.8, 0.7)
        # 多模态交叉验证 → 降低风险
        assert risk < 0.5

    def test_hallucination_risk_single_modal(self, fuser):
        modalities = [Modality.TEXT]
        risk = fuser._compute_hallucination_risk(modalities, 0.8, 1.0)
        # 单模态 → 高风险
        assert risk > 0.5

    def test_quality_calculation(self, fuser):
        quality = fuser._compute_quality(0.8, 0.8, 0.2)
        # 0.8*0.4 + 0.8*0.3 + (1-0.2)*0.3 = 0.32+0.24+0.24=0.8
        assert math.isclose(quality, 0.8, rel_tol=1e-9)


# ── 4. ImageQualityGate ───────────────────────────────────

class TestImageQualityGate:
    def test_high_quality_open(self, fuser):
        gate = ImageQualityGate()
        image = CognitiveImage(
            image_id="test",
            modalities=[Modality.TEXT, Modality.REASONING],
            content={},
            confidence=0.9,
            quality_score=0.85,
            coherence=0.8,
            hallucination_risk=0.1,
            fusion_weights={},
        )
        state, reason = gate.judge(image)
        assert state == GateState.OPEN

    def test_need_human_judgment(self, fuser):
        gate = ImageQualityGate()
        image = CognitiveImage(
            image_id="test",
            modalities=[Modality.VISION, Modality.CODE],
            content={},
            confidence=0.7,
            quality_score=0.6,
            coherence=0.5,
            hallucination_risk=0.3,
            fusion_weights={},
        )
        state, reason = gate.judge(image)
        assert state == GateState.PENDING
        assert "需要人工判断" in reason

    def test_low_quality_closed(self, fuser):
        gate = ImageQualityGate()
        image = CognitiveImage(
            image_id="test",
            modalities=[Modality.TEXT],
            content={},
            confidence=0.2,
            quality_score=0.3,
            coherence=0.2,
            hallucination_risk=0.8,
            fusion_weights={},
        )
        state, reason = gate.judge(image)
        assert state == GateState.CLOSED


# ── 5. ImagingEngine ───────────────────────────────────────

class TestImagingEngine:
    def test_image_auto_judge(self, engine):
        content = {
            Modality.TEXT: {"confidence": 0.9},
            Modality.REASONING: {"confidence": 0.85},
        }
        image, (gate, reason) = engine.image(content)
        assert image.confidence > 0.8
        assert gate in (GateState.OPEN, GateState.PENDING, GateState.CLOSED)
        assert len(engine._image_log) == 1

    def test_image_statistics(self, engine):
        content = {Modality.TEXT: {"confidence": 0.9}}
        engine.image(content)
        engine.image(content)
        stats = engine.get_statistics()
        assert stats["total_images"] == 2


# ── 6. Integration ────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self):
        engine = ImagingEngine()
        content = {
            Modality.TEXT: {"confidence": 0.9},
            Modality.VISION: {"confidence": 0.8},
            Modality.CODE: {"confidence": 0.75},
        }
        image, (gate, reason) = engine.image(content, base_confidence=0.5)
        assert image is not None
        assert image.quality_score > 0.5
        # 包含 vision/code → 需要人工判断 → 徘徊
        assert gate == GateState.PENDING
        stats = engine.get_statistics()
        # avg_quality 是四舍五入到3位小数的
        assert abs(stats["avg_quality"] - image.quality_score) < 0.001
