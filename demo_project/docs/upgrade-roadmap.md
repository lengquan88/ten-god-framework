# 升级路线图 (Upgrade Roadmap)

> TenGod Framework 版本演进与未来规划

---

## 版本历史

| 版本 | 发布日期 | 主题 | 核心变更 |
|------|----------|------|----------|
| v1.0.0 | 2026-06-21 | 项目初始化 | Stages 21-30 上线，基础框架搭建 |
| v2.1.0 | 2026-02-01 | 真太阳时与基础架构 | 真太阳时计算、八字排盘核心、五行强弱分析、AI 智能分析、可视化图表 |
| v2.2.0 | 2026-02-10 | 知识图谱融合 | 知识图谱引擎、知识融合引擎、Graphviz/JSON 图谱导出、Knowledge API |
| v2.3.0 | 2026-02-13 | 移动端适配与国际化 | 三语翻译引擎(246条)、PWA 渐进式应用、移动端轻量 API、Gzip 压缩 |
| v2.4.0 | 2026-06-23 | 可视化增强与报告系统升级 | 紫微斗数12宫位可视化、报告系统多语言集成、PNG 导出(cairosvg)、分享卡多语言 |

---

## 升级路径

### v2.3.x → v2.4.0

```bash
git pull origin main
pip install -r requirements.txt
pip install cairosvg
python -m pytest tests/test_v24_visualization.py tests/test_v23_i18n.py tests/test_chart_visualizer.py -v
```

**兼容性说明**：
- 所有新增 `lang` 参数默认 `zh-CN`，不影响现有调用
- 紫微斗数可视化器为全新模块，独立于八字可视化
- cairosvg 为可选依赖，未安装时 PNG 导出自动回退 SVG

**新增依赖**：
- `cairosvg` — SVG→PNG 转换（可选）
- `markdown` — Markdown 报告渲染

### v2.2.x → v2.3.0

```bash
git pull origin main
pip install -r requirements.txt
python -m pytest tests/test_v23_i18n.py -v
```

**新增文件**：
- `tengod/i18n.py` — 翻译引擎
- `web_console/manifest.json` — PWA 清单
- `web_console/service-worker.js` — Service Worker

### v2.1.x → v2.2.0

```bash
git pull origin main
pip install -r requirements.txt
```

**新增文件**：
- `tengod/knowledge_graph.py` — 知识图谱引擎
- `tengod/knowledge_fusion.py` — 知识融合引擎

### v1.0.0 → v2.1.0

```bash
git pull origin main
pip install -r requirements.txt
```

---

## 未来规划

### v2.5.0 — 多体系深度整合（计划中）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 紫微斗数完整排盘 | 四化飞星、大限流年、小限流月 |
| P0 | 七政四余基础支持 | 星盘计算、二十八宿 |
| P1 | 报告对比分析 | 八字/紫微/七政四余交叉验证 |
| P1 | 交互式命盘编辑器 | 拖拽调整、实时刷新 |
| P2 | 多语言扩展 | 日语(ja)、韩语(ko) |

### v2.6.0 — AI 能力增强（设想中）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 流式 AI 响应 | SSE 实时输出 |
| P1 | 多模型支持 | DeepSeek/通义千问/文心一言 |
| P1 | 命理知识问答 | RAG 增强检索 |
| P2 | 智能格局推荐 | 基于历史案例的格局匹配 |

### v3.0.0 — 平台化（远期设想）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 用户系统 | 注册/登录/历史记录 |
| P1 | 社区分享 | 命盘分享、案例讨论 |
| P1 | 开放平台 | REST API + SDK |
| P2 | 小程序 | 微信/支付宝小程序 |

---

## 技术债务追踪

| 问题 | 引入版本 | 严重程度 | 状态 |
|------|----------|----------|------|
| `test_case_library.py` SQLAlchemy 表重复定义 | v2.2.0 | 中 | 待修复 |
| `test_phase24_25.py` 导入 `I18nManager` 失败 | v2.3.0 | 低 | 待修复 |
| `test_api_integration.py` 导入 `TenGodCore` 失败 | v2.1.0 | 中 | 待修复 |
| 翻译表缺少"八字命理综合分析报告"词条 | v2.3.0 | 低 | 待补充 |

---

## 版本规范

- **主版本号**：重大架构变更，不保证向下兼容
- **次版本号**：新增功能模块，保持向下兼容
- **修订号**：Bug 修复与性能优化

遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。