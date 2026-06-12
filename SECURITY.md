# Claw 安全配置指南

本指南介绍如何配置和使用 Claw 的安全功能，确保您的部署环境安全可靠。

## 目录
- [安全配置概述](#安全配置概述)
- [快速配置](#快速配置)
- [详细配置](#详细配置)
- [漏洞修复历史](#漏洞修复历史)
- [最佳实践](#最佳实践)

---

## 安全配置概述

Claw 包含以下安全功能：

| 功能 | 说明 | 严重程度 |
|------|------|----------|
| API 认证 | 保护所有 REST API 端点 | 🔴 高 |
| CORS 安全配置 | 防止跨站请求伪造 | 🔴 高 |
| 云同步强加密 | 使用 Fernet/AES 加密敏感数据 | 🟡 中 |
| MCP 服务器安全 | 保护 HTTP 调试模式 | 🟡 中 |
| 微信白名单 | 控制机器人访问权限 | 🟢 低 |

---

## 快速配置

### 1. 生成强密钥

在部署前，请生成所有必需的强密钥：

```python
# 在 Python 中运行
import secrets

print("JWT_SECRET_KEY=" + secrets.token_hex(32))
print("API_SECRET_KEY=" + secrets.token_hex(32))
print("MCP_API_KEY=" + secrets.token_hex(32))
```

或在 Linux/Mac 上使用：

```bash
openssl rand -hex 32
```

### 2. 配置 .env 文件

复制 `.env.example` 为 `.env` 并填入生成的密钥：

```bash
# 基础配置
API_SECRET_KEY=<你的API密钥>
JWT_SECRET_KEY=<你的JWT密钥>
MCP_API_KEY=<你的MCP密钥>

# 安全开关
API_REQUIRE_AUTH=true

# 安全来源（仅允许您的域名
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## 详细配置

### API 认证配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `API_SECRET_KEY` | API 服务密钥（必填 | - |
| `API_REQUIRE_AUTH` | 是否启用认证 | true |
| `CORS_ALLOWED_ORIGINS` | 允许的 CORS 来源 | http://localhost,http://127.0.0.1 |

**使用方法：**

所有 API 请求需要在请求头中包含：

```http
Authorization: Bearer <API_SECRET_KEY>
```

例如使用 curl：

```bash
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <你的API密钥>" \
  -d '{"input": "你好"}'
```

### MCP 服务器配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `MCP_API_KEY` | MCP 服务密钥 | - |
| `MCP_BIND_HOST` | 绑定地址 | 127.0.0.1 |
| `MCP_CORS_ORIGIN` | CORS 来源 | http://localhost,http://127.0.0.1 |

**使用方法：**

```bash
# 启动 MCP 服务器
MCP_API_KEY=<你的MCP密钥> python mcp_server.py --http
```

### 云同步加密

云同步使用 Fernet (AES-128-CBC) 加密，会自动从您配置的 `CLOUD_SYNC_PASSWORD` 生成安全密钥。无需额外配置。

### 微信机器人白名单

在微信机器人配置中设置白名单：

```json
{
  "user_whitelist": ["User1", "User2"],
  "group_whitelist": ["Group1"]
}
```

---

## 漏洞修复历史

### 2026-05-19 安全补丁

| 漏洞 ID | 严重程度 | 说明 | 修复状态 |
|---------|----------|------|----------|
| HIGH-1 | 🔴 高 | API 服务缺少认证 | ✅ 已修复 |
| HIGH-2 | 🔴 高 | CORS 允许任意来源 | ✅ 已修复 |
| MEDIUM-1 | 🟡 中 | 云同步使用弱加密 | ✅ 已修复 |
| MEDIUM-2 | 🟡 中 | MCP 调试模式安全风险 | ✅ 已修复 |
| MEDIUM-3 | 🟡 中 | 密钥配置说明不足 | ✅ 已修复 |

---

## 最佳实践

### 生产环境检查清单

- [ ] 所有密钥均使用强随机值
- [ ] `.env` 文件已添加到 `.gitignore`
- [ ] `API_REQUIRE_AUTH=true`
- [ ] `CORS_ALLOWED_ORIGINS` 仅包含您的域名
- [ ] 微信白名单已配置
- [ ] 使用 HTTPS 部署
- [ ] 日志中不包含敏感信息
- [ ] 定期更新依赖

### 开发环境配置

在本地开发时，可以临时关闭认证：

```bash
# .env
API_REQUIRE_AUTH=false
```

⚠️ **警告**：不要在生产环境中使用此配置！

### 密钥安全

- **不要**将密钥提交到版本控制系统
- **不要**在客户端代码中硬编码密钥
- **定期**轮换密钥（建议每 3-6 个月）
- **使用**环境变量或密钥管理服务

---

## 联系与报告

如发现安全问题，请通过以下方式联系：

- 提交 Issue（建议脱敏处理敏感信息）
- 或通过项目沟通渠道联系维护者

