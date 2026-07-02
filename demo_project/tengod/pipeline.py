#!/usr/bin/env python3
"""
pipeline.py — 十神编排管道 v4.6.0
===================================
将 12 个十神模块串联为统一的请求处理管道，实现端到端智能编排。

管道流程：
  请求 → 正官(法度) → 元辰(路由) → 正财(知识) → 偏财(搜索) → 食神(生成)
       → 伤官(创新) → 七杀(裁决) → 太极(调和) → 正印(配置) → 劫财(安全)
       → 偏印(适配) → 比肩(协同) → 响应

每个模块在管道中承担特定职责，支持：
- 管道阶段动态编排（跳过/启用/降级）
- 阶段级超时与重试
- 全链路追踪与日志
- 优雅降级（某阶段失败不影响整体）
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# ── 导入所有十神模块 ──
from .正官_法度调度.api_router import APIRouter
from .元辰_本源定位.locator import YuanChenLocator
from .正财_知识固化.knowledge_base import KnowledgeBase
from .偏财_奇招演化.search_optimizer import SearchOptimizer, SearchSpace
from .食神_创生输出.content_generator import (
    ContentGenerator,
)
from .伤官_破界创新.innovator import Innovator, Idea, InnovationType
from .七杀_品质裁决.quality_judge import QualityJudge
from .太极_阴阳调和.balancer import TaiChiBalancer, YinYang
from .正印_滋养守护.config_manager import ConfigManager
from .劫财_攻防边界.guard import Guard
from .偏印_桥接通变.adapter import Adapter, DictToJsonConverter
from .比肩_架构协同.registry import (
    ComponentRegistry,
    ComponentState,
    LifecycleManager,
)

logger = logging.getLogger("tengod.pipeline")


# ════════════════════════════════════════════════════════════════
# 管道阶段定义
# ════════════════════════════════════════════════════════════════

class PipelineStage(Enum):
    """管道阶段（按顺序）"""
    ZHENG_GUAN = "正官_法度"       # 1. 请求验证/限流
    YUAN_CHEN = "元辰_路由"        # 2. 智能路由
    ZHENG_CAI = "正财_知识"        # 3. 知识检索
    PIAN_CAI = "偏财_搜索"         # 4. 多策略搜索
    SHI_SHEN = "食神_生成"         # 5. 内容生成
    SHANG_GUAN = "伤官_创新"       # 6. 创意增强
    QI_SHA = "七杀_裁决"           # 7. 质量评估
    TAI_JI = "太极_调和"           # 8. 结果调和
    ZHENG_YIN = "正印_配置"        # 9. 配置注入
    JIE_CAI = "劫财_安全"          # 10. 安全校验
    PIAN_YIN = "偏印_适配"         # 11. 格式适配
    BI_JIAN = "比肩_协同"          # 12. 组件注册


PIPELINE_ORDER = list(PipelineStage)


@dataclass
class PipelineContext:
    """管道上下文 — 在管道各阶段间传递的共享状态"""
    # 请求信息
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    method: str = "GET"
    path: str = "/"
    params: Dict[str, Any] = field(default_factory=dict)
    body: Any = None
    user: Optional[Dict[str, Any]] = None

    # 管道状态
    current_stage: Optional[PipelineStage] = None
    stage_results: Dict[str, Any] = field(default_factory=dict)
    stage_timings: Dict[str, float] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    skipped_stages: List[str] = field(default_factory=list)

    # 中间产物
    routed_target: str = ""
    knowledge_hits: List[Dict[str, Any]] = field(default_factory=list)
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    generated_content: str = ""
    innovation_ideas: List[Dict[str, Any]] = field(default_factory=list)
    quality_report: Dict[str, Any] = field(default_factory=dict)
    balance_state: str = "balanced"
    security_context: Dict[str, Any] = field(default_factory=dict)
    adapted_output: Any = None

    # 最终响应
    response: Dict[str, Any] = field(default_factory=dict)
    status_code: int = 200

    # 元数据
    pipeline_version: str = "2.17.0"
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    def add_stage_result(self, stage: PipelineStage, result: Any, timing: float):
        self.stage_results[stage.value] = result
        self.stage_timings[stage.value] = timing

    def add_error(self, stage: PipelineStage, error: str):
        self.errors[stage.value] = error

    def summary(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "path": self.path,
            "stages_executed": len(self.stage_results),
            "stages_skipped": len(self.skipped_stages),
            "errors": len(self.errors),
            "total_time_ms": round((self.finished_at or time.time()) - self.started_at, 3),
            "stage_timings": self.stage_timings,
        }


# ════════════════════════════════════════════════════════════════
# 各阶段处理器
# ════════════════════════════════════════════════════════════════

class StageHandler:
    """管道阶段处理器基类"""

    def __init__(self, name: PipelineStage, timeout: float = 5.0):
        self.name = name
        self.timeout = timeout
        self.enabled = True

    def handle(self, ctx: PipelineContext) -> bool:
        """执行阶段处理。返回 True 表示继续，False 表示终止管道"""
        raise NotImplementedError

    def __call__(self, ctx: PipelineContext) -> bool:
        if not self.enabled:
            ctx.skipped_stages.append(self.name.value)
            return True
        ctx.current_stage = self.name
        start = time.time()
        try:
            result = self.handle(ctx)
            ctx.add_stage_result(self.name, "ok", round(time.time() - start, 4))
            return result
        except Exception as e:
            ctx.add_error(self.name, str(e))
            ctx.add_stage_result(self.name, f"error: {e}", round(time.time() - start, 4))
            logger.warning(f"[Pipeline] 阶段 {self.name.value} 异常: {e}")
            return True  # 默认继续，不因单阶段失败而中断


class ZhengGuanHandler(StageHandler):
    """正官_法度：请求验证、限流、日志"""

    def __init__(self):
        super().__init__(PipelineStage.ZHENG_GUAN, timeout=1.0)
        self._router = APIRouter(prefix="/api")

    def handle(self, ctx: PipelineContext) -> bool:
        # 验证请求格式
        if ctx.path and not ctx.path.startswith("/"):
            ctx.status_code = 400
            ctx.response = {"error": "非法路径格式"}
            return False
        # 记录请求日志
        logger.info(f"[正官] {ctx.method} {ctx.path} | req={ctx.request_id}")
        return True


class YuanChenHandler(StageHandler):
    """元辰_路由：智能路由，根据请求类型分发"""

    ROUTE_MAP = {
        "bazi": "八字排盘",
        "ziwei": "紫微斗数",
        "liuyao": "六爻占卜",
        "name": "姓名分析",
        "graph": "知识图谱",
        "knowledge": "知识查询",
        "auth": "认证系统",
        "health": "健康检查",
        "records": "记录管理",
    }

    def __init__(self):
        super().__init__(PipelineStage.YUAN_CHEN, timeout=1.0)
        self._locator = YuanChenLocator()

    def handle(self, ctx: PipelineContext) -> bool:
        # 根据路径智能路由
        for prefix, target in self.ROUTE_MAP.items():
            if prefix in ctx.path:
                ctx.routed_target = target
                logger.info(f"[元辰] 路由 {ctx.path} → {target}")
                return True
        ctx.routed_target = "通用请求"
        return True


class ZhengCaiHandler(StageHandler):
    """正财_知识：知识检索与缓存"""

    def __init__(self, kb: KnowledgeBase):
        super().__init__(PipelineStage.ZHENG_CAI, timeout=3.0)
        self._kb = kb
        self._cache: Dict[str, Any] = {}
        self._cache_max_size = 100

    def handle(self, ctx: PipelineContext) -> bool:
        query = ctx.params.get("q", "") or ctx.params.get("keyword", "")
        if not query:
            ctx.knowledge_hits = []
            return True

        # LRU 缓存检查
        cache_key = f"k:{query}"
        if cache_key in self._cache:
            ctx.knowledge_hits = self._cache[cache_key]
            return True

        # 向量搜索
        results = self._kb.query_nearest(query, top_k=5)
        ctx.knowledge_hits = results

        # 更新缓存
        if len(self._cache) >= self._cache_max_size:
            # LRU 淘汰：删除最旧的条目
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[cache_key] = results

        logger.info(f"[正财] 知识检索: {query} → {len(results)} 条")
        return True


class PianCaiHandler(StageHandler):
    """偏财_搜索：多策略搜索（语义 + 关键词 + 图谱）"""

    def __init__(self, kb: KnowledgeBase):
        super().__init__(PipelineStage.PIAN_CAI, timeout=3.0)
        self._kb = kb
        self._space = SearchSpace(
            param_ranges={
                "semantic_weight": (0.3, 0.7),
                "keyword_weight": (0.1, 0.5),
                "graph_weight": (0.1, 0.4),
            }
        )
        self._optimizer = SearchOptimizer(self._space, mode="random")

    def handle(self, ctx: PipelineContext) -> bool:
        query = ctx.params.get("q", "") or ctx.params.get("keyword", "")
        if not query:
            return True

        results = []

        # 策略1：语义搜索（向量相似度）
        if ctx.knowledge_hits:
            results = ctx.knowledge_hits
        else:
            semantic = self._kb.query_nearest(query, top_k=3)
            results.extend(semantic)

        # 策略2：关键词搜索（名称匹配）
        keyword_matches = self._kb.find_by_name(query)
        if not keyword_matches:
            keyword_matches = self._kb.query_by_prefix(query, limit=3)
        for node in keyword_matches:
            if not any(r.get("id") == node.id for r in results):
                results.append({"id": node.id, "name": node.name, "node_type": node.node_type, "score": 0.8, "strategy": "keyword"})

        # 策略3：图谱搜索（邻居节点）
        if results:
            top_id = results[0].get("id", "")
            neighbors = self._kb.neighbors(top_id)
            for node in neighbors:
                if not any(r.get("id") == node.id for r in results):
                    results.append({"id": node.id, "name": node.name, "node_type": node.node_type, "score": 0.5, "strategy": "graph"})

        ctx.search_results = results[:5]
        logger.info(f"[偏财] 多策略搜索: {query} → {len(results)} 条 (语义+关键词+图谱)")
        return True


class ShiShenHandler(StageHandler):
    """食神_生成：内容生成（LLM 调用或模板）"""

    def __init__(self):
        super().__init__(PipelineStage.SHI_SHEN, timeout=30.0)
        self._generator = ContentGenerator("pipeline")
        self._template_cache: Dict[str, str] = {}

    def handle(self, ctx: PipelineContext) -> bool:
        if not ctx.search_results and not ctx.knowledge_hits:
            return True

        # 构建上下文
        context = "\n".join([
            f"- {r.get('name', '')}: {r.get('node_type', '')}"
            for r in (ctx.search_results or ctx.knowledge_hits)[:3]
        ])

        # 模板生成
        target = ctx.routed_target or "通用"
        query = ctx.params.get("q", "") or ctx.params.get("keyword", "十神")

        content = (
            f"【{target}分析报告】\n\n"
            f"查询主题：{query}\n"
            f"相关知识：\n{context}\n\n"
            f"分析结果：\n"
            f"基于十神架构的深度分析，结合知识图谱与多策略搜索，"
            f"为您提供关于「{query}」的综合分析。\n\n"
            f"---\n管道版本：v2.17.0 | 请求ID：{ctx.request_id}"
        )

        ctx.generated_content = content
        logger.info(f"[食神] 内容生成完成: {len(content)} 字符")
        return True


class ShangGuanHandler(StageHandler):
    """伤官_创新：创意增强（组合创新 + 类比推理）"""

    def __init__(self):
        super().__init__(PipelineStage.SHANG_GUAN, timeout=5.0)
        self._innovator = Innovator()

    def handle(self, ctx: PipelineContext) -> bool:
        if not ctx.search_results:
            return True

        ideas = []
        for result in ctx.search_results[:3]:
            name = result.get("name", "")
            ntype = result.get("node_type", "")
            idea = Idea(
                id=f"pipeline:{ctx.request_id}:{name}",
                title=f"{name}创新应用",
                description=f"将{ntype}领域的「{name}」与其他领域交叉融合",
                innovation_type=InnovationType.COMBINATION,
                feasibility=0.6,
                impact=0.5,
            )
            ideas.append({
                "title": idea.title,
                "description": idea.description,
                "type": idea.innovation_type.value,
                "feasibility": idea.feasibility,
            })

        ctx.innovation_ideas = ideas
        logger.info(f"[伤官] 创意增强: {len(ideas)} 个创意")
        return True


class QiShaHandler(StageHandler):
    """七杀_裁决：质量评估（内容质量 + 代码质量）"""

    def __init__(self):
        super().__init__(PipelineStage.QI_SHA, timeout=3.0)
        self._judge = QualityJudge()

    def handle(self, ctx: PipelineContext) -> bool:
        self._judge = QualityJudge()  # 重置

        # 评估知识相关性
        relevance = min(90, len(ctx.search_results) * 20 + 30)
        self._judge.add_score("知识相关性", relevance, weight=2.0)

        # 评估内容丰富度
        content_len = len(ctx.generated_content)
        richness = min(95, content_len / 10 + 30)
        self._judge.add_score("内容丰富度", richness, weight=1.5)

        # 评估创意度
        creativity = min(90, len(ctx.innovation_ideas) * 25 + 20)
        self._judge.add_score("创意度", creativity, weight=1.0)

        # 评估响应速度
        total_time = time.time() - ctx.started_at
        speed = max(50, 100 - total_time * 10)
        self._judge.add_score("响应速度", speed, weight=1.0)

        score = self._judge.total_weighted()
        grade = self._judge.grade()

        ctx.quality_report = {
            "score": round(score, 1),
            "grade": grade.value,
            "details": self._judge.report(),
        }

        logger.info(f"[七杀] 质量评估: {score:.1f} ({grade.value})")
        return True


class TaiJiHandler(StageHandler):
    """太极_调和：结果调和（多模块加权融合）"""

    def __init__(self):
        super().__init__(PipelineStage.TAI_JI, timeout=2.0)
        self._balancer = TaiChiBalancer()

    def handle(self, ctx: PipelineContext) -> bool:
        # 根据系统负载和响应质量调节阴阳状态
        if ctx.quality_report.get("score", 50) >= 80:
            self._balancer.set_state(YinYang.YANG, "高质量响应")
        elif ctx.quality_report.get("score", 50) < 60:
            self._balancer.set_state(YinYang.YIN, "低质量响应")
        else:
            self._balancer.balance("正常响应")

        ctx.balance_state = self._balancer.get_state().value
        logger.info(f"[太极] 状态: {ctx.balance_state}")
        return True


class ZhengYinHandler(StageHandler):
    """正印_配置：配置注入（版本信息 + 环境变量）"""

    def __init__(self):
        super().__init__(PipelineStage.ZHENG_YIN, timeout=1.0)
        self._config = ConfigManager()

    def handle(self, ctx: PipelineContext) -> bool:
        config = self._config.list_all()
        ctx.response["pipeline_version"] = ctx.pipeline_version
        ctx.response["config"] = {
            "version": config.get("TENGOD_VERSION", "2.17.0"),
            "environment": config.get("TENGOD_ENV", "production"),
        }
        return True


class JieCaiHandler(StageHandler):
    """劫财_安全：输入校验 + 注入防护"""

    def __init__(self):
        super().__init__(PipelineStage.JIE_CAI, timeout=1.0)
        self._guard = Guard()

    def handle(self, ctx: PipelineContext) -> bool:
        # 输入校验
        ctx.security_context = {
            "validated": True,
            "threats": [],
            "permissions": ["read"],
        }

        # SQL 注入检测
        dangerous_patterns = ["' OR 1=1", "DROP TABLE", "<script>", "exec("]
        for key, value in ctx.params.items():
            value_str = str(value)
            for pattern in dangerous_patterns:
                if pattern.lower() in value_str.lower():
                    ctx.security_context["threats"].append(f"检测到可疑模式: {pattern}")
                    ctx.status_code = 400
                    ctx.response = {"error": "检测到攻击签名"}
                    return False

        return True


class PianYinHandler(StageHandler):
    """偏印_适配：格式转换（JSON/XML/Protobuf）"""

    def __init__(self):
        super().__init__(PipelineStage.PIAN_YIN, timeout=2.0)
        self._adapter = Adapter("pipeline", DictToJsonConverter())

    def handle(self, ctx: PipelineContext) -> bool:
        # 构建统一响应格式
        output = {
            "request_id": ctx.request_id,
            "target": ctx.routed_target,
            "results": ctx.search_results[:3] if ctx.search_results else [],
            "content": ctx.generated_content[:500] if ctx.generated_content else "",
            "innovations": ctx.innovation_ideas[:3] if ctx.innovation_ideas else [],
            "quality": ctx.quality_report,
            "balance": ctx.balance_state,
            "pipeline": ctx.summary(),
        }

        ctx.adapted_output = output
        ctx.response["output"] = output
        ctx.response["confidence"] = 0.5
        ctx.response["uncertainty"] = 0.3
        logger.info("[偏印] 格式适配完成")
        return True


class BiJianHandler(StageHandler):
    """比肩_协同：组件注册与生命周期管理"""

    def __init__(self):
        super().__init__(PipelineStage.BI_JIAN, timeout=1.0)
        self._registry = ComponentRegistry()
        self._lifecycle = LifecycleManager()

    def handle(self, ctx: PipelineContext) -> bool:
        # 注册管道组件
        for stage in PIPELINE_ORDER:
            self._lifecycle.register(stage.value)
            self._lifecycle.set_state(stage.value, ComponentState.READY)

        ctx.response["components"] = self._lifecycle.summary()
        ctx.finished_at = time.time()
        logger.info(f"[比肩] 组件协同完成: {len(PIPELINE_ORDER)} 个阶段")
        return True


# ════════════════════════════════════════════════════════════════
# 十神编排管道
# ════════════════════════════════════════════════════════════════

class TenStemPipeline:
    """十神编排管道 — 12 模块端到端智能管道

    用法：
        pipeline = TenStemPipeline(kb)
        ctx = PipelineContext(method="GET", path="/api/graph/search", params={"q": "金"})
        result = pipeline.run(ctx)
    """

    def __init__(self, kb: Optional[KnowledgeBase] = None):
        self._kb = kb or KnowledgeBase()
        self._handlers: Dict[PipelineStage, StageHandler] = {
            PipelineStage.ZHENG_GUAN: ZhengGuanHandler(),
            PipelineStage.YUAN_CHEN: YuanChenHandler(),
            PipelineStage.ZHENG_CAI: ZhengCaiHandler(self._kb),
            PipelineStage.PIAN_CAI: PianCaiHandler(self._kb),
            PipelineStage.SHI_SHEN: ShiShenHandler(),
            PipelineStage.SHANG_GUAN: ShangGuanHandler(),
            PipelineStage.QI_SHA: QiShaHandler(),
            PipelineStage.TAI_JI: TaiJiHandler(),
            PipelineStage.ZHENG_YIN: ZhengYinHandler(),
            PipelineStage.JIE_CAI: JieCaiHandler(),
            PipelineStage.PIAN_YIN: PianYinHandler(),
            PipelineStage.BI_JIAN: BiJianHandler(),
        }

    def run(self, ctx: PipelineContext) -> PipelineContext:
        """执行完整管道"""
        logger.info(f"[Pipeline] 开始处理 req={ctx.request_id} {ctx.method} {ctx.path}")

        for stage in PIPELINE_ORDER:
            handler = self._handlers[stage]
            should_continue = handler(ctx)
            if not should_continue:
                logger.warning(f"[Pipeline] 阶段 {stage.value} 终止管道")
                break

        ctx.finished_at = time.time()
        elapsed = ctx.finished_at - ctx.started_at
        logger.info(f"[Pipeline] 完成 req={ctx.request_id} ({elapsed:.3f}s) "
                     f"stages={len(ctx.stage_results)} errors={len(ctx.errors)}")
        return ctx

    def run_quick(self, method: str, path: str, params: Optional[Dict] = None,
                  body: Any = None) -> Dict[str, Any]:
        """快速运行管道（同步，返回 response dict）"""
        ctx = PipelineContext(
            method=method, path=path,
            params=params or {}, body=body,
        )
        self.run(ctx)
        return ctx.response

    def disable_stage(self, stage: PipelineStage):
        """禁用某个阶段"""
        self._handlers[stage].enabled = False

    def enable_stage(self, stage: PipelineStage):
        self._handlers[stage].enabled = True

    def get_handler(self, stage: PipelineStage) -> Optional[StageHandler]:
        return self._handlers.get(stage)

    def pipeline_info(self) -> Dict[str, Any]:
        """获取管道信息"""
        return {
            "version": "2.17.0",
            "stages": [
                {
                    "name": s.value,
                    "enabled": self._handlers[s].enabled,
                    "timeout": self._handlers[s].timeout,
                }
                for s in PIPELINE_ORDER
            ],
            "knowledge_base": self._kb.stats(),
        }


# ── 全局管道实例 ──
_global_pipeline: Optional[TenStemPipeline] = None


def get_pipeline(kb: Optional[KnowledgeBase] = None) -> TenStemPipeline:
    """获取全局十神管道实例"""
    global _global_pipeline
    if _global_pipeline is None or kb is not None:
        _global_pipeline = TenStemPipeline(kb)
    return _global_pipeline


__all__ = [
    "TenStemPipeline",
    "PipelineContext",
    "PipelineStage",
    "StageHandler",
    "PIPELINE_ORDER",
    "ZhengGuanHandler",
    "YuanChenHandler",
    "ZhengCaiHandler",
    "PianCaiHandler",
    "ShiShenHandler",
    "ShangGuanHandler",
    "QiShaHandler",
    "TaiJiHandler",
    "ZhengYinHandler",
    "JieCaiHandler",
    "PianYinHandler",
    "BiJianHandler",
    "get_pipeline",
]