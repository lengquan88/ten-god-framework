"""
共识模块 (consensus.py) 测试套件
=================================
覆盖: NodeRole, PeerConfig, LogEntry, ConsensusState, ConsensusEngine
"""

import json
import os
import tempfile
import time
from pathlib import Path

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