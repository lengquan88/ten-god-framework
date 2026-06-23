# Release Notes

## v2.4.0 — 可视化增强与报告系统升级

> 发布日期: 2026-06-23

### Highlights

- **紫微斗数可视化引擎**: 完整12宫位渲染（HTML/SVG），星曜颜色映射，大运叠盘叠加
- **报告系统多语言集成**: BaziReportGenerator 和 ComprehensiveReportGenerator 全面支持 lang 参数
- **PNG 导出**: 基于 cairosvg 的真实 SVG→PNG 转换，含回退机制
- **分享卡多语言**: ShareCardGenerator 三个方法均支持 lang 参数

### 新增功能

#### 1. 紫微斗数可视化器 (`tengod.chart_visualizer.ZiweiChartVisualizer`)
- 12宫位标准4x4网格布局，消除宫位冲突
- 主星/辅星/四化星颜色映射（14主星 + 16辅星 + 4四化星）
- 大运叠盘信息展示（年龄范围标注）
- 命宫/身宫特殊边框标记（红色/蓝色）
- 响应式设计：768px/480px 断点适配
- hover 动画效果（金色边框 + 阴影 + 微位移）
- 暗色主题（`#1a1a2e` 背景）
- SVG 矢量输出（`generate_svg()` / `_generate_svg_grid()`）
- 便捷函数：`visualize_ziwei()` / `visualize_ziwei_svg()`

#### 2. 报告系统多语言集成 (`tengod.report_generator`)
- `BaziReportGenerator.__init__()` 新增 `lang` 参数，默认 `zh-CN`
- 所有章节标题和关键标签通过 `_t()` 翻译
- 支持的方法：`text_report()`, `markdown_report()`, `json_report()`, `html_report()`
- JSON 报告新增 `"lang"` 字段
- HTML 模板 `<html lang="{lang}">` 动态语言标记
- `ComprehensiveReportGenerator` 同样支持 `lang` 参数
- `generate_report()` / `generate_html_report()` 便捷函数新增 `lang` 参数

#### 3. PNG 导出 (`tengod.visualization`)
- `export_to_png()` 使用 cairosvg 库实现真实 SVG→PNG 转换
- cairosvg 未安装时自动回退 SVG 输出
- 支持输出到文件路径

#### 4. 分享卡多语言 (`tengod.miniapp`)
- `ShareCardGenerator` 新增 `_t()` 翻译辅助方法
- `generate_bazi_share()` 支持 `lang` 参数
- `generate_trajectory_share()` 支持 `lang` 参数
- `generate_ai_share()` 支持 `lang` 参数

#### 5. API 层更新 (`tengod.api_server`)
- 报告生成端点支持 `lang` 参数透传

### 测试覆盖
- 25 个 v2.4 新增测试用例
- 紫微斗数可视化测试（9）：HTML/SVG/星曜/四化/大运/命宫身宫/边界/便捷函数
- 报告多语言测试（5）：简中/英文/Markdown/JSON/HTML
- PNG 导出测试（2）：回退机制/文件路径
- 分享卡多语言测试（4）：八字/轨迹/AI 三种卡片的简中/英文
- 全量回归测试（5）：导入验证/签名检查

### 升级说明
```bash
git pull origin main
pip install -r requirements.txt
pip install cairosvg
python -m pytest tests/test_v24_visualization.py tests/test_v23_i18n.py tests/test_chart_visualizer.py -v
```

### 兼容性
- 向下兼容 v2.3.x 所有 API
- 新增 `lang` 参数默认为 `zh-CN`，不影响现有调用
- 紫微斗数可视化器为全新模块，不影响现有八字可视化
- PNG 导出 cairosvg 为可选依赖，未安装时自动回退

### 问题修复
- 修复紫微斗数 3x4 网格布局宫位冲突（寅/丑、亥/子 映射到同一单元格）
- 升级为 4x4 标准紫微命盘布局

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
