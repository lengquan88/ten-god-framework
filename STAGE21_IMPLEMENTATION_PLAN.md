# 阶段二十一：预测体系补全 — 技术实现方案

> 目标：将"排盘"升级为"预测"，补全命理预测最后一块拼图
> 依赖：阶段十八（案例库）、阶段二十（高级分析）
> 预计工作量：4~6 人/周

---

## 21.0 现有代码审计

| 模块 | 已有能力 | 缺口 |
|------|---------|------|
| `dayun_liunian.py` | 大运起运年龄、10步大运排盘、流年干支推算 | 无断语文本生成，无流年吉凶判断 |
| `shensha_engine.py` | 40+神煞推算（天德/月德/桃花等） | 流年神煞叠加判断缺失 |
| `divination_engine.py` | 十神关系、五行生克、天干地支引擎 | 无八字预测规则库 |
| `geju_engine.py` | 格局判断、用神忌神、调候 | 流年喜忌变化未覆盖 |
| `advanced_analysis.py` | 命例对比、批量排盘、轨迹推演 | 轨迹仅含大运列表，无断语 |

**结论：** 21.1 可完全基于现有模块叠加断语层；21.2~21.4 需新建模块。

---

## 21.1 流年吉凶自动断语

### 架构设计

```
liunian_judgment.py (新建)
├── LiunianJudgmentEngine      # 流年断语引擎
│   ├── _load_templates()      # 加载断语模板库
│   ├── _analyze_year(year, record)  # 单年分析
│   ├── _judge_luck(bazi, dayun, liunian)  # 吉凶判断
│   └── generate_judgment(years)  # 批量生成
├── JudgmentTemplate           # 断语模板类
│   ├── condition              # 触发条件
│   ├── templates[]           # 候选模板列表
│   └── render(context)        # 上下文渲染
└── TEMPLATE_LIBRARY           # 模板库（100+ 条）
```

### 核心数据结构

```python
# 流年分析输入
class LiunianInput:
    year: int                  # 流年年份
    bazi: dict                 # 完整八字（含四柱/五行/十神/格局）
    dayun: list                # 大运列表（来自 dayun_liunian.py）
    liunian: dict              # 流年干支信息
    shensha: dict              # 流年神煞

# 流年吉凶输出
class LiunianJudgment:
    year: int
    gan_zhi: str               # 流年干支
    wuxing: str                # 流年五行
    relation_to_day_master: str  # 与日主关系
    favorable_elements: list   # 有利五行
    unfavorable_elements: list  # 不利五行
    judgment: str              # 总体判断（吉/平/凶）
    score: int                 # 评分 1-100
    judgments: list[str]       # 断语列表
    warnings: list[str]        # 注意事项
    favorable_months: list[int]  # 有利月份（1-12）
    unfavorable_months: list[int]  # 不利月份
```

### 吉凶判断算法

```
吉凶评分 = 基础分(50) + 喜用神分 + 忌神分 + 神煞分 + 月令分 + 冲合分

喜用神分: 流年天干/地支五行 ∈ 喜用神 → +10/项
忌神分:  流年天干/地支五行 ∈ 忌神   → -10/项
神煞分:  吉神(天德/月德/文昌)     → +5/项
          凶神(亡神/劫煞/阴差)     → -5/项
月令分:  流年地支 = 喜神月令      → +10
冲合分:  流年冲克日支            → -15
          流年与命局三合          → +15
评分区间: ≥70=吉, 40~69=平, <40=凶
```

### 断语模板库设计

```python
TEMPLATE_LIBRARY = [
    # ── 喜用神被助 ──────────────────────────────
    JudgmentTemplate(
        id="yongshen_supported",
        condition=lambda ctx: ctx["liunian_gan"] in ctx["yongshen"],
        templates=[
            "流年天干透{gan}，得用神助力，事事顺遂，宜把握机遇。",
            "年干见{yongshen}，事业上有突破之象，贵人运佳。",
        ],
    ),
    # ── 忌神逞凶 ──────────────────────────────
    JudgmentTemplate(
        id="jishen_rampant",
        condition=lambda ctx: ctx["liunian_gan"] in ctx["jishen"],
        templates=[
            "忌神{ji}星现于流年，当保守行事，防小人暗算，破耗难免。",
            "流年干支助忌神{ji}，凡事须谨慎，不宜激进扩张。",
        ],
    ),
    # ── 日支被冲 ──────────────────────────────
    JudgmentTemplate(
        id="rizhi_chong",
        condition=lambda ctx: ctx["rizhi_chong"],
        templates=[
            "日支{rizhi}被冲，动荡之象，住所或感情易有变动。",
            "冲则必动，流年动荡期，亲密关系需妥善处理。",
        ],
    ),
    # ── 桃花星现 ──────────────────────────────
    JudgmentTemplate(
        id="taohua_present",
        condition=lambda ctx: ctx["has_taohua"],
        templates=[
            "桃花星现，姻缘运势强盛，未婚者有望遇到心仪之人。",
            "桃花临命，异性缘佳，但需把握分寸，忌感情用事。",
        ],
    ),
    # ── 官星流年 ──────────────────────────────
    JudgmentTemplate(
        id="guansheng_year",
        condition=lambda ctx: ctx["liunian_shigan"] in ["正官", "七杀"],
        templates=[
            "{shigan}流年，事业有发展之机，贵人赏识，晋升有望。",
            "官星得令，仕途顺遂，若从政或管理者宜把握良机。",
        ],
    ),
    # ... 模板库共计 100+ 条，覆盖所有主流断语场景
]
```

### API 端点

```python
class LiunianJudgmentRequest(BaseModel):
    record_id: Optional[int] = None
    birth_year: int; birth_month: int; birth_day: int
    birth_hour: int; gender: str
    start_year: int = Field(default_factory=lambda: 当前年份)
    end_year: int = Field(default_factory=lambda: 当前年份+10)
    include_details: bool = False

class LiunianJudgmentResponse(BaseModel):
    judgments: List[LiunianJudgment]
    summary: str           # 综合十年运势概述
    best_years: List[int] # 最有利年份
    worst_years: List[int] # 最不利年份
    career_tips: List[str]
    relationship_tips: List[str]
    health_tips: List[str]
```

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/liunian/judge` | POST | bazi:full | 流年断语生成 |
| `/api/liunian/year/{year}` | GET | bazi:full | 指定年份详细分析 |
| `/api/liunian/decade-summary` | POST | bazi:full | 十年综合运势 |

### 子任务分解

- [ ] `liunian_judgment.py` 核心引擎（2d）
- [ ] 断语模板库 100+ 条（2d）
- [ ] API 端点（0.5d）
- [ ] 测试用例（1d）
- [ ] 与现有 dayun_liunian.py 集成（0.5d）

---

## 21.2 玄空飞星风水排盘

### 架构设计

```
fengshui/xuankong.py (新建)
├── XuankongEngine           # 玄空飞星引擎
│   ├── _calc_yuandanpan(坐向, 运)    # 元旦盘
│   ├── _calc_yunpan(运星)            # 运盘
│   ├── _calc_shanpan(山飞星)         # 山盘（坐山）
│   ├── _calc_xiangpan(向飞星)        # 向盘
│   ├── _calc_mingpan(命盘)           # 命宫飞星（可选）
│   └── compute(坐向, 运, 日期)        # 完整排盘
├── FengshuiAnalysis         # 风水分析
│   ├── _analyze_health()              # 健康方位
│   ├── _analyze_wealth()              # 财富方位
│   ├── _analyze_relationship()        # 感情方位
│   └── _analyze_career()              # 事业方位
└── data/xuankong_schema.json   # 飞星数据（九星/九宫/运程）

fengshui/yangzhai.py (新建)
├── YangzhaiAnalyzer         # 阳宅分析
│   ├── compute(fengshui_data, 住宅坐向)
│   ├── _analyze_menwei()              # 门路方位
│   ├── _analyze_chufang()             # 厨房位置
│   └── _analyze_bedroom()             # 卧室位置
└── YangzhaiReport           # 阳宅报告
```

### 玄空飞星核心算法

```python
class XuankongEngine:
    """玄空飞星排盘"""

    # 九星定义：贪狼/巨门/禄存/文曲/廉贞/武曲/破军/左辅/右弼
    NINE_STARS = {
        "一": "贪狼", "二": "巨门", "三": "禄存", "四": "文曲",
        "五": "廉贞", "六": "武曲", "七": "破军", "八": "左辅", "九": "右弼",
    }

    # 九宫飞布规则（阳宅顺飞/阴宅逆飞）
    FLY_RULES = {
        # 入中宫之星 → 决定下一宫位置
        # 简化版：按洛书数字顺序顺布
    }

    def compute(self, 坐向: str, 运: int, 日期: str) -> XuankongResult:
        """玄空飞星完整排盘"""
        # 1. 判断立极（坐北朝南为基础）
        # 2. 确定元旦盘（根据下元几运）
        # 3. 运盘飞布（按运星飞布规则）
        # 4. 山、向飞星（按山/向宫位叠加）
        # 5. 流年飞星（叠加当前流年）
        # 6. 返回九宫图数据
```

### 九宫图数据结构

```python
class XuankongResult(BaseModel):
    坐向: str                          # 例如 "坐北向南"
    运: int                            # 上元一运/二运/三运 / 中元四运/五运/六运 / 下元七运/八运/九运
    yuan_dan_pan: Dict[str, int]       # 元旦盘 {"坎一宫": 1, "坤二宫": 2, ...}
    yun_pan: Dict[str, int]             # 运盘 {"坎一宫": 7, "坤二宫": 3, ...}
    shan_pan: Dict[str, int]            # 山盘（坐山飞星）
    xiang_pan: Dict[str, int]           # 向盘（向首飞星）
    liunian_pan: Optional[Dict[str, int]] # 流年飞星
    analysis: FengshuiAnalysis
    judgments: List[str]                # 风水判断语

class FengshuiAnalysis(BaseModel):
    # 九宫方位分析
    财富方位: List[str]      # 主财/次财宫位及星组合
    健康方位: List[str]
    感情方位: ListStr]
    事业方位: List[str]
    凶位: List[str]          # 需要化解的方位
    吉位: List[str]          # 宜加强的方位
```

### API 端点

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/fengshui/xuankong` | POST | bazi:full | 玄空飞星排盘 |
| `/api/fengshui/yangzhai` | POST | bazi:full | 阳宅风水分析 |
| `/api/fengshui/yinzhai` | POST | bazi:full | 阴宅风水分析 |
| `/api/fengshui/liunian-flying` | POST | bazi:full | 流年飞星叠加 |

### 子任务分解

- [ ] `fengshui/xuankong.py` 核心飞星算法（3d）
- [ ] `fengshui/yangzhai.py` 阳宅分析（2d）
- [ ] `data/xuankong_schema.json` 飞星数据（1d）
- [ ] API 端点（0.5d）
- [ ] 测试用例（1d）

---

## 21.3 七政四余星象排盘

### 架构设计

```
qizheng/ephemeris.py (新建)
├── EphemerisEngine          # 天文历法计算
│   ├── _init_ephem()        # 初始化星历表（Swiss Ephemeris）
│   ├── _calc_julian_day(公历日期)  # 儒略日计算
│   ├── _calc_planet_pos(星体, jd) # 星体位置计算
│   └── _calc_shu yu(星体, jd)      # 四余计算
├── QizhengEngine            # 七政引擎
│   ├── _calc_qizheng(出生jd, 经度, 纬度)  # 日月五星位置
│   └── _arrange_zodiac(星体位置)           # 排布十二宫
├── SimaEngine               # 四余引擎
│   ├── _calc_luohou(jd)     # 罗睺（升交点）
│   ├── _calc_jiadu(jd)      # 计都（降交点）
│   ├── _calc_yuepo(jd)      # 月孛（远地点）
│   └── _calc_ziqi(jd)       # 紫气（月行速度最慢点）
└── QizhengChart             # 七政四余命盘
```

### 天文计算方案

```
Swiss Ephemeris (免费天文库) vs 自建简化算法:

方案 A: Swiss Ephemeris (推荐)
  - pip install sweph
  - 精度: <1角秒
  - 支持: 日月/五星/罗计/月亮
  - 缺点: C库依赖，安装略复杂

方案 B: 简化牛顿力学
  - 无外部依赖
  - 精度: ±1~2天（在几百年范围内可接受）
  - 适合: demo/轻量级

推荐: 方案 A，生产用 Swiss Ephemeris
```

### 七政四余数据结构

```python
class QizhengChart(BaseModel):
    """七政四余命盘"""
    julian_day: float
    出生时间: str; 时区: str
    经度: float; 纬度: float

    # 七政（度数：黄经）
    日: PlanetPosition   # {星体: "日", 黄经: 123.45, 入宫: "亥", 庙旺: "旺"}
    月: PlanetPosition   # {星体: "月", 黄经: 45.67, 入宫: "子", 庙旺: "庙"}
    木星: PlanetPosition
    火星: PlanetPosition
    土星: PlanetPosition
    金星: PlanetPosition
    水星: PlanetPosition

    # 四余（度数）
    罗睺: PlanetPosition  # 升交点
    计都: PlanetPosition  # 降交点
    月孛: PlanetPosition  # 远地点
    紫气: PlanetPosition  # 月行最慢点

    # 十二宫（命宫/财帛/兄弟/田宅/男女/奴仆/妻妾/疾厄/迁移/官禄/福德/父母）
    十二宫: Dict[str, str]    # {"命宫": "亥", "财帛": "子", ...}

    # 星曜组合分析
    星曜入宫: List[str]        # 星曜落宫分析
    主星庙旺: List[str]        # 主星庙旺情况
    四化星: Dict[str, str]    # 化禄/化权/化科/化忌 落入宫位

class PlanetPosition(BaseModel):
    星体: str; 黄经: float; 黄纬: float
    入宫: str                   # 十二宫
    庙旺: str                  # 庙/旺/得/平/陷

class QizhengAnalysis(BaseModel):
    命宫主星: List[str]        # 命宫主星组合
    事业宫主星: List[str]
    财富宫主星: List[str]
    感情宫主星: List[str]
    星曜总评: str
    吉格: List[str]
    凶格: List[str]
```

### 十二宫安法

```python
class QizhengEngine:
    """七政四余排盘"""

    # 十二宫对应地支（命宫起子逆布）
    GONG_ZHI = {
        "命宫": "子", "兄弟": "亥", "夫妻": "戌",
        "子女": "酉", "财帛": "申", "疾厄": "未",
        "迁移": "午", "奴仆": "巳", "官禄": "辰",
        "田宅": "卯", "福德": "寅", "父母": "丑",
    }

    # 十四主星安法（根据五行局）
    # 火六局: 紫微在丑/未, 天机在亥/巳, ...
    # 木三局: 紫微在子/午, 天机在卯/酉, ...

    def _calc_ming_gong(self, year_gan: str, month_zhi: str, day_gan: str, hour_zhi: str):
        """安命宫（根据生月/生时）"""
        # 以生月地支逆布十二宫，以生时地支起子
        # 具体算法见《七政四余星学大成》

    def _calc_main_stars(self, ming_gong_zhi: str, wuxing_ju: str):
        """安十四主星"""
        # 紫微/天机/太阳/武曲/天同/廉贞 + 天府/太阴/贪狼/巨门/天相/天梁/七杀/破军
        # 根据命宫地支和五行局查表得出
```

### API 端点

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/qizheng/chart` | POST | bazi:full | 七政四余星盘 |
| `/api/qizheng/analysis` | POST | bazi:full | 星象分析 |
| `/api/qizheng/minggong/{chart_id}` | GET | bazi:full | 获取命盘详情 |

### 子任务分解

- [ ] `qizheng/ephemeris.py` 天文计算（2d）
- [ ] `qizheng/qizheng_engine.py` 七政四余排盘（3d）
- [ ] `qizheng/analysis.py` 星象分析（1.5d）
- [ ] `requirements.txt` 添加 sweph 依赖（0.5d）
- [ ] API 端点（0.5d）
- [ ] 测试用例（1d）

---

## 21.4 高级术数集成

### 21.4.1 铁板神数

```
tieban.py (新建)
├── TiebanEngine
│   ├── _init_table()              # 初始化铁板神数分数线（128条）
│   ├── _calc_base_number(八字)      # 计算基数（根据年柱纳音+月柱纳音）
│   ├── _calc_line_number(基数, 条件)  # 推算条文
│   └── compute(八字, 条件)         # 完整推算
└── data/tieban_lines.json    # 128条神数条文
```

**算法原理（简化版）：**
```
基数 = (年柱纳音序 × 月柱纳音序 + 日柱纳音序) mod 128
条文 = 查表[基数]
条文补数 = 根据时柱/性别/吉凶神煞进行调整
```

### 21.4.2 邵子神数

```
shaozi.py (新建)
├── ShaoziEngine
│   ├── _calc_tianfu_number(年柱)     # 天符数
│   ├── _calc_difang_number(月柱)     # 地符数
│   ├── _calc_tianren_number(日柱)    # 天人数
│   ├── _calc_hefa(date, time)       # 合十法（配合数）
│   └── compute(八字, 日期)            # 完整邵子数
```

### 21.4.3 河洛理数

```
heluo.py (新建)
├── HeluoEngine
│   ├── _calc_hetu_number(八字)    # 河图生成数
│   ├── _calc_luoshu_number(八字)   # 洛书九宫数
│   ├── _analyze_heluo_combo()     # 河洛组合分析
│   └── compute(八字)              # 河洛理数
```

### 21.4.4 小成图预测

```
xiaocheng.py (新建)
├── XiaochengEngine
│   ├── _generate_symbols(问题, 时间)  # 产生卦象符号
│   ├── _interpret_symbols(符号)        # 小成图解读
│   └── predict(问题, 日期时间)         # 小成图预测
```

### API 端点

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/advanced/tieban` | POST | bazi:full | 铁板神数 |
| `/api/advanced/shaozi` | POST | bazi:full | 邵子神数 |
| `/api/advanced/heluo` | POST | bazi:full | 河洛理数 |
| `/api/advanced/xiaocheng` | POST | bazi:full | 小成图预测 |

---

## 21.5 API Server 集成

在 `api_server.py` 中新增路由组：

```python
# ─── 阶段二十一：预测体系 ─────────────────────────────

@app.post("/api/liunian/judge", tags=["流年预测"])
async def liunian_judge(req: LiunianJudgmentRequest, request: Request):
    """流年吉凶自动断语"""
    from tengod.auth import authorize
    authorize(request, "bazi:full")
    from tengod.liunian_judgment import LiunianJudgmentEngine
    engine = LiunianJudgmentEngine()
    return engine.judge(
        start_year=req.start_year,
        end_year=req.end_year,
        record_id=req.record_id,
        birth_date=req.birth_date,
        gender=req.gender,
    )

@app.post("/api/fengshui/xuankong", tags=["风水排盘"])
async def xuankong_fengshui(req: XuankongRequest, request: Request):
    """玄空飞星风水排盘"""
    authorize(request, "bazi:full")
    from tengod.fengshui.xuankong import XuankongEngine
    engine = XuankongEngine()
    return engine.compute(坐向=req.坐向, 运=req.运, 日期=req.日期)

@app.post("/api/qizheng/chart", tags=["七政四余"])
async def qizheng_chart(req: QizhengRequest, request: Request):
    """七政四余星象排盘"""
    authorize(request, "bazi:full")
    from tengod.qizheng.qizheng_engine import QizhengEngine
    engine = QizhengEngine()
    return engine.compute(出生时间=req.出生时间, 经度=req.经度, 纬度=req.纬度)

@app.post("/api/advanced/tieban", tags=["高级术数"])
async def tieban(req: TiebanRequest, request: Request):
    """铁板神数"""
    authorize(request, "bazi:full")
    from tengod.tieban import TiebanEngine
    engine = TiebanEngine()
    return engine.compute(八字=req.八字)

@app.post("/api/advanced/shaozi", tags=["高级术数"])
async def shaozi(req: ShaoziRequest, request: Request):
    """邵子神数"""
    authorize(request, "bazi:full")
    from tengod.shaozi import ShaoziEngine
    engine = ShaoziEngine()
    return engine.compute(八字=req.八字, 日期=req.日期)

@app.post("/api/advanced/heluo", tags=["高级术数"])
async def heluo(req: HeluoRequest, request: Request):
    """河洛理数"""
    authorize(request, "bazi:full")
    from tengod.heluo import HeluoEngine
    engine = HeluoEngine()
    return engine.compute(八字=req.八字)

@app.post("/api/advanced/xiaocheng", tags=["高级术数"])
async def xiaocheng(req: XiaochengRequest, request: Request):
    """小成图预测"""
    authorize(request, "bazi:full")
    from tengod.xiaocheng import XiaochengEngine
    engine = XiaochengEngine()
    return engine.predict(问题=req.问题, 日期时间=req.日期时间)
```

---

## 21.6 文件结构

```
tengod/
├── liunian_judgment.py       # [新建] 流年断语引擎 (100+ 模板)
├── fengshui/                 # [新建] 风水模块目录
│   ├── __init__.py
│   ├── xuankong.py          # 玄空飞星引擎
│   ├── yangzhai.py          # 阳宅分析
│   └── yinwhai.py           # 阴宅分析
├── qizheng/                  # [新建] 七政四余目录
│   ├── __init__.py
│   ├── ephemeris.py          # 天文历法计算
│   ├── qizheng_engine.py     # 七政四余排盘
│   └── analysis.py           # 星象分析
├── tieban.py                 # [新建] 铁板神数
├── shaozi.py                 # [新建] 邵子神数
├── heluo.py                  # [新建] 河洛理数
└── xiaocheng.py             # [新建] 小成图预测

data/
├── xuankong_schema.json      # [新建] 玄空飞星数据（九星/运程）
├── tieban_lines.json         # [新建] 铁板神数128条文
└── qizheng_stars.json        # [新建] 七政四余星曜数据

tests/
├── test_liunian_judgment.py # [新建] 流年断语测试
├── test_xuankong.py          # [新建] 玄空飞星测试
├── test_qizheng.py           # [新建] 七政四余测试
└── test_advanced_divination.py  # [新建] 高级术数测试
```

---

## 21.7 测试计划

| 测试类 | 测试数量 | 覆盖内容 |
|--------|---------|---------|
| `TestLiunianJudgment` | 20+ | 喜用神加分/忌神减分/冲合/神煞叠加/十年判断 |
| `TestXuankongEngine` | 15+ | 元旦盘/运盘/山向飞星/流年叠加/健康/财富方位 |
| `TestQizhengEngine` | 20+ | 天文计算精度/七政四余位置/十二宫安法/星曜入宫 |
| `TestTieban` | 8+ | 基数计算/条文推算/条文调整 |
| `TestShaozi` | 8+ | 天符数/地符数/天人数/配合数 |
| `TestHeluo` | 8+ | 河图数/洛书数/组合分析 |
| `TestXiaocheng` | 5+ | 符号生成/解读逻辑 |
| `TestAPI` | 15+ | API 端点集成测试 |

**覆盖率目标：** 核心算法 ≥ 70%，API 端点 ≥ 90%

---

## 21.8 风险评估

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| Swiss Ephemeris 安装失败 | 中 | 高 | 降级为简化牛顿算法，精度可接受 |
| 断语模板库不够全面 | 高 | 中 | 分批扩展（首批50条，后续迭代） |
| 风水排盘准确性争议 | 高 | 低 | 标注为"传统推算，仅供参考" |
| 七政四余算法复杂度过高 | 中 | 中 | 先实现简化版，支持后续迭代 |
| 流年断语生成速度慢 | 低 | 中 | 结果缓存 Redis，TTL=24h |

---

## 21.9 实施顺序

```
第1周：
  □ day1-2: 流年断语核心引擎 (liunian_judgment.py)
  □ day3-4: 断语模板库 50 条 + 测试
  □ day5: API 端点 + 集成测试

第2周：
  □ day1-3: 玄空飞星核心算法 (fengshui/xuankong.py)
  □ day4-5: 阳宅分析 + 测试

第3周：
  □ day1-3: 七政四余天文计算 + 排盘
  □ day4-5: 星象分析 + 测试

第4周：
  □ day1-2: 铁板神数 + 邵子神数
  □ day3-4: 河洛理数 + 小成图
  □ day5: API 端点 + 集成测试

第5-6周：
  □ 全量测试 + Bug 修复
  □ 性能优化（缓存/异步）
  □ 文档完善
```
