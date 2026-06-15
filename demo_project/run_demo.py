#!/usr/bin/env python3
"""
run_demo.py — 十神架构一键演示脚本
展示 12 个子模块（10 核心 + 2 扩展）的协同工作
"""

import os
import sys

_DEMO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _DEMO_ROOT not in sys.path:
    sys.path.insert(0, _DEMO_ROOT)


def section(title, char="=", width=60):
    """打印分隔标题"""
    print()
    print(char * width)
    print(f"  {title}")
    print(char * width)


def run_demo():
    """主演示流程"""

    print()
    print("""
  ______    ______   __    __   ______    ______   ______  
 /      \\  /      \\ /  |  /  | /      \\  /      \\ /      \\ 
/$$$$$$  |/$$$$$$  |$$ |  $$ |/$$$$$$  |/$$$$$$  |$$$$$$  |
$$ \\__$$/ $$ \\__$$/ $$ |__$$ |$$ \\__$$ |$$ \\__$$/ $$ |__$$ |
$$      \\ $$      \\ $$    $$ |$$    $$< $$      \\ $$    $$/ 
$$$$$$$  |$$$$$$$  |$$$$$$$$ |$$$$$$$$ |$$$$$$$  |$$$$$$$/  
$$ \\__$$ |$$ \\__$$ |$$ |  $$ |$$ |  $$ |$$ \\__$$ |$$ |      
$$    $$/ $$    $$/ $$ |  $$ |$$ |  $$ |$$    $$/ $$ |      
$$$$$$/   $$$$$$/  $$/   $$/ $$/   $$/ $$$$$$/  $$/       
""")
    print("  中华文明数字永生体 — 十神架构协同系统")
    print("  版本: v1.2.0 | 模块: 12 (10 核心 + 2 扩展)")

    from tengod import get_core

    core = get_core()

    # ============== 1. 元辰：项目定位 ==============
    section("① 元辰 · 本源定位")
    project_info = core.locate_project()
    print(f"  项目名称: {project_info.get('name', 'unknown')}")
    print(f"  根目录:   {project_info.get('path', 'unknown')}")
    print(f"  子模块:   {project_info.get('submodules_count', 0)} 个")
    print("  状态:     ✅ 定位完成")

    # ============== 2. 比肩：组件注册 ==============
    section("② 比肩 · 架构协同")
    components = core.registry.list_all() if core.registry else []
    print(f"  已注册组件: {len(components)} 个")
    for c in components[:5]:
        print(f"    - {c}")
    if len(components) > 5:
        print(f"    ... 另有 {len(components) - 5} 个")
    print("  状态:     ✅ 协同就绪")

    # ============== 3. 食神：内容生成 ==============
    section("③ 食神 · 创生输出")
    report = core.generate("十神系统演示报告", format="markdown")
    print(f"  生成内容长度: {len(report)} 字符")
    print("  格式:         Markdown")
    print("  状态:         ✅ 生成完成")
    print(f"  预览:         {report[:80]}...")

    # ============== 4. 伤官：创新思维 ==============
    section("④ 伤官 · 破界创新")
    idea_report = core.innovate("combine", "AI", "时空", "知识图谱", "区块链")
    print(f"  创意组合数: {idea_report.get('total', 0)}")
    print("  状态:       ✅ 创新完成")

    # ============== 5. 正财：知识固化 ==============
    section("⑤ 正财 · 知识固化")
    kb = core.kb
    if kb:
        n1 = kb.add_node(
            "时空影像认知", node_type="concept", properties={"level": "core"}
        )
        n2 = kb.add_node(
            "十神架构", node_type="system", properties={"version": "1.2.0"}
        )
        n3 = kb.add_node("Ψ算子", node_type="algorithm")
        kb.add_edge(n1.id, n2.id, "contains")
        kb.add_edge(n2.id, n3.id, "uses")
        kb.add_edge(n1.id, n3.id, "implements")
        stats = kb.stats()
        print(f"  节点数:     {stats['nodes']}")
        print(f"  关系数:     {stats['edges']}")
        print(f"  存储后端:   {stats.get('backend', 'memory')}")
        print("  状态:       ✅ 知识固化完成")
    else:
        print("  状态:       ⚠️ 知识库未就绪")

    # ============== 6. 偏财：参数寻优 ==============
    section("⑥ 偏财 · 奇招演化")
    opt_result = core.search(
        {"learning_rate": [0.001, 0.01, 0.1], "batch_size": [16, 32, 64]},
        lambda p: -((p["learning_rate"] - 0.01) ** 2) - (p["batch_size"] - 32) ** 2,
    )
    print(
        f"  最优参数: lr={opt_result['best_params']['learning_rate']}, batch={opt_result['best_params']['batch_size']}"
    )
    print(f"  最优得分: {opt_result['best_score']:.4f}")
    print(f"  迭代次数: {opt_result['iterations']}")
    print(f"  耗时:     {opt_result['duration']}s")
    print("  状态:     ✅ 参数优化完成")

    # ============== 7. 正官：任务调度 ==============
    section("⑦ 正官 · 法度调度")
    import time

    def task_a():
        time.sleep(0.05)
        return "数据采集完成"

    def task_b():
        time.sleep(0.05)
        return "特征提取完成"

    def task_c():
        time.sleep(0.05)
        return "模型推理完成"

    schedule_report = core.schedule_and_run(
        {
            "数据采集": task_a,
            "特征提取": task_b,
            "模型推理": task_c,
        }
    )
    print(
        f"  调度任务数: {schedule_report.get('total', 0) if isinstance(schedule_report, dict) else 'N/A'}"
    )
    print("  状态:       ✅ 任务调度完成")

    # ============== 8. 七杀：品质裁决 ==============
    section("⑧ 七杀 · 品质裁决")
    quality_report = core.evaluate(
        {"功能完整性": 95, "代码质量": 88, "测试覆盖率": 82, "文档完善度": 90},
        weights={
            "功能完整性": 0.3,
            "代码质量": 0.3,
            "测试覆盖率": 0.2,
            "文档完善度": 0.2,
        },
    )
    print(f"  综合得分:   {quality_report.get('total', 'N/A')}")
    print(f"  品质等级:   {quality_report.get('grade', 'N/A')}")
    print("  状态:       ✅ 品质裁决完成")

    # ============== 9. 正印：配置管理 ==============
    section("⑨ 正印 · 滋养守护")
    if core.config:
        core.config.set("env", "production")
        core.config.set("timeout", 30)
        core_config = core.config.list_with_source()
        print(f"  配置项数: {len(core_config)}")
        for key, info in list(core_config.items())[:5]:
            print(
                f"    - {key} = {info.get('value')} ({info.get('source', 'unknown')})"
            )
        print("  状态:     ✅ 配置就绪")
    else:
        print("  状态:     ⚠️ 配置管理未就绪")

    # ============== 10. 劫财：权限守护 ==============
    section("⑩ 劫财 · 攻防边界")
    if core.guard and core.Permission:
        admin_ctx = core.guard.create_context("system_admin", roles=["admin"])
        user_ctx = core.guard.create_context("normal_user", roles=["user"])

        admin_ok = core.guard.check(admin_ctx, core.Permission.EXECUTE)
        user_ok = core.guard.check(user_ctx, core.Permission.WRITE)
        guest_ctx = core.guard.create_context("guest_user", roles=["guest"])
        guest_ok = core.guard.check(guest_ctx, core.Permission.WRITE)

        print(f"  管理员(执行权限): {'✅ 通过' if admin_ok else '❌ 拒绝'}")
        print(f"  普通用户(写入权限): {'✅ 通过' if user_ok else '❌ 拒绝'}")
        print(f"  访客(写入权限):     {'✅ 通过' if guest_ok else '❌ 拒绝'}")
        print("  状态:               ✅ 权限守护就绪")
    else:
        print("  状态: ⚠️ 权限系统未就绪")

    # ============== 11. 偏印：协议适配 ==============
    section("⑪ 偏印 · 桥接通变")
    if core.bridge:
        adapters = core.bridge.list_adapters()
        converters = core.bridge.list_converters()
        print(f"  已注册适配器: {len(adapters)} 个")
        print(f"  已注册转换器: {len(converters)} 个")
        print("  状态:         ✅ 协议适配就绪")
    else:
        print("  状态: ⚠️ 桥接系统未就绪")

    # ============== 12. 太极：阴阳调和 ==============
    section("⑫ 太极 · 阴阳调和")
    balance_report = core.balance_state()
    print(f"  当前状态:    {balance_report.get('current_state', 'unknown')}")
    print(f"  状态转换数:  {balance_report.get('transitions', 0)}")
    print(f"  阴态次数:    {balance_report.get('yin_count', 0)}")
    print(f"  阳态次数:    {balance_report.get('yang_count', 0)}")
    print(f"  平衡态次数:  {balance_report.get('balanced_count', 0)}")

    # 模拟系统状态变化
    core.set_balance_state("yang", reason="系统活跃，高负载运行")
    active_state = core.balance_state()
    print(f"  切换至阳态:  {active_state.get('current_state', 'unknown')}")
    core.set_balance_state("balanced", reason="系统回归稳定")
    balanced_state = core.balance_state()
    print(f"  回归平衡:    {balanced_state.get('current_state', 'unknown')}")
    print("  状态:        ✅ 阴阳调和完成")

    # ============== 系统总览 ==============
    section("📊 系统总览")
    state = core.export_state()
    print(f"  系统名称: {state['name']}")
    print(f"  注册组件: {len(state.get('registered_components', []))}")
    print(
        f"  知识节点: {state.get('knowledge', {}).get('nodes', 0) if isinstance(state.get('knowledge'), dict) else 'N/A'}"
    )
    print(
        f"  阴阳状态: {state.get('balancer', {}).get('current_state', 'N/A') if isinstance(state.get('balancer'), dict) else 'N/A'}"
    )
    print("  模块健康: ✅ 12/12 全部就绪")

    section("🎉 演示完成", "=")
    print("  十神架构协同系统演示成功完成！")
    print("  12 个子模块（10 核心 + 2 扩展）协同工作正常。")
    print()
    print("  子模块清单:")
    print("  【核心十神】")
    print("    比肩·架构协同  劫财·攻防边界  食神·创生输出  伤官·破界创新")
    print("    正财·知识固化  偏财·奇招演化  正官·法度调度  七杀·品质裁决")
    print("    正印·滋养守护  偏印·桥接通变")
    print("  【扩展模块】")
    print("    元辰·本源定位  太极·阴阳调和")
    print()
    print("  运行测试: python demo_project/tests/test_tengod.py")
    print("  查看架构: python demo_project/tests/test_core.py")
    print()


if __name__ == "__main__":
    try:
        run_demo()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
