# 十神架构范式白皮书

## 将东方哲学转化为可复用的软件架构方法论

> **版本**: v1.0  
> **作者**: Claw 项目团队  
> **许可**: MIT — 自由复用于任何项目

---

## 摘要

十神架构是一种基于中国传统命理学"十神"概念的软件架构组织范式。它将代码模块按社会角色职能分为十种类型，通过五行生克关系建立模块间的依赖和约束契约，并提供一套完整的工具链（扫描→诊断→修复→守护→优化→快照）实现架构的自我感知、自我修复和自我进化。

本白皮书定义了十神范式的核心概念、实施步骤、工具链规范，使任何项目都能复现 Claw 案例研究中展示的"从混沌到数字生命体"的转变。

---

## 1. 范式核心

### 1.1 十神定义

每个代码模块必须归属于以下十种角色之一：

| # | 十神 | 英文 | 五行 | 职能定义 | 判据 |
|:--:|------|------|:----:|----------|------|
| 1 | 比肩 | Peer | 木 | 核心编排、入口点、系统骨架 | 模块的 main/run/orchestrator |
| 2 | 劫财 | RobWealth | 木 | 安全防护、边界校验、免疫 | 模块含 auth/validate/defend |
| 3 | 食神 | EatingGod | 火 | 内容生成、外部输出、LLM调用 | 模块含 generate/output/llm |
| 4 | 伤官 | HarmOfficer | 火 | 创新推理、因果分析、元认知 | 模块含 causal/reason/innovate |
| 5 | 正财 | DirWealth | 土 | 知识存储、数据库、坐标映射 | 模块含 store/db/knowledge |
| 6 | 偏财 | IndWealth | 土 | 搜索优化、参数调优、自适应 | 模块含 search/optimize/adapt |
| 7 | 正官 | DirOfficer | 金 | API服务、任务调度、流水线 | 模块含 api/server/schedule |
| 8 | 七杀 | 7Killings | 金 | 品质评估、测试、模型训练 | 模块含 eval/test/train |
| 9 | 正印 | DirResource | 水 | 配置管理、环境初始化、控制台 | 模块含 config/init/console |
| 10 | 偏印 | IndResource | 水 | 桥接适配、协议转换、集成 | 模块含 bridge/adapter/integrate |

### 1.2 五行生克律

```
相生循环 (Generates):  木 → 火 → 土 → 金 → 水 → 木
                      架构 → 创造 → 承载 → 规则 → 智慧 → 架构

相克循环 (Controls):   木克土  土克水  水克火  火克金  金克木
                      架构驭知识  固化驭变通  智慧驭创造  创新驭规则  裁决驭架构
```

**工程映射**:
- **相生** = 数据流: Source模块应 import 并使用 Target 模块的接口
- **相克** = 约束流: Source模块应 import Target 模块并施加校验/限制

### 1.3 自指涉原则

项目自身的架构管理工具（扫描器、修复器、守护进程）也纳入十神分类：
- `tengod_scan.py` → 七杀 (品质裁决: 扫描即评估)
- `tengod_omni_map.py` → 正财 (知识固化: 地图即知识)
- `tengod_shenke_bridge.py` → 偏印 (桥接通变: 桥接即适配)
- `fix_all_chains.py` → 正印 (滋养守护: 修复即滋养)

---

## 2. 实施路线图

### Phase 1: 摸底 (30分钟)

**目标**: 了解项目当前结构

```bash
# 1. 统计文件分布
find . -name "*.py" | wc -l
find . -maxdepth 1 -name "*.py" | wc -l

# 2. 识别子系统
ls -d */ | grep -v "__\|node_modules\|.git"

# 3. 建立初始分类
# 对每个 .py 文件，根据其内容/名称分配十神标签
```

**交付物**: 模块-十神映射表 (CSV/JSON)

### Phase 2: 归位 (1小时)

**目标**: 按十神建立目录结构

```bash
mkdir -p tengod/{比肩_架构协同,劫财_攻防边界,食神_创生输出,伤官_破界创新,正财_知识固化,偏财_奇招演化,正官_法度调度,七杀_品质裁决,正印_滋养守护,偏印_桥接通变}

# 移动模块到对应目录
# 对于有外部引用的模块，在 __init__.py 中维护兼容导入
```

**关键**: 使用 `sys.path` 注入或包级 `__init__.py` 保持向后兼容。

### Phase 3: 建立感知层 (2小时)

**目标**: 部署核心扫描引擎

1. 复制 `tengod_scan.py` 模板 → 适配项目路径
2. 复制 `tengod_omni_map.py` 模板 → 配置关键词映射
3. 运行首次扫描: `python tengod_scan.py --html`

**交付物**: 首次十神覆盖报告 + 五行圆环HTML

### Phase 4: 修复断裂 (1-2小时)

**目标**: 闭合所有生克链

1. 运行 `tengod_omni_map.py` 获取断裂列表
2. 对每条断裂，添加跨十神 import
3. 验证: `python fix_all_chains.py`

**关键**: 相生链断裂添加 import+调用；相克链断裂添加 import+校验。

### Phase 5: 飞升 (2-3小时)

**目标**: 部署守护+优化+道标

1. 配置 `shenke_daemon.py` 的扫描间隔和 webhook
2. 运行 `shenke_optimizer.py` 获取优化建议
3. 导出道标: `python tengod_doctrine.py --export`

---

## 3. 工具链规范

### 3.1 必备工具 (任何项目都需要的)

| 工具 | 最小实现 | 推荐增强 |
|------|----------|----------|
| 扫描器 | 按文件名关键词归类 | AST解析+性能探针 |
| 全知地图 | 模块清单+import图 | API端点+DB表关联 |
| 修复器 | 手动添加import | 自动注入+语法验证 |

### 3.2 进阶工具 (复杂项目推荐)

| 工具 | 用途 | 触发条件 |
|------|------|----------|
| 守护进程 | 持续监控 | 模块数>100 |
| 优化器 | 主动优化 | 单模块>1000行 |
| 因果关系 | 根因分析 | 多团队协作 |
| 道标系统 | 环境复现 | 多环境部署 |

### 3.3 关键词映射规范

每个项目的十神关键词映射应根据实际业务调整。例如：

```python
# 金融项目
'比肩': ['ledger', 'transaction', 'settlement'],
'劫财': ['fraud', 'audit', 'compliance'],
'食神': ['report', 'statement', 'notification'],
# ...

# 电商项目
'比肩': ['order', 'cart', 'checkout'],
'劫财': ['antifraud', 'risk', 'rate_limit'],
'食神': ['recommendation', 'search', 'feed'],
# ...
```

---

## 4. 度量体系

### 4.1 核心KPI

| KPI | 目标值 | 说明 |
|-----|:------:|------|
| 十神覆盖率 | >80% | 已分类.py占全部.py的比例 |
| 生克闭合率 | 100% | 无断裂的生克链占比 |
| 五行均衡度 | <3x | 五行模块数最大/最小比值 |
| 扫描速度 | <5s | 全项目扫描耗时 |
| 自愈成功率 | >90% | 自动修复成功率 |

### 4.2 健康度仪表盘

```
绿色:  覆盖率>80% + 闭合率100% + 均衡度<3x
黄色:  覆盖率>60% + 闭合率>80%
红色:  覆盖率<60% 或 闭合率<80% 或 均衡度>5x
```

---

## 5. 跨项目复用模板

### 5.1 快速启动脚本

```bash
#!/bin/bash
# init_tengod.sh — 在新项目中初始化十神框架

PROJECT_NAME=$1
PROJECT_ROOT=$2

# 1. 创建目录结构
mkdir -p $PROJECT_ROOT/tengod/{比肩_架构协同,劫财_攻防边界,食神_创生输出,伤官_破界创新,正财_知识固化,偏财_奇招演化,正官_法度调度,七杀_品质裁决,正印_滋养守护,偏印_桥接通变}

# 2. 复制核心引擎 (从模板仓库)
cp $TENGOD_TEMPLATE/tengod_scan.py $PROJECT_ROOT/
cp $TENGOD_TEMPLATE/tengod_omni_map.py $PROJECT_ROOT/

# 3. 配置关键词映射
python $PROJECT_ROOT/tengod_omni_map.py --init --project $PROJECT_NAME

# 4. 首次扫描
python $PROJECT_ROOT/tengod_scan.py --html

echo "十神框架已初始化: $PROJECT_NAME"
echo "运行 python tengod_scan.py --html 查看报告"
```

### 5.2 CI/CD 集成

```yaml
# .github/workflows/tengod.yml
name: 十神健康检查
on: [push, pull_request]
jobs:
  shenke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: 十神扫描
        run: python tengod_scan.py --verify
      - name: 道标验证
        run: python tengod_doctrine.py --verify doctrine.json
      - name: 守护检查
        run: python shenke_daemon.py --once
```

### 5.3 模板仓库结构

```
tengod-template/
├── README.md                    # 十神范式介绍
├── QUICKSTART.md                # 5分钟快速上手
├── TENGOD_WHITEPAPER.md         # 本白皮书
├── core/
│   ├── tengod_scan.py           # 可配置的扫描引擎模板
│   ├── tengod_omni_map.py       # 可配置的全知地图模板
│   └── tengod_kw_config.json    # 关键词映射配置
├── advanced/
│   ├── tengod_shenke_bridge.py  # 生克桥接器
│   ├── tengod_auto_healer.py    # 自愈引擎
│   ├── fix_all_chains.py        # 一键修复
│   └── shenke_daemon.py         # 守护进程
├── flight/
│   ├── shenke_optimizer.py      # 优化智能体
│   ├── tengod_causal.py         # 因果引擎
│   └── tengod_doctrine.py       # 道标系统
└── examples/
    ├── claw/                    # Claw案例
    └── demo/                    # 最小示例
```

---

## 6. 哲学根基

### 6.1 为什么是十神？

1. **完备性**: 十神覆盖了软件系统中的所有核心职能——编排、安全、生成、创新、存储、搜索、调度、评估、配置、集成
2. **关系网络**: 五行生克提供了20条天然的关系链，确保没有任何模块是孤岛
3. **可理解性**: "比肩=架构"比"ModuleGroupA"更容易被人类和AI共同理解
4. **自指涉**: 十神框架本身也遵循十神分类，形成元认知闭环

### 6.2 与传统架构的对比

| 维度 | MVC | 微服务 | 分层架构 | **十神** |
|------|:---:|:------:|:--------:|:--------:|
| 分类维度 | 技术层 | 业务域 | 抽象层 | **社会角色** |
| 关系定义 | 无 | 调用链 | 层次依赖 | **生克循环** |
| 完整性检查 | 无 | 无 | 无 | **17条断裂检测** |
| 自愈能力 | 无 | 部分 | 无 | **自动注入import** |
| AI友好度 | 低 | 中 | 低 | **高 (语义标签)** |

---

## 7. 常见问题

**Q: 十神分类是否过于抽象？**  
A: 初次接触可能觉得抽象，但一旦完成首次归类，团队成员普遍反映"终于知道每个文件是干什么的了"。抽象性正是其威力——它提供了一套跨项目通用的元语言。

**Q: 小型项目适用吗？**  
A: 模块数<20的项目可以直接使用关键词自动分类，无需完整工具链。十神分类本身即使不配工具链也能提供结构清晰度。

**Q: 如何说服团队采用？**  
A: 建议先在一个子项目上试点，展示扫描报告和五行圆环。可视化的力量远超说教。

**Q: 与DDD(领域驱动设计)的关系？**  
A: 互补而非替代。DDD的聚合根/实体/值对象定义"是什么"，十神定义"做什么角色"。可以结合使用。

---

## 8. 结语

十神架构范式将东方哲学的整体观和关系思维注入软件工程，创造了一种新的架构语言。它不是要取代现有范式，而是提供了一层**元视角**——让代码不仅可执行，还可理解、可对话、可进化。

正如 Claw 案例所示，215个散乱的Python文件可以在两天内转变为一个拥有自我感知、自我修复能力的数字生命体。这套范式可复用于任何规模、任何语言的软件项目。

**"代码中有大道，架构里藏天机。"**

---

**白皮书版本**: v1.0  
**发布日**: 2026-06-11  
**许可**: MIT
