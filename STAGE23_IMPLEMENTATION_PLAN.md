# 阶段二十三：插件市场与开放平台 — 技术实现方案

> 目标：打造第三方开发者生态，构建可插拔平台（插件注册 + 沙箱隔离 + SDK + 限流分级）
> 依赖：现有 `auth.py`（用户/角色/权限）、`api_server.py`（REST 端点框架）
> 预计工作量：3-4 人/周

---

## 23.0 架构总览

```
                    ┌──────────────────  用户 / 小程序 / Web UI
                    │                        │
                    │                        ▼
                    │              ┌────────────────────┐
                    │              │   插件市场 Web UI   │  (浏览 / 搜索 / 安装 / 评分)
                    │              └────────────────────┘
                    │                        │
          FastAPI 端点层 ───────────────────┘
                    │
    ┌───────────────┼──────────────────────────────┐
    ▼               ▼                              ▼
  插件注册表      插件运行时                      API 限流分级
(plugins_db.py) (plugin_runtime.py 沙箱)           (auth.py rate_limit 扩展)
    │                │
    ▼                ▼
PostgreSQL        subprocess 隔离执行
  plugin_* 表        ├ 沙箱：独立进程，文件只读
                      ├ 超时控制：单次调用 ≤ 5s
                      └ 资源限制：内存 ≤ 128MB
```

---

## 23.1 插件注册中心（2天）

### 新建 `tengod/plugins_db.py` — 5 张表 + 管理类

```
表清单:
  1. plugins          — 插件元数据（name/version/category/author/permissions/endpoints/hooks/download_count/install_count/rating_avg）
  2. plugin_installs   — 用户安装记录（user_id + plugin_id，唯一约束）
  3. plugin_reviews    — 用户评分与评论（1-5 星 + 文字评论）
  4. plugin_endpoints  — 插件端点声明（用于路由转发，可合并入 plugins.endpoints_json）
  5. plugin_invocation_logs — 调用审计日志（plugin_id/user_id/endpoint/status/duration_ms/error_msg）

索引:
  idx_plugin_category (category)
  idx_plugin_rating   (rating_avg)
  idx_plugin_active   (is_active)
  idx_install_user_plugin (user_id, plugin_id) UNIQUE

管理类 PluginRegistry 方法:
  register(**kwargs) → Plugin        — 注册新插件
  list(category/keyword/is_active)   — 浏览/搜索
  get(plugin_id) → Plugin
  get_by_name(name) → Plugin
  install(plugin_id, user_id) → Dict  — 一键安装 + install_count++
  submit_review(plugin_id, user_id, rating, comment)  — 评分评论 + 重算平均
  list_reviews(plugin_id) → List[Dict]
  toggle_approved(plugin_id, is_approved) — 管理员审核
  log_invocation(plugin_id, user_id, endpoint, status, duration_ms, error_msg)
  get_stats() → Dict                  — 插件市场统计
```

---

## 23.2 插件沙箱运行时（2天）

### 新建 `tengod/plugin_runtime.py`

```
安全策略:
  1. 独立 subprocess 执行（避免主进程污染）
  2. 文件访问仅限插件自身目录 + 只读
  3. 网络访问默认禁止（白名单插件除外）
  4. 超时控制：5s
  5. 内存限制：128MB (resource.setrlimit RLIMIT_AS)
  6. import 白名单：json/math/datetime/time/random/hashlib/collections/itertools/functools/typing/copy
  7. 危险 import 禁止：subprocess/os/sys/eval/exec

核心类:
  PluginSandbox(plugin_name, plugin_source, allowed_permissions)
    .run(handler_path, input_data, context) → Dict
       - 构建沙箱执行脚本（嵌入 import 白名单）
       - subprocess.run(timeout=5s, capture_output=True)
       - 返回 {status: "success|error|timeout", result|error, duration_ms}
    .trigger_hook(hook_name, payload)

  PluginRouter(registry)
    .dispatch(plugin_name, endpoint, payload, user_id) → Dict
       - 验证插件存在/激活/审核通过
       - 验证用户已安装
       - 查找 endpoint handler
       - 通过 sandbox 执行
       - 写入审计日志
```

---

## 23.3 插件 SDK 与模板（1.5天）

### 新建目录 `tengod/plugins/sdk/`

```
sdk/__init__.py         — 导出 register_plugin, permission, Manifest
sdk/permission.py       — Permission 类（BAZI_READ, KNOWLEDGE_SEARCH, CASE_READ...）
sdk/manifest.py         — Manifest dataclass + generate_manifest()
sdk/testing.py          — PluginTestRunner（本地开发期调试，无需沙箱）

示例插件: tengod/plugins/examples/daily_fortune/
  __init__.py           — HANDLERS + HOOKS 声明 + handle_daily() 函数
  manifest.json         — 自动生成的 manifest
```

---

## 23.4 API 限流分级（0.5天）

### 修改 `auth.py` — 扩展 ROLE_PERMISSIONS

```
新增角色:
  pro (专业版):       permissions = [bazi:*, knowledge:*, ai:*, case:*, plugin:*]
                      quota_daily = 10000, rate_limit = 100/分钟
  enterprise (企业版): permissions = [*]
                      quota_daily = 99999, rate_limit = unlimited

原有角色:
  admin (管理员):    保持不变
  user (普通用户):   quota_daily = 100, rate_limit = 30/分钟
  guest (游客):      quota_daily = 10, rate_limit = 5/分钟

新增函数:
  rate_limit_check(user_id, role, endpoint) → bool
    - admin/enterprise: 不限制
    - 其他: 通过 CacheManager.rate_limit() 做滑动窗口限流（日配额 + 分钟配额）
```

---

## 23.5 API 端点（1天）

### 在 `api_server.py` 新增

```
┌─ 浏览与搜索
│  GET  /api/plugins/marketplace?category=&keyword=&limit=50&offset=0
│  GET  /api/plugins/{plugin_id}                  — 插件详情
│  GET  /api/plugins/{plugin_id}/reviews?limit=20 — 评论列表
│
├─ 安装与调用（需要认证 + 已安装）
│  POST /api/plugins/{plugin_id}/install          — 一键安装
│  POST /api/plugins/{plugin_name}/invoke/{endpoint} — 调用插件端点
│  GET  /api/plugins/my/installed                 — 我的已安装插件
│
├─ 评分与评论（需要认证）
│  POST /api/plugins/{plugin_id}/review           — {rating:1-5, comment:...}
│
├─ 管理端点（admin only）
│  POST /api/plugins/register                    — 注册新插件
│  POST /api/plugins/{plugin_id}/approve          — 审核开关
│  POST /api/plugins/{plugin_id}/deactivate       — 下架
│  GET  /api/plugins/stats/summary               — 插件市场统计
│  GET  /api/plugins/{plugin_id}/logs?limit=100   — 调用日志
```

---

## 23.6 文件结构

```
新增:
  tengod/plugins_db.py              # 5 张表 + PluginRegistry
  tengod/plugin_runtime.py          # PluginSandbox + PluginRouter
  tengod/plugins/sdk/__init__.py
  tengod/plugins/sdk/permission.py
  tengod/plugins/sdk/manifest.py
  tengod/plugins/sdk/testing.py
  tengod/plugins/examples/daily_fortune/__init__.py

修改:
  auth.py                           # ROLE_PERMISSIONS 扩展 pro/enterprise + rate_limit_check
  api_server.py                     # 新增 12+ 个插件端点

测试:
  tests/test_plugins.py             # 注册表/安装/评论/沙箱/路由
```

---

## 23.7 实施顺序

```
第1-2天: plugins_db.py 模型 + 注册表 API
第3天:   plugin_runtime.py 沙箱 + 路由
第4天:   SDK + 示例插件 + 限流分级
第5天:   API 端点全部集成 + 测试
```
