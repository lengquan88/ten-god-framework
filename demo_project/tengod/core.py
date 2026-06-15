#!/usr/bin/env python3
"""
core.py — 十神核心调度器 v1.3.0
整合十神子包，提供统一的高级 API：编排、生成、评估、调度一气呵成。
"""

import os
import sys
import time
import uuid
import json
import traceback
import threading
from contextvars import ContextVar, copy_context
from typing import Any, Callable, Dict, List, Optional

# 请求ID追踪（线程安全）
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")

def get_request_id() -> str:
    """获取当前请求 ID（线程安全）"""
    return _request_id_var.get()

def generate_request_id() -> str:
    """生成新的请求 ID"""
    return f"req-{uuid.uuid4().hex[:12]}"

# -------- 全局异常处理 --------
_exception_handlers: Dict[str, Callable] = {}
_exception_log: List[Dict[str, Any]] = []
_exception_log_lock = threading.Lock()

def register_exception_handler(name: str, handler: Callable[[Exception, Dict], Any]) -> None:
    """注册异常处理器"""
    _exception_handlers[name] = handler

def handle_exception(exc: Exception, context: Optional[Dict[str, Any]] = None) -> Any:
    """统一异常处理（分发到已注册的 handler）"""
    req_id = get_request_id()
    ctx = context or {}
    entry = {
        "id": generate_request_id(),
        "request_id": req_id,
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
        "context": ctx,
        "timestamp": time.time(),
    }
    with _exception_log_lock:
        _exception_log.append(entry)
        if len(_exception_log) > 1000:
            del _exception_log[:500]  # 保留最近 1000 条
    result = None
    for name, handler in _exception_handlers.items():
        try:
            r = handler(exc, ctx)
            if r is not None:
                result = r
        except Exception as inner:
            print(f"[ExceptionHandler {name}] 处理异常时出错：{inner}")
    return result

def get_exception_log(limit: int = 50) -> List[Dict[str, Any]]:
    """获取最近的异常日志"""
    with _exception_log_lock:
        return list(_exception_log[-limit:])

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

        # Oracle 引擎（推背图认知）
        _oracle_mod = _safe_import("伤官_破界创新")
        self.oracle = _oracle_mod.OracleEngine() if _oracle_mod else None

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

    # ============ 新功能集成：食神流式 / 正财搜索 / 正官 API ============

    def generate_stream(self, prompt: str, format: str = "text",
                        style: str = "default") -> Any:
        """调用食神流式生成内容。

        返回一个可迭代对象，每次 yield 一小块文本（字符串）。
        若食神模块不可用，返回空列表。
        """
        if not self.generator or not self.OutputFormat or not self.GenerationConfig:
            return []
        fmt_map = {
            "text": self.OutputFormat.TEXT,
            "markdown": self.OutputFormat.MARKDOWN,
            "md": self.OutputFormat.MARKDOWN,
            "json": self.OutputFormat.JSON,
            "html": self.OutputFormat.HTML,
        }
        config = self.GenerationConfig(
            format=fmt_map.get(format, self.OutputFormat.TEXT),
            style=style,
        )
        return self.generator.generate_stream(prompt, config)

    def generate_collect(self, prompt: str, format: str = "text",
                         style: str = "default") -> str:
        """调用食神生成内容，一次性返回完整内容（内部走流式）。"""
        return "".join(self.generate_stream(prompt, format=format, style=style))

    def search_knowledge(self, query: str, top_k: int = 5,
                         node_type: Optional[str] = None,
                         min_score: float = 0.0) -> List[Dict[str, Any]]:
        """正财模块：向量相似度查询知识库节点。"""
        if not self.kb:
            return []
        return self.kb.query_nearest(query, top_k=top_k,
                                      node_type=node_type, min_score=min_score)

    def knowledge_base(self) -> Any:
        """返回正财知识库对象（用于批量导入等高级场景）。"""
        return self.kb

    def run_api_server(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        """正官模块：启动 HTTP API 服务（阻塞式）。"""
        try:
            from 正官_法度调度.api_server import run_server
            run_server(self, host=host, port=port)
        except Exception as e:
            print(f"[Error] 启动 API 服务失败：{e}")

    def create_api_app(self) -> Any:
        """返回 FastAPI 应用（如可用），否则返回 None。"""
        try:
            from 正官_法度调度.api_server import create_app
            return create_app(self)
        except Exception as e:
            print(f"[Error] 创建 API 应用失败：{e}")
            return None

    def run(self, *, serve: bool = False, host: str = "127.0.0.1",
            port: int = 8000, init_seed: bool = False) -> Dict[str, Any]:
        """统一启动入口（v1.3.0）。

        参数：
            serve: 是否启动 HTTP API 服务（阻塞）
            host: HTTP 服务监听地址
            port: HTTP 服务监听端口
            init_seed: 是否写入中华文明种子知识节点

        返回启动摘要（即使 serve=True 也会在退出时返回）。
        """
        req_id = generate_request_id()
        token = _request_id_var.set(req_id)
        start = time.time()

        print(f"[TenGodCore] 启动 v1.3.0 (request_id={req_id})")
        print(f"[TenGodCore] 初始化模块...")

        steps = []
        def record(name: str, ok: bool, detail: str = ""):
            steps.append({"module": name, "ok": ok, "detail": detail})

        # 元辰定位
        try:
            s = self.locator.summary() if self.locator else {}
            record("元辰", True, f"path={s.get('path','N/A')}")
        except Exception as e:
            handle_exception(e, {"module": "元辰"})
            record("元辰", False, str(e))

        # 种子数据（中华文明）
        if init_seed and self.kb:
            try:
                seeds = [
                    # 先秦诸子
                    {"name": "儒家", "node_type": "school",
                     "properties": {"代表": "孔子/孟子/荀子", "典籍": "论语/孟子/大学/中庸", "核心": "仁义礼智信", "年代": "春秋战国"}},
                    {"name": "道家", "node_type": "school",
                     "properties": {"代表": "老子/庄子/列子", "典籍": "道德经/庄子/列子", "核心": "道法自然/无为", "年代": "春秋战国"}},
                    {"name": "法家", "node_type": "school",
                     "properties": {"代表": "韩非子/商鞅/李斯", "典籍": "韩非子/商君书", "核心": "以法治国", "年代": "战国"}},
                    {"name": "墨家", "node_type": "school",
                     "properties": {"代表": "墨子", "典籍": "墨子", "核心": "兼爱非攻/尚贤", "年代": "春秋战国"}},
                    {"name": "兵家", "node_type": "school",
                     "properties": {"代表": "孙子/孙膑", "典籍": "孙子兵法/孙膑兵法", "核心": "知己知彼/不战而屈人之兵", "年代": "春秋战国"}},
                    {"name": "医家", "node_type": "school",
                     "properties": {"代表": "扁鹊/华佗/张仲景", "典籍": "黄帝内经/伤寒杂病论/本草纲目", "核心": "阴阳五行/辨证论治", "年代": "先秦至东汉"}},
                    # 经典典籍
                    {"name": "易经", "node_type": "classic",
                     "properties": {"地位": "群经之首", "内容": "六十四卦/系辞/十翼", "三易": "连山/归藏/周易"}},
                    {"name": "诗经", "node_type": "classic",
                     "properties": {"篇数": 305, "类别": "风雅颂", "年代": "西周至春秋"}},
                    {"name": "尚书", "node_type": "classic",
                     "properties": {"别称": "书经", "内容": "上古政事文献", "年代": "虞夏商周"}},
                    {"name": "礼记", "node_type": "classic",
                     "properties": {"核心篇": "大学/中庸/礼运", "内容": "礼乐制度/大同理想"}},
                    {"name": "春秋", "node_type": "classic",
                     "properties": {"作者": "孔子", "体例": "编年史", "三传": "左传/公羊/谷梁"}},
                    {"name": "史记", "node_type": "classic",
                     "properties": {"作者": "司马迁", "体例": "纪传体通史", "起止": "黄帝—汉武帝", "地位": "史家之绝唱"}},
                    # 宇宙哲学
                    {"name": "河图", "node_type": "cosmic",
                     "properties": {"结构": "1-10黑白点", "对应": "先天八卦", "方位": "坐北朝南/天一生水"}},
                    {"name": "洛书", "node_type": "cosmic",
                     "properties": {"结构": "3x3九宫幻方", "对应": "九畴/后天八卦", "数": "戴九履一"}},
                    {"name": "阴阳", "node_type": "concept",
                     "properties": {"核心": "对立统一", "应用": "中医/风水/哲学/兵法", "出处": "周易·系辞"}},
                    {"name": "五行", "node_type": "concept",
                     "properties": {"构成": "金木水火土", "关系": "相生：木→火→土→金→水；相克：木克土/火克金/土克水/金克木/水克火", "应用": "中医/命理/风水"}},
                    {"name": "太极", "node_type": "concept",
                     "properties": {"图像": "阴阳鱼太极图", "出处": "周易·系辞上", "含义": "无极而太极/一生二"}},
                    {"name": "八卦", "node_type": "concept",
                     "properties": {"构成": "乾坤震巽坎离艮兑", "代表": "天地雷风水火山泽", "演变": "伏羲先天/文王后天"}},
                    # 历史人物
                    {"name": "孔子", "node_type": "historical_figure",
                     "properties": {"生卒": "前551-前479", "思想": "仁/礼/中庸", "贡献": "删述六经/有教无类", "学派": "儒家"}},
                    {"name": "老子", "node_type": "historical_figure",
                     "properties": {"生卒": "约前571-前471", "思想": "道法自然/无为", "著作": "道德经", "学派": "道家"}},
                    {"name": "诸葛亮", "node_type": "historical_figure",
                     "properties": {"生卒": "181-234", "称号": "卧龙/武侯", "代表": "出师表/八阵图", "领域": "政治/军事/发明"}},
                    {"name": "李白", "node_type": "historical_figure",
                     "properties": {"生卒": "701-762", "称号": "诗仙", "风格": "浪漫豪放", "代表作": "将进酒/蜀道难"}},
                    {"name": "苏轼", "node_type": "historical_figure",
                     "properties": {"生卒": "1037-1101", "称号": "东坡居士", "领域": "诗词/书法/绘画/美食", "代表作": "赤壁赋/水调歌头"}},
                    # 科技发明
                    {"name": "四大发明", "node_type": "technology",
                     "properties": {"造纸": "蔡伦-东汉", "印刷": "毕昇活字-北宋", "火药": "唐", "指南针": "战国司南—宋"}},
                    {"name": "都江堰", "node_type": "technology",
                     "properties": {"建造者": "李冰父子", "年代": "公元前256年", "原理": "无坝引水/鱼嘴分水", "地位": "世界水利工程鼻祖"}},
                ]
                for s in seeds:
                    self.kb.upsert_node(s["name"], node_type=s["node_type"],
                                        properties=s["properties"])
                record("正财(种子)", True, f"写入{len(seeds)}个节点")
            except Exception as e:
                handle_exception(e, {"module": "正财"})
                record("正财(种子)", False, str(e))
        else:
            record("正财(种子)", True, "跳过(init_seed=False)")

        # 太极调和
        try:
            if self.balancer:
                self.balance_state({"系统": 80})
                record("太极", True, "已评估")
        except Exception as e:
            handle_exception(e, {"module": "太极"})
            record("太极", False, str(e))

        # 劫财初始化（默认角色）
        try:
            if self.guard:
                Permission = self.Permission
                self.guard.register_role("admin", {Permission.READ, Permission.WRITE,
                                                    Permission.EXECUTE, Permission.ADMIN})
                self.guard.register_role("user", {Permission.READ, Permission.EXECUTE})
                self.guard.register_role("guest", {Permission.READ})
                record("劫财", True, "3个角色已注册")
        except Exception as e:
            handle_exception(e, {"module": "劫财"})
            record("劫财", False, str(e))

        elapsed = (time.time() - start) * 1000
        print(f"[TenGodCore] 初始化完成，耗时 {elapsed:.1f}ms")

        summary = {
            "request_id": req_id,
            "version": "1.3.0",
            "elapsed_ms": round(elapsed, 1),
            "init_steps": steps,
            "api_server": None,
        }

        if serve:
            print(f"[TenGodCore] 启动 HTTP API 服务 → http://{host}:{port}")
            try:
                self.run_api_server(host=host, port=port)
            except KeyboardInterrupt:
                print(f"[TenGodCore] API 服务被中断")
            summary["api_server"] = "stopped"
        else:
            print(f"[TenGodCore] 完成（不使用 --serve 可直接返回）")
            print(f"[TenGodCore] 启动摘要：{json.dumps(summary, ensure_ascii=False, indent=2)}")

        _request_id_var.reset(token)
        return summary

    def consult_oracle(self, question: str, mode: str = "auto") -> Dict[str, Any]:
        """推背图 Oracle 咨询。

        Args:
            question: 咨询问题
            mode: 推演模式 (tuibeitu/zhouyi/zigua/hetu/luoshu/auto)

        Returns:
            卦象、干支、解释等结果字典
        """
        if not self.oracle:
            return {"error": "Oracle 引擎未就绪"}
        result = self.oracle.cast(question)
        return {
            "question": question,
            "mode": mode,
            "hexagram": result.hexagram,
            "hexagram_index": result.hexagram_index,
            "upper_trigram": result.upper_trigram,
            "lower_trigram": result.lower_trigram,
            "gan_zhi": result.gan_zhi,
            "wuxing": result.wuxing,
            "judgment": result.judgment,
            "prediction": result.prediction,
            "wisdom": result.wisdom,
            "interpretation": self.oracle.interpret(result),
            "stats": self.oracle.stats(),
        }

    def export_state(self) -> Dict[str, Any]:
        """导出核心状态"""
        return {
            "name": self.name,
            "version": "1.5.0",
            "request_id": get_request_id(),
            "features": {
                "streaming_generate": self.generator is not None,
                "vector_search": self.kb is not None,
                "http_api": True,
                "jwt_auth": True,
                "rate_limiting": True,
                "session_management": self.generator is not None,
                "orm_persistence": self.kb is not None,
                "exception_tracking": True,
                "oracle_engine": self.oracle is not None,
                "code_scanner": True,
                "metrics": True,
            },
            "scheduler": self.scheduler.stats() if self.scheduler else None,
            "judge": self.judge.report() if self.judge else None,
            "config": self.config.list_with_source() if self.config else None,
            "knowledge": self.kb.stats() if self.kb else None,
            "registered_components": self.registry.list_all() if self.registry else [],
            "registered_adapters": self.bridge.list_adapters() if self.bridge else [],
            "registered_converters": self.bridge.list_converters() if self.bridge else [],
            "locator": self.locator.summary() if self.locator else None,
            "balancer": self.balancer.stats() if self.balancer else None,
            "oracle": self.oracle.stats() if self.oracle else None,
        }


# 便捷全局实例
_default_core: Optional[TenGodCore] = None


def get_core() -> TenGodCore:
    """获取默认核心实例"""
    global _default_core
    if _default_core is None:
        _default_core = TenGodCore()
    return _default_core


__all__ = ["TenGodCore", "get_core",
           "get_request_id", "generate_request_id",
           "register_exception_handler", "handle_exception", "get_exception_log"]
__version__ = "1.5.0"