# API 文档规范 Spec

## Why

Claw 项目包含 7 个 API 服务文件，总计 50+ 个路由端点（FastAPI + Flask），但缺乏一份**统一的、完整的 API 文档**。当前只有在 `api_server.py` 中 FastAPI 自动生成的 Swagger 文档，缺乏对请求参数（数据类型、是否必填、默认值）、响应结构（字段说明、数据类型）、错误码、认证方式的系统性描述。开发者无法快速了解全貌，外部集成者难以正确调用。

## What Changes

- 分析全部 7 个 API 文件中的所有端点
- 按照 DeepSeek API V4 规范风格生成统一的 API 文档
- 文档包含：接口描述、请求方法/路径、请求参数（名称/类型/必填/默认值/说明）、响应结构（字段/类型/说明）、成功/失败响应示例、错误码及说明、认证方式、注意事项

## Impact

- Affected specs: 无
- Affected code: 无代码修改，新增文档文件
- New deliverables:
  - `.trae/specs/api-documentation/Claw系统API文档.md` — 完整 API 文档

## ADDED Requirements

### Requirement: API 文档完整性
文档 SHALL 覆盖以下所有 API 文件中的端点：

- api_server.py (15+ 端点) — 主 API
- src/memory/immortal/api.py (15+ 端点) — 记忆永生 API
- llm_synthesis_api.py (10 端点) — LLM 合成 API
- spirit-form-api/gateway-service/main.py (6 端点) — 网关
- spirit-form-api/dialogue-service/main.py (9 端点) — 对话树
- spirit-form-api/evaluation-service/main.py (15+ 端点) — 评估引擎
- spirit-form-api/visualization-service/main.py (7 端点) — 可视化
- self_evolution_loop.py (5 端点) — 自进化回路
- 中华文明数字永生体_API.py (6 端点) — 中华文明数字永生体(Flask)

### Requirement: 文档格式规范
文档 SHALL 按 DeepSeek API V4 规范风格组织，每条接口包含：

- 接口功能描述
- HTTP 方法 + 请求路径
- 请求参数表（参数名、类型、位置、是否必填、默认值、说明）
- 响应结构表（字段名、类型、说明）
- 成功响应示例（JSON）
- 失败响应示例（JSON）
- 错误码说明
- 调用注意事项

### Requirement: 文档章节结构
文档 SHALL 包含以下章节：

1. 概述（API 基础信息、协议说明、通用约定）
2. 认证方式（API Key / Token 认证说明）
3. 通用错误码
4. 按服务分组的 API 接口文档
5. 附录（状态码速查、最佳实践）
