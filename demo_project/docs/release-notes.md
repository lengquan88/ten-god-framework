# Release Notes

## v2.4.0 — 可视化增强与报告系统升级

> 发布日期: 2026-06-23

### Highlights

- **紫微斗数完整可视化**: 4×4 网格布局映射十二宫位，主星颜色映射、四化标记、大限叠盘、身宫标记
- **报告系统多语言集成**: `BaziReportGenerator` 全格式（text/markdown/json/html）支持 `lang` 参数
- **PNG 图片导出**: 基于 cairosvg 的 SVG→PNG 转换，带 ImportError 降级
- **分享卡升级**: `ShareCardGenerator` 多语言支持 + 八字/紫微命盘分享图生成

### 新增功能

#### 1. 紫微斗数可视化引擎 (`tengod.chart_visualizer.ZiweiChartVisualizer`)
- 4×4 CSS Grid 布局，地支→网格位置精准映射（子→(3,2)、午→(0,1) 等）
- 14 主星颜色映射（紫微深红、天机宝蓝、太阳橙黄等）
- 四化标记（禄金/权红/科绿/忌灰）与宫位绑定
- 大限叠盘显示（年龄区间标注）
- 身宫标记（红色角标）
- 中心信息区：五行局/命主/身主/四化
- 响应式设计：600px / 400px 断点
- 双格式输出：`generate_html()` / `generate_svg()`
- 多语言支持：zh-CN / zh-TW / en

#### 2. 报告系统多语言集成 (`tengod.report_generator.BaziReportGenerator`)
- `__init__(lang="zh-CN")` 构造函数参数
- `_t()` 翻译辅助方法，集成 `tengod.i18n.t`
- 全格式报告方法支持 `lang` 可选参数：
  - `text_report(lang=None)`
  - `markdown_report(lang=None)`
  - `json_report(lang=None)`
  - `html_report(lang=None)`
- 所有章节标题（基本信息/四柱/五行/十神/神煞/格局/喜用神/大运/流年/建议）使用 `_t()` 翻译
- 便捷函数 `generate_report()` / `generate_html_report()` 添加 `lang` 参数

#### 3. PNG 图片导出 (`tengod.visualization.export_to_png`)
- 基于 cairosvg 库实现 SVG→PNG 矢量转换
- 支持文件输出（`output_path` 参数）和 base64 数据 URL 返回
- ImportError 降级：cairosvg 未安装时返回原 SVG 内容
- 异常降级：转换失败时返回原 SVG 内容

#### 4. 分享卡升级 (`tengod.miniapp.ShareCardGenerator`)
- `__init__(lang="zh-CN")` 构造函数参数
- 所有方法支持 `lang` 可选参数（方法级覆盖构造函数设置）
- 新增 `generate_bazi_chart_share()`: 八字命盘分享图（SVG + PNG）
- 新增 `generate_ziwei_chart_share()`: 紫微命盘分享图（SVG + PNG）
- 多语言标题/描述生成

#### 5. API 端点多语言
- `ReportQuery` 模型新增 `lang` 字段（默认 `zh-CN`）
- `/api/v2/bazi/report` 端点传递 `lang` 至报告生成器

#### 6. i18n 翻译表扩展
- 新增 33 条紫微相关词条：
  - 十二宫名称（13条）：命宫/兄弟/夫妻/子女/财帛/疾厄/迁移/交友/官禄/田宅/福德/父母/身宫
  - 四化（4条）：化禄/化权/化科/化忌
  - 辅星扩展（14条）：左辅/右弼/文昌/文曲/天魁/天钺/禄存/天马/地空/地劫/擎羊/陀罗/火星/铃星
  - 术语（5条）：大限/小限/流盘/叠盘/宫位
- 翻译表总数：246 → 279 条

### 测试覆盖
- 30 个 v2.4 新增测试用例（`tests/test_v24_viz.py`）
- 紫微可视化测试：HTML/SVG/多语言/便捷函数（6 项）
- 多语言报告测试：默认语言/构造函数/方法覆盖/markdown/json/html/zh-TW（7 项）
- PNG 导出测试：返回值/降级/文件输出（3 项）
- 分享卡测试：默认语言/构造函数/方法覆盖/八字命盘图/紫微命盘图/多语言/轨迹/AI（8 项）
- API 端点测试：ReportQuery lang 字段（2 项）
- i18n 翻译表测试：数量/完整性/紫微术语/回退（4 项）

### 修复的回归
- `ZiweiChartVisualizer.generate_html()` CSS 类名兼容：同时保留 `zw-grid` 和 `ziwei-grid` 类名，确保旧测试通过

### 升级说明
```bash
git pull origin main
pip install cairosvg  # 可选，用于 PNG 导出（未安装时自动降级为 SVG）
python -m pytest tests/test_v24_viz.py -v
```

### 兼容性
- 向下兼容 v2.3.x 所有 API
- `ShareCardGenerator()` 无参构造仍可用（`lang` 默认 `zh-CN`）
- `BaziReportGenerator` 无 `lang` 参数仍可用（默认 `zh-CN`）
- PNG 导出在 cairosvg 未安装时自动降级，不影响核心功能

---

## v2.3.0 — 移动端适配与国际化

> 发布日期: 2026-02-13

### Highlights

- **国际化引擎 (i18n)**: 三语翻译引擎（简中/繁中/英文），覆盖 200+ 命理术语
- **PWA 移动端适配**: Web App Manifest + Service Worker 离线缓存 + 响应式设计
- **移动端 API 优化**: Gzip 压缩 + 轻量八字端点 + 知识图谱分页
- **多语言 API 支持**: 所有 v2 接口支持 `lang` 参数，响应内容自动翻译

### 新增功能

#### 1. 国际化模块 (`tengod.i18n`)
- `I18nEngine` 单例翻译引擎，支持简中(zh-CN)、繁中(zh-TW)、英文(en)
- 翻译表覆盖：天干地支、五行、十神、神煞、格局、二十四节气、十二时辰
- 便捷函数：`t()`、`translate_bazi()`、`translate_wuxing()`、`translate_shier()`
- 支持嵌套字典翻译、列表翻译、自定义翻译扩展

#### 2. PWA 渐进式 Web 应用
- `manifest.json`: 应用元数据、图标配置、快捷方式（八字排盘/AI分析/知识图谱）
- `service-worker.js`: 静态资源预缓存 + 运行时缓存策略
  - HTML 页面：网络优先，失败回退缓存
  - 静态资源：缓存优先，失败回退网络
  - API 请求：网络优先，离线返回 503
- 响应式设计：768px / 480px 断点，触控友好按钮（44px 最小高度）

#### 3. 移动端 API 优化
- 新增 `/api/v2/mobile/bazi/quick` 轻量八字端点，payload 减少约 60%
- 新增 `/api/v2/knowledge/list` 知识列表，支持分页、分类过滤、多语言
- 启用 Gzip 压缩中间件，减少移动端流量消耗
- 所有 v2 API 支持 `lang` 参数，响应内容自动翻译

#### 4. 国际化 API 端点
- `GET /api/v2/i18n/languages` — 获取支持的语言列表
- `POST /api/v2/i18n/translate` — 批量文本翻译

### 测试覆盖
- 29 个 v2.3 新增测试用例
- 翻译引擎功能测试（单例模式、语言切换、回退机制）
- 翻译表完整性校验（天干/地支/五行/节气/十神）
- API 多语言响应测试
- 知识图谱分页与分类过滤测试

### 升级说明
```bash
git pull origin main
pip install -r requirements.txt
python -m pytest tests/test_v23_i18n.py -v
```

### 兼容性
- 向下兼容 v2.2.x 所有 API
- 新增 `lang` 参数默认为 `zh-CN`，不影响现有调用
- PWA 为渐进增强，不影响传统 Web 访问

---

## v2.2.0 — 知识图谱融合

> 发布日期: 2026-02-10

### Highlights
- 知识图谱引擎：实体-关系建模，支持五行、天干、地支、十神等核心概念
- 知识融合引擎：多源知识整合，关键词提取，关联推荐
- 可视化导出：Graphviz / JSON 格式图谱导出
- API 端点：`/api/v2/knowledge/*` 系列接口

---

## v2.1.0 — 真太阳时与基础架构

> 发布日期: 2026-02-01

### Highlights
- 真太阳时计算：经度校正，节气精确时间
- 八字排盘核心：年柱/月柱/日柱/时柱计算
- 五行强弱分析：旺相休囚死，得分计算
- AI 智能分析：DeepSeek 适配器，多维度解读
- 可视化图表：HTML / SVG / JSON 多格式输出

---

## v1.0.0 — 项目初始化

> 发布日期: 2026-06-21

### Highlights
- 项目初始化
- Stages 21-30 上线
