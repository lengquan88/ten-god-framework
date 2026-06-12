#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_m25_e2e.py — M2.5 全链路端到端验证脚本

验证链:
  对话输入 → [L1-L8] CognitionPsiBridge.evaluate()
           → CDE校准引擎(含 LaplacianInjector L_st注入)
           → 九宫司命调度(含 ZuowangGridInjector 坐忘注入)
           → 全链闭环反馈

覆盖PRD §六 M2.5 验收标准 + M2.4 端到端闭环:

日期: 2026-05-05
"""

import sys
import os
import time
import json
import math
import numpy as np

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 添加 evaluation-service 目录到 sys.path
_EVAL_SERVICE = os.path.join(PROJECT_ROOT, "spirit-form-api", "evaluation-service")
if _EVAL_SERVICE not in sys.path:
    sys.path.insert(0, _EVAL_SERVICE)


def _load_jiugong():
    """
    加载九宫司命_核心.py（Python 3.14 兼容方式）
    importlib.machinery.util 在 Python 3.14 中不可用，使用 exec 加载
    """
    jg_path = os.path.join(PROJECT_ROOT, "九宫司命_核心.py")
    jg = type(sys)("jiugong")
    with open(jg_path, "r", encoding="utf-8") as f:
        code = f.read()
    exec(code, jg.__dict__)
    return jg

# 全局计数器
_PASSED = 0
_FAILED = 0
_TESTS = []


def test(name: str):
    """测试装饰器：记录测试结果"""
    def decorator(fn):
        _TESTS.append((name, fn))
        return fn
    return decorator


def _ensure_paths():
    """确保所有模块路径可导入"""
    paths = [
        PROJECT_ROOT,
        os.path.join(PROJECT_ROOT, "spirit-form-api", "evaluation-service"),
        os.path.join(PROJECT_ROOT, "topo_semantic"),
        os.path.join(PROJECT_ROOT, "cognition_psi_bridge"),
    ]
    for p in paths:
        if p not in sys.path:
            sys.path.insert(0, p)


def run_all():
    """运行所有注册的测试"""
    global _PASSED, _FAILED
    _ensure_paths()
    print("=" * 70)
    print("  M2.5 全链路端到端验证 (verify_m25_e2e.py)")
    print("  M2.5-A LaplacianInjector + M2.5-B ZuowangGridInjector + E2E闭环")
    print("=" * 70)
    print()

    for name, fn in _TESTS:
        print(f"  >> {name}...", end=" ", flush=True)
        t0 = time.time()
        try:
            fn()
            elapsed = time.time() - t0
            print(f"[OK] ({elapsed:.2f}s)")
            _PASSED += 1
        except Exception as e:
            elapsed = time.time() - t0
            print(f"[FAIL] ({elapsed:.2f}s)")
            print(f"      原因: {e}")
            import traceback
            traceback.print_exc()
            _FAILED += 1
        print()

    total = _PASSED + _FAILED
    print("=" * 70)
    print(f"  汇总: {total} 项 | [OK] {_PASSED} | [FAIL] {_FAILED}")
    print("=" * 70)

    # 生成JSON格式验证报告
    _save_report()
    if _FAILED > 0:
        sys.exit(1)


def _save_report():
    """保存验证报告为JSON"""
    report = {
        "test_suite": "M2.5 全链路端到端验证",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": _PASSED + _FAILED,
        "passed": _PASSED,
        "failed": _FAILED,
        "status": "PASSED" if _FAILED == 0 else "FAILED",
        "test_chain": "对话输入 → L1-L8评估 → CDE校准(LaplacianInjector) → 九宫调度(ZuowangGridInjector) → 闭环反馈",
    }
    report_path = os.path.join(PROJECT_ROOT, "cognition_psi_bridge", "verify_m25_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  验证报告保存至: {report_path}")


# ============================================================================
# 测试1: M2.5-A LaplacianInjector 提取 L_st 特征
# ============================================================================

@test("M2.5-A#1 | LaplacianInjector 从模拟嵌入提取 L_st 特征")
def test_laplacian_extract():
    """验证 LaplacianInjector.extract() 能从嵌入矩阵提取4维L_st特征"""
    from calibration_engine import LaplacianInjector

    injector = LaplacianInjector(alpha=0.3)

    # 创建模拟嵌入（三个簇，有结构）
    np.random.seed(42)
    embeddings = np.random.randn(30, 64).astype(np.float64)
    # 加入聚类结构，产生可测量的谱间隙
    embeddings[:10] += 3.0
    embeddings[10:20] -= 2.0

    features = injector.extract(embeddings=embeddings)

    print()
    print(f"    spectral_gap = {features['spectral_gap']:.4f}")
    print(f"    fiedler_value = {features['fiedler_value']:.4f}")
    print(f"    spectral_entropy = {features['spectral_entropy']:.4f}")
    print(f"    eigenvalue_ratio = {features['eigenvalue_ratio']:.4f}")

    assert "spectral_gap" in features, "缺少 spectral_gap"
    assert "fiedler_value" in features, "缺少 fiedler_value"
    assert "spectral_entropy" in features, "缺少 spectral_entropy"
    assert features["n_nodes"] == 30, f"n_nodes应为30, 实际{features['n_nodes']}"
    # 有结构的嵌入应有正谱间隙
    assert features["spectral_gap"] > 0, f"谱间隙应为正, 实际{features['spectral_gap']}"
    assert features["fiedler_value"] > 0, f"Fiedler值应为正, 实际{features['fiedler_value']}"


@test("M2.5-A#2 | LaplacianInjector 从 snapshot 字典提取特征")
def test_laplacian_snapshot():
    """验证从已有 snapshot 字典提取"""
    from calibration_engine import LaplacianInjector

    injector = LaplacianInjector()
    snapshot_input = {
        "spectral_gap": 0.234,
        "fiedler_value": 0.456,
        "spectral_entropy": 1.234,
        "eigenvalue_ratio": 5.67,
        "topological_complexity": 1.89,
        "n_nodes": 50,
    }

    features = injector.extract(snapshot=snapshot_input)

    assert abs(features["spectral_gap"] - 0.234) < 0.001
    assert abs(features["fiedler_value"] - 0.456) < 0.001
    assert abs(features["spectral_entropy"] - 1.234) < 0.001
    print()
    print(f"    snapshot提取正确: {json.dumps(features, indent=4)}")


@test("M2.5-A#3 | LaplacianInjector.modulate 大谱间隙→增强元认知")
def test_laplacian_modulate_high_gap():
    """验证大谱间隙触发元认知/深度权重增强"""
    from calibration_engine import LaplacianInjector

    injector = LaplacianInjector(alpha=0.3, gap_threshold_high=0.1)
    params = {
        "branch_weights": {"meta_cognition": 0.20, "depth": 0.15, "intent": 0.15, "priority": 0.15},
        "zuowang_threshold": 0.3,
        "consciousness_weight": 0.15,
    }
    l_features = {
        "spectral_gap": 0.25,    # 大于高阈值
        "fiedler_value": 0.15,   # 低于0.3，不触发规则3
        "spectral_entropy": 0.3,
    }

    mod_params, action = injector.modulate(params, l_features)

    print()
    print(f"    action: {action}")
    old_meta = params["branch_weights"]["meta_cognition"]
    new_meta = mod_params["branch_weights"]["meta_cognition"]
    print(f"    meta_cognition: {old_meta:.3f} -> {new_meta:.3f}")
    assert new_meta > old_meta, f"元认知权重应上升: {old_meta:.3f} -> {new_meta:.3f}"
    assert "谱间隙" in action, f"动作描述应包含谱间隙: {action}"


@test("M2.5-A#4 | LaplacianInjector.modulate 小谱间隙+高熵→降低坐忘阈值")
def test_laplacian_modulate_low_gap():
    """验证小谱间隙+高谱熵触发坐忘阈值下调"""
    from calibration_engine import LaplacianInjector

    injector = LaplacianInjector(alpha=0.3, gap_threshold_low=0.05)
    params = {
        "branch_weights": {"meta_cognition": 0.20},
        "zuowang_threshold": 0.3,
        "consciousness_weight": 0.15,
    }
    l_features = {
        "spectral_gap": 0.03,     # 小于低阈值
        "fiedler_value": 0.15,
        "spectral_entropy": 1.5,  # 大于0.5
    }

    mod_params, action = injector.modulate(params, l_features)

    print()
    print(f"    action: {action}")
    old_thresh = params["zuowang_threshold"]
    new_thresh = mod_params["zuowang_threshold"]
    print(f"    zuowang_threshold: {old_thresh:.3f} -> {new_thresh:.3f}")
    assert new_thresh < old_thresh, f"坐忘阈值应降低: {old_thresh:.3f} -> {new_thresh:.3f}"
    assert "zuowang_threshold" in action


# ============================================================================
# 测试2: M2.5-B ZuowangGridInjector 坐忘注入
# ============================================================================

@test("M2.5-B#1 | ZuowangGridInjector.update 坐忘触发→呼吸加深+探索抑制")
def test_zuowang_triggered():
    """验证坐忘触发时：中五呼吸加深，坎一/巽四/离九抑制"""
    jg = _load_jiugong()

    injector = jg.ZuowangGridInjector()
    state = injector.update(
        zuowang_triggered=True,
        max_relevance=0.12,
        threshold=0.3,
        consciousness_score=0.7
    )

    weights = injector.current_weights

    print()
    print(f"    坐忘触发状态: {state.zuowang_triggered}")
    print(f"    呼吸调制: {state.respiration_modulation:.2f}x")
    print(f"    抑制宫位: {state.suppressed_palaces}")
    print(f"    增强宫位: {state.enhanced_palaces}")
    print(f"    九宫权重: {json.dumps({k: f'{v:.2f}' for k, v in weights.items()})}")

    assert state.zuowang_triggered is True
    assert state.respiration_modulation > 1.0, f"呼吸应 > 1.0: {state.respiration_modulation}"
    assert "坎一" in state.suppressed_palaces, "坎一应在抑制列表"
    assert "巽四" in state.suppressed_palaces, "巽四应在抑制列表"
    assert "离九" in state.suppressed_palaces, "离九应在抑制列表"
    # 验证权重值
    assert weights["消化"] < 1.0, "消化(坎一)权重应 < 1.0"
    assert weights["呼吸"] > 1.0, "呼吸(中五)权重应 > 1.0"
    assert weights["留白"] > 1.0, "留白(坤二)权重应 > 1.0"


@test("M2.5-B#2 | ZuowangGridInjector.update 坐忘关闭→恢复默认权重")
def test_zuowang_not_triggered():
    """验证坐忘未触发时全部权重恢复1.0"""
    jg = _load_jiugong()

    injector = jg.ZuowangGridInjector()

    # 先触发再关闭
    injector.update(zuowang_triggered=True, max_relevance=0.1, threshold=0.3)
    state = injector.update(zuowang_triggered=False)

    weights = injector.current_weights

    print()
    print(f"    坐忘触发状态: {state.zuowang_triggered}")
    for k, v in weights.items():
        assert abs(v - 1.0) < 0.001, f"{k}权重应为1.0, 实际{v:.4f}"
    print(f"    全部权重恢复: {json.dumps({k: f'{v:.2f}' for k, v in weights.items()})}")


@test("M2.5-B#3 | 意识得分越高→呼吸深度越大")
def test_zuowang_consciousness_modulation():
    """验证意识得分(0.3 vs 0.9)导致呼吸调制系数差异"""
    jg = _load_jiugong()

    injector = jg.ZuowangGridInjector()

    # 低意识
    injector.update(zuowang_triggered=True, consciousness_score=0.3)
    low_mod = injector.get_state().respiration_modulation

    # 高意识
    injector.update(zuowang_triggered=True, consciousness_score=0.9)
    high_mod = injector.get_state().respiration_modulation

    print()
    print(f"    意识0.3 → 呼吸调制: {low_mod:.4f}x")
    print(f"    意识0.9 → 呼吸调制: {high_mod:.4f}x")
    # 理论值: 意识0.3→1.3+0.15=1.45, 意识0.9→1.3+0.45=1.75
    assert abs(low_mod - 1.45) < 0.1, f"低意识呼吸应为~1.45, 实际{low_mod}"
    assert abs(high_mod - 1.75) < 0.1, f"高意识呼吸应为~1.75, 实际{high_mod}"
    assert high_mod > low_mod, f"高意识呼吸应大于低意识: {high_mod} < {low_mod}"


# ============================================================================
# 测试3: M2.5-A+B 顺序链验证
# ============================================================================

@test("M2.5-E2E#1 | LaplacianInjector → Compensator L_st微调 顺序链")
def test_laplacian_to_compensator():
    """验证：LaplacianInjector.modulate 的输出可以作为 Compensator.compensate 的输入"""
    from calibration_engine import (
        LaplacianInjector, Compensator, CompensationDiff
    )

    l_injector = LaplacianInjector(alpha=0.3)

    # Step 1: LaplacianInjector 调制
    initial_params = {
        "branch_weights": {"meta_cognition": 0.20, "depth": 0.15, "intent": 0.15},
        "zuowang_threshold": 0.3,
        "consciousness_weight": 0.15,
        "laplacian_features": {"spectral_gap": 0.23, "fiedler_value": 0.35, "spectral_entropy": 0.8},
    }
    l_features = {"spectral_gap": 0.23, "fiedler_value": 0.35}
    mod_params, l_action = l_injector.modulate(initial_params, l_features)

    print()
    print(f"    LaplacianInjector 动作: {l_action}")
    meta_post = mod_params["branch_weights"]["meta_cognition"]
    print(f"    meta_cognition: {initial_params['branch_weights']['meta_cognition']:.3f} -> {meta_post:.3f}")

    # Step 2: 作为 Compensator 的输入（模拟CD）
    cd = CompensationDiff(delta_info=0.05, delta_energy=0.08, delta_length=0.12)
    current_scores = {"intent_score": 0.4, "priority_score": 0.5, "insight_score": 0.6, "coherence_score": 0.3}

    comp_params, comp_action = Compensator.compensate(cd, mod_params, current_scores)

    print(f"    Compensator 动作: {comp_action[:80]}...")
    assert "meta_cognition" in mod_params.get("branch_weights", {}), "Laplacian调制后应有meta_cognition"
    assert mod_params["zuowang_threshold"] == initial_params["zuowang_threshold"], "Laplacian不应改变坐忘阈值"


@test("M2.5-E2E#2 | ZuowangGridInjector → apply_to_grid_core 九宫核心注入链")
def test_zuowang_to_grid_core():
    """验证：ZuowangGridInjector 更新状态后可以应用到九宫司命核心"""
    jg = _load_jiugong()

    # 创建 Injector 和 Core
    injector = jg.ZuowangGridInjector()
    core = jg.九宫司命核心()

    # 记录注入前的呼吸计数
    before_count = core.呼吸计数

    # 触发坐忘 + 应用
    injector.update(zuowang_triggered=True, consciousness_score=0.7)
    summary = injector.apply_to_grid_core(core)

    print()
    print(f"    注入前呼吸计数: {before_count}")
    print(f"    注入后呼吸计数: {core.呼吸计数}")
    print(f"    核心权重状态: {json.dumps({k: f'{v:.2f}' for k, v in core.权重状态.items()})}")
    print(f"    摘要: {summary}")

    assert "ZuowangGridInjector" in summary
    assert "已应用" in summary
    assert core.呼吸计数 > before_count, "呼吸计数应增加"


@test("M2.5-E2E#3 | LaplacianInjector + Compensator 全链路—谱间隙→元认知权重上升")
def test_laplacian_full_modulation_chain():
    """验证：模拟完整的 Laplacian → Compensator 全链调制，预期元认知权重上升"""
    from calibration_engine import (
        LaplacianInjector, Compensator, CompensationDiff
    )

    l_injector = LaplacianInjector(alpha=0.3)
    params = {
        "branch_weights": {"meta_cognition": 0.20, "depth": 0.15, "intent": 0.15, "priority": 0.15},
        "zuowang_threshold": 0.3,
        "consciousness_weight": 0.15,
    }
    # 大谱间隙特征
    l_features = {"spectral_gap": 0.25, "fiedler_value": 0.4, "spectral_entropy": 0.6}

    # Run modulation
    mod_params, _ = l_injector.modulate(params, l_features)

    # Run compensation
    cd = CompensationDiff(delta_info=0.05, delta_energy=0.10, delta_length=0.08)
    scores = {"intent_score": 0.4, "priority_score": 0.5, "insight_score": 0.6, "coherence_score": 0.3}
    final_params, _ = Compensator.compensate(cd, mod_params, scores)

    bw = final_params.get("branch_weights", {})
    meta_final = bw.get("meta_cognition", 0.0)

    print()
    print(f"    meta_cognition 变化: {params['branch_weights']['meta_cognition']:.3f} -> {meta_final:.3f}")
    assert meta_final > params["branch_weights"]["meta_cognition"], f"全链后元认知应上升: {meta_final}"
    # 大谱间隙下 consciousness_weight 也应上升（Fiedler规则触发）
    cw_final = final_params.get("consciousness_weight", 0.0)
    assert cw_final > params["consciousness_weight"], f"consciousness_weight 应上升: {cw_final}"


# ============================================================================
# 测试4: 模拟全链路 E2E 闭环
# ============================================================================

@test("M2.5-E2E#4 | 完整闭环模拟：模拟评估→CDE(Laplacian)→九宫(Zuowang)→报告")
def test_full_e2e_chain():
    """模拟一次完整的对话评估→CDE校准(含L_st)→九宫调度(含坐忘)→输出报告"""
    from calibration_engine import (
        LaplacianInjector, Compensator, CompensationDiff,
        RecursiveLoopController
    )

    # === Phase 1: 模拟对话评估输出 ===
    eight_layer_scores = {
        "intent_score": 0.62,
        "priority_score": 0.48,
        "insight_score": 0.55,
        "coherence_score": 0.71,
        "consciousness_score": 0.78,
    }
    params = {
        "branch_weights": {"meta_cognition": 0.20, "depth": 0.15, "intent": 0.15,
                           "priority": 0.15, "insight": 0.15, "coherence": 0.10,
                           "creativity": 0.10},
        "zuowang_threshold": 0.30,
        "consciousness_weight": 0.15,
    }

    # === Phase 2: LaplacianInjector 注入 L_st 特征 ===
    l_injector = LaplacianInjector(alpha=0.3, gap_threshold_high=0.1, gap_threshold_low=0.05)
    # 模拟高意识对话的拓扑特征
    l_features = {"spectral_gap": 0.18, "fiedler_value": 0.35, "spectral_entropy": 0.75}
    mod_params, l_action = l_injector.modulate(params, l_features)
    mod_params["laplacian_features"] = l_features
    mod_params["_laplacian_gap_high"] = 0.1

    print()
    print(f"    [Phase1] 八层评估: {json.dumps(eight_layer_scores)}")
    print(f"    [Phase2] L_st注入: {l_action}")

    # === Phase 3: RecursiveLoopController 递归校准（等价于CDE核心） ===
    controller = RecursiveLoopController(epsilon=0.05, max_iterations=5)
    states = []
    cur_scores = dict(eight_layer_scores)
    cur_params = dict(mod_params)

    for iteration in range(5):
        state = controller.run_one_iteration(
            cur_scores, cur_params,
            strategy="threshold_shift",
            iteration=iteration,
        )
        states.append(state)
        if state.compensation_diff and state.compensation_diff.is_converged(controller.epsilon):
            break
        # 更新为下一轮状态
        cur_scores = dict(state.scores_after)
        cur_params = dict(state.params)

    print(f"    [Phase3] CDE校准: {len(states)}次迭代, "
          f"收敛={states[-1].compensation_diff.is_converged(controller.epsilon) if states[-1].compensation_diff else False}")
    if states:
        print(f"    最终|CD|={states[-1].compensation_diff.magnitude:.4f}" if states[-1].compensation_diff else "")
        print(f"    最终坐忘阈值={states[-1].params.get('zuowang_threshold', 'N/A')}")

    # === Phase 4: 坐忘检测 + 九宫注入 ===
    jg = _load_jiugong()

    zw_injector = jg.ZuowangGridInjector()
    # 高意识 → 坐忘应触发
    final_params = states[-1].params if states else mod_params
    zuowang_threshold = final_params.get("zuowang_threshold", 0.3)
    # 坐忘触发条件: 意识得分 > 阈值
    consciousness = eight_layer_scores.get("consciousness_score", 0.0)
    zuowang_triggered = consciousness > zuowang_threshold

    zw_state = zw_injector.update(
        zuowang_triggered=zuowang_triggered,
        max_relevance=consciousness,
        threshold=zuowang_threshold,
        consciousness_score=consciousness,
    )

    print(f"    [Phase4] 坐忘状态: 触发={zw_state.zuowang_triggered}, "
          f"呼吸={zw_state.respiration_modulation:.2f}x, "
          f"受抑制={zw_state.suppressed_palaces}")

    # === Phase 5: 输出 E2E 报告摘要 ===
    report = {
        "tree_id": "e2e_test_001",
        "eight_layer": {
            "consciousness": consciousness,
            "coherence": eight_layer_scores["coherence_score"],
        },
        "cd_calibration": {
            "n_iterations": len(states),
            "converged": states[-1].compensation_diff.is_converged(controller.epsilon) if states and states[-1].compensation_diff else False,
        },
        "laplacian_injection": {
            "action": l_action,
            "features": l_features,
        },
        "zuowang_grid": {
            "triggered": zw_state.zuowang_triggered,
            "respiration_modulation": round(zw_state.respiration_modulation, 4),
            "suppressed_palaces": zw_state.suppressed_palaces,
            "enhanced_palaces": zw_state.enhanced_palaces,
        },
    }
    report_path = os.path.join(PROJECT_ROOT, "cognition_psi_bridge", "e2e_chain_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"    [Phase5] E2E报告: {report_path}")
    print(f"    E2E链摘要:")
    print(f"      对话评估 → {consciousness:.2f}意识")
    print(f"      L_st注入 → {'触发调制' if '谱间隙' in l_action else '无调制'}")
    print(f"      CDE校准 → {len(states)}次迭代")
    print(f"      坐忘检测 → {'触发' if zw_state.zuowang_triggered else '未触发'}")
    print(f"      九宫注入 → 呼吸{zw_state.respiration_modulation:.2f}x")

    assert len(states) > 0, "CDE校准应至少执行一次迭代"
    assert zw_state.zuowang_triggered, f"高意识({consciousness:.2f})应触发坐忘"


# ============================================================================
# 测试5: 随机数据稳定性验证
# ============================================================================

@test("M2.5-Stability#1 | LaplacianInjector 随机嵌入稳定性")
def test_laplacian_stability():
    """验证 LaplacianInjector 对噪声嵌入稳定不崩溃"""
    from calibration_engine import LaplacianInjector

    injector = LaplacianInjector()
    for n in [5, 20, 100]:
        emb = np.random.randn(n, 32).astype(np.float64)
        features = injector.extract(embeddings=emb)
        assert isinstance(features, dict)
        assert "spectral_gap" in features
        print(f"    随机嵌入(n={n:3d}): spectral_gap={features['spectral_gap']:.4f}, "
              f"fiedler={features['fiedler_value']:.4f}")


@test("M2.5-Stability#2 | ZuowangGridInjector 重复触发稳定性")
def test_zuowang_repeat_stability():
    """验证 ZuowangGridInjector 重复触发50次不退化"""
    jg = _load_jiugong()

    injector = jg.ZuowangGridInjector()

    mods = []
    for i in range(50):
        score = 0.3 + (i % 5) * 0.12  # 0.3, 0.42, 0.54, 0.66, 0.78
        trig = score > 0.4
        state = injector.update(
            zuowang_triggered=trig,
            max_relevance=score,
            threshold=0.3,
            consciousness_score=score,
        )
        mods.append(state.respiration_modulation)

    avg_mod = sum(mods) / len(mods)
    min_mod = min(mods)
    max_mod = max(mods)

    print()
    print(f"    50次触发: avg_mod={avg_mod:.4f}, min={min_mod:.4f}, max={max_mod:.4f}")
    assert max_mod >= 1.0, f"最大呼吸调制应≥1.0: {max_mod}"
    assert min_mod >= 0.9, f"最小呼吸调制应≥0.9(未触发时1.0): {min_mod}"
    assert max_mod <= 2.0, f"最大呼吸调制应≤2.0上限: {max_mod}"


# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":
    run_all()
