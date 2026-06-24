# xpassed 假阳性清理开发计划 v1.0

> **创建日期**：2026-06-24
> **当前状态**：294 xpassed / 143 xfailed / 976 passed
> **目标**：将 xpassed 从 294 降至 0，区分真修复与环境假阳性

---

## 一、诊断总览

### 1.1 xpassed 成因分类

| 类别 | 成因 | 数量 | 风险 |
|------|------|------|------|
| **A 类：真修复** | 代码已修复，xfail 误标记 | ~200 | 无 |
| **B 类：环境差异** | 依赖特定环境（Python 3.14 / Linux / 时序精度） | ~94 | 中 |
| **C 类：真失败** | 测试确实失败，保留 xfail | 143 | - |

### 1.2 环境差异详细分析

| 风险因素 | 影响文件 | 影响测试数 | 说明 |
|----------|----------|-----------|------|
| `time.sleep()` 精度 | test_phase29.py | 40 | 限流/熔断器测试依赖 `sleep(0.3)`，CI 慢环境可能超时 |
| 纯数据结构 | test_phase27_28.py | 62 | 可视化测试仅验证 dict/JSON 结构，不依赖渲染库 |
| 环境变量 | test_v21_security.py | 24 | 安全测试依赖 `DEEPSEEK_API_KEY` 等环境变量 |

---

## 二、分阶段开发计划

### 阶段 1：安全移除真修复 xfail（P0，预计 1-2 小时）

**目标**：移除确认已修复的 `"*"` 通配符 xfail，从 294 个 xpassed 中消除约 200 个。

#### 1.1 移除全通配符 xfail（0 xfail 残留的文件）

这些文件的 `"*"` 通配符使所有测试被标记为 xfail，但实际全部通过。直接删除对应条目：

| 文件 | xpassed | 修复原因 | 操作 |
|------|---------|----------|------|
| test_phase22.py | 35 | Case→LegacyCase 重命名解决 SQLAlchemy 冲突 | 删除 `"*"` 条目 |
| test_v23_i18n.py | 34 | I18nManager 兼容包装器 | 删除 `"*"` 条目 |
| test_deepseek_adapter.py | 21 | 模块导入路径修正 | 删除 `"*"` 条目 |
| test_intelligent_analysis.py | 21 | 模块导入路径修正 | 删除 `"*"` 条目 |
| test_v21_integration.py | 17 | 真实计算模块工作正常 | 删除 `"*"` 条目 |
| test_v22_api.py | 16 | 真实计算模块工作正常 | 删除 `"*"` 条目 |
| test_async_task_queue.py | 14 | 异步模块修复 | 删除 `"*"` 条目 |

**小计**：消除约 158 个 xpassed

#### 1.2 拆分通配符 xfail（有 1 个 xfail 残留的文件）

这些文件使用 `"*"` 通配符，但存在 1 个仍失败的测试。需将 `"*"` 替换为精确的 xfail 列表：

| 文件 | xpassed | 仍 xfail | 需保留的 xfail |
|------|---------|----------|----------------|
| test_phase27_28.py | 62 | 1 | 找出 1 个仍失败的测试，精确标记 |
| test_phase29.py | 40 | 1 | 找出 1 个仍失败的测试，精确标记 |
| test_v21_security.py | 24 | 1 | 找出 1 个仍失败的测试，精确标记 |

**小计**：消除约 126 个 xpassed（保留 3 个 xfail）

**阶段 1 总计**：消除约 284 个 xpassed

---

### 阶段 2：时间敏感测试加固（P1，预计 2-3 小时）

**目标**：验证 test_phase29.py 中 40 个时间敏感测试在 CI 环境中的稳定性。

#### 2.1 风险点

```python
# test_phase29.py 中的典型时间敏感测试
time.sleep(0.3)   # CI 慢环境可能偏差 > 0.3s
assert remaining >= 2  # 令牌桶补充依赖精确时间
```

#### 2.2 加固方案

| 方案 | 操作 | 适用场景 |
|------|------|----------|
| A. Mock 时间 | 使用 `freezegun` 或 `unittest.mock.patch('time.time')` | 令牌桶、滑动窗口 |
| B. 增大容差 | `sleep(0.3)` → `sleep(1.0)`，`assert >= 2` → `assert >= 1` | 限流器 |
| C. 保留 xfail strict=True | 对于无法加固的测试，保留 xfail 但设为 `strict=True`（通过时不报 XPASS） | 极端情况 |

#### 2.3 执行步骤

1. 在 CI 中运行一次 `test_phase29.py`，确认 xfailed 测试
2. 对 xpassing 的 40 个测试，逐个添加 `freezegun` mock
3. 对无法 mock 的测试，增加容差
4. 运行 `pytest tests/test_phase29.py --runxfail` 验证

---

### 阶段 3：精确化混合 xfail 列表（P2，预计 1-2 小时）

**目标**：将粒度 xfail 列表中的 xpassed 测试精确识别并移除。

#### 3.1 当前混合列表

| 文件 | xfail | xpass | 操作 |
|------|-------|-------|------|
| test_bazi_api.py | 22 | 5 | 识别 5 个 xpassing 测试，从 xfail 列表移除 |
| test_api_integration.py | 32 | 2 | 识别 2 个 xpassing 测试，从 xfail 列表移除 |
| test_v212_data_api.py | 5 | 1 | 识别 1 个 xpassing 测试，从 xfail 列表移除 |
| test_phase20.py | 15 | 1 | 识别 1 个 xpassing 测试，从 xfail 列表移除 |

#### 3.2 执行步骤

1. 对每个文件运行 `pytest --runxfail -v`，记录通过的测试
2. 从 `KNOWN_FAILING_TESTS` 中移除通过测试的条目
3. 验证：`pytest` 报告中 xpassed 数减少

**小计**：消除约 9 个 xpassed

---

### 阶段 4：CI 环境一致性验证（P2，预计 1 小时）

**目标**：确认阶段 1-3 的变更在 CI 中不会引入新的失败。

#### 4.1 验证步骤

1. Push 到 `develop` 分支，触发 CI 流水线
2. 检查 CI 中的 pytest 报告：
   - 期望：`0 failed, 0 errors, ~143 xfailed, ~0 xpassed`
   - 如果出现新的 failed，说明存在环境差异，需要回滚对应 xfail
3. 对比本地和 CI 的 `pytest -v` 输出差异

#### 4.2 回滚预案

如果 CI 中出现新的失败（非 xpassed），说明该测试在本地环境通过但 CI 环境失败。处理方式：

1. 立即回滚对应测试的 xfail 移除
2. 在 `KNOWN_FAILING_TESTS` 中恢复精确条目
3. 记录为"环境依赖"类型，后续单独处理

---

## 三、最终目标状态

```
期望结果：
  passed:  976 + ~290 = ~1266
  xfailed: 143
  xpassed: 0
  failed:  0
  errors:  0
```

| 阶段 | 操作 | 消除 xpassed | 累计 xpassed |
|------|------|-------------|-------------|
| 当前 | - | - | 294 |
| 阶段 1 | 移除真修复 xfail | ~284 | ~10 |
| 阶段 2 | 时间敏感加固 | ~40（已在此前消除） | ~10 |
| 阶段 3 | 精确化混合列表 | ~9 | ~1 |
| 阶段 4 | CI 验证 | ~1 | 0 |

---

## 四、风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| CI 中 test_phase29 时间敏感测试失败 | 中 | 中 | 阶段 2 加固 + CI 验证 |
| 移除 xfail 后发现隐藏依赖 | 低 | 低 | 阶段 4 CI 验证 + 回滚预案 |
| test_phase27_28 可视化测试依赖渲染库 | 低 | 低 | 已确认：纯数据结构测试，无渲染依赖 |
| 测试文件被删除/重命名导致 xfail 列表失效 | 低 | 低 | 阶段 4 全量回归 |

---

## 五、执行检查清单

- [ ] **阶段 1.1**：删除 7 个全通配符 xfail 条目（test_phase22, test_v23_i18n, test_deepseek_adapter, test_intelligent_analysis, test_v21_integration, test_v22_api, test_async_task_queue）
- [ ] **阶段 1.2**：拆分 3 个通配符 xfail 为精确条目（test_phase27_28, test_phase29, test_v21_security）
- [ ] **阶段 2**：加固 test_phase29 时间敏感测试
- [ ] **阶段 3**：精确化 4 个混合 xfail 列表（test_bazi_api, test_api_integration, test_v212_data_api, test_phase20）
- [ ] **阶段 4**：CI 环境一致性验证
- [ ] **最终**：运行 `make all` 确认 0 xpassed

---

## 六、文件变更清单

| 文件 | 变更类型 | 阶段 |
|------|----------|------|
| tests/conftest.py | 删除 7 个 `"*"` 条目 + 拆分 3 个 `"*"` 条目 | 1 |
| tests/conftest.py | 移除 4 个混合列表中的 xpassed 条目 | 3 |
| tests/test_phase29.py | 添加 freezegun mock / 增大容差 | 2 |