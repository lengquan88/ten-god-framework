# 项目加固综合规格 Spec

## Why

Claw 项目经过多轮迭代后，存在三个工程化短板：
1. **测试缺失** — 现有测试多为独立脚本（`test_*.py`），散落在根目录，未使用 pytest 组织，缺乏统一的测试目录和 CI 集成
2. **自动化缺失** — 项目没有 Makefile 或自动化脚本，开发/测试/部署流程全靠手动执行
3. **代码臃肿** — 多文件超过 2000 行（`advanced_spirit_evaluator.py` 2468 行、`claw_seven_layer_core.py` 〜2000 行、`topo_semantic/operators.py` 〜2000 行），需要系统性重构

## What Changes

### 测试体系
- 创建 `tests/` 统一测试目录，按模块组织（`test_core/`、`test_api/`、`test_topo/`...）
- 为关键模块编写 pytest 单元测试和集成测试（api_server、advanced_spirit_evaluator、topo_semantic 核心算子、memory_immortal、deepseek_client）
- 创建 `tests/conftest.py` 配置 pytest 共享 fixture
- 不修改任何生产代码

### 自动化脚本
- 创建 `Makefile` 统一开发/测试/代码质量/部署命令
- 包含：`make install`、`make test`、`make lint`、`make format`、`make clean`、`make run-api` 等目标

### 代码重构
- 对 `advanced_spirit_evaluator.py`（2468行）进行模块拆分
- 对 `claw_seven_layer_core.py`（〜2000行）进行职责分离
- 确保重构前后行为完全一致，不修改外部接口

## Impact

- Affected specs: 无
- Affected code:
  - 新增：`tests/` 目录 + `tests/conftest.py` + 多个测试文件
  - 新增：`Makefile`
  - 修改：`advanced_spirit_evaluator.py`（拆分为多个子模块）
  - 修改：`claw_seven_layer_core.py`（职责分离）
- No breaking changes（保持接口兼容）

## ADDED Requirements

### Requirement: 测试体系
The system SHALL have a standardized pytest test suite.

#### Scenario: 测试可运行
- **WHEN** 执行 `make test` 或 `pytest tests/`
- **THEN** 所有测试通过，覆盖率报告生成

#### Scenario: 测试覆盖关键模块
- **WHEN** 查看测试文件
- **THEN** 覆盖 api_server、advanced_spirit_evaluator、topo_semantic 核心算子、memory_immortal、deepseek_client

#### Scenario: 测试共享配置
- **WHEN** pytest 运行
- **THEN** conftest.py 提供 mock API key 等 fixture

### Requirement: 自动化脚本
The system SHALL provide a Makefile with common development commands.

#### Scenario: 常用命令
- **WHEN** 开发者执行 make install/test/lint/format/clean
- **THEN** 对应的自动化工序执行

### Requirement: 代码重构
The system SHALL refactor bloated modules without changing external behavior.

#### Scenario: advanced_spirit_evaluator 拆分
- **WHEN** 重构完成后
- **THEN** 原模块拆分为 evaluator_core.py、intention_matcher.py、semantic_scorer.py 等子模块，保持原有导入路径兼容

#### Scenario: claw_seven_layer_core 职责分离
- **WHEN** 重构完成后
- **THEN** 七层职责分离到独立类/模块，保持原有 API 兼容

## MODIFIED Requirements

### Requirement: 现有 test_*.py 文件
**Status**: 保持不变
**Note**: 现有的根目录测试脚本保留，新增的 tests/ 目录使用 pytest 框架编写。

## REMOVED Requirements
无
