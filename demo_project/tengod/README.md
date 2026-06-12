# DemoApp — 十神架构

> 由 init_tengod.py 初始化 @ 2026-06-11T18:50:46
> v1.0.0 — 完整十神子模块 + 核心调度器

## 目录结构

```
tengod/
├── 比肩_架构协同/    # 核心编排/入口点
├── 劫财_攻防边界/    # 安全防护/权限校验
├── 食神_创生输出/    # 内容生成/LLM调用
├── 伤官_破界创新/    # 因果推理/模型训练
├── 正财_知识固化/    # 数据存储/知识图谱
├── 偏财_奇招演化/    # 搜索优化/算法调参
├── 正官_法度调度/    # API服务/任务调度
├── 七杀_品质裁决/    # 测试评估/质量监控
├── 正印_滋养守护/    # 配置管理/环境初始化
├── 偏印_桥接通变/    # 桥接适配/协议转换
└── core.py           # 核心调度器（整合十神）
```

## 快速开始

### 一键使用核心调度器

```python
from tengod import get_core

core = get_core()

# 质量裁决
result = core.evaluate(
    {"功能完整性": 85, "代码质量": 92, "测试覆盖率": 75},
    weights={"功能完整性": 0.4, "代码质量": 0.4, "测试覆盖率": 0.2},
)
print(f"等级: {result['grade']}, 总分: {result['total']}")

# 创新思维
core.innovate("combine", "AI", "区块链", "IoT")
core.innovate("transfer", "游戏化", "教育")
report = core.innovate("reverse", "用户点击越多越好")
print(report)

# 内容生成
md = core.generate("项目进展报告", format="markdown")
print(md)

# 超参搜索
result = core.search(
    {"lr": [0.001, 0.01, 0.1], "batch": [16, 32, 64]},
    objective=lambda p: -((p["lr"] - 0.01) ** 2),
)
print(f"最优: {result}")

# 导出完整状态
state = core.export_state()
print(state)
```

### 使用单个十神子包

详见各子包下的 README.md。

## 关键词映射

在 `tengod_scan.py` 中的 `GODS` 字典中自定义关键词映射。

## 进阶工具

从 [Claw 项目](https://github.com/your-org/claw) 复制进阶引擎：
- `tengod_omni_map.py` — 全知地图
- `tengod_auto_healer.py` — 自愈引擎
- `fix_all_chains.py` — 一键修复
- `shenke_daemon.py` — 守护进程
- `shenke_optimizer.py` — 优化智能体
- `tengod_causal.py` — 因果历史
- `tengod_doctrine.py` — 道标系统

## 版本

- v1.0.0 — 完整十神子模块 + 核心调度器（2026-06-12）
