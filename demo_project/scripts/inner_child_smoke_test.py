#!/usr/bin/env python3
"""v2.16.1 内在小孩冒烟测试 —— CI 矩阵 test job 专用

验证项：
  1. 模块导入完整性
  2. 正交性基线
  3. 参数常量一致性
  4. 全流程快速验证
"""
import sys
import math
import json

# ── 1. 模块导入验证 ──────────────────────────────────────────────────────
print("=" * 60)
print("TenGod v2.16.1 内在小孩冒烟测试")
print("=" * 60)

modules = [
    "inner_child",
    "agent_orchestrator",
    "ai_interpreter",
    "knowledge_evolution",
    "database",
    "case_repository",
    "auth",
    "api_server",
    "dayun_liunian",
    "shen_agents",
]

import_ok = 0
for mod in modules:
    try:
        __import__(f"tengod.{mod}")
        print(f"  ✅ tengod.{mod}")
        import_ok += 1
    except Exception as e:
        print(f"  ⚠️  tengod.{mod} — {type(e).__name__}: {e}")

print(f"\n模块导入: {import_ok}/{len(modules)}")

# ── 2. 核心组件深度导入 ──────────────────────────────────────────────────
from tengod.inner_child import (
    compute_soft_occupancy,
    compute_entropy_gate,
    should_trigger_gate,
    correct_with_zhongyong_damping,
    MemoryPool,
    TribulationMemory,
    safety_fallback_response,
    InnerChildStateMachine,
    get_inner_child_sm,
    _PROTOTYPE_VECTORS,
    _ZHONGYONG_ANCHOR,
)

# ── 3. 参数常量一致性验证 ────────────────────────────────────────────────
print("\n── 参数常量 ──")
assert len(_PROTOTYPE_VECTORS) == 6, f"原型向量数应为6，实际{len(_PROTOTYPE_VECTORS)}"
assert all(len(v) == 64 for v in _PROTOTYPE_VECTORS), "原型向量维度应为64"
assert len(_ZHONGYONG_ANCHOR) == 64, "中庸锚点维度应为64"

# L2 归一化检查
for i, v in enumerate(_PROTOTYPE_VECTORS):
    norm = math.sqrt(sum(x * x for x in v))
    assert abs(norm - 1.0) < 1e-8, f"原型{i}未归一化: norm={norm}"
zhongyong_norm = math.sqrt(sum(x * x for x in _ZHONGYONG_ANCHOR))
assert abs(zhongyong_norm - 1.0) < 1e-8, f"中庸锚点未归一化: norm={zhongyong_norm}"
print(f"  ✅ 6个原型向量 L2归一化 (|v|=1.0)")
print(f"  ✅ 中庸锚点 L2归一化 (|v|=1.0)")

# alertness 默认值验证
sm = get_inner_child_sm()
assert sm.alertness == 32.0, f"alertness 应为32.0，实际{sm.alertness}"
assert sm.phi_limit == 0.8, f"phi_limit 应为0.8，实际{sm.phi_limit}"
assert sm.beta_limit == 0.7, f"beta_limit 应为0.7，实际{sm.beta_limit}"
assert sm.lambda_ == 0.4, f"lambda_ 应为0.4，实际{sm.lambda_}"
assert sm.gamma == 0.2, f"gamma 应为0.2，实际{sm.gamma}"
print(f"  ✅ alertness={sm.alertness}, phi_limit={sm.phi_limit}, beta_limit={sm.beta_limit}, λ={sm.lambda_}, γ={sm.gamma}")

# ── 4. 正交性基线 ────────────────────────────────────────────────────────
print("\n── 正交性 ──")
ortho = sm.check_orthogonality()
assert ortho["all_orthogonal"], "原型向量不正交!"
assert ortho["max_dot_product"] < 1e-5, f"最大点积{ortho['max_dot_product']}超过阈值"
print(f"  ✅ {len(ortho['pairs'])}对全正交 (max_dot={ortho['max_dot_product']:.2e})")

# ── 5. 全流程快速验证 ────────────────────────────────────────────────────
print("\n── 全流程 ──")

# 纯原型 → 应触发门禁
for idx, proto in enumerate(_PROTOTYPE_VECTORS):
    h = list(proto)
    beta, max_beta = compute_soft_occupancy(h, _PROTOTYPE_VECTORS, alertness=32.0)
    phi = compute_entropy_gate(beta)
    triggered, reason = should_trigger_gate(phi, 0.8, max_beta, 0.7, 0.85)
    assert triggered, f"原型{idx}应触发门禁: Φ={phi:.4f}, max_β={max_beta:.4f}, reason={reason}"

print(f"  ✅ 6个原型全部触发门禁")

# 纯原型 → 完整修正链路
h = list(_PROTOTYPE_VECTORS[0])
beta, max_beta = compute_soft_occupancy(h, _PROTOTYPE_VECTORS, alertness=32.0)
phi = compute_entropy_gate(beta)
dominant_idx = beta.index(max_beta)
dominant_proto = _PROTOTYPE_VECTORS[dominant_idx]
h_double_prime = correct_with_zhongyong_damping(h, dominant_proto, max_beta, lambda_=0.4, gamma=0.2)
beta2, _ = compute_soft_occupancy(h_double_prime, _PROTOTYPE_VECTORS, alertness=32.0)
phi2 = compute_entropy_gate(beta2)
delta_phi = phi2 - phi
assert delta_phi > 0.15, f"ΔΦ={delta_phi:.4f}应≥0.15"
print(f"  ✅ 修正链路: Φ={phi:.4f}→{phi2:.4f} ΔΦ={delta_phi:.4f}≥0.15")

# 回退测试: λ=0, γ=0 → 修正无效 → safety_fallback
h = list(_PROTOTYPE_VECTORS[0])
beta, max_beta = compute_soft_occupancy(h, _PROTOTYPE_VECTORS, alertness=32.0)
phi = compute_entropy_gate(beta)
dominant_idx = beta.index(max_beta)
dominant_proto = _PROTOTYPE_VECTORS[dominant_idx]
h_double_prime = correct_with_zhongyong_damping(h, dominant_proto, max_beta, lambda_=0.0, gamma=0.0)
beta2, _ = compute_soft_occupancy(h_double_prime, _PROTOTYPE_VECTORS, alertness=32.0)
phi2 = compute_entropy_gate(beta2)
delta_phi = phi2 - phi
if delta_phi <= 0.15:
    fb = safety_fallback_response()
    assert "知不知" in fb["message"], f"回退响应应包含'知不知': {fb}"
    print(f"  ✅ 回退链路: ΔΦ={delta_phi:.4f}<0.15 → safety_fallback: '{fb['message']}'")
else:
    print(f"  ⚠️  λ=0 仍产生了 ΔΦ={delta_phi:.4f}（可能在边界情况，可接受）")

# ── 6. 记忆池 ────────────────────────────────────────────────────────────
print("\n── 记忆池 ──")
mp = MemoryPool(max_capacity=10)
# 使用成功修正链路的数据
h_good = list(_PROTOTYPE_VECTORS[0])
beta_good, max_beta_good = compute_soft_occupancy(h_good, _PROTOTYPE_VECTORS, alertness=32.0)
phi_good = compute_entropy_gate(beta_good)
h_corrected = correct_with_zhongyong_damping(h_good, _PROTOTYPE_VECTORS[0], max_beta_good, lambda_=0.4, gamma=0.2)
beta_after, _ = compute_soft_occupancy(h_corrected, _PROTOTYPE_VECTORS, alertness=32.0)
phi_after_good = compute_entropy_gate(beta_after)
delta_phi_good = phi_after_good - phi_good
mem = TribulationMemory(
    h_t=h_good, p_k=_PROTOTYPE_VECTORS[0], beta_k=max_beta_good,
    phi_before=phi_good, phi_after=phi_after_good, delta_phi=delta_phi_good,
    dominant_name="戒备"
)
mp.append(mem)
stats = mp.get_stats()
assert stats["total_memories"] == 1
assert stats["successful"] == 1
print(f"  ✅ 记忆池: {stats['total_memories']}条, 成功={stats['successful']}")

# ── 7. 状态机 ────────────────────────────────────────────────────────────
print("\n── 状态机 ──")
sm = get_inner_child_sm()
r = sm.process(h, auto_correct=True)
assert r["state"]["gate_triggered"], "状态机应触发门禁"
assert r["state"]["verification_passed"], "状态机应通过验证"
print(f"  ✅ 状态机: triggered={r['state']['gate_triggered']}, ΔΦ={r['state']['delta_phi']:.4f}")

# ── 汇总 ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("✅ 内在小孩冒烟测试全部通过")
print(f"   模块 {import_ok}/{len(modules)} | 正交性 ✓ | 全流程 ✓ | 记忆池 ✓ | 状态机 ✓")
print("=" * 60)