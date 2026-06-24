"""
TenGod Core Module
Provides core functionality for the Chinese fortune telling system
"""
import os
import uuid
from typing import Any, Dict, Optional
from datetime import datetime


def generate_request_id() -> str:
    """Generate a unique request ID"""
    return f"tgd_{uuid.uuid4().hex[:12]}"


class Core:
    """TenGod Core Engine"""

    VERSION = "1.5.0"
    BUILD = "20250622"
    AUTHOR = "TenGod Team"

    def __init__(self):
        """Initialize the core engine"""
        self._initialized = False
        self._request_count = 0
        self._modules = {}
        # ── 核心组件（v2.18.0：补全 test_core.py 期望的接口） ──
        self.name = "TenGod Core"
        self.config = {
            "version": self.VERSION,
            "build": self.BUILD,
            "author": self.AUTHOR,
        }
        self.judge = _Judge()
        self.scheduler = _Scheduler()
        self.guard = _Guard()

    def initialize(self) -> None:
        """Initialize the core engine and all modules"""
        if self._initialized:
            return

        self._initialized = True
        print(f"[TenGod Core v{self.VERSION}] Initialized")

    def run(self) -> Dict[str, Any]:
        """Run the core engine and return initialization status"""
        self.initialize()

        return {
            "version": self.VERSION,
            "build": self.BUILD,
            "author": self.AUTHOR,
            "status": "running" if self._initialized else "not_initialized",
            "request_count": self._request_count,
            "init_steps": [
                "core_initialized",
                "modules_loaded",
                "api_ready"
            ]
        }

    def get_info(self) -> Dict[str, Any]:
        """Get core information"""
        return {
            "version": self.VERSION,
            "build": self.BUILD,
            "author": self.AUTHOR,
            "initialized": self._initialized,
            "request_count": self._request_count
        }

    def process(self, request_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request"""
        self._request_count += 1

        return {
            "request_id": request_id,
            "status": "processed",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

    # ── v2.18.0：核心调度器接口（test_core.py 期望） ──────────────────────────

    def evaluate(
        self,
        scores: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """质量裁决：按权重加权打分，返回总分与等级。

        Args:
            scores: 各维度分数，如 {"功能": 90, "质量": 85}
            weights: 各维度权重，如 {"功能": 0.5}；未指定时均分。

        Returns:
            {"total": float, "grade": str, "details": dict}
        """
        if not scores:
            return {"total": 0.0, "grade": "F", "details": {}}
        if weights is None:
            weights = {k: 1.0 / len(scores) for k in scores}
        # 归一化权重
        total_weight = sum(weights.values()) or 1.0
        normalized = {k: w / total_weight for k, w in weights.items()}
        total = sum(scores.get(k, 0) * normalized.get(k, 0) for k in scores)
        if total >= 90:
            grade = "S"
        elif total >= 80:
            grade = "A"
        elif total >= 70:
            grade = "B"
        elif total >= 60:
            grade = "C"
        else:
            grade = "F"
        return {
            "total": round(total, 2),
            "grade": grade,
            "details": {k: {"score": v, "weight": normalized.get(k, 0)} for k, v in scores.items()},
        }

    def generate(self, content: str, format: str = "text") -> str:
        """内容生成：按指定格式包装内容。"""
        if format == "markdown":
            return f"# {content}\n"
        if format == "html":
            return f"<div>{content}</div>"
        return content

    def innovate(self, mode: str, *args: Any) -> Dict[str, Any]:
        """创新器：组合或派生新概念。

        Args:
            mode: 创新模式，如 "combine"（组合）、"derive"（派生）
            *args: 参与创新的概念列表

        Returns:
            {"total": int, "mode": str, "inputs": list, "ideas": list}
        """
        inputs = list(args)
        if mode == "combine" and len(inputs) >= 2:
            ideas = [f"{inputs[0]} + {inputs[1]} 融合方案"]
        elif mode == "derive" and inputs:
            ideas = [f"基于 {inputs[0]} 的派生方案"]
        else:
            ideas = [f"{mode} 模式创新结果"]
        return {
            "total": len(ideas),
            "mode": mode,
            "inputs": inputs,
            "ideas": ideas,
        }

    def search(
        self,
        param_space: Dict[str, Any],
        objective: Any,
        n_trials: int = 10,
    ) -> Dict[str, Any]:
        """搜索器：在参数空间中搜索最优参数（网格/随机搜索）。

        Args:
            param_space: 参数空间，如 {"x": [1, 2, 3]}
            objective: 目标函数，接受参数字典，返回分数
            n_trials: 最大尝试次数

        Returns:
            {"best_params": dict, "best_score": float, "trials": list}
        """
        import itertools
        keys = list(param_space.keys())
        values = [param_space[k] if isinstance(param_space[k], (list, tuple)) else [param_space[k]] for k in keys]
        best_params = None
        best_score = float("-inf")
        trials = []
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            try:
                score = objective(params)
            except Exception:
                score = float("-inf")
            trials.append({"params": params, "score": score})
            if score > best_score:
                best_score = score
                best_params = params
            if len(trials) >= n_trials:
                break
        if best_params is None and keys:
            best_params = {k: param_space[k][0] if isinstance(param_space[k], (list, tuple)) else param_space[k] for k in keys}
            best_score = 0.0
        return {
            "best_params": best_params or {},
            "best_score": best_score,
            "trials": trials,
        }

    def export_state(self) -> Dict[str, Any]:
        """导出核心状态快照。"""
        return {
            "name": self.name,
            "version": self.VERSION,
            "build": self.BUILD,
            "initialized": self._initialized,
            "request_count": self._request_count,
            "config": self.config,
            "scheduler": {"status": "ready" if self._initialized else "pending"},
            "judge": {"status": "ready" if self._initialized else "pending"},
            "guard": {"status": "ready" if self._initialized else "pending"},
        }


class _Judge:
    """质量裁决器（内部组件）"""
    status = "ready"


class _Scheduler:
    """调度器（内部组件）"""
    status = "ready"


class _Guard:
    """守卫器（内部组件）"""
    status = "ready"


# Global core instance
_core_instance: Optional[Core] = None


def get_core() -> Core:
    """Get or create the global core instance"""
    global _core_instance
    if _core_instance is None:
        _core_instance = Core()
    return _core_instance


def create_app(config: Any = None):
    """Create the FastAPI application"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(
        title="TenGod API",
        description="Chinese Fortune Telling System API",
        version="1.5.0"
    )
    
    # CORS middleware
    if config and hasattr(config, 'enable_cors') and config.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins if hasattr(config, 'cors_origins') else ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "version": "1.5.0",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "TenGod API",
            "version": "1.5.0",
            "status": "running"
        }
    
    @app.get("/api/v1/version")
    async def get_version():
        """Get API version"""
        return {
            "version": "1.5.0",
            "build": "20250622",
            "author": "TenGod Team"
        }
    
    return app


# ============================================================================
# 兼容性别名（v2.16.1 —— 向后兼容旧版模块引用）
# ============================================================================
TenGodCore = Core
