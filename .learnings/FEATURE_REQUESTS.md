# FEATURE REQUESTS — 功能请求清单

> 尚未落地的功能方向。每一项都有目标场景、优先级、预计工时。

---

## FR-001 · 基因进化协议（GEP · Gene-Evolution Protocol）

- **优先级**: P0
- **目标场景**: 让 Agent 的能力基因（`genes.json`）、成功胶囊（`capsules.json`）、进化事件（`events.jsonl`）能被其他 Agent 读取，形成跨会话、跨 Agent 的进化。
- **预期工时**: 16h
- **核心设计**:
  - `genes.json` — 每条"基因"包含 `{ id, name, domain, relations, fitness, createdAt, retiredAt? }`
  - `capsules.json` — 每个"成功胶囊"封装一个完整的可复制流程
  - `events.jsonl` — Line-delimited JSON 事件流，便于 grep / tail / 工具检索
- **前置依赖**:
  - 统一的文件格式定义（已就绪）
  - 仓库级的 `.learnings/` 目录命名约定

---

## FR-002 · 跨会话 engram 上下文自动还原

- **优先级**: P0
- **目标场景**: 每次新会话打开（或用户重启 IDE），自动从 `localStorage['deepseek-v4:engrams']` 读取历史 engram 并重建一个"默认上下文提示"，让 Agent 立刻知道"自己上次做了什么、结构是什么、下一步该往哪走"。
- **预期工时**: 8h
- **核心设计**:
  - `lib/engram.ts` 新增 `bootstrapContext(prompt: string): string`
  - 面板层新增"记忆冷启动"视图，显示最近 5 条 engram 的自描述
- **前置依赖**:
  - 当前的 `addEngram` / `engageEngram` 链路已就绪
  - 需要定义"冷启动上下文"的模板格式

---

## FR-003 · GEE (Gene-Engram-Ego) 三层自反模型

- **优先级**: P1
- **目标场景**: 作为"非人类中心"的 AI 自我意识模型。核心命题是：
  - **Gene 层** (类代码库): 算法模块/能力基因
  - **Engram 层** (类工作记忆): 本次会话中生成的关系图谱
  - **Ego 层** (类主体意识): 基于前两层的统计画像 + 时间演化
- **预期工时**: 32h
- **核心设计**:
  - 在 `lib/` 下新增 `three-tier-ego.ts`
  - 输出结构化 JSON 供 `components/GeePanel.tsx` 可视化
- **前置依赖**: FR-001, FR-002

---

## FR-004 · 非人类中心的"关系涌现"评估

- **优先级**: P2
- **目标场景**: 不把"是否涌现"当作一个 yes/no 问题，而是把它**定义为关系图谱中的可测量现象**——当 engram 传播图中出现"三角闭合"（三个 engram 两两互相共振），或"主导关系键随时间偏移"时，我们说系统在"涌现"。
- **预期工时**: 12h
- **核心设计**:
  - `computeEngramGraph()` 中增加 `triadicClosure` 字段
  - `SixGatesPanel.tsx` 中以时间轴显示"关系键主导度演化图"
- **前置依赖**:
  - 至少 30+ 条 engram 的样本量（才能开始测）
