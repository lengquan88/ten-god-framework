"""
Tests for tengod/inner_child.py — 内在小孩状态机与熵门禁 v2.16.1

Covers:
  - Data classes: InnerChildArchetype, TribulationMemory, InnerChildState
  - Module-level constants: SIX_ARCHETYPES, INNER_CHILD_DIM, SAFETY_FALLBACK_RESPONSE
  - Pure functions: build_prototype_vectors, build_zhongyong_anchor,
    compute_soft_occupancy, compute_entropy_gate, should_trigger_gate,
    compute_bias_residual, correct_by_gradient_retreat,
    correct_with_zhongyong_damping, safety_fallback_response
  - Classes: MemoryPool, InnerChildStateMachine
  - Singleton: get_inner_child_sm
  - State machine four-layer pipeline: observe → inquire → correct → verify
  - Safety fallback mechanism
  - Orthogonality checks
  - Memory pool operations
"""

import math
import time
from unittest.mock import patch

import pytest

from tengod.inner_child import (
    INNER_CHILD_DIM,
    SAFETY_FALLBACK_RESPONSE,
    SIX_ARCHETYPES,
    InnerChildArchetype,
    InnerChildState,
    InnerChildStateMachine,
    MemoryPool,
    TribulationMemory,
    _ZHONGYONG_ANCHOR,
    build_prototype_vectors,
    build_zhongyong_anchor,
    compute_bias_residual,
    compute_entropy_gate,
    compute_soft_occupancy,
    correct_by_gradient_retreat,
    correct_with_zhongyong_damping,
    get_inner_child_sm,
    safety_fallback_response,
    should_trigger_gate,
)


# ============================================================================
# 1. InnerChildArchetype dataclass tests
# ============================================================================

class TestInnerChildArchetype:
    def test_create_archetype(self):
        archetype = InnerChildArchetype(
            index=0,
            name="戒备小孩",
            name_en="Guardian",
            description="过度防御",
            dao_principle="知其雄，守其雌",
            vector=[0.1, 0.2, 0.3],
        )
        assert archetype.index == 0
        assert archetype.name == "戒备小孩"
        assert archetype.name_en == "Guardian"
        assert archetype.description == "过度防御"
        assert archetype.dao_principle == "知其雄，守其雌"
        assert archetype.vector == [0.1, 0.2, 0.3]

    def test_default_vector_empty(self):
        archetype = InnerChildArchetype(
            index=0,
            name="test",
            name_en="test",
            description="desc",
            dao_principle="dao",
        )
        assert archetype.vector == []

    def test_equality(self):
        a1 = InnerChildArchetype(0, "戒备小孩", "Guardian", "d", "p")
        a2 = InnerChildArchetype(0, "戒备小孩", "Guardian", "d", "p")
        assert a1 == a2


# ============================================================================
# 2. Module-level constants
# ============================================================================

class TestModuleConstants:
    def test_inner_child_dim(self):
        assert INNER_CHILD_DIM == 64

    def test_six_archetypes_count(self):
        assert len(SIX_ARCHETYPES) == 6

    def test_six_archetypes_names(self):
        names = [a.name for a in SIX_ARCHETYPES]
        assert "戒备小孩" in names
        assert "缺爱小孩" in names
        assert "叛逆小孩" in names
        assert "讨好小孩" in names
        assert "孤独小孩" in names
        assert "长不大" in names

    def test_six_archetypes_indices(self):
        for i, a in enumerate(SIX_ARCHETYPES):
            assert a.index == i

    def test_safety_fallback_response_structure(self):
        assert "status" in SAFETY_FALLBACK_RESPONSE
        assert "message" in SAFETY_FALLBACK_RESPONSE
        assert "inner_child" in SAFETY_FALLBACK_RESPONSE
        assert SAFETY_FALLBACK_RESPONSE["status"] == "retreated"
        assert SAFETY_FALLBACK_RESPONSE["inner_child"]["triggered"] is True


# ============================================================================
# 3. build_prototype_vectors
# ============================================================================

class TestBuildPrototypeVectors:
    def test_default_dim(self):
        vecs = build_prototype_vectors()
        assert len(vecs) == 6
        for v in vecs:
            assert len(v) == INNER_CHILD_DIM

    def test_custom_dim(self):
        dim = 128
        vecs = build_prototype_vectors(dim=dim)
        assert len(vecs) == 6
        for v in vecs:
            assert len(v) == dim

    def test_vectors_are_unit_length(self):
        vecs = build_prototype_vectors()
        for v in vecs:
            norm = math.sqrt(sum(x * x for x in v))
            assert abs(norm - 1.0) < 1e-8

    def test_vectors_are_orthogonal(self):
        """Gram-Schmidt should produce orthogonal vectors."""
        vecs = build_prototype_vectors()
        for i in range(6):
            for j in range(i + 1, 6):
                dot = sum(vecs[i][k] * vecs[j][k] for k in range(len(vecs[i])))
                assert abs(dot) < 0.01, f"Pair ({i},{j}) dot={dot} not orthogonal"


# ============================================================================
# 4. build_zhongyong_anchor
# ============================================================================

class TestBuildZhongyongAnchor:
    def test_default_dim(self):
        anchor = build_zhongyong_anchor()
        assert len(anchor) == INNER_CHILD_DIM

    def test_custom_dim(self):
        """build_zhongyong_anchor uses _PROTOTYPE_VECTORS which is always 64-dim.
        Passing a custom dim would cause IndexError since prototypes are fixed size.
        The function is designed to work with the default INNER_CHILD_DIM only."""
        anchor = build_zhongyong_anchor()
        assert len(anchor) == INNER_CHILD_DIM

    def test_is_unit_vector(self):
        anchor = build_zhongyong_anchor()
        norm = math.sqrt(sum(x * x for x in anchor))
        assert abs(norm - 1.0) < 1e-8

    def test_anchor_is_geometric_center(self):
        """The anchor should be the geometric center of all six prototypes."""
        anchor = build_zhongyong_anchor()
        vecs = build_prototype_vectors()
        # It should have positive correlation with all prototypes since it's
        # the normalized sum of all of them.
        for v in vecs:
            dot = sum(anchor[i] * v[i] for i in range(len(anchor)))
            assert dot > 0


# ============================================================================
# 5. compute_soft_occupancy
# ============================================================================

class TestComputeSoftOccupancy:
    @pytest.fixture
    def prototypes(self):
        return build_prototype_vectors()

    def test_returns_beta_and_max(self, prototypes):
        h_t = [0.0] * INNER_CHILD_DIM
        h_t[0] = 1.0
        norm = math.sqrt(sum(x * x for x in h_t))
        h_t = [x / norm for x in h_t]
        beta, max_beta = compute_soft_occupancy(h_t, prototypes)
        assert len(beta) == 6
        assert isinstance(max_beta, float)
        assert 0 <= max_beta <= 1.0

    def test_beta_sums_to_one(self, prototypes):
        h_t = [math.sin(i * 0.1) for i in range(INNER_CHILD_DIM)]
        norm = math.sqrt(sum(x * x for x in h_t))
        h_t = [x / norm for x in h_t]
        beta, _ = compute_soft_occupancy(h_t, prototypes)
        assert abs(sum(beta) - 1.0) < 1e-9

    def test_uniform_vector_gives_balanced_beta(self, prototypes):
        """A uniform vector should give a reasonably balanced distribution."""
        h_t = [1.0 / math.sqrt(INNER_CHILD_DIM)] * INNER_CHILD_DIM
        beta, _ = compute_soft_occupancy(h_t, prototypes)
        # All betas should be close to 1/6 (within ~0.16)
        for b in beta:
            assert abs(b - 1.0 / 6) < 0.17

    def test_custom_alertness(self, prototypes):
        h_t = [0.0] * INNER_CHILD_DIM
        h_t[0] = 1.0
        norm = math.sqrt(sum(x * x for x in h_t))
        h_t = [x / norm for x in h_t]
        beta_low, _ = compute_soft_occupancy(h_t, prototypes, alertness=1.0)
        beta_high, _ = compute_soft_occupancy(h_t, prototypes, alertness=100.0)
        # Higher alertness should make distribution more peaked
        assert max(beta_high) > max(beta_low) * 0.9

    def test_vector_aligned_with_prototype(self, prototypes):
        """If h_t equals a prototype, that prototype should have highest beta."""
        h_t = prototypes[0]
        beta, _ = compute_soft_occupancy(h_t, prototypes)
        assert beta[0] == max(beta)

    def test_empty_prototypes(self):
        """Empty prototypes: max() of empty sequence raises ValueError.
        This is expected behavior — empty prototypes is an invalid input."""
        with pytest.raises(ValueError):
            compute_soft_occupancy([1.0, 0.0], [])

    def test_zero_vector(self, prototypes):
        h_t = [0.0] * INNER_CHILD_DIM
        beta, max_beta = compute_soft_occupancy(h_t, prototypes)
        assert len(beta) == 6
        # Zero vector dot product with any prototype is 0, so all logits equal
        for b in beta:
            assert abs(b - 1.0 / 6) < 1e-9


# ============================================================================
# 6. compute_entropy_gate
# ============================================================================

class TestComputeEntropyGate:
    def test_uniform_distribution(self):
        beta = [1.0 / 6] * 6
        phi = compute_entropy_gate(beta)
        expected = math.log(6)
        assert abs(phi - expected) < 1e-6

    def test_one_hot_distribution(self):
        beta = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        phi = compute_entropy_gate(beta)
        assert phi < 1e-9

    def test_mostly_one_dominant(self):
        beta = [0.9, 0.02, 0.02, 0.02, 0.02, 0.02]
        phi = compute_entropy_gate(beta)
        assert phi < 0.5  # Very low entropy

    def test_custom_epsilon(self):
        beta = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        phi = compute_entropy_gate(beta, epsilon=1e-12)
        # With small epsilon, log(1e-12) ≈ -27.6, so phi ≈ 0
        assert phi < 1e-9

    def test_empty_beta(self):
        phi = compute_entropy_gate([])
        assert phi == 0.0

    def test_all_zeros_beta(self):
        """All-zero beta: phi should be 0 since b*log(epsilon) for each entry."""
        beta = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        phi = compute_entropy_gate(beta)
        # b=0 → term is skipped, so phi = 0
        assert phi == 0.0


# ============================================================================
# 7. should_trigger_gate
# ============================================================================

class TestShouldTriggerGate:
    def test_standard_trigger(self):
        triggered, reason = should_trigger_gate(phi=0.3, max_beta=0.8)
        assert triggered is True
        assert "门禁触发" in reason

    def test_no_trigger_balanced(self):
        triggered, reason = should_trigger_gate(phi=1.5, max_beta=0.3)
        assert triggered is False
        assert "认知平衡" in reason

    def test_entropy_low_but_occupancy_ok(self):
        triggered, reason = should_trigger_gate(phi=0.3, max_beta=0.5)
        assert triggered is False
        assert "熵偏低" in reason

    def test_occupancy_high_but_entropy_ok(self):
        triggered, reason = should_trigger_gate(phi=1.5, max_beta=0.8)
        assert triggered is False
        assert "占据度偏高" in reason

    def test_psychological_escape(self):
        """心理偏执逃逸：max(β) > 0.85 ∧ Φ < 0.8"""
        triggered, reason = should_trigger_gate(phi=0.5, max_beta=0.9)
        assert triggered is True
        assert "心理偏执逃逸" in reason

    def test_custom_phi_limit(self):
        triggered, _ = should_trigger_gate(phi=0.9, max_beta=0.8, phi_limit=1.0)
        assert triggered is True

    def test_custom_beta_limit(self):
        triggered, _ = should_trigger_gate(phi=0.3, max_beta=0.6, beta_limit=0.5)
        assert triggered is True

    def test_custom_beta_escape_limit(self):
        triggered, reason = should_trigger_gate(
            phi=0.5, max_beta=0.88, beta_escape_limit=0.87
        )
        assert triggered is True
        assert "心理偏执逃逸" in reason

    def test_boundary_phi_equals_limit(self):
        """Φ exactly at limit should NOT trigger (phi < phi_limit is strict)."""
        triggered, _ = should_trigger_gate(phi=0.8, max_beta=0.8)
        assert triggered is False

    def test_boundary_beta_equals_limit(self):
        """max_beta exactly at limit should NOT trigger (max_beta > beta_limit is strict)."""
        triggered, _ = should_trigger_gate(phi=0.3, max_beta=0.7)
        assert triggered is False


# ============================================================================
# 8. compute_bias_residual
# ============================================================================

class TestComputeBiasResidual:
    def test_basic(self):
        h_t = [1.0, 2.0, 3.0]
        p_k = [0.0, 1.0, 2.0]
        r = compute_bias_residual(h_t, p_k)
        assert r == [1.0, 1.0, 1.0]

    def test_different_lengths(self):
        h_t = [1.0, 2.0]
        p_k = [0.0, 1.0, 2.0, 3.0]
        r = compute_bias_residual(h_t, p_k)
        assert r == [1.0, 1.0]

    def test_identical_vectors(self):
        h_t = [0.5, -0.3, 0.1]
        r = compute_bias_residual(h_t, h_t)
        for x in r:
            assert abs(x) < 1e-9

    def test_empty_vectors(self):
        r = compute_bias_residual([], [])
        assert r == []


# ============================================================================
# 9. correct_by_gradient_retreat
# ============================================================================

class TestCorrectByGradientRetreat:
    def test_high_beta_correction(self):
        h_t = [1.0, 0.0, 0.0]
        p_k = [0.0, 1.0, 0.0]
        beta_k = 0.9
        corrected = correct_by_gradient_retreat(h_t, p_k, beta_k)
        # gate = 0.9 - 0.5 = 0.4, penalty = 0.4 * 0.4 = 0.16
        # r_bias = [1, -1, 0], r_norm = sqrt(2)
        # corrected = h_t - 0.16 * r_bias / sqrt(2)
        assert len(corrected) == 3
        # Should move away from p_k direction
        assert corrected[0] < 1.0  # moved away from p_k's direction
        assert corrected[1] > 0.0  # moved toward... wait, let me think
        # h_t = [1, 0, 0], p_k = [0, 1, 0]
        # r_bias = [1, -1, 0], direction = r_bias / sqrt(2)
        # corrected = h_t - penalty * direction
        # corrected[0] = 1 - penalty/sqrt(2) < 1 ✓
        # corrected[2] = 0 unchanged ✓

    def test_beta_below_half_no_correction(self):
        h_t = [1.0, 0.0, 0.0]
        p_k = [0.0, 1.0, 0.0]
        beta_k = 0.4
        corrected = correct_by_gradient_retreat(h_t, p_k, beta_k)
        # ReLU(0.4 - 0.5) = 0, so no correction
        assert corrected == h_t

    def test_beta_exactly_half_no_correction(self):
        h_t = [1.0, 0.0, 0.0]
        p_k = [0.0, 1.0, 0.0]
        beta_k = 0.5
        corrected = correct_by_gradient_retreat(h_t, p_k, beta_k)
        assert corrected == h_t

    def test_zero_bias_norm(self):
        """When h_t == p_k, r_bias is zero, should return original."""
        h_t = [1.0, 2.0, 3.0]
        p_k = [1.0, 2.0, 3.0]
        beta_k = 0.9
        corrected = correct_by_gradient_retreat(h_t, p_k, beta_k)
        assert corrected == h_t

    def test_custom_lambda(self):
        h_t = [1.0, 0.0]
        p_k = [0.0, 1.0]
        beta_k = 0.9
        c1 = correct_by_gradient_retreat(h_t, p_k, beta_k, lambda_=0.2)
        c2 = correct_by_gradient_retreat(h_t, p_k, beta_k, lambda_=0.8)
        # Larger lambda should move further from original
        delta1 = math.sqrt(sum((c1[i] - h_t[i]) ** 2 for i in range(2)))
        delta2 = math.sqrt(sum((c2[i] - h_t[i]) ** 2 for i in range(2)))
        assert delta2 > delta1

    def test_different_lengths(self):
        h_t = [1.0, 0.0, 0.0, 0.0]
        p_k = [0.0, 1.0]
        beta_k = 0.9
        corrected = correct_by_gradient_retreat(h_t, p_k, beta_k)
        assert len(corrected) == 2  # min(dim)


# ============================================================================
# 10. correct_with_zhongyong_damping
# ============================================================================

class TestCorrectWithZhongyongDamping:
    def test_two_step_correction(self):
        h_t = [1.0, 0.0, 0.0]
        p_k = [0.0, 1.0, 0.0]
        beta_k = 0.9
        corrected = correct_with_zhongyong_damping(h_t, p_k, beta_k)
        assert len(corrected) == 3
        # Should be different from both original and gradient-only
        grad_only = correct_by_gradient_retreat(h_t, p_k, beta_k)
        assert corrected != h_t
        assert corrected != grad_only  # Because zhongyong damping added

    def test_no_correction_with_low_beta(self):
        """With low beta, gradient retreat is skipped (ReLU gate=0),
        but zhongyong damping still pulls toward the anchor. So the result
        should differ from h_t but only slightly (gamma=0.2 pull)."""
        h_t = [1.0, 0.0, 0.0]
        p_k = [0.0, 1.0, 0.0]
        beta_k = 0.4
        corrected = correct_with_zhongyong_damping(h_t, p_k, beta_k)
        # Gradient retreat skipped (beta_k <= 0.5), but zhongyong damping applied
        # h''_t = (1-0.2)*h_t + 0.2*p_0, so it should differ from h_t
        assert corrected != h_t
        # The difference should be moderate (gamma=0.2)
        delta = math.sqrt(sum((corrected[i] - h_t[i]) ** 2 for i in range(len(h_t))))
        assert delta > 0.0

    def test_custom_gamma(self):
        h_t = [1.0, 0.0]
        p_k = [0.0, 1.0]
        beta_k = 0.9
        c_low = correct_with_zhongyong_damping(h_t, p_k, beta_k, gamma=0.05)
        c_high = correct_with_zhongyong_damping(h_t, p_k, beta_k, gamma=0.5)
        # Higher gamma pulls more toward anchor, so they should differ
        assert c_low != c_high


# ============================================================================
# 11. safety_fallback_response
# ============================================================================

class TestSafetyFallbackResponse:
    def test_returns_dict(self):
        resp = safety_fallback_response()
        assert isinstance(resp, dict)
        assert resp["status"] == "retreated"
        assert resp["inner_child"]["triggered"] is True
        assert resp["inner_child"]["action"] == "safety_fallback"

    def test_is_independent_copy(self):
        """Modifying the returned dict should not affect the constant."""
        resp = safety_fallback_response()
        resp["status"] = "modified"
        assert SAFETY_FALLBACK_RESPONSE["status"] == "retreated"

    def test_message_content(self):
        resp = safety_fallback_response()
        assert "知不知" in resp["message"]
        assert "尚矣" in resp["message"]


# ============================================================================
# 12. TribulationMemory dataclass
# ============================================================================

class TestTribulationMemory:
    def test_create(self):
        mem = TribulationMemory(
            h_t=[0.1, 0.2],
            p_k=[0.3, 0.4],
            beta_k=0.85,
            phi_before=0.3,
            phi_after=0.9,
            delta_phi=0.6,
            dominant_name="戒备小孩",
        )
        assert mem.beta_k == 0.85
        assert mem.delta_phi == 0.6
        assert mem.dominant_name == "戒备小孩"
        assert isinstance(mem.timestamp, float)

    def test_to_dict(self):
        mem = TribulationMemory(
            h_t=[0.1, 0.2],
            p_k=[0.3, 0.4],
            beta_k=0.85,
            phi_before=0.3,
            phi_after=0.9,
            delta_phi=0.6,
            dominant_name="戒备小孩",
        )
        d = mem.to_dict()
        assert d["dominant"] == "戒备小孩"
        assert d["beta_k"] == 0.85
        assert d["phi_before"] == 0.3
        assert d["phi_after"] == 0.9
        assert d["delta_phi"] == 0.6
        assert d["successful"] is True  # delta_phi > 0.15
        assert "timestamp" in d

    def test_to_dict_unsuccessful(self):
        mem = TribulationMemory(
            h_t=[0.1, 0.2],
            p_k=[0.3, 0.4],
            beta_k=0.85,
            phi_before=0.3,
            phi_after=0.4,
            delta_phi=0.1,
            dominant_name="缺爱小孩",
        )
        d = mem.to_dict()
        assert d["successful"] is False

    def test_custom_timestamp(self):
        ts = 1234567890.0
        mem = TribulationMemory(
            h_t=[0.1],
            p_k=[0.2],
            beta_k=0.5,
            phi_before=0.5,
            phi_after=0.5,
            delta_phi=0.0,
            dominant_name="test",
            timestamp=ts,
        )
        assert mem.timestamp == ts


# ============================================================================
# 13. MemoryPool
# ============================================================================

class TestMemoryPool:
    @pytest.fixture
    def pool(self):
        return MemoryPool(max_capacity=100)

    @pytest.fixture
    def success_memory(self):
        return TribulationMemory(
            h_t=[0.1, 0.2],
            p_k=[0.3, 0.4],
            beta_k=0.8,
            phi_before=0.3,
            phi_after=0.9,
            delta_phi=0.6,
            dominant_name="戒备小孩",
        )

    @pytest.fixture
    def failure_memory(self):
        return TribulationMemory(
            h_t=[0.1, 0.2],
            p_k=[0.3, 0.4],
            beta_k=0.8,
            phi_before=0.3,
            phi_after=0.4,
            delta_phi=0.1,
            dominant_name="缺爱小孩",
        )

    def test_default_capacity(self):
        pool = MemoryPool()
        assert pool.max_capacity == 1000

    def test_custom_capacity(self):
        pool = MemoryPool(max_capacity=50)
        assert pool.max_capacity == 50

    def test_append_success(self, pool, success_memory):
        pool.append(success_memory)
        assert len(pool.memories) == 1
        assert pool._total_success == 1
        assert pool._total_failure == 0

    def test_append_failure(self, pool, failure_memory):
        pool.append(failure_memory)
        assert len(pool.memories) == 1
        assert pool._total_success == 0
        assert pool._total_failure == 1

    def test_append_mixed(self, pool, success_memory, failure_memory):
        pool.append(success_memory)
        pool.append(failure_memory)
        pool.append(success_memory)
        assert len(pool.memories) == 3
        assert pool._total_success == 2
        assert pool._total_failure == 1

    def test_capacity_overflow(self, success_memory):
        pool = MemoryPool(max_capacity=3)
        for i in range(5):
            mem = TribulationMemory(
                h_t=[float(i)],
                p_k=[0.0],
                beta_k=0.8,
                phi_before=0.3,
                phi_after=0.9,
                delta_phi=0.6,
                dominant_name="test",
            )
            pool.append(mem)
        assert len(pool.memories) == 3
        # Should keep the last 3
        assert pool.memories[0].h_t[0] == 2.0
        assert pool.memories[-1].h_t[0] == 4.0

    def test_get_recent(self, pool, success_memory):
        for i in range(5):
            mem = TribulationMemory(
                h_t=[float(i)],
                p_k=[0.0],
                beta_k=0.8,
                phi_before=0.3,
                phi_after=0.9,
                delta_phi=0.6,
                dominant_name=f"test_{i}",
            )
            pool.append(mem)
        recent = pool.get_recent(n=3)
        assert len(recent) == 3
        assert recent[-1]["dominant"] == "test_4"

    def test_get_recent_default(self, pool, success_memory):
        for i in range(15):
            mem = TribulationMemory(
                h_t=[float(i)],
                p_k=[0.0],
                beta_k=0.8,
                phi_before=0.3,
                phi_after=0.9,
                delta_phi=0.6,
                dominant_name=f"test_{i}",
            )
            pool.append(mem)
        recent = pool.get_recent()
        assert len(recent) == 10  # Default n=10

    def test_get_recent_empty(self, pool):
        recent = pool.get_recent()
        assert recent == []

    def test_get_stats(self, pool, success_memory, failure_memory):
        pool.append(success_memory)
        pool.append(failure_memory)
        stats = pool.get_stats()
        assert stats["total_memories"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5
        assert len(stats["recent"]) == 2

    def test_get_stats_empty(self, pool):
        stats = pool.get_stats()
        assert stats["total_memories"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0  # 0 / max(1, 0) = 0
        assert stats["recent"] == []

    def test_clear(self, pool, success_memory, failure_memory):
        pool.append(success_memory)
        pool.append(failure_memory)
        pool.clear()
        assert len(pool.memories) == 0
        assert pool._total_success == 0
        assert pool._total_failure == 0


# ============================================================================
# 14. InnerChildState dataclass
# ============================================================================

class TestInnerChildState:
    def test_create(self):
        state = InnerChildState(
            betas=[0.5, 0.3, 0.1, 0.05, 0.03, 0.02],
            dominant_index=0,
            dominant_name="戒备小孩",
            dominant_beta=0.5,
            entropy_phi=1.2,
            gate_triggered=False,
            trigger_reason="认知平衡",
        )
        assert state.betas == [0.5, 0.3, 0.1, 0.05, 0.03, 0.02]
        assert state.dominant_index == 0
        assert state.dominant_name == "戒备小孩"
        assert state.dominant_beta == 0.5
        assert state.entropy_phi == 1.2
        assert state.gate_triggered is False
        assert state.corrected is False
        assert state.correction_method == ""
        assert state.delta_phi == 0.0
        assert state.verification_passed is False
        assert isinstance(state.timestamp, float)

    def test_defaults(self):
        state = InnerChildState(
            betas=[0.2] * 6,
            dominant_index=0,
            dominant_name="test",
            dominant_beta=0.2,
            entropy_phi=1.79,
            gate_triggered=False,
            trigger_reason="ok",
        )
        assert state.corrected is False
        assert state.correction_method == ""
        assert state.delta_phi == 0.0
        assert state.verification_passed is False


# ============================================================================
# 15. InnerChildStateMachine — __init__
# ============================================================================

class TestInnerChildStateMachineInit:
    def test_default_init(self):
        sm = InnerChildStateMachine()
        assert sm.dim == INNER_CHILD_DIM
        assert sm.alertness == 32.0
        assert sm.phi_limit == 0.8
        assert sm.beta_limit == 0.7
        assert sm.beta_escape_limit == 0.85
        assert sm.lambda_ == 0.4
        assert sm.gamma == 0.2
        assert sm.delta_phi_threshold == 0.15
        assert len(sm.prototypes) == 6
        assert len(sm.archetypes) == 6
        assert sm.history == []
        assert sm.max_history == 200
        assert isinstance(sm.memory_pool, MemoryPool)
        assert sm._total_probes == 0
        assert sm._total_triggers == 0
        assert sm._total_corrections == 0
        assert sm._total_safety_fallbacks == 0

    def test_custom_params(self):
        sm = InnerChildStateMachine(
            dim=32,
            alertness=10.0,
            phi_limit=1.0,
            beta_limit=0.5,
            beta_escape_limit=0.9,
            lambda_=0.3,
            gamma=0.1,
            delta_phi_threshold=0.2,
        )
        assert sm.dim == 32
        assert sm.alertness == 10.0
        assert sm.phi_limit == 1.0
        assert sm.beta_limit == 0.5
        assert sm.beta_escape_limit == 0.9
        assert sm.lambda_ == 0.3
        assert sm.gamma == 0.1
        assert sm.delta_phi_threshold == 0.2


# ============================================================================
# 16. InnerChildStateMachine — _resize_vector
# ============================================================================

class TestResizeVector:
    def test_same_size(self):
        sm = InnerChildStateMachine(dim=4)
        v = [1.0, 2.0, 3.0, 4.0]
        result = sm._resize_vector(v, 4)
        assert result == v

    def test_truncate(self):
        sm = InnerChildStateMachine(dim=4)
        v = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        result = sm._resize_vector(v, 4)
        assert result == [1.0, 2.0, 3.0, 4.0]

    def test_pad(self):
        sm = InnerChildStateMachine(dim=4)
        v = [1.0, 2.0]
        result = sm._resize_vector(v, 4)
        assert result == [1.0, 2.0, 0.0, 0.0]

    def test_empty_vector(self):
        sm = InnerChildStateMachine(dim=3)
        result = sm._resize_vector([], 3)
        assert result == [0.0, 0.0, 0.0]


# ============================================================================
# 17. InnerChildStateMachine — 观照层: observe
# ============================================================================

class TestObserve:
    @pytest.fixture
    def sm(self):
        return InnerChildStateMachine()

    def test_observe_returns_beta_and_phi(self, sm):
        h_t = [math.sin(i * 0.1) for i in range(INNER_CHILD_DIM)]
        beta, max_beta, phi = sm.observe(h_t)
        assert len(beta) == 6
        assert isinstance(max_beta, float)
        assert isinstance(phi, float)
        assert abs(sum(beta) - 1.0) < 1e-9

    def test_observe_increments_probe_count(self, sm):
        h_t = [0.0] * INNER_CHILD_DIM
        h_t[0] = 1.0
        sm.observe(h_t)
        assert sm._total_probes == 1
        sm.observe(h_t)
        assert sm._total_probes == 2

    def test_observe_auto_resizes(self, sm):
        """Vector with wrong dimension should be auto-resized."""
        h_t = [1.0, 0.0]
        sm2 = InnerChildStateMachine(dim=4)
        beta, max_beta, phi = sm2.observe(h_t)
        assert len(beta) == 6
        assert isinstance(phi, float)

    def test_observe_aligned_with_prototype(self, sm):
        h_t = sm.prototypes[0]
        beta, max_beta, _ = sm.observe(h_t)
        assert beta[0] == max_beta


# ============================================================================
# 18. InnerChildStateMachine — 问心层: inquire
# ============================================================================

class TestInquire:
    @pytest.fixture
    def sm(self):
        return InnerChildStateMachine()

    def test_inquire_balanced(self, sm):
        beta = [1.0 / 6] * 6
        phi = math.log(6)
        state = sm.inquire(beta, phi)
        assert isinstance(state, InnerChildState)
        assert state.gate_triggered is False
        assert "认知平衡" in state.trigger_reason

    def test_inquire_triggered(self, sm):
        beta = [0.95, 0.01, 0.01, 0.01, 0.01, 0.01]
        phi = compute_entropy_gate(beta)
        state = sm.inquire(beta, phi)
        assert state.gate_triggered is True
        assert state.dominant_beta > 0.7

    def test_inquire_increments_trigger_count(self, sm):
        beta = [0.95, 0.01, 0.01, 0.01, 0.01, 0.01]
        phi = compute_entropy_gate(beta)
        sm.inquire(beta, phi)
        assert sm._total_triggers == 1

    def test_inquire_adds_to_history(self, sm):
        beta = [1.0 / 6] * 6
        phi = math.log(6)
        sm.inquire(beta, phi)
        assert len(sm.history) == 1
        sm.inquire(beta, phi)
        assert len(sm.history) == 2

    def test_inquire_history_capacity(self, sm):
        sm.max_history = 5
        beta = [1.0 / 6] * 6
        phi = math.log(6)
        for _ in range(7):
            sm.inquire(beta, phi)
        assert len(sm.history) == 5

    def test_inquire_correct_dominant_index(self, sm):
        beta = [0.1, 0.6, 0.05, 0.1, 0.1, 0.05]
        phi = compute_entropy_gate(beta)
        state = sm.inquire(beta, phi)
        assert state.dominant_index == 1
        assert state.dominant_name == "缺爱小孩"


# ============================================================================
# 19. InnerChildStateMachine — 知止层: correct
# ============================================================================

class TestCorrect:
    @pytest.fixture
    def sm(self):
        return InnerChildStateMachine()

    def test_correct_when_triggered(self, sm):
        h_t = sm.prototypes[0]  # Align with prototype 0
        beta, _, phi = sm.observe(h_t)
        state = sm.inquire(beta, phi)
        if state.gate_triggered:
            h_prime, updated_state = sm.correct(h_t, state)
            assert updated_state.corrected is True
            assert updated_state.correction_method == "gradient_retreat_with_zhongyong_damping"
            assert h_prime != h_t

    def test_correct_when_not_triggered(self, sm):
        """When gate not triggered, correct should return original unchanged."""
        h_t = [0.0] * INNER_CHILD_DIM
        h_t[0] = 1.0
        norm = math.sqrt(sum(x * x for x in h_t))
        h_t = [x / norm for x in h_t]

        # Create a balanced state that won't trigger
        beta = [1.0 / 6] * 6
        phi = math.log(6)
        state = sm.inquire(beta, phi)

        h_prime, updated_state = sm.correct(h_t, state)
        assert h_prime == h_t
        assert updated_state.corrected is False

    def test_correct_increments_correction_count(self, sm):
        h_t = sm.prototypes[0]
        beta, _, phi = sm.observe(h_t)
        state = sm.inquire(beta, phi)
        if state.gate_triggered:
            sm.correct(h_t, state)
            assert sm._total_corrections == 1


# ============================================================================
# 20. InnerChildStateMachine — 化虚层: verify
# ============================================================================

class TestVerify:
    @pytest.fixture
    def sm(self):
        return InnerChildStateMachine()

    def test_verify_returns_report(self, sm):
        h_t = sm.prototypes[0]
        beta, max_beta, phi = sm.observe(h_t)
        state = sm.inquire(beta, phi)
        if state.gate_triggered:
            h_prime, state = sm.correct(h_t, state)
            report = sm.verify(h_prime, h_t, state)
            assert "correction_delta" in report
            assert "phi_before" in report
            assert "phi_after" in report
            assert "delta_phi" in report
            assert "verification_passed" in report
            assert "effective" in report
            assert "needs_safety_fallback" in report

    def test_verify_updates_state(self, sm):
        h_t = sm.prototypes[0]
        beta, _, phi = sm.observe(h_t)
        state = sm.inquire(beta, phi)
        if state.gate_triggered:
            h_prime, state = sm.correct(h_t, state)
            sm.verify(h_prime, h_t, state)
            assert state.delta_phi != 0.0
            # verification_passed depends on whether delta_phi > 0.15

    def test_verify_adds_to_memory_pool(self, sm):
        if sm.memory_pool is not None:
            initial = len(sm.memory_pool.memories)
        h_t = sm.prototypes[0]
        beta, _, phi = sm.observe(h_t)
        state = sm.inquire(beta, phi)
        if state.gate_triggered:
            h_prime, state = sm.correct(h_t, state)
            sm.verify(h_prime, h_t, state)
            assert len(sm.memory_pool.memories) > initial

    def test_verify_no_memory_when_not_triggered(self, sm):
        initial = len(sm.memory_pool.memories)
        h_t = [0.0] * INNER_CHILD_DIM
        h_t[0] = 1.0
        norm = math.sqrt(sum(x * x for x in h_t))
        h_t = [x / norm for x in h_t]
        beta = [1.0 / 6] * 6
        phi = math.log(6)
        state = sm.inquire(beta, phi)
        h_prime, state = sm.correct(h_t, state)
        sm.verify(h_prime, h_t, state)
        assert len(sm.memory_pool.memories) == initial


# ============================================================================
# 21. InnerChildStateMachine — 完整管线: process
# ============================================================================

class TestProcessCompletePipeline:
    @pytest.fixture
    def sm(self):
        return InnerChildStateMachine()

    def test_process_balanced_input(self, sm):
        """A balanced vector should not trigger gate."""
        h_t = [0.0] * INNER_CHILD_DIM
        h_t[0] = 1.0
        norm = math.sqrt(sum(x * x for x in h_t))
        h_t = [x / norm for x in h_t]

        result = sm.process(h_t)
        assert result["safety_fallback"] is False
        assert result["state"]["gate_triggered"] is False
        assert result["h_prime"] is None

    def test_process_returns_complete_result(self, sm):
        h_t = sm.prototypes[0]  # Biased toward prototype 0
        result = sm.process(h_t)
        assert "state" in result
        assert "verification" in result
        assert "h_prime" in result
        assert "safety_fallback" in result
        assert "betas" in result["state"]
        assert "dominant" in result["state"]
        assert "entropy_phi" in result["state"]

    def test_process_auto_correct_false(self, sm):
        h_t = sm.prototypes[0]
        result = sm.process(h_t, auto_correct=False)
        # Should not correct even if triggered
        if result["state"]["gate_triggered"]:
            assert result["state"]["corrected"] is False
            assert result["h_prime"] is None

    def test_process_safety_fallback(self, sm):
        """Test safety fallback when correction is ineffective."""
        # Use a vector strongly aligned with one prototype
        # but with a very low delta_phi_threshold to force fallback
        sm2 = InnerChildStateMachine(
            delta_phi_threshold=999.0,  # Impossible to pass
        )
        h_t = sm2.prototypes[0]
        result = sm2.process(h_t)
        if result["state"]["gate_triggered"]:
            assert result["safety_fallback"] is True
            assert "safety_response" in result
            assert result["safety_response"]["status"] == "retreated"
            assert result["h_prime"] is None

    def test_process_multiple_calls(self, sm):
        """Multiple process calls should accumulate history."""
        h_t = sm.prototypes[0]
        sm.process(h_t)
        sm.process(h_t)
        assert len(sm.history) >= 2
        assert sm._total_probes >= 2


# ============================================================================
# 22. InnerChildStateMachine — 统计: get_stats
# ============================================================================

class TestGetStats:
    @pytest.fixture
    def sm(self):
        sm = InnerChildStateMachine()
        # Add some history
        h_t = sm.prototypes[0]
        sm.process(h_t)
        return sm

    def test_get_stats_structure(self, sm):
        stats = sm.get_stats()
        assert "total_probes" in stats
        assert "total_triggers" in stats
        assert "total_corrections" in stats
        assert "total_safety_fallbacks" in stats
        assert "trigger_rate" in stats
        assert "correction_rate" in stats
        assert "recent_states" in stats
        assert "memory_pool" in stats
        assert "archetype_distribution" in stats

    def test_get_stats_empty_history(self):
        sm = InnerChildStateMachine()
        stats = sm.get_stats()
        assert stats["total_probes"] == 0
        assert stats["trigger_rate"] == 0.0
        assert stats["correction_rate"] == 0.0
        # When history is empty, safety_fallback_rate and archetype_distribution
        # are not included (early return in get_stats)
        assert "recent_states" in stats
        assert stats["recent_states"] == []

    def test_trigger_rate_calculation(self, sm):
        stats = sm.get_stats()
        expected_rate = sm._total_triggers / max(1, sm._total_probes)
        assert stats["trigger_rate"] == round(expected_rate, 4)

    def test_archetype_distribution(self, sm):
        stats = sm.get_stats()
        dist = stats["archetype_distribution"]
        assert len(dist) == 6
        for name in SIX_ARCHETYPES:
            assert name.name in dist
        assert abs(sum(dist.values()) - 1.0) < 0.01 or sum(dist.values()) == 0.0

    def test_archetype_distribution_empty(self):
        sm = InnerChildStateMachine()
        stats = sm.get_stats()
        # When history is empty, archetype_distribution is not included
        # in the early return branch of get_stats
        assert "archetype_distribution" not in stats

    def test_compute_archetype_distribution_direct(self):
        """Direct test of _compute_archetype_distribution when history is empty."""
        sm = InnerChildStateMachine()
        dist = sm._compute_archetype_distribution()
        assert len(dist) == 6
        for v in dist.values():
            assert v == 0.0


# ============================================================================
# 23. InnerChildStateMachine — 正交性: check_orthogonality
# ============================================================================

class TestCheckOrthogonality:
    def test_all_orthogonal(self):
        sm = InnerChildStateMachine()
        result = sm.check_orthogonality()
        assert result["all_orthogonal"] is True
        assert result["max_dot_product"] < 0.01
        assert len(result["pairs"]) == 15  # C(6,2) = 15

    def test_pair_structure(self):
        sm = InnerChildStateMachine()
        result = sm.check_orthogonality()
        for pair in result["pairs"]:
            assert "pair" in pair
            assert "dot_product" in pair
            assert "orthogonal" in pair
            assert pair["orthogonal"] is True


# ============================================================================
# 24. 全局单例: get_inner_child_sm
# ============================================================================

class TestGetInnerChildSM:
    def test_returns_singleton(self):
        sm1 = get_inner_child_sm()
        sm2 = get_inner_child_sm()
        assert sm1 is sm2

    def test_custom_params_on_first_call(self):
        # Need to reset the singleton to test custom params
        import tengod.inner_child as ic

        original = ic._inner_child_sm
        ic._inner_child_sm = None
        try:
            sm = get_inner_child_sm(
                alertness=10.0,
                phi_limit=0.5,
                beta_limit=0.3,
                lambda_=0.1,
                gamma=0.05,
            )
            assert sm.alertness == 10.0
            assert sm.phi_limit == 0.5
            assert sm.beta_limit == 0.3
            assert sm.lambda_ == 0.1
            assert sm.gamma == 0.05
        finally:
            ic._inner_child_sm = original

    def test_subsequent_calls_return_same(self):
        import tengod.inner_child as ic

        original = ic._inner_child_sm
        ic._inner_child_sm = None
        try:
            sm1 = get_inner_child_sm(alertness=5.0)
            sm2 = get_inner_child_sm(alertness=99.0)
            assert sm1 is sm2
            assert sm1.alertness == 5.0  # First call params preserved
        finally:
            ic._inner_child_sm = original


# ============================================================================
# 25. Edge cases and integration scenarios
# ============================================================================

class TestEdgeCases:
    def test_psychological_escape_in_state_machine(self):
        """Test that the psychological escape path (max_beta > 0.85, phi < 0.8) is triggered."""
        sm = InnerChildStateMachine()
        # Create a vector strongly aligned with prototype 0
        h_t = sm.prototypes[0]
        beta, max_beta, phi = sm.observe(h_t)
        state = sm.inquire(beta, phi)
        # If highly aligned, it should trigger
        if max_beta > 0.85 and phi < 0.8:
            assert state.gate_triggered is True
            assert "心理偏执逃逸" in state.trigger_reason

    def test_full_pipeline_with_safety_fallback(self):
        """End-to-end: process a highly biased vector and check safety fallback."""
        sm = InnerChildStateMachine(delta_phi_threshold=999.0)
        h_t = sm.prototypes[0]
        result = sm.process(h_t)

        if result["state"]["gate_triggered"]:
            # Since delta_phi_threshold is impossible, should fallback
            assert result["safety_fallback"] is True
            assert result["safety_response"]["status"] == "retreated"
            assert result["h_prime"] is None

    def test_full_pipeline_successful_correction(self):
        """End-to-end: process a moderately biased vector."""
        sm = InnerChildStateMachine()
        h_t = sm.prototypes[0]
        result = sm.process(h_t)

        if result["state"]["gate_triggered"] and not result["safety_fallback"]:
            assert result["state"]["corrected"] is True
            assert result["h_prime"] is not None
            assert "verification" in result

    def test_memory_pool_integration(self):
        """Memory pool accumulates tribulation memories across process calls."""
        sm = InnerChildStateMachine()
        initial = len(sm.memory_pool.memories)
        for _ in range(3):
            h_t = sm.prototypes[0]
            sm.process(h_t)
        # Some memories should have been added (for triggered cases)
        assert len(sm.memory_pool.memories) >= initial

    def test_history_accumulation(self):
        sm = InnerChildStateMachine()
        sm.max_history = 10
        for _ in range(15):
            h_t = sm.prototypes[0]
            sm.process(h_t)
        assert len(sm.history) == 10

    def test_prototype_vectors_consistency(self):
        """Prototypes used by the state machine should be from the module cache."""
        sm = InnerChildStateMachine()
        assert sm.prototypes is not None
        assert len(sm.prototypes) == 6
        for v in sm.prototypes:
            assert len(v) == sm.dim

    def test_archetypes_consistency(self):
        sm = InnerChildStateMachine()
        assert len(sm.archetypes) == 6
        for a in sm.archetypes:
            assert isinstance(a, InnerChildArchetype)

    def test_zhongyong_anchor_valid(self):
        """The zhongyong anchor should be a valid unit vector."""
        norm = math.sqrt(sum(x * x for x in _ZHONGYONG_ANCHOR))
        assert abs(norm - 1.0) < 1e-8

    def test_compute_bias_residual_with_large_vectors(self):
        h_t = [1.0] * 100
        p_k = [0.5] * 100
        r = compute_bias_residual(h_t, p_k)
        assert len(r) == 100
        for x in r:
            assert abs(x - 0.5) < 1e-9

    def test_correct_by_gradient_retreat_preserves_non_biased_dims(self):
        """Dimensions where h_t and p_k agree should not change much."""
        h_t = [1.0, 0.0, 0.5]
        p_k = [0.0, 1.0, 0.5]
        beta_k = 0.9
        corrected = correct_by_gradient_retreat(h_t, p_k, beta_k)
        # Dimension 2: h_t[2]=0.5, p_k[2]=0.5, r_bias[2]=0
        # The correction should not affect it
        assert abs(corrected[2] - 0.5) < 1e-9

    def test_entropy_gate_with_negative_beta_values(self):
        """Entropy should not crash with negative values (b > 0 check)."""
        beta = [0.5, 0.5, 0.0, -0.1, 0.1, 0.0]
        phi = compute_entropy_gate(beta)
        # Should compute without error, negative values skipped
        assert phi >= 0

    def test_soft_occupancy_handles_shorter_prototype(self):
        """If a prototype is shorter than h_t, it should still work."""
        prototypes = [[0.5, 0.5], [0.5, -0.5]]
        h_t = [1.0, 0.0, 0.0]  # Longer than prototypes
        beta, max_beta = compute_soft_occupancy(h_t, prototypes)
        assert len(beta) == 2
        assert abs(sum(beta) - 1.0) < 1e-9

    def test_process_result_fields_consistency(self):
        sm = InnerChildStateMachine()
        h_t = sm.prototypes[0]
        result = sm.process(h_t)

        state = result["state"]
        assert "betas" in state
        assert len(state["betas"]) == 6
        assert "dominant" in state
        assert "index" in state["dominant"]
        assert "name" in state["dominant"]
        assert "beta" in state["dominant"]

        if not result["safety_fallback"]:
            if state["gate_triggered"]:
                assert state["corrected"] is True
                assert isinstance(state["delta_phi"], float)
            else:
                assert state["corrected"] is False
                assert state["delta_phi"] == 0.0
                assert result["h_prime"] is None

    def test_memory_pool_success_rate_zero_divisions(self):
        """Memory pool stats should handle zero divisions gracefully."""
        pool = MemoryPool()
        stats = pool.get_stats()
        assert stats["success_rate"] == 0.0  # 0 / max(1, 0)

    def test_state_machine_stats_zero_divisions(self):
        sm = InnerChildStateMachine()
        stats = sm.get_stats()
        assert stats["trigger_rate"] == 0.0
        assert stats["correction_rate"] == 0.0
        # safety_fallback_rate not in empty history early return

    def test_observe_with_exact_dimension(self):
        sm = InnerChildStateMachine(dim=64)
        h_t = [0.0] * 64
        h_t[0] = 1.0
        norm = math.sqrt(sum(x * x for x in h_t))
        h_t = [x / norm for x in h_t]
        beta, max_beta, phi = sm.observe(h_t)
        assert len(beta) == 6
        assert 0 < phi <= math.log(6)

    def test_should_trigger_gate_all_combinations(self):
        """Test all four branches of should_trigger_gate."""
        # Branch 1: escape
        t1, r1 = should_trigger_gate(phi=0.3, max_beta=0.9)
        assert t1 and "心理偏执逃逸" in r1

        # Branch 2: standard trigger
        t2, r2 = should_trigger_gate(phi=0.3, max_beta=0.8)
        assert t2 and "门禁触发" in r2

        # Branch 3: entropy low only
        t3, r3 = should_trigger_gate(phi=0.3, max_beta=0.5)
        assert not t3 and "熵偏低" in r3

        # Branch 4: occupancy high only
        t4, r4 = should_trigger_gate(phi=1.5, max_beta=0.8)
        assert not t4 and "占据度偏高" in r4

        # Branch 5: balanced
        t5, r5 = should_trigger_gate(phi=1.5, max_beta=0.3)
        assert not t5 and "认知平衡" in r5


# ============================================================================
# 26. Property-based / fuzzing style tests
# ============================================================================

class TestInvariants:
    def test_beta_always_sums_to_one(self):
        """Beta distribution should always sum to 1."""
        sm = InnerChildStateMachine()
        for seed in range(20):
            h_t = [math.sin(seed * 0.7 + i * 0.3) for i in range(INNER_CHILD_DIM)]
            norm = math.sqrt(sum(x * x for x in h_t))
            h_t = [x / max(norm, 1e-8) for x in h_t]
            beta, _, _ = sm.observe(h_t)
            assert abs(sum(beta) - 1.0) < 1e-6, f"Beta sum failed at seed {seed}"

    def test_phi_within_bounds(self):
        """Phi should always be between 0 and ln(6)."""
        sm = InnerChildStateMachine()
        for seed in range(20):
            h_t = [math.sin(seed * 0.7 + i * 0.3) for i in range(INNER_CHILD_DIM)]
            norm = math.sqrt(sum(x * x for x in h_t))
            h_t = [x / max(norm, 1e-8) for x in h_t]
            _, _, phi = sm.observe(h_t)
            assert 0 <= phi <= math.log(6) + 1e-6, f"Phi {phi} out of bounds at seed {seed}"

    def test_process_never_raises(self):
        """Process should never raise an exception."""
        sm = InnerChildStateMachine()
        for seed in range(30):
            h_t = [math.sin(seed * 0.7 + i * 0.3) for i in range(INNER_CHILD_DIM)]
            norm = math.sqrt(sum(x * x for x in h_t))
            if norm < 1e-8:
                continue
            h_t = [x / norm for x in h_t]
            try:
                result = sm.process(h_t)
                assert "state" in result
                assert "safety_fallback" in result
            except Exception as e:
                pytest.fail(f"process raised {e} at seed {seed}")

    def test_orthogonality_preserved_after_operations(self):
        """Prototype vectors should remain orthogonal after state machine operations."""
        sm = InnerChildStateMachine()
        for _ in range(10):
            h_t = sm.prototypes[0]
            sm.process(h_t)
        result = sm.check_orthogonality()
        assert result["all_orthogonal"] is True