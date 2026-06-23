# Release Notes

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
