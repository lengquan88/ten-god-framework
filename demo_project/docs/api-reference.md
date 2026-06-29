# Tengod API Reference

自动生成于 2026-06-29T17:08:21.242325+00:00
共 **178** 个端点，
**4** 个核心模型。

## 端点分组统计

- **八字记录**: 2
- **案例管理**: 2
- **用户管理**: 2
- **高级分析**: 3
- **系统**: 5
- **public**: 152
- **八字排盘**: 7
- **知识查询**: 4
- **数据持久化**: 1

## 端点参考

### `GET, POST /api/admin/records`

- 分组: 八字记录
- 说明: 分页获取或创建八字记录

### `GET, PATCH, DELETE /api/admin/records/{record_id}`

- 分组: 八字记录
- 说明: 单条八字记录的读/更新/删除

### `GET, POST /api/admin/cases`

- 分组: 案例管理
- 说明: 案例列表/创建

### `PATCH, DELETE /api/admin/cases/{case_id}`

- 分组: 案例管理
- 说明: 案例更新/删除

### `GET /api/admin/users`

- 分组: 用户管理
- 说明: 用户列表

### `GET, PATCH /api/admin/users/{user_id}`

- 分组: 用户管理
- 说明: 单个用户信息

### `POST /api/admin/analysis/trajectory`

- 分组: 高级分析
- 说明: 命运轨迹推演

### `POST /api/admin/analysis/batch`

- 分组: 高级分析
- 说明: 批量排盘分析

### `POST /api/admin/analysis/compare`

- 分组: 高级分析
- 说明: 案例对比

### `GET /api/admin/stats`

- 分组: 系统
- 说明: 系统统计信息

### `GET /api/admin/health`

- 分组: 系统
- 说明: 健康检查

### `GET, POST /api/admin/config`

- 分组: 系统
- 说明: 配置读取/写入

### `GET /api/v2/gate/middleware-stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/xiuzhen-progress`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/hundun-foams`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/correction-log`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/huigu-status`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/inner-child-stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/inner-child-archetypes`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/inner-child-memory-pool`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/health/full`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /metrics`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/metrics`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/knowledge/shigan`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/knowledge/dizhi`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/records/{record_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/records/{record_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/records/{record_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/records/search`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/users`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/stats/db`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/chat`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/chat/report`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/ai/interpret/bazi`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/ai/interpret/ziwei`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/ai/interpret/liuyao`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/ai/interpret/name`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/ai/interpret/marriage`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/ai/interpret/oracle`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/{case_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/{case_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/{case_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/search`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/categories/list`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/tags/list`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/stats/summary`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/export/all`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/import/batch`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/{case_id}/similar`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/{case_id}/links`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/{case_id}/links`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/{case_id}/favorite`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/cases/{case_id}/like`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks/events`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks/{sub_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks/{sub_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks/{sub_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks/{sub_id}/test`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks/{sub_id}/deliveries`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks/trigger`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/webhooks/stats/summary`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/plugins`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/plugins/stats/summary`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/prediction/liunian`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/prediction/fengshui`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/prediction/qizheng`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/prediction/comprehensive`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/prediction/comprehensive/interpret`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/prediction/shushu`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/advanced/compare`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/advanced/batch-bazi`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/advanced/trajectory`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/version`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/auth/register`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/auth/login`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/auth/refresh`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/auth/me`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/auth/change-password`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/auth/profile`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/admin/users`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/admin/users/{user_id}/role`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/admin/users/{user_id}/status`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/ziwei/calc`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/liuyao/shake`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/qimen/calc`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/name/analyze`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/marriage/analyze`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/search`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/node/{node_name}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/node/{node_name}/neighbors`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/path`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/subgraph`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/label/{label}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/match`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/graph/export`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/solar-time`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/jieqi`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/wuxing/strength`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/chart/bazi`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/ai/analyze`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/ai/stream`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/i18n/languages`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/i18n/translate`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/mobile/bazi/quick`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/knowledge/list`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/liuyao/cast`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/liuyao/chart`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/ai/stream-interpret`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/tasks`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/tasks/{task_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/tasks/{task_id}/progress`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /health`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /health/ready`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /health/live`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /metrics`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/config`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/agent/orchestrate`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/agent/tools`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/agent/detect-intent`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/evolution/feedback`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/evolution/stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/evolution/confidence`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/evolution/trend`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/evolution/graph`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/evolution/evolve`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/evolution/confidence/adjust`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/conversation/chat`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/conversation/session/{session_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/conversation/session/{session_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/conversation/suggestions/{session_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/cases`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/cases/{case_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/cases`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/cases/{case_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/cases/{case_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/cases/similar`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/cases/export`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/cases/import`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/conversations`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/conversations/{session_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/conversations/{session_id}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/feedback`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/feedback/stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/admin/db-stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/admin/backup`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/admin/restore`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/liunian/analyze`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/liunian/year/{year}`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/gate/verdict`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/realms/status`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/realms/all`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/realms/evaluate`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/correct`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/correct/stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/hundun/stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/hundun/foams`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/v2/huigu/stats`

- 分组: public
- 说明: 扫描自 api_server.py

### `GET /api/health`

- 分组: 系统
- 说明: HTTP 健康检查

### `GET /api/stats`

- 分组: 系统
- 说明: 系统指标（含向量存储）

### `POST /api/bazi/calc`

- 分组: 八字排盘
- 说明: 计算四柱、大运、流年、五行等

### `POST /api/bazi/shensha`

- 分组: 八字排盘
- 说明: 神煞推算

### `POST /api/bazi/geju`

- 分组: 八字排盘
- 说明: 格局判断

### `POST /api/bazi/yongshen`

- 分组: 八字排盘
- 说明: 喜用神分析

### `POST /api/bazi/tiaohou`

- 分组: 八字排盘
- 说明: 调候分析

### `POST /api/bazi/full`

- 分组: 八字排盘
- 说明: 综合八字分析

### `POST /api/bazi/report`

- 分组: 八字排盘
- 说明: 命理报告生成（文本/Markdown/JSON/HTML）

### `POST /api/knowledge/search`

- 分组: 知识查询
- 说明: 语义搜索（向量）

### `POST /api/knowledge/recommend`

- 分组: 知识查询
- 说明: 节点关联推荐

### `GET /api/knowledge/wuxing/{element}`

- 分组: 知识查询
- 说明: 五行查询

### `GET /api/knowledge/bagua/{trigram}`

- 分组: 知识查询
- 说明: 八卦查询

### `GET, POST /api/records`

- 分组: 数据持久化
- 说明: 八字记录（登录用户隔离）

## 数据模型

### BaziInput

- 模块: `tengod.api_server / tengod.admin_api`

| Field | Type |
| --- | --- |
| `year` | int, 1900-2100 |
| `month` | int, 1-12 |
| `day` | int, 1-31 |
| `hour` | int, 0-23 |
| `minute` | int, 0-59 |
| `gender` | 'male' | 'female' |
| `longitude` | float |
| `latitude` | float |

### BaziRecord

- 模块: `tengod.data_store`

| Field | Type |
| --- | --- |
| `id` | int (主键) |
| `year` | int |
| `month` | int |
| `day` | int |
| `hour` | int |
| `gender` | str |
| `user_id` | Optional[int] |
| `label` | str |
| `day_master` | str |
| `pillars` | dict |
| `analysis` | dict |
| `created_at` | datetime |

### PluginMetadata

- 模块: `tengod.plugins`

| Field | Type |
| --- | --- |
| `id` | str (插件唯一 ID) |
| `name` | str |
| `version` | str |
| `author` | str |
| `description` | str |
| `entry_point` | str |
| `hooks` | List[str] |
| `permissions` | List[str] |
| `dependencies` | List[str] |
| `is_active` | bool |
| `is_builtin` | bool |

### ReportQuery

- 模块: `tengod.api_server`

| Field | Type |
| --- | --- |
| `bazi` | BaziInput |
| `format` | 'text' | 'markdown' | 'json' | 'html' |
| `include_shensha` | bool |
| `include_geju` | bool |
| `include_yongshen` | bool |
