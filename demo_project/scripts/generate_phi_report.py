#!/usr/bin/env python3
"""v2.16.1 Φ 熵值基线报告 —— CI/CD phi-monitor 专用"""
import json
import math
from tengod.inner_child import (
    compute_soft_occupancy,
    compute_entropy_gate,
    _PROTOTYPE_VECTORS,
    _ZHONGYONG_ANCHOR,
)

report = {"version": "2.16.1", "samples": []}

# 六类偏执向量 → 修正前 Φ
for idx, proto in enumerate(_PROTOTYPE_VECTORS):
    h = list(proto)
    beta, _ = compute_soft_occupancy(h, _PROTOTYPE_VECTORS, alertness=32.0)
    phi_before = compute_entropy_gate(beta)
    report["samples"].append({
        "archetype": idx,
        "phi_before": round(phi_before, 4),
        "phi_limit": 0.8,
        "alert": phi_before < 0.8,
    })

# 均衡向量（不应触发门禁）
h_balanced = [math.sin(i * 0.3) * 0.3 for i in range(64)]
beta_b, _ = compute_soft_occupancy(h_balanced, _PROTOTYPE_VECTORS, alertness=32.0)
phi_b = compute_entropy_gate(beta_b)
report["samples"].append({
    "archetype": "balanced",
    "phi_before": round(phi_b, 4),
    "phi_limit": 0.8,
    "alert": phi_b < 0.8,
})

# 写入文件
with open("phi-baseline.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))