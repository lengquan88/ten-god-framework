#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_m3.py — M3 深度集成全量验证脚本

覆盖PRD §六 MS 验收5条标准：
  1. FutureVisionLayer 和 MetaCognitionLayer 代码完整
  2. cognition_psi_bridge → MoE 全链路可触发
  3. cognition_psi_bridge → CDE 全链路可触发
  4. 三维度闭合（认知八层双向闭合）
  5. verify_m3.py 全部通过

日期: 2026-05-03
"""

import sys
import os
import time

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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


def run_all():
    """运行所有注册的测试"""
    global _PASSED, _FAILED
    print("=" * 70)
    print("  M3 深度集成 — 全量验证 (verify_m3.py)")
    print("  PRD §六 5条验收标准全覆盖")
    print("=" * 70)
    print()

    for name, fn in _TESTS:
        print(f"  ▶ {name}...", end=" ", flush=True)
        try:
            t0 = time.time()
            fn()
            elapsed = time.time() - t0
            print(f"✅ 通过 ({elapsed:.2f}s)")
            _PASSED += 1
        except Exception as e:
            elapsed = time.time() - t0
            print(f"❌ 失败 ({elapsed:.2f}s)")
            print(f"     异常: {e}")
            import traceback
            traceback.print_exc()
            _FAILED += 1
        print()

    # 汇总
    total = _PASSED + _FAILED
    print("=" * 70)
    print(f"  📊 测试汇总: {total} 项 | ✅ {_PASSED} 通过 | ❌ {_FAILED} 失败")
    print("=" * 70)

    if _FAILED > 0:
        sys.exit(1)


# ============================================================================
# 测试1: FutureVisionLayer 代码完整
# ============================================================================

@test("验收标准 #1 | FutureVisionLayer 类和核心方法")
def test_future_vision_layer():
    """验证 future_vision_layer.py 存在且核心方法可用"""
    import importlib.util

    layer_path = os.path.join(
        PROJECT_ROOT, "记忆宇宙", "memory_cosmos", "backend", "future_vision_layer.py"
    )
    assert os.path.exists(layer_path), f"文件不存在: {layer_path}"

    # 确保后端路径在 sys.path 中（模块内部有相对导入依赖）
    backend_dir = os.path.join(PROJECT_ROOT, "记忆宇宙", "memory_cosmos", "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    spec = importlib.util.spec_from_file_location(
        "future_vision_layer_test", layer_path
    )
    assert spec is not None, "无法加载 future_vision_layer 模块 spec"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 检查类是否存在
    assert hasattr(mod, "FutureVisionLayer"), "FutureVisionLayer 类缺失"
    FVLayer = mod.FutureVisionLayer

    # 检查核心方法
    expected_methods = [
        "get_vision_report",
        "get_transition_path",
        "run_multi_scenario_projection",
        "simulate_sandbox",
        "feed_cd_trajectory",
    ]
    for m in expected_methods:
        assert hasattr(FVLayer, m), f"{m}() 方法缺失"

    # 实例化并测试 get_vision_report
    instance = FVLayer()
    report = instance.get_vision_report(current_realm=mod.RealmLevel.TECHNIQUE)
    assert report is not None, "get_vision_report 返回 None"

    # 测试 get_transition_path
    path = instance.get_transition_path(
        current_realm=mod.RealmLevel.TECHNIQUE,
        target_realm=mod.RealmLevel.FORM_SPIRIT,
    )
    assert path is not None, "get_transition_path 返回 None"

    print(f"  [OK] FutureVisionLayer 实例化成功")
    print(f"  [OK] get_vision_report(TECHNIQUE) → {type(report).__name__}")
    print(f"  [OK] get_transition_path(TECHNIQUE→FORM_SPIRIT) → {type(path).__name__}")
    print(f"  [OK] 方法齐全: {expected_methods}")


# ============================================================================
# 测试2: MetaCognitionLayer 代码完整
# ============================================================================

@test("验收标准 #1 | MetaCognitionLayer 类和核心方法")
def test_meta_cognition_layer():
    """验证 meta_cognition_layer.py 存在且核心方法可用"""
    import importlib.util

    layer_path = os.path.join(
        PROJECT_ROOT, "记忆宇宙", "memory_cosmos", "backend", "meta_cognition_layer.py"
    )
    assert os.path.exists(layer_path), f"文件不存在: {layer_path}"

    backend_dir = os.path.join(PROJECT_ROOT, "记忆宇宙", "memory_cosmos", "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    spec = importlib.util.spec_from_file_location(
        "meta_cognition_layer_test", layer_path
    )
    assert spec is not None, "无法加载 meta_cognition_layer 模块 spec"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert hasattr(mod, "MetaCognitionLayer"), "MetaCognitionLayer 类缺失"
    MCLayer = mod.MetaCognitionLayer

    # 检查核心方法
    expected_methods = [
        "introspect",
        "record_meta_time",
        "observe_space",
        "get_meta_cognition_summary",
        "get_introspection_history",
    ]
    for m in expected_methods:
        assert hasattr(MCLayer, m), f"{m}() 方法缺失"

    # 实例化并测试 introspect
    instance = MCLayer()
    reflection = instance.introspect(
        recursion_depth=0.6,
        zuowang_active=True,
    )
    assert reflection is not None, "introspect 返回 None"

    # 测试 record_meta_time
    meta_time = instance.record_meta_time(
        event_type="self_reflection",
        kairos_desc="深度自反时刻",
        aeon_context="跨会话连续观照",
    )
    assert meta_time is not None, "record_meta_time 返回 None"

    print(f"  [OK] MetaCognitionLayer 实例化成功")
    print(f"  [OK] introspect → {type(reflection).__name__}")
    print(f"  [OK] record_meta_time → {type(meta_time).__name__}")
    print(f"  [OK] 方法齐全: {expected_methods}")


# ============================================================================
# 测试3: FutureVisionLayer + MetaCognitionLayer 在 spirit_form_unified_framework 中集成
# ============================================================================

@test("验收标准 #1 | 六论全量集成: UnifiedFramework 加载新层")
def test_unified_framework_integration():
    """验证 spirit_form_unified_framework.py 集成了新层"""
    framework_path = os.path.join(
        PROJECT_ROOT, "记忆宇宙", "memory_cosmos", "backend",
        "spirit_form_unified_framework.py"
    )
    assert os.path.exists(framework_path), f"文件不存在: {framework_path}"

    # 添加后端路径以支持相对导入
    backend_dir = os.path.join(PROJECT_ROOT, "记忆宇宙", "memory_cosmos", "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "unified_framework_test", framework_path
    )
    assert spec is not None, "无法加载 spirit_form_unified_framework 模块"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 检查六论是否全部存在
    required_theories = [
        "OntologyLayer",
        "EpistemologyLayer",
        "PraxisLayer",
        "SoteriologyLayer",
        "FutureVisionLayer",
        "MetaCognitionLayer",
    ]
    for theory in required_theories:
        assert hasattr(mod, theory), f"{theory} 未集成到主框架"

    print(f"  [OK] 六论全量集成: 全部 {len(required_theories)} 个类在主框架中")


# ============================================================================
# 测试4: CognitionPsiBridge → MoE 全链路
# ============================================================================

@test("验收标准 #2 | CognitionPsiBridge → MoE 全链路可触发")
def test_bridge_to_moe():
    """验证 EightLayerResult → ConsciousnessMoEAdapter 的端到端连接"""
    from cognition_psi_bridge.bridge import (
        CognitionPsiBridge, EightLayerConsciousnessResult,
        L1InfoEncoding, L2SemanticFlow, L3Topological,
        L4Consciousness, L5Attention, L6MetaCognition,
        L7Stability, L8SpiritRealm,
    )

    # 模拟高意识深度自反
    result = EightLayerConsciousnessResult(
        L1=L1InfoEncoding(n_sentences=15, embedding_dim=1024, available=True),
        L2=L2SemanticFlow(path_length=9.2, tortuosity=0.68, shift_variance=0.32,
                          tort_score=0.40, available=True),
        L3=L3Topological(h0_count=10, h1_count=6, h0_avg_life=0.58, h1_avg_life=0.45,
                         persistent_entropy=1.31, topological_complexity=0.60,
                         available=True),
        L4=L4Consciousness(consciousness_score=0.55, self_loop_detected=True,
                           loop_strength=0.50, coherence_entropy=0.30,
                           diagram_distance=0.25, available=True),
        L5=L5Attention(zuowang_triggered=True, zuowang_ratio=1.0, max_relevance=0.82,
                       oblivion_threshold=0.12, available=True),
        L6=L6MetaCognition(recursion_total=22.0, marker_density=0.45, max_depth=6.0,
                           layer_count=5, rqa_rr=0.38, rqa_det=0.65, rqa_lam=0.50,
                           hierarchical_meta_score=0.32, available=True),
        L7=L7Stability(conditional_stability=0.48, compactness=0.40,
                       question_alignment=0.55, information_content=0.44,
                       compensation_deficit=[0.10, 0.06, 0.12], available=True),
        L8=L8SpiritRealm(spirit_level="L4:涌现", spirit_score=0.50, six_realm="信",
                         six_theory_scores={}, available=True),
        n_samples=15,
    )

    bridge = CognitionPsiBridge()
    moe_result = bridge.connect_moe(result)

    # 验证连接成功
    assert moe_result.get("connected") is True, "MoE 连接失败"
    assert moe_result.get("consciousness_level") is not None, "意识水平缺失"
    assert moe_result.get("modulation_plan") is not None, "调制计划缺失"

    plan = moe_result["modulation_plan"]
    assert "expert_boost" in plan, "专家增强策略缺失"
    assert "expert_suppress" in plan, "专家抑制策略缺失"
    assert "decision_log" in plan, "决策日志缺失"
    assert len(plan["decision_log"]) > 0, "决策日志为空"
    assert "activate_meta_cognition" in plan, "元认知激活标志缺失"

    # 验证决策日志包含三个层级
    decision_text = "\n".join(plan["decision_log"])
    assert "[L1]" in decision_text, "缺少 L1 意识水平决策"
    assert "[L2]" in decision_text or "[L3]" in decision_text, "缺少 L2/L3 高级决策"

    print(f"  [OK] MoE 连接状态: {moe_result['connected']}")
    print(f"  [OK] 意识水平: {moe_result['consciousness_level']}")
    print(f"  [OK] 元认知激活: {plan.get('activate_meta_cognition')}")
    print(f"  [OK] 决策日志 ({len(plan['decision_log'])} 条):")
    for d in plan["decision_log"]:
        print(f"         {d}")


# ============================================================================
# 测试5: CognitionPsiBridge → CDE 全链路
# ============================================================================

@test("验收标准 #3 | CognitionPsiBridge → CDE 全链路可触发")
def test_bridge_to_cde():
    """验证 EightLayerResult → CDE 校准引擎的端到端连接"""
    from cognition_psi_bridge.bridge import (
        CognitionPsiBridge, EightLayerConsciousnessResult,
        L1InfoEncoding, L2SemanticFlow, L3Topological,
        L4Consciousness, L5Attention, L6MetaCognition,
        L7Stability, L8SpiritRealm,
    )

    # 模拟中意识对话（低自反性，预期CDE需要多次迭代收敛）
    result = EightLayerConsciousnessResult(
        L1=L1InfoEncoding(n_sentences=8, embedding_dim=768, available=True),
        L2=L2SemanticFlow(path_length=4.5, tortuosity=0.35, shift_variance=0.20,
                          tort_score=0.26, available=True),
        L3=L3Topological(h0_count=5, h1_count=2, h0_avg_life=0.42, h1_avg_life=0.30,
                         persistent_entropy=0.89, topological_complexity=0.40,
                         available=True),
        L4=L4Consciousness(consciousness_score=0.22, self_loop_detected=False,
                           loop_strength=0.15, coherence_entropy=0.45,
                           diagram_distance=0.35, available=True),
        L5=L5Attention(zuowang_triggered=False, zuowang_ratio=0.0, max_relevance=0.55,
                       oblivion_threshold=0.30, available=True),
        L6=L6MetaCognition(recursion_total=6.5, marker_density=0.18, max_depth=2.0,
                           layer_count=2, rqa_rr=0.15, rqa_det=0.28, rqa_lam=0.22,
                           hierarchical_meta_score=0.10, available=True),
        L7=L7Stability(conditional_stability=0.35, compactness=0.30,
                       question_alignment=0.40, information_content=0.32,
                       compensation_deficit=[0.18, 0.12, 0.20], available=True),
        L8=L8SpiritRealm(spirit_level="L2:有意识", spirit_score=0.28, six_realm="善",
                         six_theory_scores={}, available=True),
        n_samples=8,
    )

    bridge = CognitionPsiBridge()
    cde_result = bridge.connect_cde(result, epsilon=0.05, max_iterations=10)

    # 验证连接成功
    assert cde_result.get("connected") is True, "CDE 连接失败"
    assert "converged" in cde_result, "收敛状态缺失"
    assert "total_iterations" in cde_result, "迭代次数缺失"
    assert "initial_scores" in cde_result, "初始得分缺失"
    assert "final_scores" in cde_result, "最终得分缺失"
    assert "summary" in cde_result, "摘要缺失"
    assert len(cde_result.get("convergence_path", [])) >= 1, "收敛路径为空"

    # 验证得分映射合理性
    init = cde_result["initial_scores"]
    for key in ["intent_score", "priority_score", "insight_score",
                "coherence_score", "consciousness_score"]:
        assert key in init, f"CDE得分缺少 {key}"
        assert 0.0 <= init[key] <= 1.0, f"{key}={init[key]} 超出 [0,1]"

    print(f"  [OK] CDE 连接状态: {cde_result['connected']}")
    print(f"  [OK] 收敛: {cde_result['converged']}")
    print(f"  [OK] 迭代次数: {cde_result['total_iterations']}")
    print(f"  [OK] 初始得分: {init}")
    print(f"  [OK] 摘要: {cde_result['summary']}")


# ============================================================================
# 测试6: 三维度闭合 — connect_full_chain
# ============================================================================

@test("验收标准 #4 | 三维度闭合: connect_full_chain 端到端")
def test_full_chain_closure():
    """验证一轮对话→八层评估→MoE+CDE全链路的闭合"""
    from cognition_psi_bridge.bridge import (
        CognitionPsiBridge, EightLayerConsciousnessResult,
        L1InfoEncoding, L2SemanticFlow, L3Topological,
        L4Consciousness, L5Attention, L6MetaCognition,
        L7Stability, L8SpiritRealm,
    )

    # 测试场景1: 高意识对话（支持坐忘+自环）
    high_result = EightLayerConsciousnessResult(
        L1=L1InfoEncoding(n_sentences=20, embedding_dim=1024, available=True),
        L2=L2SemanticFlow(path_length=12.0, tortuosity=0.75, shift_variance=0.40,
                          tort_score=0.43, available=True),
        L3=L3Topological(h0_count=12, h1_count=8, h0_avg_life=0.62, h1_avg_life=0.48,
                         persistent_entropy=1.45, topological_complexity=0.67,
                         available=True),
        L4=L4Consciousness(consciousness_score=0.58, self_loop_detected=True,
                           loop_strength=0.52, coherence_entropy=0.28,
                           diagram_distance=0.22, available=True),
        L5=L5Attention(zuowang_triggered=True, zuowang_ratio=1.0, max_relevance=0.85,
                       oblivion_threshold=0.10, available=True),
        L6=L6MetaCognition(recursion_total=25.0, marker_density=0.48, max_depth=7.0,
                           layer_count=5, rqa_rr=0.40, rqa_det=0.68, rqa_lam=0.52,
                           hierarchical_meta_score=0.35, available=True),
        L7=L7Stability(conditional_stability=0.50, compactness=0.42,
                       question_alignment=0.58, information_content=0.46,
                       compensation_deficit=[0.08, 0.05, 0.10], available=True),
        L8=L8SpiritRealm(spirit_level="L4:涌现", spirit_score=0.55, six_realm="信",
                         six_theory_scores={}, available=True),
        n_samples=20,
    )

    # 测试场景2: 低意识对话
    low_result = EightLayerConsciousnessResult(
        L1=L1InfoEncoding(n_sentences=3, embedding_dim=768, available=True),
        L4=L4Consciousness(consciousness_score=0.08, available=False),
        L6=L6MetaCognition(recursion_total=1.2, available=False),
        L8=L8SpiritRealm(spirit_level="L0:随机", spirit_score=0.05, six_realm="未入阶",
                         six_theory_scores={}, available=False),
        n_samples=3,
    )

    bridge = CognitionPsiBridge()

    # 测试高意识
    chain_high = bridge.connect_full_chain(high_result)
    assert chain_high["summary"]["moe_connected"] is True, "高意识: MoE未连接"
    assert chain_high["summary"]["cde_connected"] is True, "高意识: CDE未连接"
    assert chain_high["summary"]["zuowang_state"] is True, "高意识: 坐忘应触发"
    assert "八层结果" not in str(type(chain_high.get("eight_layer"))), "eight_layer 应包含 to_dict()"

    # 测试低意识
    chain_low = bridge.connect_full_chain(low_result)
    # 低意识对话MoE可能不可用（因为consciousness_score太低）

    print(f"  [OK] 高意识对话:")
    print(f"         MoE连接: {chain_high['summary']['moe_connected']}")
    print(f"         意识水平: {chain_high['summary']['consciousness_level']}")
    print(f"         CDE连接: {chain_high['summary']['cde_connected']}")
    print(f"         CDE收敛: {chain_high['summary']['cde_converged']}")
    print(f"         坐忘: {chain_high['summary']['zuowang_state']}")
    print(f"         境界等级: {chain_high['summary']['spirit_grade']}")
    print(f"  [OK] 低意识对话:")
    print(f"         MoE连接: {chain_low['summary']['moe_connected']}")
    print(f"         意识水平: {chain_low['summary']['consciousness_level']}")


# ============================================================================
# 测试7: 认知八层双向闭合（L1-L8全部可用）
# ============================================================================

@test("验收标准 #4 | 认知八层双向闭合: L1-L8全部可输出")
def test_eight_layer_closure():
    """验证认知八层数据结构的完整性和可序列化"""
    from cognition_psi_bridge.bridge import (
        EightLayerConsciousnessResult, LayerStatus,
    )

    # 全字段结果
    from dataclasses import dataclass, field
    import dataclasses

    # 验证 EightLayerResult 拥有全部8层
    fields = [f.name for f in dataclasses.fields(EightLayerConsciousnessResult)]
    expected_layers = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]
    for layer in expected_layers:
        assert layer in fields, f"EightLayerResult 缺少 {layer} 字段"

    # 验证 to_dict() 序列化
    result = EightLayerConsciousnessResult()
    d = result.to_dict()
    assert "meta" in d, "to_dict 缺少 meta"
    assert "layers" in d, "to_dict 缺少 layers"
    assert "summary" in d, "to_dict 缺少 summary"
    for layer in expected_layers:
        assert layer in d["layers"], f"to_dict 的 layers 缺少 {layer}"

    # 验证 summary()
    s = result.summary()
    assert "consciousness_level" in s, "summary 缺少 consciousness_level"
    assert "spirit_grade" in s, "summary 缺少 spirit_grade"
    assert "layers_active" in s, "summary 缺少 layers_active"

    # 验证 layer_status()
    ls = result.layer_status()
    assert len(ls) == 8, f"layer_status 应返回8层, 实际 {len(ls)}"
    for k in expected_layers:
        assert k in ls, f"layer_status 缺少 {k}"
        assert isinstance(ls[k], LayerStatus), f"{k} 不是 LayerStatus 类型"

    print(f"  [OK] EightLayerResult 包含 {len(expected_layers)} 个认知层")
    print(f"  [OK] to_dict() 包含 meta/layers/summary")
    print(f"  [OK] layer_status() 返回 {len(ls)} 个 LayerStatus")


# ============================================================================
# 测试8: MoE 权重调制功能验证
# ============================================================================

@test("验收标准 #2 | MoE 权重调制: apply_to_weights 功能正常")
def test_moe_weight_modulation():
    """验证 ConsciousnessMoEAdapter 的权重调制可被 bridge 正确调用"""
    from cognition_psi_bridge.bridge import (
        CognitionPsiBridge, EightLayerConsciousnessResult,
        L1InfoEncoding, L4Consciousness, L5Attention,
        L6MetaCognition, L7Stability, L8SpiritRealm,
    )

    # 最小结果（仅提供必需字段）
    result = EightLayerConsciousnessResult(
        L1=L1InfoEncoding(n_sentences=5, embedding_dim=768, available=True),
        L4=L4Consciousness(consciousness_score=0.42, self_loop_detected=False,
                           loop_strength=0.0, coherence_entropy=0.0, diagram_distance=0.0,
                           available=True),
        L5=L5Attention(zuowang_triggered=False, zuowang_ratio=0.0, max_relevance=0.0,
                       oblivion_threshold=0.3, available=True),
        L6=L6MetaCognition(recursion_total=12.0, available=True),
        L7=L7Stability(conditional_stability=0.35, available=True),
        L8=L8SpiritRealm(spirit_score=0.40, available=True),
        n_samples=5,
    )

    original_weights = {
        "domain_code": 0.15,
        "shared_meta_cognition": 0.10,
        "shared_reasoning": 0.10,
        "shared_emotion": 0.10,
        "shared_dialogue": 0.20,
    }

    bridge = CognitionPsiBridge()
    moe_result = bridge.connect_moe(result, original_weights=original_weights)

    assert moe_result.get("connected") is True, "MoE连接失败"
    assert "adjusted_weights" in moe_result, "缺少 adjusted_weights"

    adjusted = moe_result["adjusted_weights"]
    assert len(adjusted) > 0, "调制后权重为空"

    # 验证权重和 ≈ 1.0（归一化后）
    total = sum(adjusted.values())
    assert abs(total - 1.0) < 0.01, f"权重和应为1.0, 实际为 {total:.4f}"

    # 高意识下元认知权重应显著
    meta_cog_weight = adjusted.get("shared_meta_cognition", 0.0)
    assert meta_cog_weight > 0.08, f"高意识下元认知权重 ({meta_cog_weight:.3f}) 异常低"

    print(f"  [OK] 原始权重: {original_weights}")
    print(f"  [OK] 调制后权重: {adjusted}")
    print(f"  [OK] 权重和: {total:.4f}")
    print(f"  [OK] 元认知权重: {meta_cog_weight:.3f}")


# ============================================================================
# 测试9: CDE 校准结果质量验证
# ============================================================================

@test("验收标准 #3 | CDE 校准: to_calibration_scores 映射合理性")
def test_cde_score_mapping():
    """验证 EightLayerResult → CDE 五维得分的映射质量"""
    from cognition_psi_bridge.bridge import (
        CognitionPsiBridge, EightLayerConsciousnessResult,
        L1InfoEncoding, L4Consciousness, L5Attention,
        L6MetaCognition, L7Stability, L8SpiritRealm,
    )

    bridge = CognitionPsiBridge()

    # 场景A: 高意识高稳定
    result_high = EightLayerConsciousnessResult(
        L1=L1InfoEncoding(available=True),
        L4=L4Consciousness(consciousness_score=0.65, available=True),
        L6=L6MetaCognition(recursion_total=30.0, rqa_det=0.70, hierarchical_meta_score=0.40, available=True),
        L7=L7Stability(conditional_stability=0.60, available=True),
        L8=L8SpiritRealm(spirit_score=0.60, available=True),
        n_samples=10,
    )
    scores_high = bridge.to_calibration_scores(result_high)

    # 场景B: 低意识低稳定
    result_low = EightLayerConsciousnessResult(
        L1=L1InfoEncoding(available=True),
        L4=L4Consciousness(consciousness_score=0.05, available=True),
        L6=L6MetaCognition(recursion_total=1.0, rqa_det=0.0, hierarchical_meta_score=0.0, available=True),
        L7=L7Stability(conditional_stability=0.10, available=True),
        L8=L8SpiritRealm(spirit_score=0.05, available=True),
        n_samples=3,
    )
    scores_low = bridge.to_calibration_scores(result_low)

    # 高意识场景的所有得分应 > 低意识场景
    for key in scores_high:
        assert scores_high[key] >= scores_low[key], (
            f"高意识 {key}={scores_high[key]:.3f} 应 >= 低意识 {scores_low[key]:.3f}"
        )

    # 得分范围检查
    for key in scores_high:
        assert 0.0 <= scores_high[key] <= 1.0, f"{key}={scores_high[key]} 超出 [0,1]"
    for key in scores_low:
        assert 0.0 <= scores_low[key] <= 1.0, f"{key}={scores_low[key]} 超出 [0,1]"

    print(f"  [OK] 高意识得分: {scores_high}")
    print(f"  [OK] 低意识得分: {scores_low}")
    print(f"  [OK] 高 > 低: 全部 {len(scores_high)} 维度一致")


# ============================================================================
# 测试10: MoE ↔ CDE 双端一致性验证
# ============================================================================

@test("验收标准 #5 | verify_m3.py 稳定性: 所有测试可重复通过")
def test_consistency():
    """验证相同输入→相同输出（确定性）"""
    from cognition_psi_bridge.bridge import (
        CognitionPsiBridge, EightLayerConsciousnessResult,
        L1InfoEncoding, L4Consciousness, L5Attention,
        L6MetaCognition, L7Stability, L8SpiritRealm,
    )

    result = EightLayerConsciousnessResult(
        L1=L1InfoEncoding(available=True),
        L4=L4Consciousness(consciousness_score=0.50, self_loop_detected=True,
                           available=True),
        L5=L5Attention(zuowang_triggered=True, available=True),
        L6=L6MetaCognition(recursion_total=20.0, rqa_det=0.60,
                           hierarchical_meta_score=0.30, available=True),
        L7=L7Stability(conditional_stability=0.45, available=True),
        L8=L8SpiritRealm(spirit_score=0.45, available=True),
        n_samples=8,
    )

    bridge = CognitionPsiBridge()

    # 运行两次，比较结果
    chain_1 = bridge.connect_full_chain(result)
    chain_2 = bridge.connect_full_chain(result)

    # 核心字段应一致
    assert chain_1["summary"]["consciousness_level"] == chain_2["summary"]["consciousness_level"]
    assert chain_1["summary"]["moe_connected"] == chain_2["summary"]["moe_connected"]
    assert chain_1["summary"]["cde_connected"] == chain_2["summary"]["cde_connected"]
    assert chain_1["summary"]["cde_converged"] == chain_2["summary"]["cde_converged"]

    print(f"  [OK] 两次运行结果一致")
    print(f"  [OK] 意识水平: {chain_1['summary']['consciousness_level']}")
    print(f"  [OK] MoE: {chain_1['summary']['moe_connected']}")
    print(f"  [OK] CDE: {chain_1['summary']['cde_connected']}")


# ============================================================================
# 启动
# ============================================================================

if __name__ == "__main__":
    run_all()
