"""Tests for tengod.federated_consensus — FederatedConsensus engine."""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from tengod.federated_consensus import FederatedConsensus


# ═══════════════════════════════════════════════════════════════════
# 1. __init__  tests
# ═══════════════════════════════════════════════════════════════════

class TestInit:
    """Tests for the constructor."""

    def test_init_with_default_node_id(self):
        """Default init generates a random 8-char hex node_id."""
        fc = FederatedConsensus()
        assert isinstance(fc._node_id, str)
        assert len(fc._node_id) == 8
        assert all(c in "0123456789abcdef" for c in fc._node_id)

    def test_init_with_custom_node_id(self):
        """Custom node_id is preserved."""
        fc = FederatedConsensus(node_id="master-1")
        assert fc._node_id == "master-1"

    def test_init_creates_empty_peers_model_history(self):
        """Fresh instance has empty peers, model, and history."""
        fc = FederatedConsensus()
        assert fc._peers == {}
        assert fc._global_model == {}
        assert fc._history == []
        assert fc._round == 0


# ═══════════════════════════════════════════════════════════════════
# 2. add_peer / remove_peer  tests
# ═══════════════════════════════════════════════════════════════════

class TestPeerManagement:
    """Tests for add_peer and remove_peer."""

    def test_add_peer_adds_entry_with_defaults(self):
        fc = FederatedConsensus()
        fc.add_peer("peer-a")
        assert "peer-a" in fc._peers
        p = fc._peers["peer-a"]
        assert p["data_size"] == 1000
        assert p["weight"] == 1.0
        assert p["status"] == "active"
        assert p["model"] == {}

    def test_add_peer_respects_custom_data_size(self):
        fc = FederatedConsensus()
        fc.add_peer("peer-b", data_size=5000)
        assert fc._peers["peer-b"]["data_size"] == 5000

    def test_remove_peer_deletes_entry(self):
        fc = FederatedConsensus()
        fc.add_peer("peer-c")
        fc.remove_peer("peer-c")
        assert "peer-c" not in fc._peers

    def test_remove_nonexistent_peer_does_not_raise(self):
        fc = FederatedConsensus()
        fc.remove_peer("ghost")  # must not raise


# ═══════════════════════════════════════════════════════════════════
# 3. submit_gradient  tests
# ═══════════════════════════════════════════════════════════════════

class TestSubmitGradient:
    """Tests for submit_gradient."""

    def test_submit_gradient_valid_peer(self):
        fc = FederatedConsensus()
        fc.add_peer("p1")
        res = fc.submit_gradient("p1", {"w": [0.1, 0.2]})
        assert res["status"] == "ok"
        assert res["peer"] == "p1"
        assert fc._peers["p1"]["model"] == {"w": [0.1, 0.2]}

    def test_submit_gradient_invalid_peer_returns_error(self):
        fc = FederatedConsensus()
        res = fc.submit_gradient("unknown", {"w": [1.0]})
        assert res["status"] == "error"
        assert "Unknown peer" in res["message"]

    def test_submit_gradient_updates_data_size_when_provided(self):
        fc = FederatedConsensus()
        fc.add_peer("p1", data_size=100)
        fc.submit_gradient("p1", {"w": [1.0]}, data_size=500)
        assert fc._peers["p1"]["data_size"] == 500

    def test_submit_gradient_does_not_overwrite_data_size_with_zero(self):
        fc = FederatedConsensus()
        fc.add_peer("p1", data_size=200)
        fc.submit_gradient("p1", {"w": [1.0]}, data_size=0)
        assert fc._peers["p1"]["data_size"] == 200

    def test_submit_gradient_updates_last_update_timestamp(self):
        fc = FederatedConsensus()
        fc.add_peer("p1")
        old_ts = fc._peers["p1"]["last_update"]
        import time
        time.sleep(0.01)
        fc.submit_gradient("p1", {"w": [1.0]})
        assert fc._peers["p1"]["last_update"] > old_ts


# ═══════════════════════════════════════════════════════════════════
# 4. aggregate  tests
# ═══════════════════════════════════════════════════════════════════

class TestAggregate:
    """Tests for aggregate with different methods."""

    # -- helpers ---------------------------------------------------
    def _setup_peers(self, fc):
        """Add two peers with known data_sizes and gradients."""
        fc.add_peer("p1", data_size=100)
        fc.add_peer("p2", data_size=300)
        fc.submit_gradient("p1", {"w": [1.0, 2.0]})
        fc.submit_gradient("p2", {"w": [3.0, 4.0]})

    # -- fedavg ----------------------------------------------------
    def test_aggregate_fedavg_weighted_by_data_size(self):
        """fedavg weights contributions by data_size proportion."""
        fc = FederatedConsensus()
        self._setup_peers(fc)
        # total_data = 400; p1 weight=0.25, p2 weight=0.75
        # w[0] = 1.0*0.25 + 3.0*0.75 = 2.5
        # w[1] = 2.0*0.25 + 4.0*0.75 = 3.5
        result = fc.aggregate("fedavg")
        assert result["status"] == "ok"
        assert result["method"] == "fedavg"
        model = fc.get_global_model()
        assert model["w"] == pytest.approx([2.5, 3.5])

    # -- equal ----------------------------------------------------
    def test_aggregate_equal_uniform_weights(self):
        """equal method ignores data_size and averages uniformly."""
        fc = FederatedConsensus()
        self._setup_peers(fc)
        # w[0] = (1.0 + 3.0) / 2 = 2.0
        # w[1] = (2.0 + 4.0) / 2 = 3.0
        result = fc.aggregate("equal")
        assert result["status"] == "ok"
        assert result["method"] == "equal"
        model = fc.get_global_model()
        assert model["w"] == pytest.approx([2.0, 3.0])

    # -- median ----------------------------------------------------
    def test_aggregate_median_anti_byzantine(self):
        """Median aggregation is robust against a Byzantine outlier."""
        fc = FederatedConsensus()
        fc.add_peer("honest1", data_size=100)
        fc.add_peer("honest2", data_size=100)
        fc.add_peer("byzantine", data_size=100)
        fc.submit_gradient("honest1", {"w": [1.0, 2.0]})
        fc.submit_gradient("honest2", {"w": [3.0, 4.0]})
        fc.submit_gradient("byzantine", {"w": [100.0, -50.0]})
        result = fc.aggregate("median")
        assert result["status"] == "ok"
        model = fc.get_global_model()
        # sorted pos0: [1.0, 3.0, 100.0] → median 3.0
        # sorted pos1: [-50.0, 2.0, 4.0] → median 2.0
        assert model["w"] == pytest.approx([3.0, 2.0])

    def test_aggregate_median_with_even_peers(self):
        """Median with even number of peers picks lower-middle."""
        fc = FederatedConsensus()
        for i, vals in enumerate(["p1", "p2", "p3", "p4"]):
            fc.add_peer(vals, data_size=100)
        fc.submit_gradient("p1", {"w": [10.0]})
        fc.submit_gradient("p2", {"w": [20.0]})
        fc.submit_gradient("p3", {"w": [30.0]})
        fc.submit_gradient("p4", {"w": [40.0]})
        result = fc.aggregate("median")
        # sorted [10, 20, 30, 40], len=4, idx=2 → 30
        assert result["status"] == "ok"
        assert fc.get_global_model()["w"] == pytest.approx([30.0])

    # -- no active peers -------------------------------------------
    def test_aggregate_no_active_peers_returns_error(self):
        fc = FederatedConsensus()
        result = fc.aggregate("fedavg")
        assert result["status"] == "error"
        assert "No active peers" in result["message"]

    def test_aggregate_no_active_peers_after_removal(self):
        fc = FederatedConsensus()
        fc.add_peer("p1")
        fc.remove_peer("p1")
        result = fc.aggregate("fedavg")
        assert result["status"] == "error"

    # -- round increment -------------------------------------------
    def test_aggregate_increments_round(self):
        fc = FederatedConsensus()
        fc.add_peer("p1")
        fc.submit_gradient("p1", {"w": [1.0]})
        assert fc._round == 0
        fc.aggregate("fedavg")
        assert fc._round == 1
        fc.aggregate("equal")
        assert fc._round == 2

    # -- default method --------------------------------------------
    def test_aggregate_default_method_is_fedavg(self):
        fc = FederatedConsensus()
        fc.add_peer("p1", data_size=500)
        fc.add_peer("p2", data_size=500)
        fc.submit_gradient("p1", {"w": [2.0]})
        fc.submit_gradient("p2", {"w": [4.0]})
        result = fc.aggregate()
        assert result["method"] == "fedavg"
        assert fc.get_global_model()["w"] == pytest.approx([3.0])


# ═══════════════════════════════════════════════════════════════════
# 5. add_differential_privacy  tests
# ═══════════════════════════════════════════════════════════════════

class TestDifferentialPrivacy:
    """Tests for add_differential_privacy."""

    def test_dp_adds_non_zero_perturbation(self):
        """Laplace noise should change at least some gradient values."""
        fc = FederatedConsensus()
        grads = {"w": [0.0] * 100}
        noisy = fc.add_differential_privacy(grads, epsilon=1.0, delta=1e-5)
        # With 100 values it's virtually impossible that all are zero
        assert noisy["w"] != grads["w"]
        assert len(noisy["w"]) == 100

    def test_dp_preserves_gradient_keys_and_shapes(self):
        fc = FederatedConsensus()
        grads = {"layer1": [1.0, 2.0, 3.0], "layer2": [4.0, 5.0]}
        noisy = fc.add_differential_privacy(grads, epsilon=1.0)
        assert set(noisy.keys()) == {"layer1", "layer2"}
        assert len(noisy["layer1"]) == 3
        assert len(noisy["layer2"]) == 2

    def test_dp_small_epsilon_produces_larger_noise(self):
        """Smaller epsilon → larger scale → larger noise variance."""
        fc = FederatedConsensus()
        grads = {"w": [0.0] * 500}
        noisy_lo = fc.add_differential_privacy(grads, epsilon=0.01)
        noisy_hi = fc.add_differential_privacy(grads, epsilon=100.0)
        var_lo = sum(v * v for v in noisy_lo["w"]) / len(noisy_lo["w"])
        var_hi = sum(v * v for v in noisy_hi["w"]) / len(noisy_hi["w"])
        assert var_lo > var_hi


# ═══════════════════════════════════════════════════════════════════
# 6. get_global_model  tests
# ═══════════════════════════════════════════════════════════════════

class TestGetGlobalModel:
    """Tests for get_global_model."""

    def test_get_global_model_returns_empty_initially(self):
        fc = FederatedConsensus()
        assert fc.get_global_model() == {}

    def test_get_global_model_after_aggregation(self):
        fc = FederatedConsensus()
        fc.add_peer("p1")
        fc.submit_gradient("p1", {"w": [5.0, 6.0]})
        fc.aggregate("fedavg")
        model = fc.get_global_model()
        assert model == {"w": [5.0, 6.0]}


# ═══════════════════════════════════════════════════════════════════
# 7. get_peers_status  tests
# ═══════════════════════════════════════════════════════════════════

class TestGetPeersStatus:
    """Tests for get_peers_status."""

    def test_get_peers_status_empty(self):
        fc = FederatedConsensus()
        assert fc.get_peers_status() == []

    def test_get_peers_status_reflects_peer_state(self):
        fc = FederatedConsensus()
        fc.add_peer("p1", data_size=200)
        fc.add_peer("p2", data_size=400)
        statuses = fc.get_peers_status()
        assert len(statuses) == 2
        ids = {s["peer_id"] for s in statuses}
        assert ids == {"p1", "p2"}
        for s in statuses:
            assert s["status"] == "active"
            assert "data_size" in s
            assert "last_update" in s


# ═══════════════════════════════════════════════════════════════════
# 8. get_history  tests
# ═══════════════════════════════════════════════════════════════════

class TestGetHistory:
    """Tests for get_history."""

    def test_get_history_empty_initially(self):
        fc = FederatedConsensus()
        assert fc.get_history() == []

    def test_get_history_after_aggregations(self):
        fc = FederatedConsensus()
        fc.add_peer("p1")
        fc.submit_gradient("p1", {"w": [1.0]})
        fc.aggregate("fedavg")
        fc.aggregate("equal")
        history = fc.get_history()
        assert len(history) == 2
        assert history[0]["method"] == "fedavg"
        assert history[0]["round"] == 1
        assert history[1]["method"] == "equal"
        assert history[1]["round"] == 2


# ═══════════════════════════════════════════════════════════════════
# 9. stats  tests
# ═══════════════════════════════════════════════════════════════════

class TestStats:
    """Tests for stats()."""

    def test_stats_returns_correct_counts(self):
        fc = FederatedConsensus(node_id="node-x")
        fc.add_peer("p1")
        fc.add_peer("p2")
        fc.add_peer("p3")
        fc.submit_gradient("p1", {"w": [1.0]})
        fc.submit_gradient("p2", {"w": [2.0]})
        fc.aggregate("fedavg")
        s = fc.stats()
        assert s["node_id"] == "node-x"
        assert s["total_peers"] == 3
        assert s["active_peers"] == 3
        assert s["round"] == 1
        assert s["model_size"] == 1

    def test_stats_reflects_removed_peer(self):
        fc = FederatedConsensus()
        fc.add_peer("p1")
        fc.add_peer("p2")
        fc.remove_peer("p1")
        s = fc.stats()
        assert s["total_peers"] == 1
        assert s["active_peers"] == 1


# ═══════════════════════════════════════════════════════════════════
# 10. Multiple-round / integration  tests
# ═══════════════════════════════════════════════════════════════════

class TestMultipleRounds:
    """End-to-end multi-round tests."""

    def test_multiple_rounds_accumulate_history(self):
        fc = FederatedConsensus()
        fc.add_peer("p1", data_size=100)
        fc.add_peer("p2", data_size=200)
        for rnd in range(3):
            fc.submit_gradient("p1", {"w": [float(rnd + 1)]})
            fc.submit_gradient("p2", {"w": [float(rnd + 2)]})
            fc.aggregate("fedavg")
        assert fc._round == 3
        assert len(fc.get_history()) == 3
        assert fc.stats()["round"] == 3

    def test_rounds_appear_in_history_with_correct_round_numbers(self):
        fc = FederatedConsensus()
        fc.add_peer("p1")
        fc.submit_gradient("p1", {"w": [1.0]})
        fc.aggregate("fedavg")
        fc.submit_gradient("p1", {"w": [2.0]})
        fc.aggregate("equal")
        fc.submit_gradient("p1", {"w": [3.0]})
        fc.aggregate("median")
        history = fc.get_history()
        assert [h["round"] for h in history] == [1, 2, 3]
        assert [h["method"] for h in history] == ["fedavg", "equal", "median"]

    def test_peer_can_rejoin_after_removal(self):
        """A removed peer can be re-added and participate."""
        fc = FederatedConsensus()
        fc.add_peer("p1")
        fc.remove_peer("p1")
        fc.add_peer("p1", data_size=300)
        fc.submit_gradient("p1", {"w": [7.0]})
        res = fc.aggregate("fedavg")
        assert res["status"] == "ok"
        assert fc.get_global_model()["w"] == [7.0]