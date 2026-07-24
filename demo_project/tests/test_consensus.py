"""
共识模块 (consensus.py) 测试套件
=================================
覆盖: NodeRole, PeerConfig, LogEntry, ConsensusState, ConsensusEngine
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest

from tengod.consensus import (
    ConsensusEngine,
    ConsensusState,
    LogEntry,
    NodeRole,
    PeerConfig,
)


# ═══════════════════════════════════════════════════════════
# NodeRole 测试
# ═══════════════════════════════════════════════════════════

def test_node_role_values():
    """验证 NodeRole 枚举值"""
    assert NodeRole.FOLLOWER.value == "follower"
    assert NodeRole.CANDIDATE.value == "candidate"
    assert NodeRole.LEADER.value == "leader"


def test_node_role_count():
    """验证 NodeRole 有三个成员"""
    assert len(NodeRole) == 3


def test_node_role_membership():
    """验证 NodeRole 成员可迭代"""
    roles = list(NodeRole)
    assert NodeRole.FOLLOWER in roles
    assert NodeRole.CANDIDATE in roles
    assert NodeRole.LEADER in roles


# ═══════════════════════════════════════════════════════════
# PeerConfig 测试
# ═══════════════════════════════════════════════════════════

def test_peer_config_creation():
    """创建 PeerConfig — 验证字段和默认值"""
    pc = PeerConfig(node_id="node-1", address="http://localhost:8000")
    assert pc.node_id == "node-1"
    assert pc.address == "http://localhost:8000"
    assert pc.healthy is True
    assert pc.last_heartbeat == 0.0


def test_peer_config_custom():
    """PeerConfig — 自定义全部字段"""
    pc = PeerConfig(
        node_id="node-x",
        address="http://10.0.0.1:9000",
        healthy=False,
        last_heartbeat=123.45,
    )
    assert pc.node_id == "node-x"
    assert pc.address == "http://10.0.0.1:9000"
    assert pc.healthy is False
    assert pc.last_heartbeat == 123.45


def test_peer_config_equality():
    """PeerConfig — 同字段实例相等"""
    a = PeerConfig("n1", "http://a:8000")
    b = PeerConfig("n1", "http://a:8000")
    assert a == b


def test_peer_config_inequality():
    """PeerConfig — 不同 node_id 不相等"""
    a = PeerConfig("n1", "http://a:8000")
    b = PeerConfig("n2", "http://a:8000")
    assert a != b


# ═══════════════════════════════════════════════════════════
# LogEntry 测试
# ═══════════════════════════════════════════════════════════

def test_log_entry_creation_defaults():
    """创建 LogEntry — 验证字段和默认值"""
    le = LogEntry(index=0, term=1, command="test")
    assert le.index == 0
    assert le.term == 1
    assert le.command == "test"
    assert le.data == {}
    assert le.committed is False
    assert isinstance(le.timestamp, float)
    assert le.timestamp > 0


def test_log_entry_with_data():
    """LogEntry — 带自定义 data 和 committed"""
    le = LogEntry(index=5, term=3, command="set", data={"key": "val"}, committed=True)
    assert le.data == {"key": "val"}
    assert le.committed is True


def test_log_entry_timestamp_fresh():
    """LogEntry — timestamp 接近当前时间"""
    now = time.time()
    le = LogEntry(index=0, term=1, command="test")
    assert abs(le.timestamp - now) < 1.0


# ═══════════════════════════════════════════════════════════
# ConsensusState 测试
# ═══════════════════════════════════════════════════════════

def test_consensus_state_creation():
    """创建 ConsensusState — 验证所有字段"""
    cs = ConsensusState(
        node_id="n1",
        role="leader",
        current_term=1,
        voted_for="n1",
        commit_index=5,
        last_applied=5,
        peer_count=3,
        healthy_peers=2,
        log_count=10,
        uptime=100.0,
    )
    assert cs.node_id == "n1"
    assert cs.role == "leader"
    assert cs.current_term == 1
    assert cs.voted_for == "n1"
    assert cs.commit_index == 5
    assert cs.last_applied == 5
    assert cs.peer_count == 3
    assert cs.healthy_peers == 2
    assert cs.log_count == 10
    assert cs.uptime == 100.0


def test_consensus_state_follower():
    """ConsensusState — Follower 状态"""
    cs = ConsensusState(
        node_id="n2", role="follower", current_term=0, voted_for=None,
        commit_index=-1, last_applied=-1, peer_count=0, healthy_peers=0,
        log_count=0, uptime=0.0,
    )
    assert cs.role == "follower"
    assert cs.voted_for is None
    assert cs.commit_index == -1


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def _make_engine(tmpdir, **kwargs):
    """创建 ConsensusEngine 的辅助函数。

    默认使用长选举超时，避免测试中意外触发选举。
    """
    defaults = dict(
        node_id="test-node",
        peers=[],
        data_dir=tmpdir,
        election_timeout=(10.0, 20.0),
    )
    defaults.update(kwargs)
    return ConsensusEngine(**defaults)


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: 初始化
# ═══════════════════════════════════════════════════════════

def test_engine_init_defaults():
    """ConsensusEngine — 初始化默认值"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        assert engine.node_id == "test-node"
        assert engine.listen_port == 8000
        assert engine._role == NodeRole.FOLLOWER
        assert engine._current_term == 0
        assert engine._voted_for is None
        assert engine._commit_index == -1
        assert engine._last_applied == -1
        assert engine._running is False
        assert engine._leader_id is None
        engine.stop()


def test_engine_init_with_peers():
    """ConsensusEngine — 初始化带 peers 字典"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://host1:8000")
        p2 = PeerConfig("p2", "http://host2:8000")
        engine = _make_engine(tmpdir, node_id="main", peers=[p1, p2])
        assert len(engine.peers) == 2
        assert "p1" in engine.peers
        assert "p2" in engine.peers
        engine.stop()


def test_engine_init_custom_port():
    """ConsensusEngine — 自定义 listen_port"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, listen_port=9999)
        assert engine.listen_port == 9999
        engine.stop()


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: start / stop 生命周期
# ═══════════════════════════════════════════════════════════

def test_engine_start_stop():
    """start() 设置 running=True；stop() 恢复 FOLLOWER 且 running=False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        assert not engine._running
        engine.start()
        assert engine._running
        engine.stop()
        assert not engine._running
        assert engine._role == NodeRole.FOLLOWER


def test_engine_double_start():
    """重复 start() 不报错"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine.start()
        engine.start()
        engine.stop()


def test_engine_stop_without_start():
    """stop() 在未 start 时调用不报错"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine.stop()


def test_engine_stop_cancels_timer():
    """stop() 取消选举计时器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(0.5, 0.6))
        engine.start()
        assert engine._election_timer is not None
        engine.stop()
        # 计时器应已取消，不应再触发选举
        assert engine._role == NodeRole.FOLLOWER


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: propose
# ═══════════════════════════════════════════════════════════

def test_propose_as_follower():
    """Follower 调用 propose() 返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        assert engine._role == NodeRole.FOLLOWER
        assert engine.propose("cmd") is False
        engine.stop()


def test_propose_as_leader_via_election():
    """单节点选举成为 Leader 后 propose() 返回 True 并增加日志"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(0.05, 0.1))
        engine.start()
        # 等待选举完成（最多 5 秒）
        for _ in range(50):
            if engine.query().role == "leader":
                break
            time.sleep(0.1)
        state = engine.query()
        assert state.role == "leader", f"Expected leader, got {state.role}"
        result = engine.propose("test_cmd", {"a": 1})
        assert result is True
        state2 = engine.query()
        assert state2.log_count == 1
        engine.stop()


def test_propose_multiple():
    """Leader 多次 propose 后日志数量递增"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(0.05, 0.1))
        engine.start()
        for _ in range(50):
            if engine.query().role == "leader":
                break
            time.sleep(0.1)
        assert engine.query().role == "leader"
        for i in range(3):
            assert engine.propose(f"cmd_{i}") is True
        assert engine.query().log_count == 3
        engine.stop()


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: query
# ═══════════════════════════════════════════════════════════

def test_query_returns_consensus_state():
    """query() 返回 ConsensusState 实例"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        state = engine.query()
        assert isinstance(state, ConsensusState)
        assert state.node_id == "test-node"
        assert state.role == "follower"
        assert state.current_term == 0
        assert state.peer_count == 0
        assert state.healthy_peers == 0
        assert state.log_count == 0
        engine.stop()


def test_query_reflects_peer_health():
    """query() 反映 peer 健康状态"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://h1:8000", healthy=True)
        p2 = PeerConfig("p2", "http://h2:8000", healthy=False)
        engine = _make_engine(tmpdir, peers=[p1, p2])
        state = engine.query()
        assert state.peer_count == 2
        assert state.healthy_peers == 1
        engine.stop()


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: on_leader_change
# ═══════════════════════════════════════════════════════════

def test_on_leader_change_callback():
    """on_leader_change() 注册的回调在成为 Leader 时被调用"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        calls = []

        def cb(old: str, new: str):
            calls.append((old, new))

        engine.on_leader_change(cb)
        # 直接调用 _become_leader 触发回调
        engine._become_leader()
        assert len(calls) == 1
        assert calls[0][1] == "test-node"
        engine.stop()


def test_on_leader_change_multiple_callbacks():
    """多个回调都会被触发"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        calls = []

        engine.on_leader_change(lambda o, n: calls.append(1))
        engine.on_leader_change(lambda o, n: calls.append(2))
        engine._become_leader()
        assert len(calls) == 2
        engine.stop()


def test_on_leader_change_callback_exception_ignored():
    """回调抛异常不应影响其他回调"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        called = []

        def bad_cb(o, n):
            raise RuntimeError("boom")

        def good_cb(o, n):
            called.append(True)

        engine.on_leader_change(bad_cb)
        engine.on_leader_change(good_cb)
        engine._become_leader()
        assert len(called) == 1
        engine.stop()


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: handle_vote_request
# ═══════════════════════════════════════════════════════════

def test_handle_vote_request_term_less_than_current():
    """term < current_term → 拒绝投票"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine._current_term = 5
        resp = engine.handle_vote_request({
            "term": 3,
            "candidate_id": "c1",
            "last_log_index": 0,
            "last_log_term": 0,
        })
        assert resp["vote_granted"] is False
        assert resp["term"] == 5
        engine.stop()


def test_handle_vote_request_term_greater_updates_state():
    """term > current_term → 更新 current_term、step down 并授予投票"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._current_term = 2
        engine._role = NodeRole.CANDIDATE
        engine._voted_for = "someone"
        resp = engine.handle_vote_request({
            "term": 5,
            "candidate_id": "c1",
            "last_log_index": 0,
            "last_log_term": 0,
        })
        assert engine._current_term == 5
        assert engine._role == NodeRole.FOLLOWER
        assert resp["vote_granted"] is True
        assert engine._voted_for == "c1"
        engine.stop()


def test_handle_vote_request_vote_granted():
    """term >= current_term, voted_for is None, log OK → 投票授予"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._current_term = 1
        resp = engine.handle_vote_request({
            "term": 2,
            "candidate_id": "c1",
            "last_log_index": 0,
            "last_log_term": 0,
        })
        assert resp["vote_granted"] is True
        assert resp["term"] == 2
        assert engine._voted_for == "c1"
        engine.stop()


def test_handle_vote_request_already_voted_for_other():
    """已投票给其他候选人 → 拒绝"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine._current_term = 3
        engine._voted_for = "other"
        engine._logs = [LogEntry(index=0, term=1, command="x")]
        resp = engine.handle_vote_request({
            "term": 3,
            "candidate_id": "c2",
            "last_log_index": 0,
            "last_log_term": 1,
        })
        assert resp["vote_granted"] is False
        engine.stop()


def test_handle_vote_request_same_candidate_ok():
    """已投票给同一候选人 → 允许（重复投票）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._current_term = 3
        engine._voted_for = "c1"
        engine._logs = [LogEntry(index=0, term=1, command="x")]
        resp = engine.handle_vote_request({
            "term": 3,
            "candidate_id": "c1",
            "last_log_index": 0,
            "last_log_term": 1,
        })
        assert resp["vote_granted"] is True
        engine.stop()


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: handle_append_entries
# ═══════════════════════════════════════════════════════════

def test_handle_append_entries_term_less_than_current():
    """term < current_term → 拒绝"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine._current_term = 5
        resp = engine.handle_append_entries({
            "term": 3,
            "leader_id": "leader-1",
            "prev_log_index": -1,
            "prev_log_term": 0,
            "entries": [],
            "leader_commit": -1,
        })
        assert resp["success"] is False
        assert resp["term"] == 5
        engine.stop()


def test_handle_append_entries_valid_heartbeat():
    """有效心跳 → 更新状态为 Follower"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._current_term = 3
        engine._role = NodeRole.CANDIDATE
        resp = engine.handle_append_entries({
            "term": 4,
            "leader_id": "leader-1",
            "prev_log_index": -1,
            "prev_log_term": 0,
            "entries": [],
            "leader_commit": -1,
        })
        assert resp["success"] is True
        assert resp["term"] == 4
        assert engine._role == NodeRole.FOLLOWER
        assert engine._leader_id == "leader-1"
        assert engine._current_term == 4
        engine.stop()


def test_handle_append_entries_with_log_entries():
    """AppendEntries 带日志条目 → 追加到本地日志"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        resp = engine.handle_append_entries({
            "term": 1,
            "leader_id": "leader-1",
            "prev_log_index": -1,
            "prev_log_term": 0,
            "entries": [
                {"index": 0, "term": 1, "command": "put", "data": {"k": "v"}, "timestamp": time.time()},
            ],
            "leader_commit": -1,
        })
        assert resp["success"] is True
        assert len(engine._logs) == 1
        assert engine._logs[0].command == "put"
        assert engine._logs[0].data == {"k": "v"}
        engine.stop()


def test_handle_append_entries_prev_log_index_out_of_range():
    """prev_log_index 超出本地日志范围 → 拒绝"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        resp = engine.handle_append_entries({
            "term": 1,
            "leader_id": "leader-1",
            "prev_log_index": 10,
            "prev_log_term": 0,
            "entries": [],
            "leader_commit": -1,
        })
        assert resp["success"] is False
        engine.stop()


def test_handle_append_entries_prev_log_term_mismatch():
    """prev_log_term 不匹配 → 拒绝"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine._logs = [LogEntry(index=0, term=1, command="old")]
        resp = engine.handle_append_entries({
            "term": 2,
            "leader_id": "leader-1",
            "prev_log_index": 0,
            "prev_log_term": 99,  # 不匹配
            "entries": [],
            "leader_commit": -1,
        })
        assert resp["success"] is False
        engine.stop()


def test_handle_append_entries_prev_log_term_match():
    """prev_log_term 匹配 → 成功"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._logs = [LogEntry(index=0, term=1, command="old")]
        resp = engine.handle_append_entries({
            "term": 2,
            "leader_id": "leader-1",
            "prev_log_index": 0,
            "prev_log_term": 1,  # 匹配
            "entries": [
                {"index": 1, "term": 2, "command": "new", "data": {}, "timestamp": time.time()},
            ],
            "leader_commit": -1,
        })
        assert resp["success"] is True
        assert len(engine._logs) == 2
        assert engine._logs[1].command == "new"
        engine.stop()


def test_handle_append_entries_leader_commit_advances():
    """leader_commit > commit_index → 提交本地日志"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._logs = [LogEntry(index=0, term=1, command="e0")]
        resp = engine.handle_append_entries({
            "term": 2,
            "leader_id": "leader-1",
            "prev_log_index": -1,
            "prev_log_term": 0,
            "entries": [],
            "leader_commit": 0,  # 提交索引 0
        })
        assert resp["success"] is True
        assert engine._commit_index == 0
        assert engine._logs[0].committed is True
        engine.stop()


def test_handle_append_entries_on_commit_callback():
    """提交时触发 on_commit 回调"""
    with tempfile.TemporaryDirectory() as tmpdir:
        committed = []
        engine = _make_engine(
            tmpdir,
            election_timeout=(10.0, 20.0),
            on_commit=lambda e: committed.append(e.command),
        )
        engine._logs = [LogEntry(index=0, term=1, command="e0")]
        resp = engine.handle_append_entries({
            "term": 2,
            "leader_id": "leader-1",
            "prev_log_index": -1,
            "prev_log_term": 0,
            "entries": [],
            "leader_commit": 0,
        })
        assert resp["success"] is True
        assert len(committed) == 1
        assert committed[0] == "e0"
        engine.stop()


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: handle_peer_status
# ═══════════════════════════════════════════════════════════

def test_handle_peer_status_update_healthy():
    """handle_peer_status() 更新 peer 为健康"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://h1:8000", healthy=False)
        engine = _make_engine(tmpdir, peers=[p1])
        engine.handle_peer_status("p1", True)
        assert engine.peers["p1"].healthy is True
        assert engine.peers["p1"].last_heartbeat > 0
        engine.stop()


def test_handle_peer_status_update_unhealthy():
    """handle_peer_status() 更新 peer 为不健康"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://h1:8000", healthy=True)
        engine = _make_engine(tmpdir, peers=[p1])
        engine.handle_peer_status("p1", False)
        assert engine.peers["p1"].healthy is False
        engine.stop()


def test_handle_peer_status_unknown_peer():
    """handle_peer_status() 对未知 peer 不报错"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine.handle_peer_status("ghost", True)  # 不应抛出异常
        engine.stop()


# ═══════════════════════════════════════════════════════════
# ConsensusEngine: 持久化
# ═══════════════════════════════════════════════════════════

def test_persistence_saves_state_file():
    """stop() 后 data_dir 中有持久化文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine.start()
        engine.stop()
        state_path = os.path.join(tmpdir, "test-node_state.json")
        assert os.path.isfile(state_path)
        with open(state_path, "r") as f:
            data = json.load(f)
        assert "current_term" in data
        assert "voted_for" in data
        assert "logs" in data


def test_persistence_loads_term():
    """从持久化文件恢复 current_term"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 先创建引擎并修改 term
        engine1 = _make_engine(tmpdir)
        engine1._current_term = 7
        engine1._save_persistent()
        engine1.stop()

        # 从同一 data_dir 创建新引擎，应恢复 term
        engine2 = _make_engine(tmpdir)
        assert engine2._current_term == 7
        engine2.stop()


def test_persistence_loads_voted_for():
    """从持久化文件恢复 voted_for"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine1 = _make_engine(tmpdir)
        engine1._voted_for = "candidate-42"
        engine1._save_persistent()
        engine1.stop()

        engine2 = _make_engine(tmpdir)
        assert engine2._voted_for == "candidate-42"
        engine2.stop()


def test_persistence_loads_logs():
    """从持久化文件恢复日志"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine1 = _make_engine(tmpdir)
        engine1._logs = [
            LogEntry(index=0, term=1, command="cmd_a", data={"x": 1}),
            LogEntry(index=1, term=1, command="cmd_b", committed=True),
        ]
        engine1._save_persistent()
        engine1.stop()

        engine2 = _make_engine(tmpdir)
        assert len(engine2._logs) == 2
        assert engine2._logs[0].command == "cmd_a"
        assert engine2._logs[0].data == {"x": 1}
        assert engine2._logs[1].command == "cmd_b"
        assert engine2._logs[1].committed is True
        engine2.stop()


def test_persistence_handles_missing_file():
    """data_dir 中无持久化文件时不报错"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        assert engine._current_term == 0
        assert engine._voted_for is None
        assert engine._logs == []
        engine.stop()


def test_persistence_handles_corrupted_file():
    """持久化文件损坏时不报错，使用默认值"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = os.path.join(tmpdir, "test-node_state.json")
        with open(state_path, "w") as f:
            f.write("not valid json {{{")
        engine = _make_engine(tmpdir)
        assert engine._current_term == 0
        engine.stop()


def test_persistence_truncates_logs():
    """持久化只保留最近 100 条日志"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine._logs = [
            LogEntry(index=i, term=1, command=f"cmd_{i}") for i in range(150)
        ]
        engine._save_persistent()

        engine2 = _make_engine(tmpdir)
        assert len(engine2._logs) == 100
        assert engine2._logs[0].command == "cmd_50"
        assert engine2._logs[-1].command == "cmd_149"
        engine2.stop()


# ═══════════════════════════════════════════════════════════
# 新增: _reset_election_timer
# ═══════════════════════════════════════════════════════════

def test_reset_election_timer_creates_timer():
    """_reset_election_timer 创建并启动选举计时器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        old_timer = engine._election_timer
        engine._reset_election_timer()
        assert engine._election_timer is not None
        assert isinstance(engine._election_timer, threading.Timer)
        assert engine._election_timer.daemon is True
        engine.stop()


def test_reset_election_timer_cancels_old_timer():
    """_reset_election_timer 取消旧计时器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._election_timer = threading.Timer(999, lambda: None)
        old_timer = engine._election_timer
        engine._reset_election_timer()
        assert engine._election_timer is not old_timer
        # 旧计时器应已被 cancel
        assert old_timer.is_alive() is False
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: _start_election
# ═══════════════════════════════════════════════════════════

def test_start_election_no_peers_becomes_leader():
    """无 peer 的单节点 _start_election 立即成为 Leader"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._running = True
        engine._start_election()
        assert engine._role == NodeRole.LEADER
        assert engine._leader_id == "test-node"
        assert engine._current_term == 1
        assert engine._voted_for == "test-node"
        engine.stop()


def test_start_election_increments_term():
    """_start_election 递增 current_term"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._running = True
        engine._current_term = 5
        engine._start_election()
        assert engine._current_term == 6
        engine.stop()


def test_start_election_not_running_returns_early():
    """_start_election 在 _running=False 时直接返回"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._running = False
        engine._start_election()
        assert engine._role == NodeRole.FOLLOWER
        assert engine._current_term == 0
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: _request_vote
# ═══════════════════════════════════════════════════════════

def test_request_vote_success():
    """_request_vote — mock urlopen 返回 vote_granted=True"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        peer = PeerConfig("p1", "http://peer1:8000")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"vote_granted": True}).encode("utf-8")

        with patch("tengod.consensus.urlopen", return_value=mock_resp):
            result = engine._request_vote(peer, term=1, last_log_index=0, last_log_term=0)
        assert result is True
        assert peer.healthy is True
        assert peer.last_heartbeat > 0
        engine.stop()


def test_request_vote_network_error():
    """_request_vote — mock urlopen 抛 URLError，peer 标记为 unhealthy"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        peer = PeerConfig("p1", "http://peer1:8000", healthy=True)

        with patch("tengod.consensus.urlopen", side_effect=URLError("unreachable")):
            result = engine._request_vote(peer, term=1, last_log_index=0, last_log_term=0)
        assert result is False
        assert peer.healthy is False
        engine.stop()


def test_request_vote_vote_not_granted():
    """_request_vote — peer 返回 vote_granted=False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        peer = PeerConfig("p1", "http://peer1:8000")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"vote_granted": False}).encode("utf-8")

        with patch("tengod.consensus.urlopen", return_value=mock_resp):
            result = engine._request_vote(peer, term=1, last_log_index=0, last_log_term=0)
        assert result is False
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: _become_leader
# ═══════════════════════════════════════════════════════════

def test_become_leader_initializes_indices():
    """_become_leader 初始化 next_index 和 match_index"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://p1:8000")
        p2 = PeerConfig("p2", "http://p2:8000")
        engine = _make_engine(tmpdir, peers=[p1, p2])
        engine._become_leader()
        assert engine._role == NodeRole.LEADER
        assert engine._leader_id == "test-node"
        # next_index 初始化为 last_idx + 1 = -1 + 1 = 0
        assert engine._next_index["p1"] == 0
        assert engine._next_index["p2"] == 0
        assert engine._next_index["test-node"] == 0
        # match_index 初始化为 -1
        assert engine._match_index["p1"] == -1
        assert engine._match_index["p2"] == -1
        engine.stop()


def test_become_leader_with_existing_leader():
    """_become_leader 传递旧 leader 给回调"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._leader_id = "old-leader-99"
        calls = []

        def cb(old: str, new: str):
            calls.append((old, new))

        engine.on_leader_change(cb)
        engine._become_leader()
        assert len(calls) == 1
        assert calls[0][0] == "old-leader-99"
        assert calls[0][1] == "test-node"
        engine.stop()


def test_become_leader_no_previous_leader():
    """_become_leader 无旧 leader 时回调收到空字符串"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._leader_id = None
        calls = []

        def cb(old: str, new: str):
            calls.append((old, new))

        engine.on_leader_change(cb)
        engine._become_leader()
        assert len(calls) == 1
        assert calls[0][0] == ""
        assert calls[0][1] == "test-node"
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: _send_append_entries
# ═══════════════════════════════════════════════════════════

def test_send_append_entries_with_entries():
    """_send_append_entries — mock urlopen，验证 payload 结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://p1:8000")
        engine = _make_engine(tmpdir, peers=[p1])
        engine._logs = [LogEntry(index=0, term=1, command="cmd0", data={"k": "v"})]
        engine._next_index["p1"] = 0
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode("utf-8")

        with patch("tengod.consensus.urlopen", return_value=mock_resp):
            engine._send_append_entries(p1, term=1, commit_index=-1)

        assert p1.healthy is True
        # next_index 应更新
        assert engine._next_index["p1"] == 1
        assert engine._match_index["p1"] == 0
        engine.stop()


def test_send_append_entries_network_error():
    """_send_append_entries — mock urlopen 抛 URLError，peer 标记为 unhealthy"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://p1:8000", healthy=True)
        engine = _make_engine(tmpdir, peers=[p1])

        with patch("tengod.consensus.urlopen", side_effect=URLError("unreachable")):
            engine._send_append_entries(p1, term=1, commit_index=-1)

        assert p1.healthy is False
        engine.stop()


def test_send_append_entries_no_entries():
    """_send_append_entries — 无新日志时的空心跳"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://p1:8000")
        engine = _make_engine(tmpdir, peers=[p1])
        engine._next_index["p1"] = 0
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode("utf-8")

        with patch("tengod.consensus.urlopen", return_value=mock_resp):
            engine._send_append_entries(p1, term=1, commit_index=-1)

        assert p1.healthy is True
        # 没有 entries，next_index 不变
        assert engine._next_index["p1"] == 0
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: _check_commit
# ═══════════════════════════════════════════════════════════

def test_check_commit_advances_commit_index():
    """_check_commit — 单节点多数派提交"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine._logs = [
            LogEntry(index=0, term=1, command="e0"),
            LogEntry(index=1, term=1, command="e1"),
        ]
        engine._commit_index = -1
        # 无 peer，quorum = (0+1)//2 + 1 = 1，Leader 自己算 1 票
        engine._check_commit()
        assert engine._commit_index == 1
        assert engine._logs[0].committed is True
        assert engine._logs[1].committed is True
        engine.stop()


def test_check_commit_with_on_commit_callback():
    """_check_commit — 触发 on_commit 回调"""
    with tempfile.TemporaryDirectory() as tmpdir:
        committed = []
        engine = _make_engine(
            tmpdir,
            on_commit=lambda e: committed.append(e.command),
        )
        engine._logs = [
            LogEntry(index=0, term=1, command="e0"),
            LogEntry(index=1, term=1, command="e1"),
        ]
        engine._commit_index = -1
        engine._check_commit()
        assert len(committed) == 2
        assert committed[0] == "e0"
        assert committed[1] == "e1"
        engine.stop()


def test_check_commit_quorum_with_peers():
    """_check_commit — 有 peer 时需达到多数派"""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = PeerConfig("p1", "http://p1:8000")
        p2 = PeerConfig("p2", "http://p2:8000")
        engine = _make_engine(tmpdir, peers=[p1, p2])
        engine._logs = [LogEntry(index=0, term=1, command="e0")]
        engine._commit_index = -1
        # quorum = (2+1)//2 + 1 = 2，Leader 1票，需 1 个 peer 也匹配
        # 无 peer 匹配 → 不提交
        engine._check_commit()
        assert engine._commit_index == -1
        assert engine._logs[0].committed is False

        # 设 p1 的 match_index >= 0 → 达到 quorum
        engine._match_index["p1"] = 0
        engine._check_commit()
        assert engine._commit_index == 0
        assert engine._logs[0].committed is True
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: handle_append_entries — gap filling / term mismatch
# ═══════════════════════════════════════════════════════════

def test_handle_append_entries_gap_filling():
    """handle_append_entries — prev_log_index 超出当前日志，创建间隙条目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        # 发送 entry index=3, prev_log_index=-1 (跳过 prev 检查)
        resp = engine.handle_append_entries({
            "term": 1,
            "leader_id": "leader-1",
            "prev_log_index": -1,
            "prev_log_term": 0,
            "entries": [
                {"index": 3, "term": 1, "command": "real", "data": {}, "timestamp": time.time()},
            ],
            "leader_commit": -1,
        })
        assert resp["success"] is True
        assert len(engine._logs) == 4
        # 间隙条目
        assert engine._logs[0].command == "__gap__"
        assert engine._logs[0].term == 0
        assert engine._logs[1].command == "__gap__"
        assert engine._logs[2].command == "__gap__"
        assert engine._logs[3].command == "real"
        assert engine._logs[3].term == 1
        engine.stop()


def test_handle_append_entries_term_mismatch_truncation():
    """handle_append_entries — 已有条目 term 不匹配时截断日志"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._logs = [
            LogEntry(index=0, term=1, command="old0"),
            LogEntry(index=1, term=1, command="old1"),
            LogEntry(index=2, term=1, command="old2"),
        ]
        # 发送 entry index=1 但 term=99（不匹配），prev_log_index=0
        resp = engine.handle_append_entries({
            "term": 2,
            "leader_id": "leader-1",
            "prev_log_index": 0,
            "prev_log_term": 1,  # 匹配
            "entries": [
                {"index": 1, "term": 99, "command": "new1", "data": {}, "timestamp": time.time()},
            ],
            "leader_commit": -1,
        })
        assert resp["success"] is True
        # 日志被截断到 index 0，然后追加新条目
        assert len(engine._logs) == 2
        assert engine._logs[0].command == "old0"
        assert engine._logs[1].command == "new1"
        assert engine._logs[1].term == 99
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: handle_vote_request — log_ok 逻辑
# ═══════════════════════════════════════════════════════════

def test_handle_vote_request_log_ok_better_term():
    """handle_vote_request — 候选人 last_log_term 更高 → log_ok=True"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._current_term = 3
        engine._logs = [LogEntry(index=0, term=1, command="x")]
        # 候选人 last_log_term=5 > 我们的 last_log_term=1
        resp = engine.handle_vote_request({
            "term": 4,
            "candidate_id": "c1",
            "last_log_index": 0,
            "last_log_term": 5,
        })
        assert resp["vote_granted"] is True
        engine.stop()


def test_handle_vote_request_log_ok_same_term_more_entries():
    """handle_vote_request — 相同 term 但候选人日志更多 → log_ok=True"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._current_term = 3
        engine._logs = [LogEntry(index=0, term=2, command="x")]
        # 候选人 last_log_term=2 (相同), last_log_index=5 >= 我们的 0
        resp = engine.handle_vote_request({
            "term": 4,
            "candidate_id": "c1",
            "last_log_index": 5,
            "last_log_term": 2,
        })
        assert resp["vote_granted"] is True
        engine.stop()


def test_handle_vote_request_log_not_ok_lower_term():
    """handle_vote_request — 候选人 last_log_term 更低 → log_ok=False → 拒绝"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._current_term = 3
        engine._logs = [LogEntry(index=0, term=5, command="x")]
        # 候选人 last_log_term=2 < 我们的 last_log_term=5
        resp = engine.handle_vote_request({
            "term": 4,
            "candidate_id": "c1",
            "last_log_index": 10,
            "last_log_term": 2,
        })
        assert resp["vote_granted"] is False
        engine.stop()


def test_handle_vote_request_log_not_ok_same_term_less_entries():
    """handle_vote_request — 相同 term 但候选人日志更少 → log_ok=False → 拒绝"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._current_term = 3
        engine._logs = [
            LogEntry(index=0, term=2, command="x"),
            LogEntry(index=1, term=2, command="y"),
        ]
        # 候选人 last_log_term=2 (相同), last_log_index=0 < 我们的 last_log_index=1
        resp = engine.handle_vote_request({
            "term": 4,
            "candidate_id": "c1",
            "last_log_index": 0,
            "last_log_term": 2,
        })
        assert resp["vote_granted"] is False
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: _save_persistent / _load_persistent 边界
# ═══════════════════════════════════════════════════════════

def test_save_persistent_empty_logs():
    """_save_persistent 空日志 → 文件包含 logs: []"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine._current_term = 3
        engine._voted_for = "c1"
        engine._logs = []
        engine._save_persistent()
        state_path = os.path.join(tmpdir, "test-node_state.json")
        with open(state_path, "r") as f:
            data = json.load(f)
        assert data["current_term"] == 3
        assert data["voted_for"] == "c1"
        assert data["logs"] == []
        engine.stop()


def test_load_persistent_missing_fields():
    """_load_persistent — 部分 JSON 字段缺失时使用默认值"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = os.path.join(tmpdir, "test-node_state.json")
        # 只写 current_term，不写 voted_for 和 logs
        with open(state_path, "w") as f:
            json.dump({"current_term": 5}, f)
        engine = _make_engine(tmpdir)
        assert engine._current_term == 5
        assert engine._voted_for is None
        assert engine._logs == []
        engine.stop()


def test_load_persistent_empty_logs_list():
    """_load_persistent — 恢复时 logs 为空列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = os.path.join(tmpdir, "test-node_state.json")
        with open(state_path, "w") as f:
            json.dump({"current_term": 2, "voted_for": "x", "logs": []}, f)
        engine = _make_engine(tmpdir)
        assert engine._current_term == 2
        assert engine._voted_for == "x"
        assert engine._logs == []
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: query / propose 边界
# ═══════════════════════════════════════════════════════════

def test_query_after_start_uptime():
    """query() — start 后 uptime > 0"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine.start()
        state = engine.query()
        assert state.uptime > 0
        engine.stop()


def test_propose_with_data_none():
    """propose() — data=None 时默认为空 dict"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        engine._running = True
        engine._start_election()  # 单节点，立即成为 Leader
        assert engine._role == NodeRole.LEADER
        result = engine.propose("test_cmd")  # data=None
        assert result is True
        assert engine._logs[0].data == {}
        engine.stop()


def test_propose_not_leader_multiple():
    """propose() — Follower 多次调用均返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        for i in range(3):
            assert engine.propose(f"cmd_{i}") is False
        assert engine._logs == []
        engine.stop()


# ═══════════════════════════════════════════════════════════
# 新增: handle_append_entries 重置选举计时器
# ═══════════════════════════════════════════════════════════

def test_handle_append_entries_resets_election_timer():
    """handle_append_entries — 收到有效心跳时重置选举计时器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir, election_timeout=(10.0, 20.0))
        # 用 patch.object 验证 _reset_election_timer 被调用
        with patch.object(engine, "_reset_election_timer") as mock_reset:
            resp = engine.handle_append_entries({
                "term": 1,
                "leader_id": "leader-1",
                "prev_log_index": -1,
                "prev_log_term": 0,
                "entries": [],
                "leader_commit": -1,
            })
            assert resp["success"] is True
            mock_reset.assert_called_once()
        engine.stop()


def test_handle_append_entries_no_reset_on_term_less():
    """handle_append_entries — term < current_term 时不重置计时器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = _make_engine(tmpdir)
        engine._current_term = 5
        with patch.object(engine, "_reset_election_timer") as mock_reset:
            resp = engine.handle_append_entries({
                "term": 3,
                "leader_id": "leader-1",
                "prev_log_index": -1,
                "prev_log_term": 0,
                "entries": [],
                "leader_commit": -1,
            })
            assert resp["success"] is False
            mock_reset.assert_not_called()
        engine.stop()