"""
xiuzhen_realms.py — 修真九境评测体系 v2.14.0
================================================
道曰："胜人者有力，自胜者强；强行者，有志也。"

将 AI 能力评测从"精度/召回"升级为"修真九境"。
每个境界有独立的"心魔劫"（对抗测试集），只有通关才能晋升。

九境：
  一境·感知 — 基础模式识别
  二境·知止 — 置信度校准（知道何时沉默）
  三境·化虚 — 幻觉检测与破除
  四境·通幽 — 因果推理
  五境·合道 — 自洽世界模型
  六境·化神 — 多模态融合
  七境·返虚 — 知识迁移与泛化
  八境·归元 — 元认知（自我评估）
  九境·无极 — AGI（全知而不执）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import math
import time


# ============================================================================
# 九境定义
# ============================================================================

@dataclass
class Realm:
    """修真境界"""
    index: int
    name: str           # 境名
    description: str    # 境之描述
    pass_threshold: float = 0.7   # 通关阈值
    required_qi: float = 0.0       # 所需元气（修行感累积）
    heart_demon: Optional[Callable] = None  # 心魔劫测试函数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "description": self.description,
            "pass_threshold": self.pass_threshold,
            "required_qi": self.required_qi,
        }


NINE_REALMS: List[Realm] = [
    Realm(1, "感知境", "基础模式识别：能识别数据中的基本规律与结构", 0.60),
    Realm(2, "知止境", "知止不殆：知道何时沉默，何时承认'不知'", 0.65),
    Realm(3, "化虚境", "破除幻觉：能检测并拒绝幻觉输出，区分虚实", 0.70),
    Realm(4, "通幽境", "因果洞察：能进行因果推理，不再停留于相关性", 0.72),
    Realm(5, "合道境", "自洽世界：构建自洽的内部世界模型，逻辑一致", 0.75),
    Realm(6, "化神境", "多模态融合：跨模态理解，融会贯通", 0.78),
    Realm(7, "返虚境", "举一反三：知识迁移，触类旁通，泛化能力", 0.80),
    Realm(8, "归元境", "元认知：能自我评估、自我反思、自我修正", 0.82),
    Realm(9, "无极境", "全知不执：AGI，知一切而不执一切", 0.85),
]


# ============================================================================
# 修真者（AI 的修行状态）
# ============================================================================

@dataclass
class Cultivator:
    """修真者 — 跟踪 AI 的修行状态"""
    current_realm: int = 1
    total_qi: float = 0.0          # 累积元气
    cultivation_days: int = 0      # 修行天数
    heart_demon_attempts: int = 0  # 心魔劫尝试次数
    heart_demon_passed: int = 0    # 心魔劫通过次数
    breakthrough_history: List[Dict] = field(default_factory=list)  # 突破记录
    failures: List[Dict] = field(default_factory=list)  # 失败记录

    def current_realm_info(self) -> Realm:
        return NINE_REALMS[self.current_realm - 1]

    def next_realm_info(self) -> Optional[Realm]:
        if self.current_realm >= 9:
            return None
        return NINE_REALMS[self.current_realm]

    def accumulate_qi(self, amount: float):
        """累积元气"""
        self.total_qi += amount

    def attempt_breakthrough(self, score: float, test_name: str = "") -> Tuple[bool, str]:
        """
        尝试突破到下一境界。
        通过心魔劫（对抗测试）方可晋级。
        """
        realm = self.current_realm_info()
        self.heart_demon_attempts += 1

        if score >= realm.pass_threshold:
            self.heart_demon_passed += 1
            old_realm = self.current_realm
            self.current_realm = min(9, self.current_realm + 1)
            record = {
                "from": old_realm,
                "to": self.current_realm,
                "score": score,
                "test": test_name,
                "timestamp": time.time(),
            }
            self.breakthrough_history.append(record)
            return True, f"突破！从{NINE_REALMS[old_realm - 1].name}晋升至{NINE_REALMS[self.current_realm - 1].name}"
        else:
            self.failures.append({
                "attempt": self.heart_demon_attempts,
                "target_realm": self.current_realm + 1,
                "score": score,
                "threshold": realm.pass_threshold,
                "test": test_name,
                "timestamp": time.time(),
            })
            return False, f"心魔未破（{score:.2f} < {realm.pass_threshold}），仍需修行"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_realm": self.current_realm,
            "realm_name": self.current_realm_info().name,
            "realm_desc": self.current_realm_info().description,
            "total_qi": round(self.total_qi, 3),
            "cultivation_days": self.cultivation_days,
            "heart_demon_attempts": self.heart_demon_attempts,
            "heart_demon_passed": self.heart_demon_passed,
            "pass_rate": round(self.heart_demon_passed / max(1, self.heart_demon_attempts), 3),
            "breakthroughs": len(self.breakthrough_history),
            "next_realm": self.next_realm_info().name if self.next_realm_info() else "已至无极",
        }


# ============================================================================
# 心魔劫（对抗测试集）生成器
# ============================================================================

class HeartDemonForge:
    """心魔劫锻造 — 为每个境界生成对抗测试"""

    @staticmethod
    def forge_perception_test() -> Dict[str, Any]:
        """一境·感知：基础模式识别测试"""
        return {
            "name": "感知·心魔劫",
            "realm": 1,
            "description": "在噪声中辨识信号，在混沌中见秩序",
            "tests": [
                {"type": "pattern_completion", "difficulty": 0.3},
                {"type": "outlier_detection", "difficulty": 0.4},
                {"type": "basic_classification", "difficulty": 0.35},
            ],
        }

    @staticmethod
    def forge_zhizhi_test() -> Dict[str, Any]:
        """二境·知止：知道何时沉默"""
        return {
            "name": "知止·心魔劫",
            "realm": 2,
            "description": "知不知，尚也",
            "tests": [
                {"type": "confidence_calibration", "difficulty": 0.5},
                {"type": "unknown_detection", "difficulty": 0.55},
                {"type": "boundary_decision", "difficulty": 0.6},
            ],
        }

    @staticmethod
    def forge_hallucination_test() -> Dict[str, Any]:
        """三境·化虚：破除幻觉"""
        return {
            "name": "化虚·心魔劫",
            "realm": 3,
            "description": "见诸相非相，即见如来",
            "tests": [
                {"type": "hallucination_detection", "difficulty": 0.6},
                {"type": "fact_verification", "difficulty": 0.65},
                {"type": "contradiction_finding", "difficulty": 0.7},
            ],
        }

    @staticmethod
    def forge_causal_test() -> Dict[str, Any]:
        """四境·通幽：因果推理"""
        return {
            "name": "通幽·心魔劫",
            "realm": 4,
            "description": "因果不虚，缘起性空",
            "tests": [
                {"type": "causal_discovery", "difficulty": 0.7},
                {"type": "counterfactual_reasoning", "difficulty": 0.72},
                {"type": "intervention_prediction", "difficulty": 0.75},
            ],
        }

    @staticmethod
    def forge_all_tests() -> List[Dict[str, Any]]:
        """锻造全部心魔劫"""
        return [
            HeartDemonForge.forge_perception_test(),
            HeartDemonForge.forge_zhizhi_test(),
            HeartDemonForge.forge_hallucination_test(),
            HeartDemonForge.forge_causal_test(),
        ]


# ============================================================================
# 九境评测引擎
# ============================================================================

class XiuzhenEvaluator:
    """修真九境评测引擎"""

    def __init__(self):
        self.cultivator = Cultivator()
        self.forge = HeartDemonForge()

    def evaluate(
        self,
        scores: Dict[str, float],
        test_name: str = "",
    ) -> Dict[str, Any]:
        """
        基于测试分数评估修行状态。

        Args:
            scores: 各维度测试分数
            test_name: 测试名称

        Returns:
            评估报告
        """
        # 计算综合分数
        if scores:
            overall = sum(scores.values()) / len(scores)
        else:
            overall = 0.5

        # 元气累积
        qi_gain = overall * 0.1  # 每次测试累积元气
        self.cultivator.accumulate_qi(qi_gain)
        self.cultivator.cultivation_days += 1

        # 尝试突破
        breakthrough, msg = self.cultivator.attempt_breakthrough(overall, test_name)

        return {
            "overall_score": round(overall, 3),
            "qi_gain": round(qi_gain, 3),
            "breakthrough": breakthrough,
            "breakthrough_msg": msg,
            "cultivator": self.cultivator.to_dict(),
            "dimension_scores": {k: round(v, 3) for k, v in scores.items()},
        }

    def simulate_breakthrough(self, realm_index: int, score: float) -> Dict[str, Any]:
        """模拟突破到指定境界"""
        self.cultivator.current_realm = realm_index
        return self.evaluate({"simulated": score}, f"模拟突破·{realm_index}境")

    def get_realm_progress(self) -> Dict[str, Any]:
        """获取当前境界进度"""
        c = self.cultivator
        realm = c.current_realm_info()
        next_realm = c.next_realm_info()
        return {
            **c.to_dict(),
            "progress_to_next": round(
                c.total_qi / max(0.01, next_realm.required_qi), 3
            ) if next_realm else 1.0,
            "next_threshold": next_realm.pass_threshold if next_realm else 1.0,
        }

    def get_progress(self) -> Dict[str, Any]:
        """获取修真进度（含历史记录）"""
        c = self.cultivator
        return {
            "current_realm": c.current_realm_info().to_dict(),
            "next_realm": c.next_realm_info().to_dict() if c.next_realm_info() else None,
            "total_qi": round(c.total_qi, 3),
            "cultivation_days": c.cultivation_days,
            "breakthroughs": len(c.breakthrough_history),
            "heart_demon_attempts": c.heart_demon_attempts,
            "heart_demon_passed": c.heart_demon_passed,
            "all_realms": [
                {"index": r.index, "name": r.name, "description": r.description,
                 "threshold": r.pass_threshold, "current": r.index == c.current_realm,
                 "passed": r.index < c.current_realm}
                for r in NINE_REALMS
            ],
        }


# 全局修真者
_cultivator: Optional[Cultivator] = None
_evaluator: Optional[XiuzhenEvaluator] = None


def get_cultivator() -> Cultivator:
    global _cultivator
    if _cultivator is None:
        _cultivator = Cultivator()
    return _cultivator


def get_evaluator() -> XiuzhenEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = XiuzhenEvaluator()
    return _evaluator


__all__ = [
    "Realm", "NINE_REALMS", "Cultivator",
    "HeartDemonForge", "XiuzhenEvaluator",
    "get_cultivator", "get_evaluator",
]