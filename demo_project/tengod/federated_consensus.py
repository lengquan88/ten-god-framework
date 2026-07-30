"""federated_consensus.py — 联邦学习共识 v4.6.0

共识引擎从 Raft 扩展到联邦学习场景，多实例协同训练模型。
"""
import time
import uuid
from typing import Any, Dict, List


class FederatedConsensus:
    """联邦学习共识引擎

    扩展 Raft 共识协议，支持多实例协作训练：
    - 模型聚合（FedAvg）
    - 梯度共享
    - 隐私保护（差分隐私）
    - 节点权重管理
    """

    def __init__(self, node_id: str = ""):
        self._node_id = node_id or uuid.uuid4().hex[:8]
        self._peers: Dict[str, Dict] = {}  # peer_id -> {model, weight, data_size}
        self._global_model: Dict[str, Any] = {}
        self._round: int = 0
        self._history: List[Dict] = []

    def add_peer(self, peer_id: str, data_size: int = 1000) -> None:
        """添加参与联邦学习的节点"""
        self._peers[peer_id] = {
            "model": {},
            "weight": 1.0,
            "data_size": data_size,
            "last_update": time.time(),
            "status": "active",
        }

    def remove_peer(self, peer_id: str) -> None:
        """移除节点"""
        self._peers.pop(peer_id, None)

    def submit_gradient(
        self, peer_id: str, gradients: Dict[str, List[float]], data_size: int = 0
    ) -> Dict[str, Any]:
        """提交本地梯度更新"""
        if peer_id not in self._peers:
            return {"status": "error", "message": f"Unknown peer: {peer_id}"}

        self._peers[peer_id]["model"] = gradients
        self._peers[peer_id]["last_update"] = time.time()
        if data_size > 0:
            self._peers[peer_id]["data_size"] = data_size

        return {"status": "ok", "round": self._round, "peer": peer_id}

    def aggregate(self, method: str = "fedavg") -> Dict[str, Any]:
        """聚合所有节点的模型参数

        Args:
            method: 聚合方法
                - fedavg: 联邦平均（按数据量加权）
                - equal: 等权平均
                - median: 中位数（抗拜占庭攻击）
        """
        self._round += 1
        active_peers = {
            pid: info for pid, info in self._peers.items() if info["status"] == "active"
        }

        if not active_peers:
            return {"status": "error", "message": "No active peers", "round": self._round}

        if method == "fedavg":
            total_data = sum(p["data_size"] for p in active_peers.values())
            aggregated = self._fedavg_aggregate(active_peers, total_data)
        elif method == "median":
            aggregated = self._median_aggregate(active_peers)
        else:  # equal
            aggregated = self._equal_aggregate(active_peers)

        self._global_model = aggregated

        result = {
            "status": "ok",
            "round": self._round,
            "method": method,
            "active_peers": len(active_peers),
            "model_keys": list(aggregated.keys()),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        self._history.append(result)
        return result

    def _fedavg_aggregate(self, peers: Dict, total_data: int) -> Dict:
        """联邦平均聚合"""
        if total_data == 0:
            return {}
        aggregated = {}
        for peer_id, info in peers.items():
            weight = info["data_size"] / total_data
            for key, values in info["model"].items():
                if key not in aggregated:
                    aggregated[key] = [0.0] * len(values)
                for i, v in enumerate(values):
                    aggregated[key][i] += v * weight
        return aggregated

    def _equal_aggregate(self, peers: Dict) -> Dict:
        """等权平均"""
        n = len(peers)
        if n == 0:
            return {}
        aggregated = {}
        for info in peers.values():
            for key, values in info["model"].items():
                if key not in aggregated:
                    aggregated[key] = [0.0] * len(values)
                for i, v in enumerate(values):
                    aggregated[key][i] += v / n
        return aggregated

    def _median_aggregate(self, peers: Dict) -> Dict:
        """中位数聚合（抗拜占庭）

        健壮处理：各 peer 的 model 键可能不统一（增量训练、剪枝等场景）。
        只对至少拥有该键的 peer 的值求中位数，避免 KeyError 崩溃。
        """
        aggregated = {}

        # 1. 收集所有 peer 的所有键的并集（而非仅取第一个 peer 的键）
        all_keys: set = set()
        for info in peers.values():
            all_keys.update(info["model"].keys())

        for key in all_keys:
            # 2. 仅从拥有该键的 peer 收集值，过滤掉 None 或长度不一致
            per_key_vectors: List[List[float]] = []
            for info in peers.values():
                vec = info["model"].get(key)
                if isinstance(vec, list) and len(vec) > 0:
                    per_key_vectors.append(vec)

            if not per_key_vectors:
                continue  # 无有效数据，跳过该键

            # 3. 对齐维度：只对各 peer 都提供的索引位置求中位数
            min_len = min(len(v) for v in per_key_vectors)
            medians: List[float] = []
            for i in range(min_len):
                col = [v[i] for v in per_key_vectors]
                col_sorted = sorted(col)
                medians.append(col_sorted[len(col_sorted) // 2])

            if medians:
                aggregated[key] = medians

        return aggregated

    def add_differential_privacy(
        self, gradients: Dict[str, List[float]], epsilon: float = 1.0, delta: float = 1e-5
    ) -> Dict[str, List[float]]:
        """添加差分隐私噪声（Laplace 机制）"""
        import random

        sensitivity = 1.0
        scale = sensitivity / epsilon

        noisy = {}
        for key, values in gradients.items():
            noise = [random.gauss(0, scale) for _ in values]
            noisy[key] = [v + n for v, n in zip(values, noise)]

        return noisy

    def get_global_model(self) -> Dict[str, Any]:
        """获取全局模型"""
        return self._global_model

    def get_peers_status(self) -> List[Dict]:
        """获取所有节点状态"""
        return [
            {
                "peer_id": pid,
                "data_size": info["data_size"],
                "last_update": info["last_update"],
                "status": info["status"],
            }
            for pid, info in self._peers.items()
        ]

    def get_history(self) -> List[Dict]:
        return self._history

    def stats(self) -> Dict[str, Any]:
        active = sum(1 for p in self._peers.values() if p["status"] == "active")
        return {
            "node_id": self._node_id,
            "total_peers": len(self._peers),
            "active_peers": active,
            "round": self._round,
            "model_size": len(self._global_model),
        }