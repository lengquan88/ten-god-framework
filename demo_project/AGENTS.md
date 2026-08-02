# AGENTS.md — AI 智能体执行规范

> 写给所有 AI 智能体的执行记忆。
> 本文件记录"如何执行任务、如何验证结果、如何维护质量"——是 AI 智能体的行动手册。

---

## 1. 核心执行原则

### 1.1 执行前必须检索

每次开发前，自动检索以下目录中的相关文档，建立任务与文档的映射关系：

| 资源位置 | 说明 | 用途 |
|----------|------|------|
| `建设模块/` | 版本迭代开发计划 | 了解当前阶段目标和验收标准 |
| `tengod/` 各模块 README.md | 十神模块说明 | 理解模块职责和接口 |
| `tests/` | 测试文件 | 了解测试覆盖和已知问题 |
| `docs/` | 架构与设计文档 | 了解整体架构 |
| `STAGE*_IMPLEMENTATION_PLAN.md` | 阶段实施计划 | 了解 roadmap 和各阶段安排 |

### 1.2 执行流程

```
接收任务 → 检索相关文档 → 建立上下文 → 提取关键信息 → 确定执行策略
    → 执行变更 → 自我验证 → 修复问题 → 最终确认 → 更新追踪
```

### 1.3 记忆维护

- **执行前**：加载相关文档到工作记忆
- **执行中**：实时更新文档引用，记录变更原因
- **执行后**：更新 CLAUDE.md（项目记忆）和 ROADMAP.md（进度看板）

---

## 2. 测试规范

### 2.1 测试清理优先级

| 优先级 | 类型 | 处理方式 |
|--------|------|----------|
| 🔴 P0 | 死测试（无对应实现） | 直接删除测试文件 |
| 🔴 P0 | xfailed 可修复 | 修复实现或移除 xfail |
| 🟡 P1 | xpassed 假阳性 | 移除 xfail 标记，确认稳定性 |
| 🟡 P1 | 环境依赖失败的测试 | 添加 mock 或增大容差 |
| 🟢 P2 | 低优先级 xfailed | 保留，下版本处理 |

### 2.2 测试执行规范

```bash
# 全量测试（默认）
pytest

# 仅运行非 xfail 测试
pytest --runxfail

# 带覆盖率报告
pytest --cov=tengod --cov-report=term

# 快速冒烟测试
pytest -x --timeout=60
```

### 2.3 验收标准

| 指标 | 目标 |
|------|------|
| passed | 持续增长 |
| xfailed | 0（P0 目标） |
| xpassed | 0（P1 目标） |
| failed | 0 |
| 测试覆盖率 | ≥ 70% |

---

## 3. 代码规范

### 3.1 文件组织

```
tengod/<模块名>/
├── __init__.py
├── <模块功能>.py
└── README.md       # 模块说明
```

### 3.2 命名约定

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块目录 | 中文名_功能名 | `正官_法度调度/` |
| 模块文件 | 英文小写+下划线 | `api_router.py` |
| 测试文件 | `test_<模块名>.py` | `test_api_router.py` |
| 类名 | PascalCase | `TaskScheduler` |
| 函数名 | snake_case | `schedule_task()` |

### 3.3 版本标签

所有文件头必须包含版本信息：

```python
"""
@module <模块名>
@version <当前版本号>
@description <模块功能描述>
"""
```

---

## 4. 文档维护规范

### 4.1 文档体系

| 文档 | 负责对象 | 更新时机 |
|------|----------|----------|
| `CLAUDE.md` | 所有 AI | 每次任务完成时 |
| `AGENTS.md` | AI 智能体 | 执行规范变更时 |
| `ROADMAP.md` | 所有 AI | 里程碑达成时 |
| `建设模块/*.md` | 开发团队 | 版本迭代计划时 |

### 4.2 文档引用追踪

```
变更 → 更新 CLAUDE.md（项目记忆）
     → 更新 ROADMAP.md（进度看板）
     → 更新关联文档引用
     → 验证文档一致性
```

### 4.3 质量检查清单

- [ ] 执行前检索了相关文档
- [ ] 确认了产物类型和数量
- [ ] 遵循了标准执行流程
- [ ] 运行了全量测试
- [ ] 修复了所有不符合项
- [ ] 更新了项目记忆（CLAUDE.md）
- [ ] 更新了进度看板（ROADMAP.md）

---

## 5. 环境与依赖

### 5.1 依赖安装

```bash
# 核心依赖
pip install -r requirements.txt

# 测试依赖
pip install pytest pytest-asyncio pytest-cov pytest-timeout

# 可选依赖
pip install scikit-learn fastapi uvicorn httpx2
```

### 5.2 已知环境问题

| 问题 | 影响 | 解决方案 |
|------|------|----------|
| `pytest.mark.asyncio` 未注册 | async 测试警告 | 安装 `pytest-asyncio` |
| `sklearn` 未安装 | 部分测试跳过 | `pip install scikit-learn` |
| `fastapi` 未安装 | API 测试跳过 | `pip install fastapi uvicorn` |
| 异步测试支持 | async 测试失败 | `pip install pytest-asyncio` |

---

## 6. 不应做的事

- 不要跳过文档检索直接开始执行
- 不要忽略测试失败，即使只是 xfailed
- 不要在未运行测试前声称"修复完成"
- 不要创建无对应实现的测试文件
- 不要修改 conftest.py 中的全局 xfail 而不验证
- 不要在未确认稳定性时删除 xfail 标记
- 不要在一个任务中同时处理多个无关模块
- 不要忘记更新 CLAUDE.md 和 ROADMAP.md

---

## 7. 快速参考

### 7.1 常用命令

```bash
pytest                           # 全量测试
pytest tests/test_xxx.py -v     # 单文件测试
pytest -x --tb=long             # 首个失败停止，详细回溯
pytest --cov=tengod --cov-report=term  # 带覆盖率
pytest --runxfail               # 运行所有测试（包括标记为 xfail 的）
```

### 7.2 当前项目状态

| 项目 | 值 |
|------|-----|
| 当前版本 | v5.1.0「端到端验证」 |
| 测试总数 | ~10500 |
| 十神模块 | 10/12 已部署 |
| 核心模块 | 八字/紫微/六爻/奇门/风水/七政 |
| 门禁系统 | 认知六维门禁 + 知识图谱桥接 |

---

*最后更新: 2026-08-02*
*版本: v1.0.0*