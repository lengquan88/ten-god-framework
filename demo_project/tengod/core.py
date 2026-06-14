#!/usr/bin/env python3
"""
core.py — 十神核心调度器
整合十神子包，提供统一的高级 API：编排、生成、评估、调度一气呵成。
"""

import os
import sys
from typing import Any, Callable, Dict, List, Optional

# 确保 tengod 子模块可被发现
_TENGOD_ROOT = os.path.dirname(os.path.abspath(__file__))
# 把 tengod 目录自身也加入 path
if _TENGOD_ROOT not in sys.path:
    sys.path.insert(0, _TENGOD_ROOT)
for _subdir in os.listdir(_TENGOD_ROOT):
    _full = os.path.join(_TENGOD_ROOT, _subdir)
    if os.path.isdir(_full) and not _subdir.startswith(('.', '_')):
        if _full not in sys.path:
            sys.path.insert(0, _full)


def _safe_import(name: str):
    """安全导入子模块，失败时记录警告"""
    try:
        return __import__(name)
    except ImportError as e:
        print(f"[Warning] Failed to import {name}: {e}", file=sys.stderr)
        return None


class TenGodCore:
    """十神核心 — 统御十神之枢

    整合所有十神子模块，提供一键式的高阶能力组合。
    """

    def __init__(self, name: str = "tengod"):
        self.name = name

        # 懒加载各子模块（10 核心 + 2 扩展）
        _bijian = _safe_import("比肩_架构协同")
        _jiecai = _safe_import("劫财_攻防边界")
        _shishen = _safe_import("食神_创生输出")
        _shangguan = _safe_import("伤官_破界创新")
        _zhengcai = _safe_import("正财_知识固化")
        _piancai = _safe_import("偏财_奇招演化")
        _zhengguan = _safe_import("正官_法度调度")
        _qisha = _safe_import("七杀_品质裁决")
        _zhengyin = _safe_import("正印_滋养守护")
        _pianyin = _safe_import("偏印_桥接通变")
        _yuanchen = _safe_import("元辰_本源定位")
        _taichi = _safe_import("太极_阴阳调和")

        self.registry = _bijian.get_registry() if _bijian else None
        self.guard = _jiecai.Guard() if _jiecai else None
        self.generator = _shishen.ContentGenerator(name=f"{name}_generator") if _shishen else None
        self.innovator = _shangguan.Innovator() if _shangguan else None
        self.kb = _zhengcai.KnowledgeBase() if _zhengcai else None
        self.scheduler = _zhengguan.TaskScheduler(max_workers=4) if _zhengguan else None
        self.judge = _qisha.QualityJudge() if _qisha else None
        self.test_runner = _qisha.TestRunner(verbose=False) if _qisha else None
        self.config = _zhengyin.ConfigManager() if _zhengyin else None
        self.bridge = _pianyin.BridgeRegistry() if _pianyin else None
        self.locator = _yuanchen.YuanChenLocator() if _yuanchen else None
        self.balancer = _taichi.TaiChiBalancer() if _taichi else None

        # 保存权限枚举
        self.Permission = _jiecai.Permission if _jiecai else None
        self.OutputFormat = _shishen.OutputFormat if _shishen else None
        self.GenerationConfig = _shishen.GenerationConfig if _shishen else None
        self.TaskPriority = _zhengguan.TaskPriority if _zhengguan else None
        self.YinYang = _taichi.YinYang if _taichi else None

        if self.bridge and _pianyin:
            self.bridge.register_converter("json", _pianyin.DictToJsonConverter())

        self._setup_default_roles()
        self._setup_default_config()

    def _setup_default_roles(self) -> None:
        """配置默认角色"""
        if not self.guard or not self.Permission:
            return
        P = self.Permission
        self.guard.register_role(
            "admin",
            {P.READ, P.WRITE, P.DELETE, P.EXECUTE, P.ADMIN},
        )
        self.guard.register_role("user", {P.READ, P.EXECUTE})
        self.guard.register_role("guest", {P.READ})

    def _setup_default_config(self) -> None:
        """配置默认值"""
        if not self.config:
            return
        self.config.set_default("max_workers", 4)
        self.config.set_default("timeout", 30)
        self.config.set_default("cache_enabled", True)
        self.config.set_default("audit_enabled", True)

    def evaluate(
        self,
        items: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """质量裁决"""
        if not self.judge:
            return {"error": "judge unavailable"}
        self.judge.reset()
        weights = weights or {}
        for name, value in items.items():
            self.judge.add_score(name, value, weight=weights.get(name, 1.0))
        return self.judge.report()

    def innovate(
        self,
        method: str = "combine",
        *args: Any,
    ) -> Dict[str, Any]:
        """生成创意"""
        if not self.innovator:
            return {"error": "innovator unavailable"}
        if method == "combine" and len(args) >= 1:
            self.innovator.combine(list(args))
        elif method == "transfer" and len(args) == 2:
            self.innovator.transfer(args[0], args[1])
        elif method == "reverse" and len(args) == 1:
            self.innovator.reverse(args[0])
        return self.innovator.report()

    def generate(
        self,
        prompt: str,
        format: str = "text",
        style: str = "default",
    ) -> str:
        """生成内容"""
        if not self.generator or not self.OutputFormat or not self.GenerationConfig:
            return ""
        fmt_map = {
            "text": self.OutputFormat.TEXT,
            "markdown": self.OutputFormat.MARKDOWN,
            "md": self.OutputFormat.MARKDOWN,
            "json": self.OutputFormat.JSON,
            "html": self.OutputFormat.HTML,
        }
        config = self.GenerationConfig(
            format=fmt_map.get(format, self.OutputFormat.TEXT), style=style
        )
        return self.generator.generate(prompt, config)

    def schedule_and_run(
        self,
        tasks: Dict[str, Callable],
    ) -> Dict[str, Any]:
        """提交并执行一批任务"""
        if not self.scheduler:
            return {"error": "scheduler unavailable"}
        for task_id, func in tasks.items():
            self.scheduler.submit(task_id, func)
        self.scheduler.run_all()
        return self.scheduler.stats()

    def search(
        self,
        space: Dict[str, Any],
        objective: Callable[[Dict[str, Any]], float],
        n_trials: int = 20,
    ) -> Dict[str, Any]:
        """超参数搜索"""
        _piancai = _safe_import("偏财_奇招演化")
        if not _piancai:
            return {"error": "optimizer unavailable"}
        opt = _piancai.SearchOptimizer(_piancai.SearchSpace(space), mode="random")
        result = opt.optimize(objective, n_trials=n_trials, maximize=True)
        return {
            "best_params": result.best_params,
            "best_score": result.best_score,
            "iterations": result.iterations,
            "duration": round(result.duration, 3),
        }

    def locate_project(self) -> Dict[str, Any]:
        """元辰：项目根目录定位"""
        if not self.locator:
            return {"error": "locator unavailable"}
        self.locator.locate()
        return self.locator.summary()

    def balance_state(self, metrics: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """太极：阴阳调和状态"""
        if not self.balancer:
            return {"error": "balancer unavailable"}
        if metrics is not None:
            self.balancer.evaluate(metrics)
        stats = self.balancer.stats()
        stats["history"] = self.balancer.get_history(limit=5)
        return stats

    def set_balance_state(self, state: str, reason: str = "") -> Dict[str, Any]:
        """太极：设置阴阳状态"""
        if not self.balancer or not self.YinYang:
            return {"error": "balancer unavailable"}
        state_map = {
            "yin": self.YinYang.YIN,
            "yang": self.YinYang.YANG,
            "balanced": self.YinYang.BALANCED,
        }
        target = state_map.get(state)
        if target is None:
            return {"error": f"unknown state: {state}"}
        self.balancer.set_state(target, reason=reason)
        return self.balancer.stats()

    def export_state(self) -> Dict[str, Any]:
        """导出核心状态"""
        return {
            "name": self.name,
            "scheduler": self.scheduler.stats() if self.scheduler else None,
            "judge": self.judge.report() if self.judge else None,
            "config": self.config.list_with_source() if self.config else None,
            "knowledge": self.kb.stats() if self.kb else None,
            "registered_components": self.registry.list_all() if self.registry else [],
            "registered_adapters": self.bridge.list_adapters() if self.bridge else [],
            "registered_converters": self.bridge.list_converters() if self.bridge else [],
            "locator": self.locator.summary() if self.locator else None,
            "balancer": self.balancer.stats() if self.balancer else None,
        }


# 便捷全局实例
_default_core: Optional[TenGodCore] = None


def get_core() -> TenGodCore:
    """获取默认核心实例"""
    global _default_core
    if _default_core is None:
        _default_core = TenGodCore()
    return _default_core


__all__ = ["TenGodCore", "get_core"]
