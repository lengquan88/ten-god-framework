# Release Notes

## v2.7.0 — 六爻可视化 + 流式API + 异步任务

> 发布日期: 2026-06-23

### Highlights

- **六爻卦象可视化**: 本卦/变卦/互卦+六爻+世应+六亲+六神，HTML/SVG双格式
- **SSE 流式 API**: `/api/v2/ai/stream-interpret` 流式解读输出
- **六爻 REST API**: `/api/liuyao/cast` 起卦 + `/api/liuyao/chart` 可视化
- **异步任务系统**: 创建/查询/更新进度端点 + 内存任务存储

### 新增功能

#### 1. 六爻卦象可视化 (`LiuyaoChartVisualizer`)
- 六爻卦象图（初爻→上爻），阳爻/阴爻区分显示
- 六亲颜色映射：父母(蓝)/兄弟(金)/妻财(绿)/官鬼(红)/子孙(紫)
- 六神标签：青龙/朱雀/勾陈/螣蛇/白虎/玄武
- 世应标记：世爻(红圆点)/应爻(绿方点)
- 动爻高亮（红色左边框 + 动爻标记）
- 卦名展示：本卦/变卦/互卦
- 断辞展示区域
- 暗色主题 + hover 动画 + 移动端响应式
- SVG 矢量输出（爻线+世应标记+六亲标签）
- 便捷函数：`visualize_liuyao()` / `visualize_liuyao_svg()`

#### 2. 六爻 API 端点
- `POST /api/liuyao/cast` — 起卦（支持随机/手动，返回完整卦象JSON）
- `GET /api/liuyao/chart` — 卦象 HTML 可视化（可直接嵌入 iframe）

#### 3. SSE 流式解读
- `POST /api/v2/ai/stream-interpret` — SSE 流式输出
- 支持 bazi/liuyao 两套提示词
- 标准 SSE 格式 (`text/event-stream`)

#### 4. 异步任务系统
- `POST /api/tasks` — 创建异步任务
- `GET /api/tasks/{task_id}` — 查询任务状态
- `POST /api/tasks/{task_id}/progress` — 更新任务进度
- 状态：pending → running → done/failed
- 内存存储（生产环境可换 Redis）

### 测试覆盖
- 26 个 v2.7 新增测试用例
- 六爻可视化测试（14）：初始化/HTML(dict+dataclass)/爻信息/六亲/六神/世应/动爻/SVG/便捷函数/颜色映射
- 六爻引擎集成测试（6）：起卦/日干/六亲/六神/世应/断辞
- 异步任务测试（1）：任务存储状态流转
- 回归测试（5）：导入/v2.6/v2.5/v2.4兼容

### 全量测试
```bash
# 174 passed (26 v2.7 + 30 v2.6 + 40 v2.5 + 25 v2.4 + 34 v2.3 + 30 chart_visualizer)
python -m pytest tests/test_v23_i18n.py tests/test_v24_visualization.py \
     tests/test_v25_fusion.py tests/test_v26_visualization.py \
     tests/test_v27_liuyao.py tests/test_chart_visualizer.py -v -k "not async"
```

### 升级说明
```bash
git pull origin main
pip install -r requirements.txt
python -m pytest tests/test_v27_liuyao.py -v
```

### 兼容性
- 向下兼容 v2.6.x 所有 API
- 六爻可视化器与现有 `chart_visualizer.py` 共享暗色主题风格
- 异步任务为独立端点，不影响现有同步 API

---

## v2.6.0 — 术数可视化完善 + 缓存系统

> 发布日期: 2026-06-23

### Highlights

- **奇门遁甲可视化**: 九宫格+八门+九星+八神+天地盘，HTML/SVG双格式
- **风水可视化**: 玄空飞星九宫+运星/山星/向星/流年星四层叠加+风水断语
- **引擎缓存系统**: 装饰器模式+TTL策略+命中率统计
- **全术数可视化覆盖**: 八字→紫微→奇门→风水→轨迹→六爻(引擎已有)

### 新增功能

#### 1. 奇门遁甲可视化 (`QimenChartVisualizer`)
- 洛书九宫布局（坎一/坤二/震三/巽四/中五/乾六/兑七/艮八/离九）
- 每宫六层信息：宫名+九星+八神+天盘干+地盘干+八门
- 八门颜色映射：吉门(绿)/凶门(红)/中平(金)
- 暗色主题 + hover 动画 + 移动端响应式
- SVG 矢量输出
- 便捷函数：`visualize_qimen()` / `visualize_qimen_svg()`

#### 2. 风水可视化 (`FengshuiVisualizer`)
- 玄空飞星九宫格：运星/山星/向星/流年星四层叠加
- 九星名称映射：一白至九紫 + 吉凶标注
- 九星颜色映射：吉(绿)/凶(红)/大凶(深红)
- 风水断语展示（可从 `xuankong.py` 计算输出）
- HTML + SVG 双格式
- 便捷函数：`visualize_fengshui()` / `visualize_fengshui_svg()`

#### 3. 引擎缓存系统 (`cache_manager.py`)
- `EngineCacheStats` 类：命中/未命中计数 + 命中率统计
- `cached_engine()` 装饰器：自动 TTL + 命中率追踪
- 引擎专用装饰器：`cached_bazi`/`cached_ziwei`/`cached_qimen`/`cached_fengshui`/`cached_fusion`
- TTL 策略：八字 24h / 紫微 24h / 奇门 1h / 风水 1h / 融合 30min / 报告 10min
- `get_engine_cache_stats()` 全局统计 API

### 测试覆盖
- 30 个 v2.6 新增测试用例
- 奇门可视化测试（8）：初始化/HTML/SVG/九宫/八门/便捷函数/空数据
- 风水可视化测试（9）：初始化/HTML/SVG/星名/断语/山向/便捷函数/空数据
- 引擎缓存测试（9）：TTL默认值/统计记录/命中率/重置/装饰器
- 回归测试（4）：导入/v2.5兼容/缓存管理器

### 全量测试
```bash
# 149 passed (30 v2.6 + 40 v2.5 + 25 v2.4 + 34 v2.3 + 30 chart_visualizer)
python -m pytest tests/test_v23_i18n.py tests/test_v24_visualization.py \
     tests/test_v25_fusion.py tests/test_v26_visualization.py \
     tests/test_chart_visualizer.py -v -k "not async"
```

### 升级说明
```bash
git pull origin main
pip install -r requirements.txt
python -m pytest tests/test_v26_visualization.py -v
```

### 兼容性
- 向下兼容 v2.5.x 所有 API
- 新可视化器与现有 `chart_visualizer.py` 共享暗色主题风格
- 缓存装饰器可选使用，不影响现有代码路径

---

## v2.5.0 — 智能分析与命运轨迹

> 发布日期: 2026-06-23

### Highlights

- **三体系融合分析引擎**: 八字+紫微+奇门加权交叉验证，综合评分+置信度
- **命运轨迹时间线**: 大运/流年可视化，HTML/SVG双格式，评分柱状图
- **AI 深度解读增强**: 上下文感知+个性化建议+对话记忆
- **案例对比分析**: 向量相似度检索+对比报告+历史验证

### 新增功能

#### 1. 融合分析引擎 (`tengod.fusion_analyzer.FusionAnalyzer`)
- 三体系独立分析：`_analyze_bazi()`, `_analyze_ziwei()`, `_analyze_qimen()`
- 交叉验证：喜用神一致性、评分一致性、吉凶方向一致性，产出置信度
- 加权综合评分：八字45%+紫微35%+奇门20%，交叉验证修正
- 关键事件提取：大运/大限/流年节点自动标注
- 个性化建议：五行调补+运势时机+用户目标
- 融合报告：文本格式结构化输出
- 便捷函数：`quick_fusion()`
- 常量导出：`SYSTEM_WEIGHTS`, `AGREEMENT_LEVELS`, `FORTUNE_LEVELS`

#### 2. 命运轨迹时间线 (`tengod.chart_visualizer.TrajectoryTimeline`)
- 左右交替时间线布局，大运（金色节点）+ 流年（蓝色节点）分层
- 流年运势评分柱状图（绿/金/红三色渐变）
- 暗色主题 + hover 动画 + 移动端响应式
- SVG 矢量输出（`generate_svg()`）
- 便捷函数：`visualize_trajectory()` / `visualize_trajectory_svg()`

#### 3. AI 深度解读增强 (`tengod.ai_interpreter`)
- 上下文感知解读：`interpret_bazi_contextual()` — 注入历史对话+用户目标
- 个性化建议生成：`generate_personalized_recommendations()` — 五行调补库（颜色/方位/行业/数字/行动）
- 对话记忆：`init_conversation()`, `add_to_conversation()`, `get_conversation_history()`, `clear_conversation()`
- 带记忆对话：`chat_with_memory()` — 多轮对话，LUI 一致性

#### 4. 案例对比分析 (`tengod.case_comparator.CaseComparator`)
- 向量相似度检索（余弦相似度）
- 向量存储对接（可选，回退到规则计算）
- 对比报告：相似度统计+共同模式+差异分析
- 5例模拟案例库（含验证标记）
- 便捷函数：`quick_compare()`

### 测试覆盖
- 40 个 v2.5 新增测试用例
- 融合分析测试（14）：初始化/三体系分析/交叉验证/序列化/权重/等级
- 轨迹时间线测试（9）：HTML/SVG/大运/流年/评分/空数据/便捷函数
- AI增强测试（7）：建议生成/吉凶运/目标/对话记忆/五行完整性
- 案例对比测试（6）：初始化/查找/对比/快速对比/空案例/序列化
- 回归测试（4）：导入/现有模块兼容性

### 全量测试
```bash
# 129 tests passed (40 v2.5 + 25 v2.4 + 34 v2.3 + 30 chart_visualizer)
python -m pytest tests/test_v23_i18n.py tests/test_v24_visualization.py \
     tests/test_v25_fusion.py tests/test_chart_visualizer.py -v
```

### 升级说明
```bash
git pull origin main
pip install -r requirements.txt
python -m pytest tests/test_v25_fusion.py -v
```

### 兼容性
- 向下兼容 v2.4.x 所有 API
- 新增模块均为独立文件，不影响现有代码
- 案例对比器向量搜索失败时自动回退规则计算

---

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
