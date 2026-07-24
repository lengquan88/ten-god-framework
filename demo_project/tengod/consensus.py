#!/usr/bin/env python3
"""
consensus.py — 十神多实例共识引擎 v4.6.0
===========================================
Raft-inspired 分布式共识协议：
- Leader 选举（基于心跳/任期）
- 日志复制（AppendEntries）
- 状态机：Follower → Candidate → Leader
- 多数派确认（Quorum）
- HTTP-based peer 通信

用法：
    from consensus import ConsensusEngine, PeerConfig

    engine = ConsensusEngine(
        node_id="tengod-1",
        peers=[
            PeerConfig("tengod-2", "http://192.168.1.2:8000"),
            PeerConfig("tengod-3", "http://192.168.1.3:8000"),
        ],
        listen_port=8000,
    )
    engine.start()
"""

import json
import os
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ── 数据模型 ────────────────────────────────────────────


class NodeRole(Enum):
    """节点角色"""

    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class PeerConfig:
    """对等节点配置"""

    node_id: str
    address: str  # http://host:port
    healthy: bool = True
    last_heartbeat: float = 0.0


@dataclass
class LogEntry:
    """共识日志条目"""

    index: int
    term: int
    command: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    committed: bool = False


@dataclass
class ConsensusState:
    """共识状态快照"""

    node_id: str
    role: str
    current_term: int
    voted_for: Optional[str]
    commit_index: int
    last_applied: int
    peer_count: int
    healthy_peers: int
    log_count: int
    uptime: float


# ── 共识引擎 ────────────────────────────────────────────


class ConsensusEngine:
    """Raft-inspired 分布式共识引擎

    Args:
        node_id: 本节点 ID
        peers: 对等节点配置列表
        listen_port: 本节点监听端口
        election_timeout: 选举超时范围 (min, max) 秒
        heartbeat_interval: 心跳间隔秒数
        data_dir: 持久化目录
        on_commit: 日志提交回调
    """

    def __init__(
        self,
        node_id: str,
        peers: List[PeerConfig],
        listen_port: int = 8000,
        election_timeout: Tuple[float, float] = (5.0, 10.0),
        heartbeat_interval: float = 2.0,
        data_dir: str = "./data/consensus",
        on_commit: Optional[Callable[[LogEntry], None]] = None,
    ):
        self.node_id = node_id
        self.peers: Dict[str, PeerConfig] = {p.node_id: p for p in peers}
        self.listen_port = listen_port
        self._election_timeout = election_timeout
        self._heartbeat_interval = heartbeat_interval
        self._data_dir = data_dir
        self._on_commit = on_commit

        # 持久化状态
        self._current_term: int = 0
        self._voted_for: Optional[str] = None
        self._logs: List[LogEntry] = []

        # 易失状态
        self._role: NodeRole = NodeRole.FOLLOWER
        self._leader_id: Optional[str] = None
        self._commit_index: int = -1
        self._last_applied: int = -1

        # Leader 状态
        self._next_index: Dict[str, int] = {}
        self._match_index: Dict[str, int] = {}

        # 运行时
        self._running = False
        self._lock = threading.RLock()
        self._election_timer: Optional[threading.Timer] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._start_time: float = 0.0

        # 回调
        self._on_leader_change: List[Callable[[str, str], None]] = []  # (old, new)

        os.makedirs(self._data_dir, exist_ok=True)
        self._load_persistent()

    def _load_persistent(self) -> None:
        """加载持久化状态"""
        path = os.path.join(self._data_dir, f"{self.node_id}_state.json")
        try:
            with open(path, "r") as f:
                data = json.load(f)
                self._current_term = data.get("current_term", 0)
                self._voted_for = data.get("voted_for")
                logs = data.get("logs", [])
                self._logs = [LogEntry(**e) for e in logs]
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_persistent(self) -> None:
        """持久化状态"""
        path = os.path.join(self._data_dir, f"{self.node_id}_state.json")
        with self._lock:
            data = {
                "current_term": self._current_term,
                "voted_for": self._voted_for,
                "logs": [
                    {
                        "index": e.index,
                        "term": e.term,
                        "command": e.command,
                        "data": e.data,
                        "timestamp": e.timestamp,
                        "committed": e.committed,
                    }
                    for e in self._logs[-100:]
                ],  # 保留最近 100 条
            }
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 公共 API ────────────────────────────────────────

    def start(self) -> None:
        """启动共识引擎"""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._start_time = time.time()

        self._reset_election_timer()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()

    def stop(self) -> None:
        """停止共识引擎"""
        with self._lock:
            self._running = False
            self._role = NodeRole.FOLLOWER
        if self._election_timer:
            self._election_timer.cancel()
        self._save_persistent()

    def propose(self, command: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """提议一个操作（仅 Leader 可提议）"""
        with self._lock:
            if self._role != NodeRole.LEADER:
                return False
            entry = LogEntry(
                index=len(self._logs),
                term=self._current_term,
                command=command,
                data=data or {},
            )
            self._logs.append(entry)
            self._match_index[self.node_id] = entry.index
            self._next_index[self.node_id] = entry.index + 1
        self._save_persistent()
        return True

    def query(self) -> ConsensusState:
        """查询共识状态"""
        with self._lock:
            healthy = sum(1 for p in self.peers.values() if p.healthy)
            return ConsensusState(
                node_id=self.node_id,
                role=self._role.value,
                current_term=self._current_term,
                voted_for=self._voted_for,
                commit_index=self._commit_index,
                last_applied=self._last_applied,
                peer_count=len(self.peers),
                healthy_peers=healthy,
                log_count=len(self._logs),
                uptime=time.time() - self._start_time,
            )

    def on_leader_change(self, callback: Callable[[str, str], None]) -> None:
        """注册 Leader 变更回调"""
        self._on_leader_change.append(callback)

    # ── Leader 选举 ─────────────────────────────────────

    def _reset_election_timer(self) -> None:
        """重置选举计时器"""
        if self._election_timer:
            self._election_timer.cancel()
        timeout = random.uniform(*self._election_timeout)
        self._election_timer = threading.Timer(timeout, self._start_election)
        self._election_timer.daemon = True
        self._election_timer.start()

    def _start_election(self) -> None:
        """开始选举"""
        with self._lock:
            if not self._running:
                return
            self._role = NodeRole.CANDIDATE
            self._current_term += 1
            self._voted_for = self.node_id
            self._leader_id = None
            current_term = self._current_term
            last_log_index = len(self._logs) - 1
            last_log_term = self._logs[last_log_index].term if self._logs else 0

        self._save_persistent()

        # 请求投票
        votes = 1  # 自己一票
        for peer in list(self.peers.values()):
            granted = self._request_vote(
                peer, current_term, last_log_index, last_log_term
            )
            if granted:
                votes += 1

        quorum = (len(self.peers) + 1) // 2 + 1
        if votes >= quorum:
            self._become_leader()
        else:
            self._reset_election_timer()

    def _request_vote(
        self, peer: PeerConfig, term: int, last_log_index: int, last_log_term: int
    ) -> bool:
        """向对等节点请求投票"""
        try:
            data = json.dumps(
                {
                    "term": term,
                    "candidate_id": self.node_id,
                    "last_log_index": last_log_index,
                    "last_log_term": last_log_term,
                }
            ).encode("utf-8")
            req = Request(
                f"{peer.address}/api/consensus/vote",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urlopen(req, timeout=3)
            result = json.loads(resp.read().decode("utf-8"))
            peer.healthy = True
            peer.last_heartbeat = time.time()
            return result.get("vote_granted", False)
        except (URLError, HTTPError, Exception):
            peer.healthy = False
            return False

    def _become_leader(self) -> None:
        """成为 Leader"""
        old_leader = self._leader_id
        with self._lock:
            self._role = NodeRole.LEADER
            self._leader_id = self.node_id
            # 初始化 Leader 状态
            last_idx = len(self._logs) - 1
            for pid in self.peers:
                self._next_index[pid] = last_idx + 1
                self._match_index[pid] = -1
            self._next_index[self.node_id] = last_idx + 1

        # 触发回调
        for cb in self._on_leader_change:
            try:
                cb(old_leader or "", self.node_id)
            except Exception:
                pass

    # ── 心跳循环 ────────────────────────────────────────

    def _heartbeat_loop(self) -> None:
        """Leader 心跳循环"""
        while self._running:
            with self._lock:
                is_leader = self._role == NodeRole.LEADER
            if is_leader:
                self._send_heartbeats()
            time.sleep(self._heartbeat_interval)

    def _send_heartbeats(self) -> None:
        """发送心跳和日志复制"""
        with self._lock:
            current_term = self._current_term
            commit_index = self._commit_index

        for peer in list(self.peers.values()):
            self._send_append_entries(peer, current_term, commit_index)

        # 检查是否达到多数派提交
        self._check_commit()

    def _send_append_entries(
        self, peer: PeerConfig, term: int, commit_index: int
    ) -> None:
        """发送 AppendEntries RPC"""
        with self._lock:
            prev_log_index = self._next_index.get(peer.node_id, 0) - 1
            prev_log_term = (
                self._logs[prev_log_index].term
                if prev_log_index >= 0 and self._logs
                else 0
            )
            entries = self._logs[prev_log_index + 1 : prev_log_index + 1 + 10]

        try:
            payload = {
                "term": term,
                "leader_id": self.node_id,
                "prev_log_index": prev_log_index,
                "prev_log_term": prev_log_term,
                "entries": [
                    {
                        "index": e.index,
                        "term": e.term,
                        "command": e.command,
                        "data": e.data,
                        "timestamp": e.timestamp,
                    }
                    for e in entries
                ],
                "leader_commit": commit_index,
            }
            data = json.dumps(payload).encode("utf-8")
            req = Request(
                f"{peer.address}/api/consensus/append",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urlopen(req, timeout=3)
            result = json.loads(resp.read().decode("utf-8"))
            peer.healthy = True
            peer.last_heartbeat = time.time()

            if result.get("success"):
                with self._lock:
                    if entries:
                        self._next_index[peer.node_id] = entries[-1].index + 1
                        self._match_index[peer.node_id] = entries[-1].index
        except (URLError, HTTPError, Exception):
            peer.healthy = False

    def _check_commit(self) -> None:
        """检查多数派提交"""
        with self._lock:
            for idx in range(self._commit_index + 1, len(self._logs)):
                count = 1  # Leader
                for pid, match_idx in self._match_index.items():
                    if match_idx >= idx:
                        count += 1
                quorum = (len(self.peers) + 1) // 2 + 1
                if count >= quorum:
                    self._logs[idx].committed = True
                    self._commit_index = idx
                    if self._on_commit:
                        self._on_commit(self._logs[idx])

    # ── RPC 处理 ────────────────────────────────────────

    def handle_vote_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理投票请求"""
        term = data.get("term", 0)
        candidate_id = data.get("candidate_id", "")
        last_log_index = data.get("last_log_index", -1)
        last_log_term = data.get("last_log_term", 0)

        with self._lock:
            if term < self._current_term:
                return {"term": self._current_term, "vote_granted": False}

            if term > self._current_term:
                self._current_term = term
                self._role = NodeRole.FOLLOWER
                self._voted_for = None
                self._leader_id = None

            # 日志至少一样新
            log_ok = False
            my_last_idx = len(self._logs) - 1
            my_last_term = self._logs[my_last_idx].term if self._logs else 0
            if last_log_term > my_last_term or (
                last_log_term == my_last_term and last_log_index >= my_last_idx
            ):
                log_ok = True

            if (self._voted_for is None or self._voted_for == candidate_id) and log_ok:
                self._voted_for = candidate_id
                self._reset_election_timer()
                self._save_persistent()
                return {"term": self._current_term, "vote_granted": True}

            return {"term": self._current_term, "vote_granted": False}

    def handle_append_entries(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理 AppendEntries RPC"""
        term = data.get("term", 0)
        leader_id = data.get("leader_id", "")
        prev_log_index = data.get("prev_log_index", -1)
        prev_log_term = data.get("prev_log_term", 0)
        entries = data.get("entries", [])
        leader_commit = data.get("leader_commit", -1)

        with self._lock:
            if term < self._current_term:
                return {"term": self._current_term, "success": False}

            # 收到有效 Leader 心跳
            self._current_term = term
            self._role = NodeRole.FOLLOWER
            self._leader_id = leader_id
            self._reset_election_timer()

            # 检查日志一致性
            if prev_log_index >= 0:
                if prev_log_index >= len(self._logs):
                    return {"term": self._current_term, "success": False}
                if (
                    prev_log_index >= 0
                    and self._logs[prev_log_index].term != prev_log_term
                ):
                    return {"term": self._current_term, "success": False}

            # 追加日志
            for entry_data in entries:
                idx = entry_data["index"]
                if idx < len(self._logs):
                    if self._logs[idx].term != entry_data["term"]:
                        self._logs = self._logs[:idx]
                        self._logs.append(LogEntry(**entry_data))
                else:
                    # 补齐间隙
                    while len(self._logs) <= idx:
                        self._logs.append(
                            LogEntry(
                                index=len(self._logs),
                                term=0,
                                command="__gap__",
                            )
                        )
                    self._logs[idx] = LogEntry(**entry_data)

            # 更新提交索引
            if leader_commit > self._commit_index:
                old_commit = self._commit_index
                self._commit_index = min(leader_commit, len(self._logs) - 1)
                # 应用新提交的日志
                for i in range(old_commit + 1, self._commit_index + 1):
                    if self._logs[i].committed:
                        continue
                    self._logs[i].committed = True
                    if self._on_commit:
                        self._on_commit(self._logs[i])

            self._save_persistent()
            return {"term": self._current_term, "success": True}

    def handle_peer_status(self, peer_id: str, healthy: bool) -> None:
        """更新对等节点状态"""
        peer = self.peers.get(peer_id)
        if peer:
            peer.healthy = healthy
            peer.last_heartbeat = time.time()
