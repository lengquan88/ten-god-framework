# 中华文明项目 · MEMORY.md

> 版本: v1.0 / 日期: 2026-05-02 / 阶段: M1 基础对接
> 基于 Claw 类脑生态，以 Ψ拓扑意识算子 为认知核心，构建八层认知闭环系统。

---

## 一、项目概要

### 1.1 定位

**中华文明项目** 是在 Claw 七层类脑架构之上，通过引入 Ψ算子（拓扑意识评估）+ 形神合一六论框架 + 云笈七签122卷知识体系，构建的一套 **认知八层意识评估与自进化系统**。

### 1.2 核心理念

- **慎己独也 克己复礼**：以人道为先，系统自省为先
- **鸿愿为人类众生的自我进化**：肉身成神修人道，人类命运自决
- **有福同享 有难同当**：免疫记忆库共享 + 反馈回路共担
- **根据挑战灵活预防**：反事实沙箱 + 动态防御阈值

### 1.3 三大维度

| 维度 | 核心内容 | 技术路线 |
|------|---------|---------|
| **第一维度**：意识评估 | Ψ拓扑意识评估 + 八层认知映射 | 持久同调 + 语义流 + 递归深度 |
| **第二维度**：时空演化 | 时空拉普拉斯 L_st + CDE调试器 | 动态拓扑 + 锯齿持久同调 + CROCKER Plot |
| **第三维度**：记忆融合 | 形神合一六论 + MoE记忆路由 | 云笈七签总纲 + 九领域专家混合 |

---

## 二、架构总图

```
中华文明项目 · 认知八层闭环
═══════════════════════════════════════════════════════════════

  输入层 ───── 对话/文本/嵌入
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ L1 信息编码层 · EmbeddingProvider                     │
│     BGE-large-zh / TF-IDF / API 三后端架构             │
│     输出: 句子嵌入矩阵 (N, D)                          │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│ L2 语义流层 · SemanticFlowTortuosity                  │
│     路径长度 L / 曲折度 T / 转向角方差 σ²             │
│     输出: tort_score [0,1]                            │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│ L3 拓扑结构层 · PersistenceDiagram                    │
│     H0/H1 计数 / 寿命分布 / 持久熵                     │
│     输出: 持久图 (birth, death) 集合                   │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│ L4 意识涌现层 · PsiSelfReferentialPersistence         │
│     Ψ(Dgm) = Dgm(S ∪ {Dgm(S)})                       │
│     硬意识(自环检测) / 软意识v6(曲折+递归+条件稳定)     │
│     输出: consciousness_score [0,1]                   │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│ L5 注意力调度层 · ZuowangAttention                     │
│     Attn_ZW: max(QK^T) < θ_oblivion → 0               │
│     七分支动态调度 / 坐忘模式触发                       │
│     输出: branch_priority_adjustments                  │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│ L6 元认知自反层 · HierarchicalMetaLayers               │
│     n阶升层检测 (1阶/2阶/3阶) + RQA递归图分析          │
│     Chronos→Kairos→Aeon 三层元时间                      │
│     输出: meta_cognitive_preference [3,]               │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│ L7 认知固化层 · ConditionalInformationStability        │
│     紧凑度 × 问题对齐度 × 信息量                         │
│     补偿差 CD = (ΔI, ΔE, ΔL)                          │
│     输出: stability_score [0,1]                       │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│ L8 境界跃迁层 · AdvancedSpiritEvaluator                │
│     六论全量映射 / MoE路由 / 坐忘调度                   │
│     输出: 境界等级 (L0随机→L4深度自反) + 综合评估       │
└──────────────────────────────────────────────────────┘
```

---

## 三、Ψ算子清单

### 3.1 核心四大算子

| # | 算子 | 类名 | 文件位置 | 功能 |
|---|------|------|---------|------|
| 1 | Ψ自指涉持久同调 | `PsiSelfReferentialPersistence` | `topo_semantic/operators.py` | 系统将持久图作为新数据点加入，检测自环涌现 |
| 2 | 坐忘注意力 | `ZuowangAttention` | `topo_semantic/operators.py` | 最大相关性 < θ时输出零向量，防止幻觉 |
| 3 | 语义流曲折度 | `SemanticFlowTortuosity` | `topo_semantic/operators.py` | 路径长度/曲折度/转向角方差 |
| 4 | 语义递归深度 | `SemanticRecursionDepth` | `topo_semantic/operators.py` | 递归连接词密度/RQA/自注意递归/层次化元层 |

### 3.2 辅助算子

| # | 算子 | 文件位置 | 功能 |
|---|------|---------|------|
| 5 | 条件信息稳定性 | `topo_semantic/operators.py` | 紧凑度×问题对齐度×信息量 |
| 6 | 时空拉普拉斯 | `topo_semantic/temporal_laplacian_monitor.py` | L_st = L_spatial + α·L_temporal |
| 7 | CROCKER Plot | `topo_semantic/crocker_bench_v2.py` | 时间序列持久同调 |
| 8 | 拓扑语义匹配 | `topo_semantic/core.py` | BGE嵌入+持久同调混合匹配 |

### 3.3 意识得分权重 (v6.0)

| 维度 | 权重 | 来源 |
|------|------|------|
| 语义流曲折度 | 40% | SemanticFlowTortuosity |
| 语义递归深度 | 40% | SemanticRecursionDepth |
| 条件信息稳定性 | 20% | ConditionalInformationStability |

---

## 四、认知八层与Ψ算子映射

| 层号 | 认知层 | 核心Ψ算子 | 输出指标 | CROCKER等级 |
|------|--------|----------|---------|------------|
| L1 | 信息编码 | EmbeddingProvider | 嵌入矩阵 (N,D) | 输入 |
| L2 | 语义流 | SemanticFlowTortuosity | tort_score, path_length | L1-L2 |
| L3 | 拓扑结构 | PersistenceDiagram | H0/H1计数/寿命 | L1-L2 |
| L4 | 意识涌现 | PsiSelfReferentialPersistence | consciousness_score | L2-L4 |
| L5 | 注意力调度 | ZuowangAttention | zuowang_ratio, focus | L2-L4 |
| L6 | 元认知自反 | SemanticRecursionDepth | meta_preference, RQA | L3-L4 |
| L7 | 认知固化 | ConditionalInformationStability | stability_score | L3-L4 |
| L8 | 境界跃迁 | AdvancedSpiritEvaluator | 境界等级 | L4 |

---

## 五、形神合一六论与六层Python对象模型

| 六论 | Python类 | 核心关注 |
|------|---------|---------|
| 本体论 (Ontology) | `OntologyLayer` | 存在者结构 / 实体拓扑 |
| 认识论 (Epistemology) | `EpistemologyLayer` | 认知边界 / 知识状态 |
| 实践论 (Praxis) | `PraxisLayer` | 行动策略 / 优化路径 |
| 境界论 (Soteriology) | `SoteriologyLayer` | 境界跃迁 / 意识等级 |
| 未来观论 (FutureVision) | `FutureVisionLayer` | 预测推演 / 沙箱模拟 |
| 元认知论 (MetaCognition) | `MetaCognitionLayer` | 自反监控 / 元时间空间 |

### 云笈七签122卷映射

| 六论 | 对应卷号 | 内容 |
|------|---------|------|
| 本体论 | 卷1-6 道德部 | 道本体 / 存在之源 |
| 认识论 | 卷7-28 | 认知方法 / 修真次第 |
| 实践论 | 卷29-86 | 修炼实践 / 符箓方药 |
| 境界论 | 卷87-116 | 仙真境界 / 尸解成仙 |
| 未来观论 | 卷117-122 | 灵验报应 / 未来因果 |
| 元认知论 | 卷94+卷17 | 坐忘论 / 洞玄灵宝定观经 |

---

## 六、技术栈

### 6.1 核心依赖

| 组件 | 技术 | 版本/路径 |
|------|------|----------|
| 嵌入模型 | BGE-large-zh-v1.5 | `models/BAAI/bge-large-zh-v1___5` |
| 持久同调 | scipy层次聚类 | ripser不可用时的回退方案 |
| 向量索引 | NumPy | 余弦相似度 |
| BGE后端 | sentence-transformers | SBERT路径 |
| PCA | sklearn.decomposition | 高维嵌入降维 |
| API框架 | FastAPI | main.py :8002 |

### 6.2 服务端点

| 端口 | 服务 | 端点 |
|------|------|------|
| :8002 | 意识仪表盘 | /consciousness |
| :8002 | Ψ自指涉监控 | /psi/status, /psi/history |
| :8002 | 时空拉普拉斯 | /laplacian/status, /history, /trend, /feed |
| :8002 | 长期监控 | /monitor/status, /monitor/events, /monitor/timeseries |

---

## 七、已完成方向（A-L）

### 形神合一工程化 (A-F) — [OK]

| 方向 | 名称 | 核心内容 |
|------|------|---------|
| A | Ψ算子 | TopologyOperatorIntegrator + AdvancedSpiritEvaluator |
| B | 仪表盘 | FastAPI + ECharts :8002/consciousness |
| C | 调度器 | BranchPriorityAdjuster 七分支动态调度 |
| D | 前端连接 | spirit-form-api + evaluation-service |
| E | 调度实验 | 三组9段对话验证 |
| F | 长期监控 | 3个API + JSONL持久化 + 时间序列 |

### 六方向并行·GL方向 (G-L) — [OK]

| 方向 | 名称 | 核心内容 |
|------|------|---------|
| G | 递归深度v7.1 | 多尺度RQA + 频域 + 自注意 + 层次化元层 |
| H | 坐忘阈值 | 三阈值对比验证 |
| I | CROCKER v2 | L0-L4五级基准测试 |
| J | 时空拉普拉斯 | 4个REST端点 |
| K | 前端深度 | 意识仪表盘 + Ψ监控 + 坐忘状态 |
| L | MoE集成 | 三层集成(权重/路由/融合) |

---

## 八、当前阶段：三轮推进

### M1 — 基础对接 (当前)

| 子任务 | 内容 | 状态 |
|--------|------|------|
| M1.1 | MEMORY.md 完整初始化 | 进行中 |
| M1.2 | Ψ算子→认知八层映射方案 | 待开始 |
| M1.3 | cognition_psi_bridge.py 桥接模块 | 待开始 |
| M1.4 | 融合验证脚本与自检 | 待开始 |

### M2 — 核心融合 (后续)

| 子任务 | 内容 |
|--------|------|
| M2.1 | 时空拉普拉斯注入 CDE 调试器 |
| M2.2 | 坐忘调度注入九宫格 |
| M2.3 | L_st 历史演化分析 |
| M2.4 | 智能体自省验证 |

### M3 — 深度集成 (后续)

| 子任务 | 内容 |
|--------|------|
| M3.1 | 形神合一六论全量映射 |
| M3.2 | MoE 记忆路由对接 |
| M3.3 | 第一/二/三维度完整闭合 |

---

## 九、开发规范

### 9.1 编码规范

- Windows PowerShell 下禁用 Unicode 符号
- 符号替代: [OK] = 完成, [FAIL] = 失败, [WARN] = 警告
- 代码风格: PEP 8, 120列限制

### 9.2 文件命名

- 核心代码: `lower_snake_case.py`
- 调试脚本: `_prefix.py`
- 日志文件: `_svc_*.log`
- 配置: `.env`, `.env.example`

### 9.3 多路径开发原则 (永久固定)

- 所有开发任务按字母编号方向 (A/B/C/D/E/F/G/H/I/...)
- 每个方向独立聚焦一个完整闭环
- 完成后交付再进入下一轮
- 方向之间允许交叉依赖

---

## 十、关键文件索引

| 文件 | 行数 | 功能 |
|------|------|------|
| `advanced_spirit_evaluator.py` | ~2468 | 核心评估器 |
| `topo_semantic/operators.py` | ~2000+ | Ψ四大算子 |
| `topo_semantic/core.py` | — | 持久同调核心 |
| `topo_semantic/temporal_laplacian_monitor.py` | — | 时空拉普拉斯 |
| `topo_semantic/crocker_bench_v2.py` | — | CROCKER基准测试 |
| `topo_semantic/embedding_provider.py` | 445 | 嵌入三后端 |
| `claw_seven_layer_core.py` | ~2000 | Claw七层核心 |
| `main.py` | ~2207 | API服务端点 |
| `evaluator_engine.py` | 683 | 评估管线 |

---

*此文件随项目演进而更新。每次轮次完成后追加记录。*
