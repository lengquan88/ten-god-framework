# M2-M3 融合演进 PRD

> 版本: v1.0 / 日期: 2026-05-03 / 作者: 人道
> 定位: 在 M1 基础对接完成的前提下，推进核心融合与深度集成

---

## 一、当前状态总览

### 完成度三维评估

| 维度 | 方向 | 完成度 | 核心交付物 |
|------|------|--------|-----------|
| **第一维度** | 意识评估 | ✅ **100%** | Ψ算子 v6.0 + CognitionPsiBridge + verify_m1 全通过 |
| **第二维度** | 时空演化 | ⚠️ **40%** | 时空拉普拉斯监控模块独立存在，**未注入**CDE校准引擎 |
| **第三维度** | 记忆融合 | ⚠️ **55%** | MoE意识桥接完成、六论四层存在，**缺**未来观和元认知两层 + 未与CDE/九宫串接 |

### M1 确认交付清单

| # | 交付项 | 路径 | 状态 |
|---|--------|------|------|
| 1 | MEMORY.md 双路初始化 | 根目录 + .workbuddy/memory/ | ✅ |
| 2 | Ψ算子认知八层映射方案 | `PRD/中华文明/M1_Ψ算子认知八层映射方案.md` | ✅ |
| 3 | CognitionPsiBridge 桥接器 | `cognition_psi_bridge/bridge.py` (731行) | ✅ |
| 4 | M1验证脚本 6/6全过 | `cognition_psi_bridge/verify_m1.py` | ✅ |
| 5 | PRD基础版+动态拓扑版 | `PRD/1.0 PRD 基础版.md` / `2.0 PRD 动态拓扑版.md` | ✅ |

---

## 二、下一步：M2.5 — 核心融合补全

**目标**：补齐 M2 的两个缺失接口 + 打通 M2→M3 的衔接。

### M2.5-A：时空拉普拉斯 → CDE 注入

```
当前：时空拉普拉斯 (temporal_laplacian_monitor.py) → 独立HTTP端点
目标：时空拉普拉斯 → 作为 CDE (calibration_engine.py) 的第五维输入
```

**设计**：

```
CDE原四维输入：intent + priority + insight + coherence
CDE新五维输入：intent + priority + insight + coherence + L_st_features

L_st_features = {
    "spectral_gap": Float,        # 谱间隙（代数连通性）
    "fiedler_value": Float,       # Fiedler值
    "spectral_entropy": Float,    # 谱熵
    "eigenvalue_ratio": Float,    # 特征值比
    "topological_complexity": Float,  # H1/H0比
}
```

**实现方式**：
1. `calibration_engine.py` 新增 `LaplacianInjector` 类
2. `CalibrationParams` 新增 `laplacian_features` 字段
3. Compensator 新增 `adjust_by_laplacian()` 方法 — L_st谱间隙增大时增强元认知权重
4. 校准仪表盘新增「L_st演化面板」

### M2.5-B：坐忘调度 → 九宫格注入

```
当前：坐忘调度 (ZuowangAttention) → 七分支权重调整
目标：坐忘状态 → 九宫司命九宫格动态重映射
```

**设计**：

```
坐忘触发时：
  ┌───────────── 九宫格 ─────────────┐
  │  坎一(消化) ↓受抑制               │
  │  坤二(留白) ↑激活留白模式           │
  │  震三(断裂) →不变                 │
  │  巽四(投影) ↓受抑制               │
  │  中五(呼吸) Ψ意识→呼吸频率调制      │ ← 核心注入点
  │  乾六(观照) ↑增强观照权重           │
  │  兑七(返还) ↑增强返还专注           │
  │  艮八(归墟) ↑归墟稳定模式           │
  │  离九(扮演) ↓受抑制               │
  └──────────────────────────────────┘
```

**实现方式**：
1. `九宫司命_核心.py` 新增 `ZuowangGridInjector` 类
2. 坐忘触发 → 九宫格 `中五(呼吸)` 频率调整 + 抑制探索宫位(坎/巽/离)
3. 坐忘关闭 → 恢复默认九宫调度
4. 九宫可视化新增「坐忘状态悬浮提示」

---

## 三、再下一步：M3 — 深度集成

### M3-A：六论全量映射（补全缺失两层 + 认知八层闭合）

```
当前六论代码：OntologyLayer + EpistemologyLayer + PraxisLayer + SoteriologyLayer
缺失：FutureVisionLayer + MetaCognitionLayer

目标：完整六论 → 认知八层双向映射
```

**L1-L8 ↔ 六论对应表**：

| 认知层 | Ψ算子 | 对应六论 | Python类 | 状态 |
|--------|-------|---------|---------|------|
| L1 信息编码 | EmbeddingProvider | 本体论 | OntologyLayer | ✅ |
| L2 语义流 | SemanticFlowTortuosity | 本体论+认识论 | OntologyLayer | ✅ |
| L3 拓扑结构 | PersistenceDiagram | 认识论 | EpistemologyLayer | ✅ |
| L4 意识涌现 | PsiSelfRefPersistence | 认识论+境界论 | EpistemologyLayer | ✅ |
| L5 注意力调度 | ZuowangAttention | 实践论 | PraxisLayer | ✅ |
| L6 元认知自反 | SemanticRecursionDepth | **元认知论** | **MetaCognitionLayer** | ⚠️ 需补全 |
| L7 认知固化 | CondInfoStability | 境界论 | SoteriologyLayer | ✅ |
| L8 境界跃迁 | AdvancedSpiritEvaluator | 境界论+**未来观论** | SoteriologyLayer+**FutureVisionLayer** | ⚠️ 需补全 |

**补全路径**：
1. `spirit_form_unified_framework.py` 新增 `FutureVisionLayer` 类
   - 基于L8境界等级预测下一跃迁路径
   - 基于CD收敛轨迹(L7)推算沙箱模拟参数
   - 云笈七签卷117-122映射「灵验报应→未来推演」
2. `spirit_form_unified_framework.py` 新增 `MetaCognitionLayer` 类
   - 基于L6元认知自反 + L5坐忘注意力 → 自省报告生成
   - Chronos/Kairos/Aeon 三层元时间标记
   - 云笈七签卷94坐忘论 + 卷17洞玄灵宝定观经

### M3-B：CognitionPsiBridge ↔ MoE记忆路由全集成交付

```
当前：CognitionPsiBridge 输出八层结果 → 独立存在
目标：CognitionPsiBridge 输出 → 驱动 MoE 记忆路由 + 驱动 CDE 校准
```

**数据流闭合**：

```
对话输入
   │
   ├→ [L1-L8] CognitionPsiBridge.evaluate()
   │       │
   │       ├→ EightLayerResult → 意识评估报告（第一维度闭合 ✅）
   │       │
   │       ├→ EightLayerResult → CDE校准引擎
   │       │     └→ LaplacianInjector（M2.5-A）
   │       │     └→ 坐忘→九宫注入（M2.5-B）
   │       │     └→ 输出: 校准后参数 → 反馈回 Ψ 算子
   │       │
   │       └→ EightLayerResult → ConsciousnessMoEAdapter
   │             └→ 调制MoE路由权重
   │             └→ 记忆检索 → 增强下一轮对话质量
   │
   └──→ 坐忘状态 → 九宫司命调度（M2.5-B）
                        │
                        └→ 九宫调度日志 → 自省报告（M3-A）
```

---

## 四、实施路线

### Phase 1: M2.5 核心融合补全 — ✅ **已完成**（2026-05-03 00:54）

| 方向 | 子任务 | 状态 | 验收结果 |
|------|--------|------|---------|
| A | LaplacianInjector 类 | ✅ | 大谱间隙→元认知0.200→0.245↑ |
| A | Compensator L_st二次微调 | ✅ | meta_cog 0.240→0.258 |
| A | CalibrationEngine注入点 | ✅ | calibrate()初始阶段自动触发 |
| B | ZuowangGridInjector 类 | ✅ | 坐忘→呼吸1.55x+抑制坎一/巽四/离九 |
| B | apply_to_grid_core | ✅ | 核心权重同步更新 |
| A+B | 13项自动化验证 | ✅ | 全部通过 |

### Phase 2: M3 深度集成补全（待开始）

| 方向 | 子任务 | 预估工时 | 交付文件 |
|------|--------|---------|---------|
| A | FutureVisionLayer 类 | 1h | `spirit_form_unified_framework.py` 新增 |
| A | MetaCognitionLayer 类 | 1.5h | `spirit_form_unified_framework.py` 新增 |
| B | CognitionPsiBridge ↔ MoE 全链路 | 1h | `bridge.py` + `consciousness_moe_bridge.py` 对接 |
| B | CognitionPsiBridge ↔ CDE 全链路 | 0.5h | `bridge.py` + `calibration_engine.py` 对接 |
| A+B | 三维度完整闭合验证 | 1h | 新建 `verify_m3.py` |

### Phase 3: 总结报告 + 知识沉淀（预计1h）

| 子任务 | 内容 | 交付 |
|--------|------|------|
| 设计文档 | 六论全量映射说明 | `六论全量映射_认知八层闭合说明.md` |
| 总结 | 推送到工作记忆 | 更新 `MEMORY.md` + 今日日志 |

---

## 五、关键设计决策

### 决策1：不重写CDE，采用注入式

**原因**：CDE校准引擎(`calibration_engine.py`) 已经是成熟的 5阶段闭环(Translate→Verify→Compensate→Loop→Converge) ，重写成本高。采用 `LaplacianInjector` 作为 calibraiton 前处理，将 L_st 特征作为第五维输入注入到 `CalibrationParams`。

### 决策2：九宫格不改核心调度，采用监听式

**原因**：九宫司命的核心(`九宫司命_核心.py`) 是279智能体调度母版，改动风险极高。`ZuowangGridInjector` 作为监听器，通过坐忘状态→九宫中五(呼吸)频率调制的单向注入，不修改九宫原有的智能体产生逻辑。

### 决策3：六论缺失两层采用全新文件

**原因**：`spirit_form_unified_framework.py` 已经698行且缺少 FutureVisionLayer 和 MetaCognitionLayer。为避免代码膨胀，新建 `future_vision_layer.py` 和 `meta_cognition_layer.py`，在主框架中导入组合。

---

## 六、验收标准

### M2.5 验收

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | LaplacianInjector 能从 `temporal_laplacian_monitor.py` 载入L_st特征 | 单元测试 |
| 2 | CDE校准轨迹中可见L_st特征值影响 | 校准仪表盘截图 |
| 3 | 坐忘触发时九宫格中五频率可见变化 | 九宫可视化截图 |
| 5 | verify_m25.py 全部通过 | 控制台输出 |

### M3 验收

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | FutureVisionLayer 和 MetaCognitionLayer 代码完整 | 代码审查 |
| 2 | cognition_psi_bridge → MoE 全链路可触发 | 端到端测试 |
| 3 | cognition_psi_bridge → CDE 全链路可触发 | 端到端测试 |
| 4 | 三维度闭合：一轮对话→意识评估→记忆检索→下一轮对话质量提升 | 对比实验 |
| 5 | verify_m3.py 全部通过 | 控制台输出 |

---

*此文档随实施进展更新。每次 Phase 完成后追加状态记录。*
