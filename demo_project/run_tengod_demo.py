#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_tengod_demo.py — 十神架构 · 一键串联演示

一次性跑通 12 个模块 + 核心调度器，覆盖：
    元辰定位 → 正印加载配置 → 食神生成(流式) → 伤官破界创新
    → 正财入库 & 向量搜索 → 七杀评估打分 → 偏财参数寻优
    → 比肩注册 → 偏印转换 → 劫财鉴权 → 太极阴阳调和
    → 正官启动 HTTP API 提示

运行:
    python demo_project/run_tengod_demo.py
"""

import json
import os
import sys
import time

# -------- 路径准备（让脚本可在任意目录下运行）--------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TENGOD_ROOT = os.path.join(_THIS_DIR, "tengod")
for _p in [_THIS_DIR, _TENGOD_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
for _sub in os.listdir(_TENGOD_ROOT):
    _full = os.path.join(_TENGOD_ROOT, _sub)
    if os.path.isdir(_full) and not _sub.startswith((".", "_")):
        if _full not in sys.path:
            sys.path.insert(0, _full)


# ============================================================
#  · 终端彩色输出 ·
# ============================================================
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


def banner(title: str) -> None:
    bar = "━" * 62
    print()
    print(f"{C.BOLD}{C.CYAN}{bar}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{bar}{C.RESET}")


def step(idx: int, total: int, title: str, module: str) -> None:
    print()
    print(
        f"{C.BOLD}[{idx:02d}/{total:02d}]{C.RESET} "
        f"{C.MAGENTA}{module:<12}{C.RESET}  "
        f"{C.BOLD}{C.WHITE}{title}{C.RESET}"
    )
    print(f"{C.DIM}  {'─' * 58}{C.RESET}")


def info(msg: str) -> None:
    print(f"  {C.CYAN}·{C.RESET} {msg}")


def ok(msg: str) -> None:
    print(f"  {C.GREEN}✔{C.RESET} {C.GREEN}{msg}{C.RESET}")


def warn(msg: str) -> None:
    print(f"  {C.YELLOW}!{C.RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {C.RED}✘{C.RESET} {C.RED}{msg}{C.RESET}")


def kv(key: str, value) -> None:
    print(f"     {C.DIM}{key}:{C.RESET} {C.WHITE}{value}{C.RESET}")


def hr() -> None:
    print(f"{C.DIM}  {'─' * 58}{C.RESET}")


# ============================================================
#  · 主演示流程 ·
# ============================================================
def main() -> int:
    t0 = time.time()

    # -------- 开场 Banner --------
    os.system("")  # Windows 下开启 ANSI
    banner("中华文明数字永生体 · 十神架构 一键串联演示")
    info(f"版本 {C.YELLOW}1.2.0{C.RESET}  |  commit ee6e09b → 15e0b71")
    info(f"时间 {C.YELLOW}{time.strftime('%Y-%m-%d %H:%M:%S')}{C.RESET}")

    # -------- 导入核心 --------
    step(0, 12, "初始化核心调度器 (TenGodCore)", "核心")
    try:
        from tengod.core import get_core

        core = get_core()
        ok("TenGodCore 实例化成功")
        kv("核心名称", core.name)
    except Exception as e:
        fail(f"核心初始化失败：{e}")
        return 1

    TOTAL = 12

    # ========================================================
    # [01] 元辰 · 本源定位
    # ========================================================
    step(1, TOTAL, "元辰 · 定位项目根目录与文件结构", "元辰")
    try:
        summary = core.locate_project()
        ok("项目定位完成")
        kv("path", summary.get("path", "N/A"))
        kv("name", summary.get("name", "N/A"))
        kv("submodules_count", summary.get("submodules_count", 0))
        kv("config_files", summary.get("config_files", []))
        kv("submodules_sample", summary.get("submodules", [])[:6])
    except Exception as e:
        fail(f"元辰定位失败：{e}")

    # ========================================================
    # [02] 正印 · 滋养守护（加载配置）
    # ========================================================
    step(2, TOTAL, "正印 · 加载默认配置", "正印")
    try:
        cfg = core.config
        cfg.set_default("max_workers", 4)
        cfg.set_default("timeout", 30)
        cfg.set_default("cache_enabled", True)
        cfg.set_default("project_name", "中华文明数字永生体")
        src = cfg.list_with_source()
        ok("配置已写入并可检索")
        for k, v in list(src.items())[:4]:
            kv(k, v)
    except Exception as e:
        fail(f"正印配置失败：{e}")

    # ========================================================
    # [03] 比肩 · 架构协同（注册各模块组件）
    # ========================================================
    step(3, TOTAL, "比肩 · 注册各模块组件到协同表", "比肩")
    try:
        reg = core.registry
        reg.register("食神_generator", core.generator)
        reg.register("正财_kb", core.kb)
        reg.register("七杀_judge", core.judge)
        reg.register("正印_config", core.config)
        all_comps = reg.list_all()
        ok(f"共注册 {len(all_comps)} 个组件")
        for comp in all_comps:
            kv("component", comp)
    except Exception as e:
        fail(f"比肩注册失败：{e}")

    # ========================================================
    # [04] 食神 · 创生输出（流式）
    # ========================================================
    step(4, TOTAL, "食神 · 流式生成一段『中华文明简述』", "食神")
    try:
        prompt = "简述中华文明的一个核心特点"
        info(f'prompt = "{prompt}"')
        print(f"     {C.DIM}流式输出：{C.RESET}", end="", flush=True)

        chunks = []
        for chunk in core.generate_stream(prompt):
            print(f"{C.WHITE}{chunk}{C.RESET}", end="", flush=True)
            chunks.append(chunk)

        print()  # 换行
        full = "".join(chunks)
        ok(f"流式生成完成，共 {len(chunks)} 段，总长度 {len(full)} 字符")
        kv("provider", "mock(本地模拟，无需 API Key)")

        # 再调用一次一次性生成，验证 API 一致性
        full2 = core.generate_collect("中华文明与西方文明的差异")
        kv("collect_len", len(full2))
    except Exception as e:
        fail(f"食神生成失败：{e}")

    # ========================================================
    # [05] 伤官 · 破界创新
    # ========================================================
    step(5, TOTAL, "伤官 · 以『AI + 周易』组合寻找创新点", "伤官")
    try:
        innov = core.innovator
        innov.combine(["AI", "知识图谱", "周易", "河图洛书"])
        innov.transfer("神经网络", "诸子百家")
        ideas = getattr(innov, "_ideas", [])
        ok(f"已生成 {len(ideas)} 个创意")
        for i, idea in enumerate(ideas[-3:], 1):
            score = getattr(idea, "score", 0.0)
            title = getattr(idea, "title", str(idea))
            kv(f"idea#{i}", f"{title}  (score={score:.2f})")
    except Exception as e:
        fail(f"伤官创新失败：{e}")

    # ========================================================
    # [06] 正财 · 知识固化：写入中华文明种子节点
    # ========================================================
    step(6, TOTAL, "正财 · 写入中华文明种子节点（诸子百家/六经/河图洛书等）", "正财")
    try:
        kb = core.knowledge_base()
        seeds = [
            {
                "name": "儒家",
                "node_type": "school",
                "properties": {
                    "代表": "孔子/孟子",
                    "典籍": "论语/孟子",
                    "时代": "春秋",
                },
            },
            {
                "name": "道家",
                "node_type": "school",
                "properties": {
                    "代表": "老子/庄子",
                    "典籍": "道德经/庄子",
                    "时代": "春秋",
                },
            },
            {
                "name": "墨家",
                "node_type": "school",
                "properties": {"代表": "墨子", "典籍": "墨子", "时代": "战国"},
            },
            {
                "name": "法家",
                "node_type": "school",
                "properties": {"代表": "韩非/商鞅", "典籍": "韩非子", "时代": "战国"},
            },
            {
                "name": "兵家",
                "node_type": "school",
                "properties": {"代表": "孙武/吴起", "典籍": "孙子兵法", "时代": "春秋"},
            },
            {
                "name": "易经",
                "node_type": "classic",
                "properties": {
                    "分类": "六经之首",
                    "内容": "六十四卦",
                    "地位": "群经之首",
                },
            },
            {
                "name": "诗经",
                "node_type": "classic",
                "properties": {"分类": "六经", "内容": "305 篇", "朝代": "西周至春秋"},
            },
            {
                "name": "尚书",
                "node_type": "classic",
                "properties": {"分类": "六经", "内容": "上古政令", "朝代": "上古"},
            },
            {
                "name": "礼记",
                "node_type": "classic",
                "properties": {"分类": "六经", "内容": "礼仪制度", "朝代": "先秦"},
            },
            {
                "name": "春秋",
                "node_type": "classic",
                "properties": {"分类": "六经", "作者": "孔子", "时代": "春秋"},
            },
            {
                "name": "河图",
                "node_type": "cosmic",
                "properties": {
                    "传说": "龙马负图",
                    "结构": "1-10 黑白点",
                    "对应": "八卦",
                },
            },
            {
                "name": "洛书",
                "node_type": "cosmic",
                "properties": {
                    "传说": "神龟负书",
                    "结构": "3x3 九宫幻方",
                    "对应": "九畴",
                },
            },
            {
                "name": "阴阳",
                "node_type": "concept",
                "properties": {
                    "核心": "对立统一",
                    "起源": "上古",
                    "应用": "中医/风水/哲学",
                },
            },
            {
                "name": "五行",
                "node_type": "concept",
                "properties": {
                    "构成": "金木水火土",
                    "关系": "相生相克",
                    "应用": "中医/命理",
                },
            },
            {
                "name": "太极",
                "node_type": "concept",
                "properties": {
                    "图像": "阴阳鱼",
                    "出处": "周易·系辞",
                    "含义": "万物本源",
                },
            },
            {
                "name": "中庸",
                "node_type": "concept",
                "properties": {"出处": "礼记", "作者": "子思", "核心": "不偏不易"},
            },
        ]
        for s in seeds:
            kb.add_node(s["name"], node_type=s["node_type"], properties=s["properties"])
        stats = kb.stats()
        ok(f"已写入 {stats['nodes']} 个节点，共 {stats['node_types']} 个类型")
        for k, v in stats.items():
            kv(k, v)
    except Exception as e:
        fail(f"正财入库失败：{e}")

    # ========================================================
    # [07] 正财 · 向量相似度搜索
    # ========================================================
    step(7, TOTAL, "正财 · 向量相似度搜索『周易 阴阳 六十四卦』", "正财")
    try:
        results = core.search_knowledge("周易 阴阳 六十四卦", top_k=5)
        ok(f"命中 {len(results)} 个节点（按相似度排序）")
        for i, r in enumerate(results, 1):
            print(
                f"     {C.CYAN}{i}.{C.RESET} {C.WHITE}{r['name']:<8}{C.RESET}  "
                f"{C.YELLOW}type={r['node_type']:<10}{C.RESET}  "
                f"{C.GREEN}score={r['score']:.4f}{C.RESET}"
            )

        # 再来一次类型过滤
        hr()
        info("过滤 school（学派）类型，再次搜索『孔子 孟子』：")
        filtered = core.search_knowledge("孔子 孟子", top_k=5, node_type="school")
        for i, r in enumerate(filtered, 1):
            print(
                f"     {C.CYAN}{i}.{C.RESET} {C.WHITE}{r['name']:<8}{C.RESET}  "
                f"{C.YELLOW}type={r['node_type']:<10}{C.RESET}  "
                f"{C.GREEN}score={r['score']:.4f}{C.RESET}"
            )
    except Exception as e:
        fail(f"正财向量搜索失败：{e}")

    # ========================================================
    # [08] 七杀 · 品质裁决（对候选创意打分）
    # ========================================================
    step(8, TOTAL, "七杀 · 对『食神/伤官/正财』三模块表现打分", "七杀")
    try:
        report = core.evaluate(
            {
                "生成质量": 88,
                "创新度": 76,
                "知识完整度": 92,
                "检索相关性": 84,
                "响应速度": 95,
            },
            weights={
                "生成质量": 1.2,
                "创新度": 1.0,
                "知识完整度": 1.1,
                "检索相关性": 1.0,
                "响应速度": 0.8,
            },
        )
        ok("综合评估完成")
        for k, v in report.items():
            if isinstance(v, float):
                kv(k, f"{v:.2f}")
            else:
                kv(k, v)
    except Exception as e:
        fail(f"七杀评估失败：{e}")

    # ========================================================
    # [09] 偏财 · 奇招演化（超参数寻优）
    # ========================================================
    step(9, TOTAL, "偏财 · 在一组演示超参数上做网格搜索", "偏财")
    try:

        def demo_objective(params: dict) -> float:
            """一个示意目标函数：越接近『学习率 0.01 / batch 32 / 层数 4』越高分"""
            score = 0.0
            score -= abs(params.get("lr", 0.01) - 0.01) * 1000
            score -= abs(params.get("batch", 32) - 32) * 0.5
            score -= abs(params.get("layers", 4) - 4) * 2
            score -= abs(params.get("dropout", 0.2) - 0.2) * 20
            return score

        result = core.search(
            {
                "lr": [0.001, 0.01, 0.1],
                "batch": [16, 32, 64],
                "layers": [2, 4, 8],
                "dropout": [0.1, 0.2, 0.3],
            },
            demo_objective,
        )
        ok(
            f"参数寻优完成：迭代 {result['iterations']} 次，耗时 {result['duration']} ms"
        )
        kv("best_params", result["best_params"])
        kv("best_score", f"{result['best_score']:.4f}")
    except Exception as e:
        fail(f"偏财参数寻优失败：{e}")

    # ========================================================
    # [10] 偏印 · 桥接通变（dict ↔ JSON）
    # ========================================================
    step(10, TOTAL, "偏印 · 把核心状态桥接转换为 JSON", "偏印")
    try:
        bridge = core.bridge
        state = core.export_state()
        lite = {
            k: v
            for k, v in state.items()
            if k in ("name", "version", "features", "knowledge")
        }

        # 构造一个自定义 JSON 桥接器，并注册到 bridge
        class JsonConverter:
            name = "json"

            def encode(self, value):
                import json as _json

                return _json.dumps(value, ensure_ascii=False, default=str)

            def decode(self, payload):
                import json as _json

                return _json.loads(payload) if isinstance(payload, str) else payload

        if bridge is not None:
            bridge.register_converter("json", JsonConverter())
            conv = bridge.get_converter("json")
            encoded = conv.encode(lite) if conv is not None else "N/A"
            decoded = conv.decode(encoded) if conv is not None else None
            ok("JSON 桥接完成（注册 → 编码 → 解码）")
            kv("encoder", JsonConverter.__name__)
            kv(
                "encoded_len",
                len(encoded) if isinstance(encoded, str) else len(str(encoded)),
            )
            kv(
                "decoded_name",
                decoded.get("name") if isinstance(decoded, dict) else "N/A",
            )
            kv("adapters_registered", bridge.list_adapters())
            kv("converters_registered", bridge.list_converters())
        else:
            warn("bridge 未就绪，跳过")
    except Exception as e:
        fail(f"偏印桥接失败：{e}")

    # ========================================================
    # [11] 劫财 · 攻防边界（角色权限）
    # ========================================================
    step(11, TOTAL, "劫财 · 验证 admin / user / guest 三类角色权限", "劫财")
    try:
        guard = core.guard
        Permission = core.Permission
        if guard is None or Permission is None:
            warn("guard 或 Permission 未就绪，跳过")
        else:
            # 注册角色权限
            role_perms = {
                "admin": [
                    Permission.READ,
                    Permission.WRITE,
                    Permission.EXECUTE,
                    Permission.ADMIN,
                ],
                "user": [Permission.READ, Permission.EXECUTE],
                "guest": [Permission.READ],
            }
            for role, perms in role_perms.items():
                guard.register_role(role, set(perms))

            # 创建用户安全上下文（每个角色映射为一个"用户"）
            contexts = {
                role: guard.create_context(user_id=f"user_{role}", roles=[role])
                for role in role_perms
            }

            ok("角色与安全上下文初始化完成")
            for role, perms in role_perms.items():
                results = {p.value: guard.check(contexts[role], p) for p in perms}
                kv(role, results)

            # 边界：guest 尝试写 应被拒绝
            if not guard.check(contexts["guest"], Permission.WRITE):
                info("✓ 边界测试：guest 尝试 WRITE 被正确拒绝")

            # 限流一次
            rl = guard.rate_limit("user_admin", max_requests=5, window_seconds=60)
            kv("admin_rate_limit", "允许" if rl else "拒绝")

            # 审计日志条数
            audit = guard.get_audit_log()
            kv("audit_events", len(audit))
    except Exception as e:
        fail(f"劫财鉴权失败：{e}")

    # ========================================================
    # [12] 太极 · 阴阳调和
    # ========================================================
    step(12, TOTAL, "太极 · 根据当前模块表现做阴阳状态评估", "太极")
    try:
        stats = core.balance_state(
            metrics={
                "创新度": 76,
                "生成质量": 88,
                "检索相关性": 84,
                "响应速度": 95,
            }
        )
        ok("太极阴阳调和评估完成")
        for k, v in stats.items():
            if isinstance(v, float):
                kv(k, f"{v:.2f}")
            elif isinstance(v, list):
                # history 列表做简短摘要
                kv(k, f"len={len(v)}")
            else:
                kv(k, v)
    except Exception as e:
        fail(f"太极评估失败：{e}")

    # ========================================================
    # 收尾 · 正官启动提示
    # ========================================================
    banner("正官 · 启动 HTTP API 服务（可选）")
    print(
        f"  {C.GREEN}演示已全部完成！{C.RESET} 可继续启动 {C.CYAN}REST API{C.RESET} 与框架交互：\n"
        f"     {C.YELLOW}python -m demo_project.tengod.正官_法度调度.api_server --host 127.0.0.1 --port 8000{C.RESET}\n"
        f"     {C.YELLOW}python demo_project/run_tengod_demo.py --serve --port 8000{C.RESET}\n"
        f"  健康检查：curl http://127.0.0.1:8000/health\n"
        f"  知识搜索：curl -X POST -H 'Content-Type: application/json' \\\n"
        f"              -d '{json.dumps({'query': '周易', 'top_k': 3}, ensure_ascii=False)}' \\\n"
        f"              http://127.0.0.1:8000/api/knowledge/search"
    )

    # -------- 总耗时 --------
    dt = (time.time() - t0) * 1000
    hr()
    print(
        f"{C.BOLD}{C.GREEN}  ✦ 演示完毕{C.RESET}  "
        f"共 {TOTAL} 步，总耗时 {C.YELLOW}{dt:.1f} ms{C.RESET}  |  "
        f"核心版本 {C.YELLOW}{core.export_state()['version']}{C.RESET}"
    )
    hr()

    # -------- 可选：--serve 直接启动 API --------
    if "--serve" in sys.argv:
        port = 8000
        for a in sys.argv:
            if a.startswith("--port="):
                try:
                    port = int(a.split("=", 1)[1])
                except ValueError:
                    pass
        print(
            f"  启动正官 HTTP API 于 {C.CYAN}http://127.0.0.1:{port}{C.RESET} ... (Ctrl+C 退出)"
        )
        core.run_api_server(host="127.0.0.1", port=port)

    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}[用户中断]{C.RESET}")
        rc = 130
    sys.exit(rc)
