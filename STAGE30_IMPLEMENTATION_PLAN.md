# 阶段三十：文档与社区 — 技术实现方案

> 目标：建立开发者生态，降低接入门槛（API 文档站 + SDK 文档 + 开发者门户 + 技术博客）
> 依赖：现有 `api_server.py`（FastAPI 自带 Swagger/Redoc）、SDK（Python/JS/Go）
> 预计工作量：2-3 人/周

---

## 30.0 架构总览

```
┌─ docs.tengod.com (开发者门户) ───────────────────┐
│                                                   │
│  ├── /                                    首页    │
│  ├── /api/                                API 文档 │
│  │   ├── /reference  (基于 OpenAPI 自动生成)      │
│  │   ├── /quickstart (5分钟快速上手指南)          │
│  │   ├── /auth       (认证说明)                  │
│  │   └── /examples   (代码示例集)                │
│  ├── /sdk/                               SDK 文档 │
│  │   ├── /python                           │
│  │   ├── /javascript                       │
│  │   └── /go                              │
│  ├── /changelog/                          更新日志 │
│  ├── /blog/                               技术博客 │
│  └── /community/                          社区入口 │
│                                                   │
│  构建: VitePress 或 MkDocs Material                │
│  静态: HTML + 搜索（本地）                        │
│  CI:  每次部署自动更新 OpenAPI spec              │
└──────────────────────────────────────────────────┘
```

---

## 30.1 API 开发者文档站（1天）

### 方案 A：MkDocs Material（推荐，美观/搜索强大/mermaid 图表）

```yaml
# 项目结构:
docs-tengod/
├── mkdocs.yml                 # 站点配置
├── docs/
│   ├── index.md              # 首页
│   ├── quickstart.md          # 5分钟快速上手
│   ├── api/                  # API 文档
│   │   ├── reference.md       # Swagger/Redoc 嵌入
│   │   ├── authentication.md  # JWT + API Key
│   │   ├── rate-limits.md    # 配额与限流
│   │   ├── error-codes.md    # 错误码表
│   │   └── examples/          # 代码示例
│   │       ├── bazi.md
│   │       ├── cases.md
│   │       ├── ai.md
│   │       ├── webhooks.md
│   │       └── plugins.md
│   ├── sdk/                  # SDK 文档
│   │   ├── python.md
│   │   ├── javascript.md
│   │   └── go.md
│   ├── concepts/              # 命理概念（十神/格局/五行）
│   ├── changelog/             # 更新日志
│   ├── blog/                 # 技术博客
│   └── community.md           # 社区入口
├── scripts/
│   └── generate_openapi.py    # 从 FastAPI 自动导出 openapi.json
└── requirements-docs.txt
```

### mkdocs.yml 配置

```yaml
site_name: 十神架构开发者文档
site_url: https://docs.tengod.com
site_description: 十神架构 · 中华文明数字永生体 API 与 SDK 文档

theme:
  name: material
  language: zh
  palette:
    primary: deep purple
    accent: amber
  features:
    - content.code.copy
    - content.code.annotate
    - navigation.tabs
    - navigation.top
    - search.suggest
    - search.highlight
    - content.tabs.link

nav:
  - 首页: index.md
  - 快速上手: quickstart.md
  - API 文档:
    - 参考: api/reference.md
    - 认证: api/authentication.md
    - 限流: api/rate-limits.md
    - 错误码: api/error-codes.md
    - 八字排盘: api/examples/bazi.md
    - 案例库: api/examples/cases.md
    - AI 解读: api/examples/ai.md
    - Webhook: api/examples/webhooks.md
    - 插件系统: api/examples/plugins.md
  - SDK:
    - Python: sdk/python.md
    - JavaScript: sdk/javascript.md
    - Go: sdk/go.md
  - 命理概念:
    - 十神: concepts/shigan.md
    - 五行: concepts/wuxing.md
    - 格局: concepts/geju.md
    - 大运流年: concepts/dayun.md
  - 更新日志: changelog/index.md
  - 技术博客: blog/index.md
  - 社区: community.md

markdown_extensions:
  - admonition
  - codehilite
  - toc:
      permalink: true
  - pymdownx.highlight
  - pymdownx.superfences
  - pymdownx.tabbed
  - mdx_math

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          selection:
            docstring_style: google
```

### 自动生成 OpenAPI spec

```python
# scripts/generate_openapi.py
import json, sys
sys.path.insert(0, "/app")
from tengod.api_server import app

with open("docs/api/openapi.json", "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, ensure_ascii=False, indent=2)

print("OpenAPI spec 已生成: docs/api/openapi.json")
```

### 在文档中嵌入 Swagger UI

```markdown
<!-- docs/api/reference.md -->
# API 参考

<div id="swagger-ui"></div>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.5/swagger-ui.css">
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.5/swagger-ui-bundle.js"></script>
<script>
SwaggerUI({
    url: "/api/openapi.json",
    dom_id: "#swagger-ui",
    deepLinking: true,
    presets: [SwaggerUI.presets.apis],
    defaultModelsExpandDepth: -1,
    docExpansion: "none"
});
</script>
```

---

## 30.2 官方 SDK 文档（1天）

### Python SDK 文档 (`docs/sdk/python.md`)

````markdown
# Python SDK

## 安装

```bash
pip install tengod-client
```

## 快速开始

```python
from tengod_client import TengodClient

client = TengodClient(
    api_key="your_api_key_here",
    base_url="https://api.tengod.com"  # 默认
)

# 八字排盘
result = client.bazi.calculate(
    year=1990, month=6, day=15, hour=10,
    gender="male"
)
print(result["analysis"]["day_master"])  # 日主

# 案例库
cases = client.cases.list(category="事业", limit=10)
for case in cases:
    print(case["title"])

# AI 解读
interpretation = client.ai.interpret(
    record_id=result["record_id"],
    question="我的事业运势如何？"
)
print(interpretation["text"])

# Webhook 订阅
client.webhooks.create(
    url="https://your-app.com/webhook",
    events=["case.created", "ai.interpretation.completed"],
    secret="your_webhook_secret"
)
```

## 完整 API

### `client.bazi`

| 方法 | 说明 |
|------|------|
| `calculate(year, month, day, hour, gender)` | 完整八字排盘 |
| `calculate_full(...)` | 包含神煞/格局/喜用神/大运 |
| `get_record(record_id)` | 获取已保存的排盘记录 |
| `list_records(user_id, limit, offset)` | 排盘历史列表 |

### `client.cases`

| 方法 | 说明 |
|------|------|
| `list(category, keyword, limit, offset)` | 案例搜索与筛选 |
| `get(case_id)` | 案例详情 |
| `create(record_id, title, category, ...)` | 创建案例 |
| `update(case_id, **fields)` | 更新案例 |
| `delete(case_id)` | 删除案例 |
| `find_similar(case_id, limit)` | 相似案例推荐 |

### `client.ai`

| 方法 | 说明 |
|------|------|
| `interpret(record_id, question)` | AI 自然语言解读 |
| `interpret_stream(record_id, question)` | 流式解读 |

### `client.webhooks`

| 方法 | 说明 |
|------|------|
| `list()` | 订阅列表 |
| `create(url, events, secret)` | 创建订阅 |
| `delete(webhook_id)` | 删除订阅 |
| `ping(webhook_id)` | 发送测试事件 |

### `client.plugins`

| 方法 | 说明 |
|------|------|
| `list(category, keyword)` | 插件市场浏览 |
| `install(plugin_id)` | 安装插件 |
| `invoke(plugin_name, endpoint, payload)` | 调用插件 |

## 错误处理

```python
from tengod_client import TengodAPIError, TengodAuthError, TengodRateLimitError

try:
    result = client.bazi.calculate(year=1990, month=13, day=15, hour=10, gender="male")
except TengodRateLimitError:
    print("配额超限，请稍后重试")
except TengodAuthError:
    print("API Key 无效")
except TengodAPIError as e:
    print(f"API 错误 [{e.status_code}]: {e.message}")
```

## Changelog

- **v3.0.0** (2026-06-01)
  - 新增 `client.plugins` 模块
  - 新增 `client.cases.find_similar()`
  - 废弃旧的 `client.predict()`，请使用 `client.ai.interpret()`

- **v2.5.0** (2026-03-15)
  - 新增 `client.ai.interpret_stream()` 流式输出
  - 新增 `client.bazi.calculate_full()` 综合排盘
````

### JS/Go SDK 文档（同样的结构，不同语言的代码示例）

---

## 30.3 开发者门户主页（0.5天）

```markdown
# 十神架构 · 开发者门户

<p align="center">
  <img src="/logo.png" width="200" />
</p>

<h2 align="center">中华文明数字永生体 · API & SDK</h2>

---

## 为什么选择十神架构 API?

### 🚀 5分钟完成一次八字排盘
```python
from tengod_client import TengodClient
result = TengodClient("YOUR_KEY").bazi.calculate(1990, 6, 15, 10, "male")
```

### 📚 海量命例库 · 智能推荐
> 超过 10,000+ 公开案例，支持按日主/格局/标签搜索，自动推荐相似案例

### 🤖 AI 智能解读 · 自然语言分析
> 基于传统命理规则 + 大语言模型，生成个性化解读文本

### 🔌 开放插件生态 · Webhook 推送
> 支持第三方开发者创建插件，通过 Webhook 接收实时事件

---

## 快速开始

### 1. 获取 API Key

[注册免费账户](/signup) → [获取 API Key](/dashboard)

### 2. 安装 SDK

=== "Python"

    ```bash
    pip install tengod-client
    ```

=== "JavaScript"

    ```bash
    npm install @tengod/client
    # 或
    yarn add @tengod/client
    ```

=== "Go"

    ```bash
    go get github.com/tengod/client-go
    ```

### 3. 首次调用

=== "Python"

    ```python
    from tengod_client import TengodClient
    client = TengodClient("your_api_key")
    result = client.bazi.calculate(1990, 6, 15, 10, "male")
    print(f"日主: {result['analysis']['day_master']}")
    ```

=== "JavaScript"

    ```javascript
    import { TengodClient } from "@tengod/client";
    const client = new TengodClient("your_api_key");
    const result = await client.bazi.calculate(1990, 6, 15, 10, "male");
    console.log("日主:", result.analysis.day_master);
    ```

=== "Go"

    ```go
    package main
    import "github.com/tengod/client-go"
    func main() {
        client := tengod.NewClient("your_api_key")
        result, _ := client.Bazi.Calculate(1990, 6, 15, 10, "male")
        fmt.Println("日主:", result.Analysis.DayMaster)
    }
    ```

---

## 核心能力概览

| 模块 | 说明 | API 端点 |
|------|------|---------|
| 八字排盘 | 完整四柱/五行/十神/格局/喜用神/大运流年 | `/api/bazi/*` |
| 案例库 | 10,000+ 公开案例库 + 搜索推荐 | `/api/cases/*` |
| AI 解读 | 自然语言命理解读 + 流式输出 | `/api/ai/*` |
| 知识图谱 | 五行/天干/地支/十神关系图 | `/api/knowledge/*` |
| Webhook | 事件订阅与实时推送 | `/api/webhooks/*` |
| 插件系统 | 第三方扩展能力 | `/api/plugins/*` |

---

## 定价

| 层级 | 日配额 | 价格 |
|------|--------|------|
| 免费版 | 100 次/天 | ¥0 |
| 专业版 | 10,000 次/天 | ¥99/月 |
| 企业版 | 无限 | 联系我们 |

[查看完整定价](/pricing)

---

## 社区

- [GitHub Discussions](https://github.com/tengod/tengod/discussions) - 提问/讨论/反馈
- [Issue Tracker](https://github.com/tengod/tengod/issues) - 报告 Bug / 建议功能
- [开发者博客](/blog) - 最新技术分享
```

---

## 30.4 API Key 管理与开发者仪表板（0.5天）

### 页面结构

```
┌─ 开发者仪表板 ─────────────────────────────────────
│
│  [我的 API Key]
│    • sk_live_************************ (点击复制)
│    • [创建新 Key]  [撤销 Key]
│    • 创建时间: 2026-06-01  | 状态: 活跃
│
│  [使用统计]
│    今日调用: 1,234 / 10,000   [████████──────] 12%
│    本月调用: 45,678
│    上月调用: 32,100
│
│  [最近调用]
│    ┌ 时间 ─┬─ 端点 ─────┬─ 状态 ─┬─ 延迟 ─┐
│    │ 10:23 │ /bazi/full │  200   │ 120ms  │
│    │ 10:22 │ /cases/list│  200   │  85ms  │
│    │ 10:22 │ /ai/interpret │ 200 │ 850ms │
│    └────────┴──────────┴───────┴───────┘
│
│  [当前套餐]
│    专业版 Pro (¥99/月)  [升级企业版]
│    配额: 10,000 次/天
│    支持: 邮件 + 文档
│
│  [Webhook 订阅]
│    • https://api.myapp.com/tengod/events [编辑] [测试]
│      事件: case.created, ai.interpretation.completed
│      最近推送: 10 分钟前 (成功)
│
│  [已安装插件]
│    • 每日运势 Daily Fortune v1.2 [启用/禁用]
│    • 姓名学 Name Analysis v0.9 [启用/禁用]
│
└─────────────────────────────────────────────────┘
```

### 后端端点

```
GET    /api/developer/api-keys              我的 API Key 列表
POST   /api/developer/api-keys              创建新 API Key
DELETE /api/developer/api-keys/{key_id}     撤销 API Key

GET    /api/developer/usage?days=30         用量统计
GET    /api/developer/usage/recent?limit=20 最近调用

GET    /api/developer/plan                  当前套餐
POST   /api/developer/plan/upgrade          升级

GET    /api/developer/webhooks              Webhook 订阅
POST   /api/developer/webhooks/test/{id}    发送测试事件
```

---

## 30.5 技术博客与成功案例（1天）

### 博客文章模板库

```
博客文章目录（持续更新）：

┌─ 技术深度 ───────────────────────────────────
│  · 十神架构解读：如何将10,000条规则编码到系统中
│  · 八字排盘算法详解：从公历到天干地支的计算
│  · 我们是如何做到 P95 < 200ms 的性能优化
│  · Postgres + pgvector vs FAISS：向量检索方案对比
│  · 从 SQLite 到 PostgreSQL：迁移经验分享
│
├─ 产品与设计 ─────────────────────────────────
│  · 设计哲学：为什么选择"十神"作为架构分类
│  · 用户体验笔记：如何设计一份让用户信服的命盘
│  · 移动端 PWA 的离线优先策略
│
├─ 成功案例 ───────────────────────────────────
│  · 某命理 APP 集成十神 API：日均调用 50万
│  · 某电商平台用案例库做用户画像匹配
│  · 某心理咨询平台用 AI 解读做辅助分析
│
└─ 开放数据 ───────────────────────────────────
   · 脱敏八字记录集 v1.0 发布（学术研究用）
   · 中国传统命理术语英文对照表 v2.0
```

---

## 30.6 OpenAPI 规范导出（自动化）

### 在 api_server.py 中新增

```python
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi():
    """返回 OpenAPI 3.0 spec（供文档站使用）"""
    return app.openapi()

@app.get("/api/openapi.json", tags=["元信息"])
async def get_openapi_public():
    """公开 OpenAPI spec（可用于 Postman/Insomnia 导入）"""
    spec = app.openapi()
    # 脱敏：移除内部端点（如 /admin/*）
    if "paths" in spec:
        public_paths = {}
        for path, methods in spec["paths"].items():
            if "/admin/" not in path and "/cache/" not in path:
                public_paths[path] = methods
        spec["paths"] = public_paths
    return spec

@app.get("/api/version", tags=["元信息"])
async def get_version():
    """API 版本信息"""
    return {
        "api_version": "3.0.0",
        "openapi_version": "3.0.0",
        "server_time": datetime.now(timezone.utc).isoformat(),
        "environment": os.environ.get("TENGOD_ENV", "production"),
    }
```

---

## 30.7 文件结构汇总

```
新增:
  docs-tengod/                    # 开发者文档站项目（MkDocs）
  ├── mkdocs.yml                  # 站点配置
  ├── docs/
  │   ├── index.md               # 门户首页
  │   ├── quickstart.md          # 快速上手
  │   ├── api/reference.md       # API 参考（嵌入 Swagger UI）
  │   ├── api/authentication.md  # 认证说明
  │   ├── api/rate-limits.md     # 限流与配额
  │   ├── api/error-codes.md     # 错误码表
  │   ├── api/examples/bazi.md   # 八字示例
  │   ├── api/examples/cases.md  # 案例库示例
  │   ├── api/examples/ai.md     # AI 解读示例
  │   ├── api/examples/webhooks.md # Webhook 示例
  │   ├── api/examples/plugins.md # 插件系统
  │   ├── sdk/python.md          # Python SDK 文档
  │   ├── sdk/javascript.md      # JS SDK 文档
  │   ├── sdk/go.md              # Go SDK 文档
  │   ├── concepts/shigan.md     # 十神概念
  │   ├── concepts/wuxing.md     # 五行概念
  │   ├── concepts/geju.md       # 格局概念
  │   ├── concepts/dayun.md      # 大运流年
  │   ├── changelog/index.md     # 更新日志
  │   └── community.md           # 社区入口
  ├── scripts/generate_openapi.py # 自动导出 OpenAPI spec
  └── requirements-docs.txt      # mkdocs-material 等依赖

修改:
  tengod/api_server.py           # 新增 /openapi.json /api/openapi.json /api/version
  web_console/index.html         # 增加开发者门户入口

CI/CD:
  .github/workflows/docs.yml     # 文档自动部署到 GitHub Pages / Vercel
```

---

## 30.8 实施顺序

```
第1天:   MkDocs 文档站基础结构 + API 文档 + 门户首页
第2天:   SDK 文档（Python/JS/Go）+ 概念文档
第3天:   开发者仪表板 UI + API Key 管理 + 自动部署脚本
第4天:   博客文章 + 成功案例 + 更新日志整理
```

---

## 30.9 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| 文档站内容滞后（API 更新后文档不同步） | 中 | 高 | CI 中自动导出 OpenAPI spec，diff 检测失败阻止部署 |
| 外部字体/库加载失败（CND 不可用） | 低 | 低 | 预加载本地字体副本 + 备用 CDN 列表 |
| 中文搜索效果差 | 中 | 低 | MkDocs Material 支持中文分词（jieba），或使用 Algolia |
| API Key 泄露风险（文档示例中硬编码） | 低 | 高 | 代码示例中使用 "your_api_key_here" 占位符，Lint 检查 |
| 文档站 SEO 排名上不去 | 中 | 低 | 使用 sitemap.xml + robots.txt，提交搜索引擎 |
