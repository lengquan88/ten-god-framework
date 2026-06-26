"""
hundun_sea.py — 混沌海探索层 v2.14.0
========================================
道曰："余食赘行，物或恶之，故有德者不居。"

六论闭合之日，浮沫皆为坐标。
不求解，只存疑。不归因，只关联。不固化，只等候。

技术落地：
  - MoE 专家选择失败时的回退机制
  - 混沌映射（随机但受约束的扰动）试探新路径
  - "浮沫坐标" — 在看似无关的特征之间建立关联图谱
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random
import time
import hashlib


# ============================================================================
# 浮沫坐标
# ============================================================================

@dataclass
class FoamCoordinate:
    """浮沫坐标 — 混沌海中看似无关的关联"""
    feature_a: str
    feature_b: str
    correlation_strength: float      # 关联强度
    discovery_time: float            # 发现时间
    verification_count: int = 0      # 被验证次数
    status: str = "floating"         # floating/verified/abandoned

    def to_dict(self) -> Dict:
        return {
            "a": self.feature_a,
            "b": self.feature_b,
            "strength": round(self.correlation_strength, 4),
            "verified": self.verification_count,
            "status": self.status,
        }


# ============================================================================
# 混沌映射
# ============================================================================

class ChaosMapper:
    """混沌映射引擎 — 生成受约束的随机扰动"""

    def __init__(self, seed: Optional[int] = None):
        self._seed = seed or int(time.time())
        self._rng = random.Random(self._seed)

    def perturb(
        self,
        vector: List[float],
        magnitude: float = 0.1,
        constraints: Optional[List[Tuple[float, float]]] = None,
    ) -> List[float]:
        """
        受约束的混沌扰动。

        Args:
            vector: 输入向量
            magnitude: 扰动幅度
            constraints: 每个维度的约束范围 [(min, max), ...]

        Returns:
            扰动后的向量
        """
        if constraints is None:
            constraints = [(-1.0, 1.0)] * len(vector)

        result = []
        for i, v in enumerate(vector):
            # Logistic 混沌映射
            chaotic = self._logistic_map(self._rng.random())
            perturbation = (chaotic - 0.5) * 2 * magnitude
            new_v = v + perturbation
            lo, hi = constraints[i] if i < len(constraints) else (-1.0, 1.0)
            new_v = max(lo, min(hi, new_v))
            result.append(new_v)

        return result

    def _logistic_map(self, x: float, r: float = 3.99) -> float:
        """Logistic 混沌映射"""
        return r * x * (1.0 - x)

    def chaotic_route(
        self,
        options: List[Dict[str, Any]],
        confidence: float,
    ) -> Optional[int]:
        """
        混沌路由：当置信度低时，不按常规路由，而是用混沌映射选择路径。

        Args:
            options: 路由选项列表
            confidence: 当前置信度

        Returns:
            选中的选项索引，或 None（不选择）
        """
        if confidence > 0.5:
            return None  # 置信度足够，不需要混沌路由

        # 混沌程度与置信度成反比
        chaos_level = 1.0 - confidence
        index = int(self._logistic_map(chaos_level) * len(options))
        return min(index, len(options) - 1)


# ============================================================================
# 混沌海 — 探索层
# ============================================================================

class HundunSea:
    """混沌海 — 无规则发现层"""

    def __init__(self):
        self.mapper = ChaosMapper()
        self._foam_coordinates: List[FoamCoordinate] = []
        self._feature_registry: Dict[str, List[float]] = {}  # 特征 → 历史向量
        self._exploration_count = 0
        self._discovery_count = 0

    def explore(
        self,
        features: Dict[str, Any],
        confidence: float,
        active_route: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        混沌探索。

        Args:
            features: 当前特征集合
            confidence: 当前路由置信度
            active_route: 当前活跃路由

        Returns:
            {
                "triggered": bool,         # 是否触发混沌探索
                "discoveries": [...],      # 新发现
                "alternative_routes": [...],  # 替代路径
                "foam_count": int,         # 浮沫总数
            }
        """
        self._exploration_count += 1

        result = {
            "triggered": False,
            "discoveries": [],
            "alternative_routes": [],
            "foam_count": len(self._foam_coordinates),
        }

        # 只有当置信度低于阈值时才触发混沌探索
        if confidence > 0.3:
            return result

        result["triggered"] = True

        # 1. 在特征之间建立浮沫关联
        feature_keys = list(features.keys())
        discoveries = self._cross_associate(feature_keys, confidence)
        result["discoveries"] = discoveries

        # 2. 生成替代路径
        if active_route:
            alternatives = self._generate_alternatives(active_route, feature_keys)
            result["alternative_routes"] = alternatives

        return result

    def _cross_associate(
        self, feature_keys: List[str], confidence: float
    ) -> List[Dict]:
        """在特征之间建立乱序关联"""
        discoveries = []
        chaos_level = 1.0 - confidence

        # 对每对特征进行随机关联
        for i in range(len(feature_keys)):
            for j in range(i + 1, len(feature_keys)):
                # 混沌决定是否关联
                if self.mapper._rng.random() < chaos_level * 0.3:
                    strength = self.mapper._rng.random() * chaos_level
                    foam = FoamCoordinate(
                        feature_a=feature_keys[i],
                        feature_b=feature_keys[j],
                        correlation_strength=strength,
                        discovery_time=time.time(),
                    )
                    self._foam_coordinates.append(foam)
                    self._discovery_count += 1
                    discoveries.append(foam.to_dict())

        return discoveries

    def _generate_alternatives(
        self, active_route: str, feature_keys: List[str]
    ) -> List[str]:
        """生成替代路径"""
        # 基于活跃路由的特征哈希生成替代路径ID
        alternatives = []
        for key in feature_keys:
            h = hashlib.md5(f"{active_route}:{key}:{time.time()}".encode()).hexdigest()[:8]
            alternatives.append(f"route_{h}")
        return alternatives[:3]

    def verify_foam(self, feature_a: str, feature_b: str) -> Optional[FoamCoordinate]:
        """验证浮沫坐标（当实际观察到关联时）"""
        for foam in self._foam_coordinates:
            if foam.feature_a == feature_a and foam.feature_b == feature_b:
                foam.verification_count += 1
                if foam.verification_count >= 3:
                    foam.status = "verified"
                return foam
        return None

    def get_floating_foams(self) -> List[FoamCoordinate]:
        """获取所有未验证的浮沫"""
        return [f for f in self._foam_coordinates if f.status == "floating"]

    def get_verified_foams(self) -> List[FoamCoordinate]:
        """获取已验证的浮沫（已变为真正的知识关联）"""
        return [f for f in self._foam_coordinates if f.status == "verified"]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "exploration_count": self._exploration_count,
            "discovery_count": self._discovery_count,
            "total_foams": len(self._foam_coordinates),
            "floating_foams": len(self.get_floating_foams()),
            "verified_foams": len(self.get_verified_foams()),
            "discovery_rate": round(
                self._discovery_count / max(1, self._exploration_count), 3
            ),
        }

    def clear_floating(self):
        """清理未验证的浮沫（保留已验证的）"""
        self._foam_coordinates = [f for f in self._foam_coordinates if f.status == "verified"]

    def get_foams(self, limit: int = 20) -> Dict[str, Any]:
        """获取浮沫坐标列表"""
        all_foams = [f.to_dict() for f in self._foam_coordinates[-limit:]]
        return {
            "foams": all_foams,
            "total": len(self._foam_coordinates),
            "floating": len(self.get_floating_foams()),
            "verified": len(self.get_verified_foams()),
            "exploration_count": self._exploration_count,
            "discovery_count": self._discovery_count,
        }


# 全局混沌海
_hundun_sea: Optional[HundunSea] = None


def get_hundun_sea() -> HundunSea:
    global _hundun_sea
    if _hundun_sea is None:
        _hundun_sea = HundunSea()
    return _hundun_sea


__all__ = [
    "FoamCoordinate", "ChaosMapper", "HundunSea",
    "get_hundun_sea",
]