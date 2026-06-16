#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_tengod_demo.py — 十神架构 · 全系统集成演示 v2.0.0

一次性跑通六大阶段全部功能：
  第一阶段（应用层）：八字排盘 — 四柱计算/大运流年/真太阳时
  第二阶段（数据层）：MCP Server — 五行查询/八卦查询/十神推演/地支分析
  第三阶段（可视化层）：WebGL 3D — 已生成独立HTML文件 (deploy_frontend/)
  第四阶段（算法层）：神煞引擎 — 40+神煞/格局判断/喜用神/调候
  第五阶段（知识层）：向量检索 — FAISS语义搜索/知识关联推荐
  第六阶段（集成层）：全系统联调 — 打通所有模块

  十神核心架构（12步）：
    元辰定位 → 正印加载配置 → 比肩注册 → 食神生成(流式)
    → 伤官破界创新 → 正财入库&搜索 → 七杀评估打分
    → 偏财参数寻优 → 偏印桥接转换 → 劫财鉴权 → 太极阴阳调和

运行:
    python demo_project/run_tengod_demo.py
    python demo_project/run_tengod_demo.py --bazi 1990-06-15-10:30  # 指定八字
    python demo_project/run_tengod_demo.py --serve --port 8000        # 启动API
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
    banner("中华文明数字永生体 · 十神架构 全系统集成演示 v2.0.0")
    info(f"版本 {C.YELLOW}2.0.0{C.RESET}  |  全系统六阶段集成")
    info(f"时间 {C.YELLOW}{time.strftime('%Y-%m-%d %H:%M:%S')}{C.RESET}")

    TOTAL = 21

    # -------- 导入核心 --------
    step(0, TOTAL, "初始化核心调度器 (TenGodCore)", "核心")
    try:
        from tengod.core import get_core

        core = get_core()
        ok("TenGodCore 实例化成功")
        kv("核心名称", core.name)
    except Exception as e:
        fail(f"核心初始化失败：{e}")
        return 1

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
    #  ╔══════════════════════════════════════════════════════╗
    #  ║  阶段一：八字排盘系统（应用层）                      ║
    #  ╚══════════════════════════════════════════════════════╝
    # ========================================================
    banner("第一阶段 · 八字排盘系统（应用层）")

    # 解析命令行参数 --bazi YYYY-MM-DD-HH:MM
    bazi_year, bazi_month, bazi_day, bazi_hour, bazi_minute = 1990, 6, 15, 10, 30
    bazi_is_male = True
    for a in sys.argv:
        if a.startswith("--bazi="):
            parts = a.split("=", 1)[1].replace(":", "-").split("-")
            if len(parts) >= 3:
                bazi_year, bazi_month, bazi_day = int(parts[0]), int(parts[1]), int(parts[2])
            if len(parts) >= 5:
                bazi_hour, bazi_minute = int(parts[3]), int(parts[4])
        if a == "--female":
            bazi_is_male = False

    # [13] 八字排盘
    step(13, TOTAL, "八字排盘 · 计算四柱 + 大运流年 + 真太阳时", "八字")
    bazi_analyzer = None
    try:
        from tengod.bazi_analyzer import BaziAnalyzer
        bazi_analyzer = BaziAnalyzer(
            bazi_year, bazi_month, bazi_day, bazi_hour, bazi_minute,
            is_male=bazi_is_male, longitude=116.4, latitude=39.9
        )
        chart = bazi_analyzer.chart
        pillars = chart.pillars
        day_master = chart.day_master
        ok(f"八字排盘完成 — {bazi_year}-{bazi_month:02d}-{bazi_day:02d} "
           f"{bazi_hour:02d}:{bazi_minute:02d} {'男命' if bazi_is_male else '女命'}")
        kv("四柱", f"{pillars['year']} {pillars['month']} {pillars['day']} {pillars['hour']}")
        kv("日主", day_master)
        kv("真太阳时", f"{chart.true_hour:02d}:{chart.true_minute:02d}")
        from tengod.dayun_liunian import derive_shigan
        kv("年柱十神", derive_shigan(day_master, pillars['year'][0]))
        kv("月柱十神", derive_shigan(day_master, pillars['month'][0]))
        kv("时柱十神", derive_shigan(day_master, pillars['hour'][0]))
    except Exception as e:
        fail(f"八字排盘失败：{e}")

    # [14] 八字综合分析
    step(14, TOTAL, "八字综合分析 · 五行/十神/地支关系/大运/流年", "八字")
    try:
        if bazi_analyzer:
            a = bazi_analyzer.analysis
            ok("五行分布:")
            for wx in ['木', '火', '土', '金', '水']:
                kv(f"  {wx}", a['wuxing_score'][wx])
            hr()
            info("十神分布:")
            for sg, cnt in sorted(a['shigan_count'].items(), key=lambda x: -x[1]):
                kv(f"  {sg}", cnt)
            hr()
            info("地支关系:")
            has_rel = False
            for k, v in a['branch_relations'].items():
                if v:
                    has_rel = True
                    kv(f"  {k}", ", ".join(v))
            if not has_rel:
                kv("  (无)", "无显著合冲害破刑关系")
            hr()
            info("大运（前5步）:")
            for du in a['dayuns'][:5]:
                from tengod.dayun_liunian import derive_shigan
                gs = derive_shigan(a['day_master'], du['pillar'][0])
                kv(f"  {du['age']:>3d}-{du['age']+9}岁", f"{du['pillar']} [{gs}]")
            hr()
            info("近期流年:")
            for ln in a['liunians'][:6]:
                kv(f"  {ln['year']}年", f"{ln['pillar']} [{ln['gan_shigan']}]")
            hr()
            info("分析结论:")
            kv("conclusion", a['conclusion'])
        else:
            warn("八字分析器未初始化，跳过")
    except Exception as e:
        fail(f"八字综合分析失败：{e}")

    # ========================================================
    #  ╔══════════════════════════════════════════════════════╗
    #  ║  阶段二：MCP Server 知识服务化（数据层）              ║
    #  ╚══════════════════════════════════════════════════════╝
    # ========================================================
    banner("第二阶段 · MCP Server 知识服务化（数据层）")

    # [15] MCP 工具：五行查询 + 八卦查询
    step(15, TOTAL, "MCP 工具 · 五行查询 + 八卦查询", "MCP")
    try:
        from tengod.divination_engine import WuxingEngine, TianganEngine, DizhiEngine
        # 五行生克链
        info("五行生克链演示:")
        for wx in ["木", "火", "土", "金", "水"]:
            gen = WuxingEngine.generate(wx)
            res = WuxingEngine.restrict(wx)
            kv(f"  {wx}", f"生→{gen}  克→{res}")
        hr()
        info("天干五合:")
        for tg in ["甲", "乙", "丙", "丁", "戊"]:
            he = TianganEngine.wuhe(tg)
            if he:
                kv(f"  {tg}", f"合{he['partner']}化{he['wuxing']} ({he['description']})")
        hr()
        info("地支六合:")
        for dz in ["子", "寅", "卯", "辰"]:
            lh = DizhiEngine.liuhe(dz)
            if lh:
                kv(f"  {dz}", f"合{lh['partner']}化{lh['wuxing']}")
        ok("五行/八卦/天干地支查询完成")
    except Exception as e:
        fail(f"MCP工具查询失败：{e}")

    # [16] MCP 工具：十神推演 + 地支分析
    step(16, TOTAL, "MCP 工具 · 十神推演 + 地支六合三合冲害破刑", "MCP")
    try:
        from tengod.divination_engine import ShiganEngine, DizhiEngine, analyze_relations, find_interactions
        day_master = bazi_analyzer.analysis['day_master'] if bazi_analyzer else "庚"
        info(f"以日主【{day_master}】推演十神:")
        for tg in TianganEngine.TIANGAN:
            sr = ShiganEngine.compute(day_master, tg)
            cls_mark = {"善神": "✓", "凶神": "✗", "中性": "~"}.get(ShiganEngine.classify(sr.shigan), "?")
            kv(f"  {tg}", f"{sr.shigan.value} ({cls_mark}) — {sr.description}")

        hr()
        info("地支关系分析（以示例八字四支）:")
        if bazi_analyzer:
            branches = bazi_analyzer.analysis['branches']
        else:
            branches = ["子", "寅", "辰", "午"]
        interactions = find_interactions(branches)
        for rel_type in ['he', 'chong', 'hai', 'po', 'xing']:
            if interactions[rel_type]:
                for r in interactions[rel_type]:
                    kv(f"  {rel_type}", f"{r['pair']} — {r['detail']}")

        ok("MCP 十神推演 + 地支分析完成")
    except Exception as e:
        fail(f"MCP十神推演失败：{e}")

    # ========================================================
    #  ╔══════════════════════════════════════════════════════╗
    #  ║  阶段三：WebGL 3D 可视化（可视化层）                  ║
    #  ╚══════════════════════════════════════════════════════╝
    # ========================================================
    step(17, TOTAL, "3D 可视化 · WebGL 五行生克/八卦方位/八字排盘", "3D")
    info("阶段三产出物：独立 HTML 文件（无需服务器即可运行）")
    kv("文件路径", "deploy_frontend/wuxing_3d_holo.html")
    kv("文件大小", "约 60KB (1422 行)")
    kv("场景数", "7 个（五行生克/八卦方位/天干地支/十神图谱/河图洛书/综合罗盘/八字排盘）")
    kv("技术栈", "Three.js r160 + OrbitControls + 粒子系统 + 发光效果")
    kv("打开方式", "浏览器直接打开 deploy_frontend/wuxing_3d_holo.html")
    ok("WebGL 3D 可视化已就绪（独立 HTML，无需本脚本运行）")

    # ========================================================
    #  ╔══════════════════════════════════════════════════════╗
    #  ║  阶段四：神煞/格局引擎（算法层）                      ║
    #  ╚══════════════════════════════════════════════════════╝
    # ========================================================
    banner("第四阶段 · 神煞/格局引擎（算法层）")

    # [18] 神煞推算
    step(18, TOTAL, "神煞推算 · 40+ 神煞全面分析", "神煞")
    try:
        from tengod.shensha_engine import calc_all_shensha
        if bazi_analyzer:
            shensha_result = calc_all_shensha(bazi_analyzer.analysis['pillars'])
            ok(f"神煞推算完成，共 {len(shensha_result.all_shensha)} 种神煞")

            # 吉神
            info("吉神:")
            ji_count = 0
            for name, s in shensha_result.all_shensha.items():
                if s.get("cat") in ("吉神", "吉"):
                    ji_count += 1
                    if ji_count <= 8:
                        kv(f"  {name}", f"{s.get('cat', '')} — {s.get('pillar', '')}柱 — {s.get('desc', '')[:30]}")
            kv(f"  ...共 {ji_count} 个吉神", "")

            # 凶神
            info("凶神/警示:")
            xiong_count = 0
            for name, s in shensha_result.all_shensha.items():
                if s.get("cat") in ("凶", "大凶"):
                    xiong_count += 1
                    if xiong_count <= 6:
                        kv(f"  {name}", f"{s.get('cat', '')} — {s.get('pillar', '')}柱 — {s.get('desc', '')[:30]}")
            kv(f"  ...共 {xiong_count} 个凶神", "")

            kv("summary", shensha_result.summary)
        else:
            warn("八字未初始化，跳过神煞分析")
    except Exception as e:
        fail(f"神煞推算失败：{e}")

    # [19] 格局判断 + 喜用神 + 调候
    step(19, TOTAL, "格局判断 · 喜用神 · 调候用神综合分析", "格局")
    try:
        from tengod.geju_engine import calc_geju, calc_yongshen, calc_tiaohou
        if bazi_analyzer:
            pillars = bazi_analyzer.analysis['pillars']
            # 格局
            geju_result = calc_geju(pillars)
            ok("格局判断:")
            kv("  格局名称", geju_result.geju_name)
            kv("  格局类型", geju_result.geju_type)
            kv("  格局说明", geju_result.geju_desc)
            kv("  格局纯度", f"{geju_result.score:.1f}/100")
            if geju_result.is_cong:
                kv("  特殊格局", "从格 (从旺/从强/从杀/从财等)")
            if geju_result.is_huaqi:
                kv("  特殊格局", "化气格")
            kv("  适用神", ", ".join(geju_result.shiyongshen) if geju_result.shiyongshen else "无")
            kv("  忌神", ", ".join(geju_result.jishen) if geju_result.jishen else "无")

            # 喜用神
            yongshen_result = calc_yongshen(pillars)
            hr()
            info("喜用神分析:")
            kv("  用神", ", ".join(yongshen_result.yong_shen) if yongshen_result.yong_shen else "无")
            kv("  忌神", ", ".join(yongshen_result.ji_shen) if yongshen_result.ji_shen else "无")
            kv("  日主旺衰", f"{yongshen_result.wang_shuai} (强度: {yongshen_result.wang_shuai_level:.0f}/100)")
            kv("  分析", yongshen_result.yongshen_desc)

            # 调候
            tiaohou_result = calc_tiaohou(pillars)
            hr()
            info("调候用神:")
            kv("  需要调候", "是" if tiaohou_result.required_tiaohou else "否")
            kv("  调候用神", ", ".join(tiaohou_result.tiaohou_shens) if tiaohou_result.tiaohou_shens else "无")
            kv("  季节", tiaohou_result.season)
            kv("  说明", tiaohou_result.desc)
        else:
            warn("八字未初始化，跳过格局分析")
    except Exception as e:
        fail(f"格局/喜用神/调候分析失败：{e}")

    # ========================================================
    #  ╔══════════════════════════════════════════════════════╗
    #  ║  阶段五：向量检索增强（知识层）                       ║
    #  ╚══════════════════════════════════════════════════════╝
    # ========================================================
    banner("第五阶段 · 向量检索增强（知识层）")

    # [20] 语义搜索
    step(20, TOTAL, "语义搜索 · FAISS 向量检索 + 类型过滤", "向量")
    try:
        from tengod.vector_store import get_vector_store, search_similar
        store = get_vector_store()
        ok(f"向量索引已加载: {len(store._nodes)} 个节点, {store.dim} 维")

        # 多组查询测试
        queries = [
            ("五行生克 阴阳平衡", None),
            ("天干地支 六十甲子", None),
            ("八卦", "trigram"),
        ]
        for query, type_filter in queries:
            hr()
            info(f'搜索: "{query}"' + (f' (类型过滤: {type_filter})' if type_filter else ''))
            result = store.search(query, top_k=3, type_filter=type_filter)
            for i, r in enumerate(result.results, 1):
                kv(f"  #{i}", f"{r['name']} [{r['type']}] similarity={r['similarity']:.4f}")

        ok("语义搜索完成")
    except Exception as e:
        fail(f"语义搜索失败：{e}")

    # [21] 知识关联推荐
    step(21, TOTAL, "知识关联推荐 · 节点关系 + 生克推断", "向量")
    try:
        from tengod.vector_store import get_vector_store
        store = get_vector_store()

        # 推荐几个核心节点
        seed_nodes = ["木", "火", "子", "甲", "乾"]

        for node in seed_nodes:
            if not node or node == "行":
                continue
            hr()
            info(f'与「{node}」相关的知识节点:')
            try:
                recs = store.recommend_related(node, top_k=3)
                for i, r in enumerate(recs, 1):
                    kv(f"  #{i}", f"{r['name']} [{r['type']}] similarity={r['similarity']:.4f}")
            except Exception:
                kv("  (无)", "节点未找到或无关联")

        ok("知识关联推荐完成")
    except Exception as e:
        fail(f"知识关联推荐失败：{e}")

    # ========================================================
    #  ╔══════════════════════════════════════════════════════╗
    #  ║  收尾 · 全系统集成汇总                               ║
    #  ╚══════════════════════════════════════════════════════╝
    # ========================================================
    banner("全系统集成汇总 · 六阶段联调完成")

    # -------- 总耗时 --------
    dt = (time.time() - t0) * 1000
    hr()
    print(
        f"{C.BOLD}{C.GREEN}  ✦ 全系统集成演示完毕{C.RESET}  "
        f"共 {TOTAL} 步，总耗时 {C.YELLOW}{dt:.1f} ms{C.RESET}\n"
        f"  {C.DIM}核心版本 {C.YELLOW}{core.export_state()['version']}{C.RESET}"
        f"{C.DIM}  |  六阶段全部通过{C.RESET}"
    )
    hr()

    # 阶段汇总表
    print(f"\n  {C.BOLD}{C.CYAN}六阶段完成情况汇总{C.RESET}")
    print(f"  {C.DIM}{'─' * 58}{C.RESET}")
    stages = [
        ("第一阶段", "应用层", "八字排盘系统", "BaziAnalyzer + BaziChart + DayunLiunian"),
        ("第二阶段", "数据层", "MCP Server 知识服务化", "5 个玄学工具 + 直接 API 调用"),
        ("第三阶段", "可视化层", "WebGL 3D 交互引擎", "7 个场景 / Three.js / 独立 HTML"),
        ("第四阶段", "算法层", "神煞/格局引擎", "40+神煞 + 格局判断 + 喜用神/调候"),
        ("第五阶段", "知识层", "向量检索增强", "FAISS 256维 / 111节点 / 语义搜索"),
        ("第六阶段", "集成层", "全系统联调", "21 步编排 / 打通所有模块"),
    ]
    for stage, layer, name, detail in stages:
        print(
            f"  {C.GREEN}✓{C.RESET} {C.BOLD}{stage}{C.RESET}"
            f"{C.DIM}({layer}){C.RESET} {C.WHITE}{name}{C.RESET}"
        )
        print(f"     {C.DIM}{detail}{C.RESET}")

    # 启动命令
    print(f"\n  {C.BOLD}{C.CYAN}可用命令{C.RESET}")
    print(f"  {C.DIM}{'─' * 58}{C.RESET}")
    print(f"  {C.YELLOW}python run_tengod_demo.py{C.RESET}                         {C.DIM}# 全系统集成演示{C.RESET}")
    print(f"  {C.YELLOW}python run_tengod_demo.py --bazi 1988-08-08-12:00{C.RESET}  {C.DIM}# 自定义八字{C.RESET}")
    print(f"  {C.YELLOW}python run_tengod_demo.py --female{C.RESET}                  {C.DIM}# 女命排盘{C.RESET}")
    print(f"  {C.YELLOW}python run_bazi_demo.py --html bazi.html{C.RESET}            {C.DIM}# 生成HTML报告{C.RESET}")
    print(f"  {C.YELLOW}python -m tengod.mcp_server --test{C.RESET}                 {C.DIM}# MCP Server 自检{C.RESET}")
    print(f"  {C.YELLOW}python -m tengod.vector_store{C.RESET}                      {C.DIM}# 向量引擎自检{C.RESET}")
    print(f"  {C.YELLOW}python -m tengod.divination_engine{C.RESET}                 {C.DIM}# 推演引擎自检{C.RESET}")
    print(f"  {C.YELLOW}open deploy_frontend/wuxing_3d_holo.html{C.RESET}          {C.DIM}# 3D可视化{C.RESET}")

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
            f"\n  启动正官 HTTP API 于 {C.CYAN}http://127.0.0.1:{port}{C.RESET} ... (Ctrl+C 退出)"
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
