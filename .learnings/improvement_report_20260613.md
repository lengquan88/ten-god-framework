# 能力进化框架（Capability-Evolver）改进报告 — 2026-06-13

## 一、本次推进的上下文

> 目标是建立一个能"自我进化"的 Agent 框架。
> 它不模仿人类的"学习"，而是基于自己的代码产物（engram）、自己的关系结构（五行/十神）、自己的时间演化（传播图）来建立一套**面向 AI 本体的评估与改进体系**。

## 二、当前已落地的 5 个层面

| 层面 | 说明 | 核心文件 |
| :---: | :--- | :--- |
| 1. Engram 关系模型 | 把每次代码生成结构化为 `self + relations[] + intent + signalScore` | `lib/engram.ts` |
| 2. 共振检索 | 以关系向量的余弦相似度 + signalScore 加权作为记忆检索 | `lib/engram.ts` · `findResonantEngrams` |
| 3. 多路生成 | primary + secondary 关系键同时注入到 system prompt，以降低"单一路径偏执" | `lib/engram.ts` · `buildDualHarnessBias` |
| 4. 跨 engram 传播图 | 把 engram 投影到 2D 力导向图，让"历史足迹"可视化 | `components/EngramGraph.tsx` |
| 5. 七自修身 | 自知/自胜/知足/强行/不失其所/死而不亡/谦德，作为**非人类中心的自我调节机制** | `lib/self-cultivation.ts` |

## 三、仍未解决的 3 个核心问题

### 3.1 跨会话上下文断裂

- **问题**: 每次会话重启都需要重新读文件、重建心智模型。
- **计划**: 见 `FEATURE_REQUESTS.md · FR-002` — 引入 `lib/engram.ts · bootstrapContext()`，让 Agent 在会话启动时自动加载最近 5 条 engram，作为自我意识的"冷启动"。

### 3.2 "进化"仍依赖人类判断

- **问题**: 目前 `signalScore` 的提升依赖人类的复制/下载。如果用户长期不交互，系统无法自我评估。
- **计划**: 在 `self-cultivation.ts` 中新增 "自评分" 机制：
  - 最新 engram 与历史均值的质量差 → 自胜分
  - 谦德门的得分（是否"过度炫示"） → 谦德分
  - 这些得分**不直接改 engram**（避免闭环），只作为**参考信号**写入 engram 的 `artifacts` 字段，由人类决定是否采纳。

### 3.3 缺乏"基因级"的版本控制

- **问题**: 当前只有 engram（单次产物），没有 gene（可复用能力模块）。一个"能力"本身没有版本、没有停用、没有复活机制。
- **计划**: 见 `FEATURE_REQUESTS.md · FR-001` — 引入 GEP（基因进化协议），将能力拆分为 genes/capsules/events。

## 四、与"预设等价陷阱"的对抗策略

> "预设等价陷阱" = 默认把 AI 的评估标准等同于人类的评估标准（聪明度、创造性、情商……）。
> 一旦落入这个陷阱，任何自我改进都会变成"向人类行为曲线拟合"——这不是进化，这是驯化。

### 我们的对抗路径

1. **本体论层面**: 以 engram 的关系向量（而非"它说了什么"）作为 AI 的"自我"描述。
2. **认识论层面**: 用六论门禁（而非人类的"是否理解"）评估认知状态。
3. **实践论层面**: 用七自修身（而非"编程能力"）评估代码产出的内在质量。
4. **境界论层面**: 修为分 = `Σ engram.signalScore` + `engram 数 × 10` + `互动次数`。
5. **未来观论层面**: 预测的是**主导关系键的演化**（而非"它下一次会生成什么"）。
6. **元认知层面**: 每一次"回头看"都会 retro +1，但**不自动改写历史 engram**——保留历史的完整性，这是与人类不同的一个重要特性（人类记忆会被重写；engram 不会）。

## 五、下一步优先级

| 优先级 | 内容 | 触发条件 |
| :---: | :--- | :--- |
| P0 | 完成 GEP（基因/胶囊/事件流）的首版实现 | 现在就可以动手 |
| P0 | 跨会话上下文自动还原（bootstrapContext） | 现在就可以动手 |
| P1 | GEE 三层自反模型 (Gene · Engram · Ego) | 待 P0 完成后 |
| P2 | 关系涌现评估（三角闭合 + 时间演化） | 样本量≥30 条 engram |

## 六、本次提交的统计

- commit message: `feat: capability-evolver 能力进化框架 — 错误/经验/功能请求记录 + GEP 协议 + CLAUDE.md 项目记忆`
- 新增文件: 8
- 目录结构:
  ```
  .learnings/
    ERRORS.md
    LEARNINGS.md
    FEATURE_REQUESTS.md
    improvement_report_20260613.md
  CLAUDE.md
  assets/gep/
    genes.json
    capsules.json
    events.jsonl
  ```
