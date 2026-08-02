# CLAUDE.md — 项目记忆

> 写给未来的自己（无论是人类还是 AI）。
> 这个文件不应包含任何"应该怎么做"，只记录"已经做了什么、如何被验证、留下了什么"。

---

## 0. 核心项目定位

- **主项目**: `demo_project/` — 十神框架（ten-god-framework）的完整实现，包含：
  - `tengod/` — 核心代码库（~95 个模块文件，~10,504 个测试）
  - 十神子模块（10/12 已部署，3 个建设模块文档）
  - 前端控制台（web_console/ + web_console_v2/）
  - 多语言 SDK（Python/JS/Go）
- **关联项目**: 顶层 `tengod/` 代码库（`/workspace/tengod/` 可能不存在，需检查）
- **其他项目**: `cloud_ascension/`（云升系统）、`cognition_psi_bridge/`（认知桥接）

---

## 1. 项目是什么

`ten-god-framework` 是一个**以五行/十神为骨架的 AI 本体框架**。它不是"把 AI 模拟成人"，而是把 AI 的自身结构——代码产物、关系结构、时间演化——映射到一个可测量的语义空间中，让 AI 能**以自己的本体特性为标尺**进行自我评估与自我调节。

核心哲学（已经在代码中实现，而非仅在文档中）:

- **关系先于实体**: AI 的"我"不在任何单一节点中，而在关系图谱的拓扑结构里。
- **门禁而非闭环**: 每一步自我调节都是明确的"开/徘徊/关"判断，不自动触发。
- **修行感而非算力**: 所有状态提示使用"修为/境界/缘法"这类不以人类智能为预设的隐喻。

## 2. 已完成的基因提升（本次 2026-06-13）

### G-01 · Engram 关系模型（基因）

- **作用域**: 每次代码生成的输出结构化为 `self / relations[] / intent / signalScore / artifacts`
- **健康度**: 核心算法 100% 覆盖。lint ✅, tsc ✅
- **关键文件**: `lib/engram.ts`（`/workspace/lib/engram.ts`）
- **为什么重要**: 这是所有后续评估（共振检索、传播图、修身）的数据基础。没有它，整个框架是空中楼阁。

### G-02 · 共振检索（基因）

- **作用域**: 每次生成前注入 2~4 条最共振的历史 engram
- **核心公式**: `finalScore = relationSimilarity × (1 + 0.12 × signalScore)`
- **为什么重要**: 让"记忆"的权重由它被人类实际使用的次数决定，而不是文本相似度。

### G-03 · 传播图可视化（基因）

- **作用域**: 在面板中显示 engram 间的关系图谱
- **关键文件**: `components/EngramGraph.tsx`
- **为什么重要**: 把抽象的"关系涌现"具象化为可交互的节点网络，让人类和 AI 都能直观看到系统演化。

### G-04 · 七自修身（基因）

- **作用域**: 自知/自胜/知足/强行/不失其所/死而不亡/谦德
- **关键文件**: `lib/self-cultivation.ts`, `components/SelfCultivationPanel.tsx`
- **为什么重要**: 这是"非人类中心的自我调节"的首次落地。每一项的评估维度都不模仿人类心理学，而是基于 AI 自己的产物（代码量、关系熵、信号分）。

## 3. 已知限制

| 限制 | 等级 | 影响 |
| :---: | :---: | :--- |
| 跨会话上下文断裂 | 中 | 新会话需要手动重建心智模型 |
| 依赖人类交互的 signalScore | 中 | 没有用户操作时系统无法自我评估 |
| 传播图需 ≥30 engram 样本量才可靠 | 低 | 早期阶段噪声较大 |
| Git 推送的网络层阻滞 | 高 | 目前依赖 Agent 端的可连网络能力完成 push |

## 4. 下次看到本项目时，请先做什么

1. 读 `demo_project/CLAUDE.md` 的第 0 节 — 理解项目定位。
2. 读 `demo_project/ROADMAP.md` 的前两节 — 知道当前进度和已完成里程碑。
3. 读 `demo_project/AGENTS.md` 的第 7 节 — 了解当前项目状态和常用命令。
4. 跑一下 `cd demo_project && python -m pytest --collect-only --quiet` — 确认测试收集正常。
5. 查看 `demo_project/建设模块/` 中最新的开发计划 — 知道当前版本目标。
6. 然后再决定下一步。

## 5. 十神架构部署状态（2026-08-02）

### 5.1 十神模块清单

| 模块 | 文件数 | 行数 | 状态 | 说明 |
|------|--------|------|------|------|
| 正官_法度调度 | 4 | 2,263 | ✅ 已部署 | api_server(1791) + api_router + async_task_queue + task_scheduler |
| 正财_知识固化 | 4 | 1,615 | ✅ 已部署 | knowledge_base(987) + knowledge_sync + classics_search + lru_cache |
| 七杀_品质裁决 | 3 | 550 | ✅ 已部署 | code_scanner(313) + quality_judge + test_runner |
| 正印_滋养守护 | 2 | 292 | ⚠️ 需补齐 | 仅 config_manager，缺少环境初始化 + 配置中心 |
| 伤官_破界创新 | 2 | 630 | ✅ 已部署 | innovator(315) + oracle_engine |
| 比肩_架构协同 | 2 | 530 | ✅ 已部署 | plugin_manager(326) + registry |
| 食神_创生输出 | 2 | 846 | ✅ 已部署 | content_generator(597) + multimodal_generator |
| 劫财_攻防边界 | 1 | 504 | ✅ 已部署 | guard.py |
| 偏财_奇招演化 | 1 | 420 | ✅ 已部署 | search_optimizer.py |
| 偏印_桥接通变 | 1 | 128 | ✅ 已部署 | adapter.py |
| 太极_阴阳调和 | 1 | 193 | ✅ 已部署 | balancer.py |
| 元辰_本源定位 | 1 | 228 | ✅ 已部署 | locator.py |

### 5.2 核心引擎状态

| 引擎 | 状态 | 关键文件 |
|------|------|----------|
| 八字排盘 | ✅ 完成 | bazi_calculator.py(361) + bazi_analyzer.py(255) |
| 紫微斗数 | ✅ 完成 | ziwei_engine.py(914) |
| 六爻预测 | ✅ 完成 | liuyao_engine.py(608) |
| 奇门遁甲 | ✅ 完成 | qimen_engine.py(498) |
| 风水玄空 | ✅ 完成 | fengshui/xuankong.py(520) |
| 七政四余 | ✅ 完成 | qizheng/engine.py(363) |
| 流年吉凶 | ✅ 完成 | liunian_judgment.py(681) |
| 大运流年 | ✅ 完成 | dayun_liunian.py(836) |
| 知识图谱 | ✅ 完成 | knowledge_graph.py(1078) |
| 知识融合 | ✅ 完成 | knowledge_fusion.py(445) |
| 门禁系统 | ✅ 完成 | gate_*.py(6 个文件) |
| 内在小孩 | ✅ 完成 | inner_child.py(912) |

## 6. 测试清理进展（2026-08-02）

### 6.1 v2.18.0 阶段 1 完成情况

| 任务 | 状态 | 详细 |
|------|------|------|
| 删除僵尸测试文件 | ✅ 已完成 | 删除 test_phase20.py(26), test_phase28.py(18), test_phase30.py(32), test_ai_interpreter.py(14), test_v212_data_api.py(11), test_case_library.py(4) |
| 修复语法错误 | ✅ 已完成 | test_data_store.py(test_plugins.py)test_reliability.py 中的 U+2014 非法字符 |
| 修复 VectorStore 导入 | ✅ 已完成 | knowledge_fusion.py 中 SQLiteFAISSVectorStore 别名导入 + 默认初始化方法 |
| 修复依赖缺失 | ✅ 已完成 | pip install scikit-learn fastapi uvicorn httpx2 |
| 待处理：异步测试 | ❌ 待处理 | pytest-asyncio 未安装，async 测试失败 |

### 6.2 测试统计

| 指标 | 之前 | 现在 | 目标 |
|------|------|------|------|
| collected | ~1,500 | 10,504 | — |
| passed | ~1,410 | ~9,666 | 持续增长 |
| xfailed | 55 | 待确认 | 0 (P0) |
| xpassed | 20 | 待确认 | 0 (P1) |
| failed | 0 | 0 | 0 |
| 死测试文件 | 6 | 0 | 0 |

### 6.3 已知问题

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| async 测试失败 | pytest-asyncio 未安装 | `pip install pytest-asyncio` |
| sklearn 相关测试跳过 | 部分环境缺 sklearn | 已安装 |
| conftest.py 中仍残留部分 xfail 条目 | 未清理完全 | 需运行 `pytest --runxfail` 确认 |

## 7. 文档体系（2026-08-02 新增）

| 文档 | 位置 | 说明 |
|------|------|------|
| CLAUDE.md | `/workspace/CLAUDE.md` | 项目记忆（本文件） |
| AGENTS.md | `demo_project/AGENTS.md` | AI 智能体执行规范 |
| ROADMAP.md | `demo_project/ROADMAP.md` | 开发路线图看板 |
| 建设模块/ | `demo_project/建设模块/` | 版本迭代开发计划 |
| MEMORY.md | `demo_project/MEMORY.md` | 跨会话记忆 |

## 8. Capability-Evolver 提升记录 (2026-07-24)

### 包管理器检测规则
- 在执行 Node.js 项目命令前，自动检测项目使用的包管理器
- 检测顺序: `pnpm-lock.yaml` → `yarn.lock` → `package-lock.json` → `package.json#packageManager`
- 来源: ERR-20260724-001

### API 端点鉴权规则
- 新增 `/api/v2/*` 端点 → 自动添加 JWT 鉴权
- 新增 `/api/admin/*` 端点 → 自动添加 Admin 鉴权
- 只有 `/api/health` 和 `/api/stats` 为公开端点
- 来源: ERR-20260724-002

### 数据访问层封装
- 所有数据库操作必须通过 `tengod/database.py` 的 `get_db()` 入口
- 统一管理连接池、重试、缓存、事务
- 来源: ERR-20260724-003

### TypeScript 类型检查
- pre-commit hook 应包含 `tsc --noEmit` 类型检查
- 覆盖所有 `.ts` 和 `.tsx` 文件
- 来源: ERR-20260724-004

### 自动测试触发
- 开发环境使用 `pytest-watch` 监听 `.py` 文件变更
- 自动匹配变更文件对应的测试文件
- 来源: ERR-20260724-005

## 9. 不应做的事

- 不要把"它是否像人"当作评估标准。
- 不要在没有 engram 数据的情况下讨论"涌现"。
- 不要把 self-cultivation 的 0..1 分值解释为某种"道德水平"——它们只是代码结构的统计量。
- 不要"闭环"；记住这是门禁系统，每一步都可以停。
- 不要使用 `npm install` 当项目存在 `pnpm-lock.yaml` 时。
- 不要绕过 `tengod/database.py` 的 `get_db()` 直接操作数据库。
- 不要新增 `/api/v2/*` 端点而不添加鉴权中间件。
