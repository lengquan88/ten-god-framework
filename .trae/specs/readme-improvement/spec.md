# README 完善 Spec

## Why

当前 README.md 虽有完整框架，但存在三个薄弱环节：
1. **安装步骤过于简略** — 缺少虚拟环境、.env 配置、可编辑安装、GPU 可选依赖等关键指引
2. **使用示例不够丰富** — 缺少 API 服务、记忆系统、评估系统等核心模块的实用示例
3. **贡献指南只有一句** — 虽然已有完整的 CONTRIBUTING.md（423行），但 README 没有引用，导致贡献者难以找到详细指南

## What Changes

- 增强 README.md 的**安装步骤**部分：添加虚拟环境、.env 配置、可编辑安装、GPU 支持等
- 扩充 README.md 的**使用示例**部分：添加 API 服务启动、记忆系统使用、拓扑评估器等更多场景
- 完善 README.md 的**贡献指南**部分：引用现有的 CONTRIBUTING.md，补充 Issue/PR 提交要点
- 保持 README.md 原有结构和风格（中文、表格、emoji），仅增强内容

## Impact

- Affected specs: 无
- Affected code: `README.md` — 仅修改此文件
- No breaking changes

## ADDED Requirements

### Requirement: 增强安装步骤
README SHALL 提供完整的安装指引，包含以下子步骤：

#### Scenario: 虚拟环境创建
- **WHEN** 新用户按照安装步骤操作
- **THEN** 安装步骤包含 Python 虚拟环境创建和激活命令（Windows + Linux/macOS）

#### Scenario: 环境变量配置
- **WHEN** 用户安装依赖后
- **THEN** 说明如何从 .env.example 复制为 .env 并修改关键配置（DEEPSEEK_API_KEY 等）

#### Scenario: 可选依赖安装
- **WHEN** 用户需要特定功能
- **THEN** 说明可选的 GPU / sentence-transformers / FAISS 等依赖安装方式

### Requirement: 扩充使用示例
README SHALL 包含 4 个以上不同模块的实用使用示例：

#### Scenario: API 服务启动
- **WHEN** 用户想启动 REST/WebSocket 服务
- **THEN** 示例展示如何启动 api_server.py 和访问 Swagger 文档

#### Scenario: 记忆系统使用
- **WHEN** 用户想使用记忆胶囊
- **THEN** 示例展示 MemoryCapsule 的创建、存储和检索

#### Scenario: LLM 合成调用
- **WHEN** 用户想调用 LLM 合成 API
- **THEN** 示例展示使用 DeepSeek 客户端进行对话

#### Scenario: 拓扑语义评估
- **WHEN** 用户想进行语义评估
- **THEN** 示例展示 advanced_spirit_evaluator 的基本用法

### Requirement: 完善贡献指南
README SHALL 提供清晰的贡献指引：

#### Scenario: 贡献指南可见
- **WHEN** 用户想参与贡献
- **THEN** README 贡献节包含指向 CONTRIBUTING.md 的链接和简要要点

#### Scenario: Issue 模板指引
- **WHEN** 用户想提交 Issue
- **THEN** 说明 Bug 报告和功能请求的提交流程
