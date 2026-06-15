#!/usr/bin/env python3
"""
run_pipeline.py — 十神架构端到端协同工作流演示 v1.5.0
演示 12 模块的协同闭环：从知识检索到创意生成到质量评估的完整链路。

用法：
    python run_pipeline.py                # 运行标准演示
    python run_pipeline.py --serve 8000   # 运行演示 + 启动 HTTP 服务
    python run_pipeline.py --scan         # 扫描项目生成知识图谱
    python run_pipeline.py --oracle       # 测试推背图 Oracle
"""

import os
import sys
import json
import time
from typing import Any, Dict, List

# 确保可导入十神模块
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TENGOD_DIR = os.path.join(_SCRIPT_DIR, "tengod")
if _TENGOD_DIR not in sys.path:
    sys.path.insert(0, _TENGOD_DIR)

if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


def print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(label: str, result: Any, indent: int = 2) -> None:
    prefix = " " * indent
    if isinstance(result, dict):
        for k, v in result.items():
            if isinstance(v, dict):
                print(f"{prefix}{label}.{k}:")
                for sk, sv in v.items():
                    print(f"{prefix}  {sk}: {sv}")
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                print(f"{prefix}{label}.{k}: [{len(v)} items]")
                for item in v[:3]:
                    print(f"{prefix}  {item}")
            else:
                print(f"{prefix}{label}.{k}: {v}")
    else:
        print(f"{prefix}{label}: {result}")


def demo_2_1_food_god_creator(core) -> Dict[str, Any]:
    """2.1 食神+伤官：用 LLM 生成实际可执行的创新方案"""
    print_section("2.1 食神+伤官 — 创意→方案→评估闭环")

    # 注入生成器
    core.innovator.set_generator(core.generator)

    print("  [1] 生成创意：主题='AI辅助古典文学研究'")
    idea = core.innovator.generate_with_llm("AI辅助古典文学研究", style="creative")
    if idea:
        print(f"      创意ID: {idea.id}")
        print(f"      标题: {idea.title}")
        print(f"      类型: {idea.innovation_type}")
        print(f"      描述: {idea.description[:80]}...")
        print(f"      可行性: {idea.feasibility}, 影响力: {idea.impact}")
    else:
        print("      (LLM生成器未就绪，使用内置组合创意)")
        core.innovator.combine(["AI", "古典文学", "研究"])
        ideas = core.innovator.top_ideas(3)
        if ideas:
            idea = ideas[0]
            print(f"      创意ID: {idea.id}, 标题: {idea.title}")

    print("  [2] 详细化创意方案")
    if idea:
        elaboration = core.innovator.elaborate_idea(idea.id, style="detailed")
        if elaboration:
            print(f"      方案长度: {len(elaboration)} 字符")
            print(f"      方案概要: {elaboration[:120]}...")
        else:
            print("      (LLM未就绪，跳过)")

    print("  [3] LLM评估")
    if idea:
        evaluation = core.innovator.evaluate_with_llm(idea.id)
        if evaluation:
            print(f"      评分: {evaluation}")
        else:
            print("      (LLM未就绪，跳过)")

    print("  [4] 保存到知识库")
    if idea and core.kb:
        kn = core.innovator.idea_to_knowledge(idea.id, core.kb)
        if kn:
            print(f"      知识节点: {kn.get('name', 'N/A')}")
        else:
            print("      (保存失败)")

    print("  [5] 完整Pipeline（不使用LLM）")
    pipeline_result = core.innovator.pipeline(
        ["中华文明", "数字化", "保护"], use_llm=False, save_to_kb=core.kb
    )
    print_result("Pipeline", pipeline_result, 4)

    return pipeline_result


def demo_2_2_async_search(core) -> Dict[str, Any]:
    """2.2 偏财+正官：超参搜索作为异步任务"""
    print_section("2.2 偏财+正官 — 异步超参搜索")

    from 偏财_奇招演化.search_optimizer import (
        SearchOptimizer, SearchSpace, AsyncOptimizer, submit_async,
    )

    space = SearchSpace(param_ranges={
        "learning_rate": (0.0, 1.0),
        "layers": (1, 10),
    })
    optimizer = SearchOptimizer(space, mode="random")

    def dummy_objective(params: Dict[str, Any]) -> float:
        return params.get("learning_rate", 0.5) * params.get("layers", 5) * 0.1

    print("  [1] 提交异步搜索任务")
    task_id = optimizer.optimize_async(dummy_objective, n_trials=5)
    print(f"      任务ID: {task_id}")

    print("  [2] 同步搜索验证")
    result = optimizer.optimize(dummy_objective, n_trials=5)
    print(f"      最佳分数: {result.best_score:.4f}")
    print(f"      迭代次数: {result.iterations}")

    return {"task_id": task_id, "result": result.best_score}


def demo_2_3_batch_import(core) -> Dict[str, Any]:
    """2.3 正财+偏印：批量导入知识节点"""
    print_section("2.3 正财+偏印 — 批量导入（JSON/CSV/YAML）")
    import tempfile, os

    # JSON导入
    print("  [1] JSON批量导入")
    json_data = json.dumps([
        {"name": "屈原", "node_type": "poet",
         "properties": {"作品": "离骚/九歌", "年代": "战国"}},
        {"name": "华佗", "node_type": "medicine",
         "properties": {"贡献": "麻沸散/五禽戏", "年代": "东汉"}},
        {"name": "张衡", "node_type": "scientist",
         "properties": {"发明": "地动仪/浑天仪", "年代": "东汉"}},
    ], ensure_ascii=False)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        f.write(json_data)
        json_file = f.name
    try:
        json_result = core.kb.import_from_json(json_file)
        print_result("JSON导入", json_result, 4)
    finally:
        os.unlink(json_file)

    # CSV导入
    print("  [2] CSV批量导入")
    csv_data = "name,node_type,key1,key2\n祖冲之,math,圆周率,大明历\n张仲景,medicine,伤寒论,辨证论治"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_data)
        csv_file = f.name
    try:
        csv_result = core.kb.import_from_csv(csv_file)
        print_result("CSV导入", csv_result, 4)
    finally:
        os.unlink(csv_file)

    # 统计
    stats = core.kb.stats()
    print(f"      知识库总计: {stats.get('nodes', 0)} 个节点, {stats.get('edges', 0)} 条边")

    return {"json": json_result, "csv": csv_result}


def demo_2_4_config_quality(core) -> Dict[str, Any]:
    """2.4 七杀+正印：配置变更触发质量评估"""
    print_section("2.4 七杀+正印 — 配置变更→质量评估联动")

    # 初始化配置
    core.config.set("quality_threshold", 80)
    core.config.set("code_style", "pep8")
    core.config.set("max_line_length", 120)

    print("  [1] 当前配置")
    config_list = core.config.list_all()
    for k, v in config_list.items():
        print(f"      {k}: {v}")

    print("  [2] 质量评估（基于配置触发）")
    core.judge.reset()
    threshold = int(core.config.get("quality_threshold") or 80)
    core.judge.add_score("config_compliance", threshold, weight=0.4, comment="配置合规性")
    core.judge.add_score("code_quality", 90, weight=0.6, comment="代码质量")
    report = core.judge.report()
    print_result("评估报告", report, 4)

    return report


def demo_2_5_balance_degradation(core) -> Dict[str, Any]:
    """2.5 太极+比肩：负载过高时自动降级"""
    print_section("2.5 太极+比肩 — 自动降级模式")

    # 注册降级处理器
    degradation_flags: Dict[str, bool] = {"degraded": False}

    def handle_degradation(metrics: Dict[str, Any]) -> None:
        degradation_flags["degraded"] = True
        degradation_flags["reason"] = metrics.get("reason", "")
        degradation_flags["recommendations"] = metrics.get("recommendations", [])
        print(f"      [降级处理器] 触发: {metrics['reason']}")

    core.balancer.set_degradation_handler(handle_degradation)

    # 正常负载
    print("  [1] 正常负载")
    result_normal = core.balancer.auto_balance({"cpu": 0.3, "memory": 0.4, "error_rate": 0.01})
    print_result("正常", result_normal, 4)
    print(f"      降级触发: {degradation_flags['degraded']}")

    # 高负载
    print("  [2] 高负载（CPU 95%）")
    degradation_flags["degraded"] = False
    result_high = core.balancer.auto_balance({"cpu": 0.95, "memory": 0.85, "error_rate": 0.15})
    print_result("高负载", result_high, 4)
    print(f"      降级触发: {degradation_flags['degraded']}")

    return {"normal": result_normal, "high": result_high}


def demo_2_6_project_scan(core) -> Dict[str, Any]:
    """2.6 元辰+正财：自动扫描项目生成知识图谱"""
    print_section("2.6 元辰+正财 — 项目扫描→知识图谱")

    if not core.locator:
        print("      元辰模块未就绪")
        return {"error": "locator unavailable"}

    core.locator.locate()

    print("  [1] 项目扫描")
    files = core.locator.scan_files(max_depth=3)
    py_count = sum(1 for f in files if f["ext"] == ".py")
    dir_count = sum(1 for f in files if f["is_dir"])
    print(f"      文件总数: {len(files)}, Python: {py_count}, 目录: {dir_count}")

    print("  [2] 生成知识图谱节点")
    stats = core.locator.scan_to_knowledge(core.kb)
    print_result("图谱生成", stats, 4)

    # 验证知识库已更新
    kb_stats = core.kb.stats()
    print(f"      知识库总计: {kb_stats.get('nodes', 0)} 个节点, {kb_stats.get('edges', 0)} 条边")

    return stats


def demo_3_1_bayesian_optimization() -> Dict[str, Any]:
    """3.1 偏财：贝叶斯优化"""
    print_section("3.1 偏财 — 贝叶斯优化")

    from 偏财_奇招演化.search_optimizer import SearchOptimizer, SearchSpace

    space = SearchSpace(param_ranges={
        "x": (-5.0, 5.0),
        "y": (-5.0, 5.0),
    })
    optimizer = SearchOptimizer(space, mode="bayes")

    # 目标函数：寻找最小值 (x-1)^2 + (y+2)^2 + 3
    def objective(params: Dict[str, Any]) -> float:
        x = params.get("x", 0.0)
        y = params.get("y", 0.0)
        return -((x - 1.0) ** 2 + (y + 2.0) ** 2 + 3.0)  # 取负以最大化

    print("  [1] 贝叶斯优化: 寻找 (x-1)^2 + (y+2)^2 + 3 的最小值")
    print("      理论最小值: f(1.0, -2.0) = 3.0")

    result = optimizer.optimize_bayes(objective, n_trials=10, maximize=True)
    print(f"      最优参数: x={result.best_params.get('x', 'N/A'):.4f}, y={result.best_params.get('y', 'N/A'):.4f}")
    print(f"      最优值: {-result.best_score:.4f}")
    print(f"      迭代次数: {result.iterations}")

    # 搜索历史
    history = optimizer.get_history()
    print(f"      历史记录: {len(history)} 条")
    if history:
        print(f"      前3条: {history[:3]}")

    return {"best_params": result.best_params, "best_value": -result.best_score}


def demo_3_2_vector_search(core) -> Dict[str, Any]:
    """3.2 正财：向量语义检索"""
    print_section("3.2 正财 — 向量语义检索")

    print("  [1] 语义查询: '道家哲学思想'")
    results = core.kb.query_nearest("道家哲学思想", top_k=3)
    print(f"      返回 {len(results)} 条")
    for r in results:
        print(f"      [{r.get('score', 0):.4f}] {r.get('name', 'N/A')} ({r.get('node_type', 'N/A')})")

    print("  [2] 向量搜索: '中国古代医学成就'")
    vec_results = core.kb.vector_search("中国古代医学成就", top_k=3)
    if vec_results:
        print(f"      返回 {len(vec_results)} 条")
        for r in vec_results[:3]:
            print(f"      [{r.get('score', 0):.4f}] {r.get('name', 'N/A')}")
    else:
        print("      (向量搜索返回空，可能未初始化向量DB)")

    return {"semantic": results, "vector": vec_results}


def demo_3_4_code_scanner() -> Dict[str, Any]:
    """3.4 七杀：flake8/pylint代码质量扫描"""
    print_section("3.4 七杀 — 代码质量自动扫描")

    from 七杀_品质裁决.code_scanner import CodeScanner
    from 七杀_品质裁决.quality_judge import QualityJudge

    scanner = CodeScanner(_TENGOD_DIR)
    judge = QualityJudge()

    print("  [1] 查找 Python 文件")
    py_files = scanner._find_python_files(_TENGOD_DIR)
    print(f"      发现 {len(py_files)} 个 .py 文件")

    print("  [2] 运行质量扫描 (内置分析)")
    # 使用内置扫描（不依赖外部工具）
    from 七杀_品质裁决.code_scanner import ScanReport, ScanIssue, ScanLevel
    report = ScanReport(tool="tengod_builtin", total_issues=0)

    # 内置静态分析: 检查文件大小、行数、命名等
    for fpath in py_files[:20]:  # 限制数量
        fname = os.path.basename(fpath)
        try:
            with open(fpath, 'r') as f:
                lines = f.readlines()
            size = os.path.getsize(fpath)
            # 检查大文件
            if size > 50000:
                report.issues.append(ScanIssue(
                    file_path=fpath, line=0, level=ScanLevel.WARNING,
                    code="SIZE001", message=f"文件过大 ({size} bytes)"
                ))
            # 检查长行
            for i, line in enumerate(lines, 1):
                if len(line.rstrip('\n')) > 120:
                    report.issues.append(ScanIssue(
                        file_path=fpath, line=i, level=ScanLevel.CONVENTION,
                        code="LINE001", message=f"行过长 ({len(line.rstrip())} cols)"
                    ))
            # 检查TODO
            for i, line in enumerate(lines, 1):
                if "TODO" in line and not line.strip().startswith("#"):
                    report.issues.append(ScanIssue(
                        file_path=fpath, line=i, level=ScanLevel.INFO,
                        code="TODO001", message="未处理的TODO"
                    ))
        except Exception:
            pass

    scanner._compute_score(report)
    print(f"      总问题: {report.total_issues}")
    print(f"      评分: {report.score}/100")
    print(f"      分布: {report.by_level}")

    # 写入QualityJudge
    print("  [3] 写入QualityJudge")
    judge.reset()
    judge.add_score("tengod_scan", report.score, weight=1.0,
                    comment=f"内置扫描发现{report.total_issues}个问题")
    judge_report = judge.report()
    print_result("评估", judge_report, 4)

    return {"scan": report, "judge": judge_report}


def demo_5_4_oracle(core) -> Dict[str, Any]:
    """5.4 推背图 Oracle 咨询"""
    print_section("5.4 推背图 Oracle — 认知引擎")

    if not core.oracle:
        print("      Oracle 引擎未就绪")
        return {"error": "oracle unavailable"}

    print("  [1] 咨询: '中华文明传承之道'")
    result = core.consult_oracle("中华文明传承之道")
    print(f"      卦象: {result.get('hexagram', 'N/A')}")
    print(f"      干支: {result.get('gan_zhi', 'N/A')}")
    interpretation = result.get('interpretation', '')
    print(f"      解释: {interpretation[:80]}...")

    print("  [2] Oracle 统计")
    stats = core.oracle.stats()
    print_result("统计", stats, 4)

    return result


def run_full_pipeline(args: List[str]) -> None:
    """运行全部演示工作流"""
    from core import TenGodCore

    core = TenGodCore()
    serve = "--serve" in sys.argv
    do_scan = "--scan" in sys.argv
    do_oracle = "--oracle" in sys.argv

    print("=" * 60)
    print("  十神架构 · 端到端协同工作流演示")
    print(f"  版本: 1.5.0")
    print(f"  模块数: 12")
    print("=" * 60)

    # Phase 2: 协同层
    results: Dict[str, Any] = {}

    results["2.1"] = demo_2_1_food_god_creator(core)
    results["2.2"] = demo_2_2_async_search(core)
    results["2.3"] = demo_2_3_batch_import(core)
    results["2.4"] = demo_2_4_config_quality(core)
    results["2.5"] = demo_2_5_balance_degradation(core)

    if do_scan:
        results["2.6"] = demo_2_6_project_scan(core)
    else:
        print_section("2.6 元辰+正财 — 项目扫描 (使用 --scan 执行)")

    # Phase 3: 高级算法
    results["3.1"] = demo_3_1_bayesian_optimization()
    results["3.2"] = demo_3_2_vector_search(core)
    results["3.4"] = demo_3_4_code_scanner()

    # Phase 5: Oracle
    if do_oracle:
        results["5.4"] = demo_5_4_oracle(core)
    else:
        print_section("5.4 推背图 Oracle (使用 --oracle 执行)")

    # 系统健康检查
    print_section("系统健康检查")
    state = core.export_state()
    print(f"  版本: {state.get('version')} (core: v{core.__class__.__module__})")
    print(f"  功能: {json.dumps(state.get('features', {}), ensure_ascii=False)}")
    kb_stats = state.get("knowledge", {})
    print(f"  知识库: {kb_stats.get('nodes', 0)} 节点, {kb_stats.get('edges', 0)} 边")

    # HTTP 服务
    if serve:
        port = 8000
        for a in sys.argv:
            if a.startswith("--serve="):
                port = int(a.split("=")[1])
            elif a.isdigit() and "--serve" in sys.argv:
                try:
                    port = int(a)
                except ValueError:
                    pass
        print_section("启动 HTTP 服务")
        print(f"  地址: http://localhost:{port}")
        print(f"  端点: /health /metrics /api/status /api/oracle 等")
        core.run(serve=True, host="0.0.0.0", port=port, init_seed=False)
    else:
        print_section("演示完成")
        print("  使用 --serve [port] 启动 HTTP 服务")
        print("  使用 --scan 扫描项目生成知识图谱")
        print("  使用 --oracle 测试推背图 Oracle")


if __name__ == "__main__":
    run_full_pipeline(sys.argv[1:])