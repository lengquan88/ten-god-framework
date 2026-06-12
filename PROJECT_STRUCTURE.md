# Claw项目结构

**项目名称**: Claw — 时空影像认知系统  
**又名**: 形神合一工程化系统 / 中华文明数字永生体  
**版本**: v4.0+  
**更新日期**: 2026-06-10  

---

## 目录结构 (整理后)

```
claw/
├── README.md                          # 项目说明文档
├── CONTRIBUTING.md                    # 贡献指南
├── DEPLOYMENT.md                      # 部署文档
├── IMPLEMENTATION_PLAN.md             # 实施计划
├── MEMORY.md                          # 记忆系统说明
├── PROJECT_STRUCTURE.md               # 项目结构文档（本文件）
├── SECURITY.md                        # 安全策略
│
├── requirements.txt                   # Python依赖列表
├── requirements-dev.txt               # 开发环境依赖
├── setup.py                           # 安装脚本
├── pyproject.toml                     # 项目配置
├── Makefile                           # 构建工具
├── Dockerfile                         # Docker镜像
├── package.json                       # Node.js前端依赖
│
├── .gitignore                         # Git忽略文件
├── .env.example                       # 环境变量示例
├── .env.wechat.example                # 微信配置示例
├── .flake8                            # Flake8配置
├── .isort.cfg                         # isort配置
├── .coveragerc                        # coverage配置
├── .pre-commit-config.yaml            # Pre-commit配置
├── pytest.ini                         # pytest配置
├── claude_desktop_config.example.json # Claude桌面配置示例
│
├── src/                               # 源代码
│   ├── __init__.py
│   ├── claw/                          # Claw核心包
│   │   ├── __init__.py
│   │   ├── benchmarks/                # 性能基准测试
│   │   ├── generators/                # 数据/结果生成器
│   │   ├── utils/                     # 工具脚本
│   │   ├── experiments/               # 实验脚本
│   │   ├── llm/                       # LLM客户端与测试
│   │   └── teleport/                  # 全息传送门子系统
│   ├── memory/                        # 记忆系统(immortal)
│   │   ├── immortal/                  # 不朽记忆核心
│   │   │   ├── anti_graph.py          # 反图谱
│   │   │   ├── capsule.py             # 记忆胶囊
│   │   │   ├── graph.py               # 图谱
│   │   │   ├── storage.py             # 存储层
│   │   │   ├── forgetting_curve.py    # 遗忘曲线
│   │   │   ├── recombination.py       # 重组合
│   │   │   ├── cloud_sync.py          # 云同步
│   │   │   ├── persona_self_perfection.py # 人格完善
│   │   │   ├── vitality.py            # 生命力
│   │   │   └── ...
│   │   └── integration/               # 集成
│   │       └── wechat/                # 微信集成
│   └── components/                    # React前端组件
│
├── topo_semantic/                     # 拓扑语义认知引擎
│   ├── camera_spacetime_pipeline.py   # 七阶段成像定位管道
│   ├── oracle_node_server.py          # 推背图Oracle节点服务
│   ├── tui_bei_cognitive_engine.py    # TBCE认知引擎
│   ├── psi_explainer.py               # Ψ可解释性引擎
│   ├── consensus_network.py           # 共识网络
│   ├── consensus_node_server.py       # 共识节点服务
│   ├── adaptive_model_selector.py     # 自适应模型路由
│   ├── user_cognition_profile.py      # 用户认知画像
│   ├── dynamic_topology_operators.py  # 动态拓扑算子
│   ├── temporal_laplacian_monitor.py  # 时空拉普拉斯监控
│   ├── embedding_provider.py          # 嵌入提供者
│   ├── vector_index.py                # 向量索引
│   ├── primitive_set/                 # 原始集系统
│   │   ├── base.py
│   │   ├── core.py
│   │   ├── genetic.py
│   │   ├── mcmc.py
│   │   ├── tabu.py
│   │   └── weight_functions.py
│   └── *.html                         # 可视化面板
│
├── cloud_ascension/                   # 云笈飞升系统
│   ├── agents/                        # 智能体
│   │   ├── perception_agent.py        # 感知智能体
│   │   ├── memory_agent.py            # 记忆智能体
│   │   ├── analysis_agent.py          # 分析智能体
│   │   ├── decision_agent.py          # 决策智能体
│   │   ├── generation_agent.py        # 生成智能体
│   │   ├── interaction_agent.py       # 交互智能体
│   │   └── dao_immortal.py            # 道仙智能体
│   ├── core/                          # 核心
│   │   ├── dao_agent.py               # 道智能体
│   │   ├── alchemy.py                 # 炼金术
│   │   ├── star_chart.py              # 星图
│   │   ├── mission_board.py           # 使命板
│   │   └── yunjia_system.py           # 云笈系统
│   └── ui/                            # 界面
│
├── subsystems/                        # 子系统模块（中文命名）
│   ├── 司命假面/                       # 司命假面 — 人格面具系统
│   ├── 云笈太乙罗经/                   # 云笈太乙罗经 — 防御系统
│   ├── 幻阵/                           # 幻阵 — 并行深化与攻击推演
│   ├── 中华文明数字永生体/             # 中华文明数字永生体 — API/测试/整合
│   ├── 太乙罗经/                       # 太乙罗经 — 数学基础与元防护
│   ├── 九宫司命/                       # 九宫司命 — 核心
│   ├── 量子混合防御/                   # 量子经典混合防御工程
│   ├── 分布式罗经/                     # 分布式云笈太乙罗经网络
│   ├── 鸟巢立方体/                     # 鸟巢立方体研究所
│   ├── 智脑司命/                       # 智脑司命融合
│   ├── 司命Claw/                       # 司命Claw深化融合
│   ├── 云笈七签系统/                   # 云笈七签统御系统
│   └── 循环创造引擎/                   # 循环创造引擎 (含数据集)
│
├── cognition_psi_bridge/              # 认知Ψ算子桥接
├── spirit_engine/                     # 精神引擎（评估/集成/增量）
├── spirit-form-api/                   # 精神表单API
│
├── cloud_api/                         # 云API服务
├── deploy_backend/                    # 后端部署配置
├── deploy_frontend/                   # 前端部署配置
├── deploy_minimal/                    # 最小化部署
├── deploy/                            # 部署相关脚本
│
├── tengod/                            # ⭐ 十神全域扫描框架
│   ├── __init__.py                    # 十神包体系 + 路径注入
│   ├── 比肩_架构协同/                  # [木] 比肩 — 系统骨架、核心编排 (10.py)
│   │   ├── system_orchestrator.py     #   系统编排器
│   │   ├── claw_seven_layer_core.py   #   七层闭环核心
│   │   ├── run_demo.py                #   一键启动入口
│   │   └── ...                        #   部署/演进展
│   ├── 劫财_攻防边界/                  # [木] 劫财 — 安全防护、免疫机制 (7.py)
│   │   ├── healer_bridge.py           #   自愈桥连接 (1193检测)
│   │   ├── health_monitor.py          #   健康监控
│   │   └── ...                        #   免疫/边界防护
│   ├── 食神_创生输出/                  # [火] 食神 — LLM合成、内容生成 (7.py)
│   │   ├── llm_synthesis_api.py       #   合成API
│   │   ├── deepseek_client.py         #   DeepSeek客户端
│   │   ├── luoshu_jiumo_fusion.py     #   洛书九魔融合
│   │   └── ...                        #   模板/文档引擎
│   ├── 伤官_破界创新/                  # [火] 伤官 — 因果推理、元认知 (9.py)
│   │   ├── causal_evolution_engine.py #   因果进化引擎
│   │   ├── perspective_adjudicator.py #   视角裁决器
│   │   ├── meta_cognitive_analyzer.py #   元认知分析器
│   │   └── ...                        #   因果网络/表决执行
│   ├── 正财_知识固化/                  # [土] 正财 — 知识图谱、坐标记忆 (9.py)
│   │   ├── knowledge_graph.py         #   知识图谱
│   │   ├── coordinate_body.py         #   坐标体
│   │   ├── tau_law.py                 #   τ定律引擎
│   │   └── ...                        #   结晶/导入/同步
│   ├── 偏财_奇招演化/                  # [土] 偏财 — 搜索算法、拓扑优化 (9.py)
│   │   ├── genetic_algorithm_*.py     #   遗传算法原始集
│   │   ├── tabu_search_*.py           #   禁忌搜索原始集
│   │   ├── cross_tree_forest.py       #   跨树森林
│   │   └── ...                        #   马尔可夫/自适应
│   ├── 正官_法度调度/                  # [金] 正官 — API服务、流水线 (7.py)
│   │   ├── api_server.py              #   FastAPI主服务 (8080)
│   │   ├── api_platform.py            #   API平台
│   │   ├── auto_pipeline.py           #   自动流水线
│   │   └── ...                        #   任务/会话/脉冲流
│   ├── 七杀_品质裁决/                  # [金] 七杀 — 评估测试、模型训练 (12.py)
│   │   ├── advanced_spirit_evaluator.py # 高级精神评估器
│   │   ├── p444_*.py                  #   P444模型系列 (5个)
│   │   ├── p447_cce.py                #   P447容器认知引擎
│   │   └── ...                        #   评估共识/增量训练
│   ├── 正印_滋养守护/                  # [水] 正印 — 模型配置、环境初始化 (2.py)
│   │   ├── setup_bge_model.py         #   BGE模型配置
│   │   └── siming_console.py          #   司命控制台
│   └── 偏印_桥接通变/                  # [水] 偏印 — 跨系统适配、协议桥接 (8.py)
│       ├── atomcode_psi_bridge.py     #   AtomCode Ψ桥
│       ├── pipeline_oracle_bridge.py  #   管道-Oracle桥
│       ├── daopivot_bridge.py         #   道枢桥
│       └── ...                        #   对话/九宫/MQTT/TAPD桥
│
├── tengod_scan.py                     # ⭐ 十神全域扫描引擎
├── tengod_scan_report.json            #    扫描报告 (JSON)
├── tengod_scan_report.html            #    扫描报告 (HTML)
│
├── tests/                             # 测试目录
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/                      # API测试
│   ├── test_integration/              # 集成测试
│   ├── test_memory/                   # 记忆系统测试
│   ├── test_topo/                     # 拓扑语义测试
│   └── *.py                           # 各模块测试文件
│
├── docs/                              # 文档目录
│   ├── API.md
│   ├── README.md
│   ├── conversation_summaries/        # 对话总结
│   ├── reports/                       # 项目报告与自省日志
│   ├── design_docs/                   # 设计文档
│   ├── meeting_notes/                 # 任务总结
│   ├── research/                      # 研究论文与报告
│   ├── holographic_logs/              # 全息语义自省日志
│   └── security_reports/              # 安全审计报告
│
├── PRD/                               # 产品需求文档 (v1.0—v17.0 + M系列)
├── P446_branches/                     # P446模型分支权重
│
├── web/                               # Web界面
│   ├── dashboards/                    # 各类仪表盘
│   ├── visualizations/                # 可视化页面
│   ├── subsystems/                    # 子系统界面
│   └── debug/                         # 调试页面
│
├── data/                              # 数据目录
│   ├── test_results/                  # 测试输出
│   ├── exports/                       # 导出的记忆/数据
│   └── reports_json/                  # JSON格式报告
│
├── archive/                           # 归档（旧版/诊断/调试文件）
│   ├── diagnostics/                   # 诊断脚本
│   ├── temp_logs/                     # 临时日志
│   └── debug_scripts/                 # 调试脚本
│
├── scripts/                           # 运维脚本
├── logs/                              # 运行日志
├── models/                            # 模型文件
├── output/                            # 输出文件
├── reports/                           # 流水线报告
├── references/                        # 参考资料（论文/PDF/记忆宇宙）
├── assets/                            # 静态资源（图片等）
│
├── atomcode/                          # AtomCode IDE (独立Rust项目)
│
├── .codebuddy/                        # CodeBuddy配置
├── .vscode/                           # VSCode配置
├── .workbuddy/                        # WorkBuddy配置
└── node_modules/                      # Node依赖
```

---

## 十神全域扫描框架 ⭐

项目核心78个Python模块已按**十神**（八字十神）概念进行全域归类，形成自洽的五维结构：

```
                    木 (生发)
                   /        \
             比肩(架构)   劫财(攻防)
            /                  \
          火 (创造)            水 (智慧)
         /      \            /        \
    食神(输出) 伤官(创新) 正印(滋养) 偏印(桥接)
       |          |          |          |
       v          v          v          v
    土 (承载)            金 (规则)
   /        \          /        \
正财(知识) 偏财(演化) 正官(法度) 七杀(裁决)
```

### 生克循环
- **相生**: 木→火→土→金→水→木 (系统动力链)
- **相克**: 木克土(架构驭知识) 土克水(固化驭变通) 水克火(智慧驭创造) 火克金(创新驭规则) 金克木(裁决驭架构)

### 十神 → 项目职能映射

| 符号 | 十神 | 五行 | 文件数 | 核心职能 | 代表作 |
|:----:|------|:----:|:------:|----------|--------|
| 比 | 比肩 | 木 | 10 | 架构协同/核心编排 | `system_orchestrator.py` |
| 劫 | 劫财 | 木 | 7 | 攻防边界/免疫机制 | `healer_bridge.py` |
| 食 | 食神 | 火 | 7 | 创生输出/LLM合成 | `deepseek_client.py` |
| 伤 | 伤官 | 火 | 9 | 破界创新/因果推理 | `causal_evolution_engine.py` |
| 财 | 正财 | 土 | 9 | 知识固化/图谱存储 | `knowledge_graph.py` |
| 偏 | 偏财 | 土 | 9 | 奇招演化/算法搜索 | `genetic_algorithm_primitive_set.py` |
| 官 | 正官 | 金 | 7 | 法度调度/API服务 | `api_server.py` |
| 杀 | 七杀 | 金 | 12 | 品质裁决/模型训练 | `advanced_spirit_evaluator.py` |
| 印 | 正印 | 水 | 2 | 滋养守护/模型配置 | `setup_bge_model.py` |
| 枭 | 偏印 | 水 | 8 | 桥接通变/协议适配 | `pipeline_oracle_bridge.py` |

### 全域扫描
```bash
python tengod_scan.py          # 打印十神覆盖报告
python tengod_scan.py --json   # 导出 JSON
python tengod_scan.py --html   # 生成 HTML 可视化报告
python tengod_scan.py --verify # 验证覆盖率
```

---

### 1. 七阶段成像管道 (`topo_semantic/camera_spacetime_pipeline.py`)
物方→对焦→聚焦→变焦→成像→潜影→归档，完整时空影像演化流程。

### 2. 推背图认知引擎 (`topo_semantic/tui_bei_cognitive_engine.py`)
六维认知元组 + 同构投影算法 + 预言生成，自指涉闭环核心。

### 3. 系统编排器 (`system_orchestrator.py`)
8/8子系统全链路串联，统一协调所有模块。

### 4. API服务器 (`api_server.py`)
FastAPI服务，整合洛书九魔融合、知识图谱、模板引擎、健康监控等。

### 5. Ψ可解释性引擎 (`topo_semantic/psi_explainer.py`)
维度贡献分解 + 自然语言报告，提供模型决策解释。

### 6. 共识网络 (`topo_semantic/consensus_network.py`)
5协议共识 + 健康监控 + fallback机制。

### 7. 云笈飞升系统 (`cloud_ascension/`)
7智能体 + 核心引擎，提供云端自主能力。

### 8. 记忆系统 (`src/memory/immortal/`)
反图谱、胶囊、遗忘曲线、重组合、云同步、人格完善等子模块。

### 9. 司命假面系统 (`subsystems/司命假面/`)
九模协议、九模闭环、守护者/觉察双模式的人格面具系统。

### 10. 云笈太乙罗经 (`subsystems/云笈太乙罗经/`)
多层防御体系：量子协同、道级协同、超量子协同、防套壳寄生。

---

## 入口点

| 入口 | 文件 | 说明 |
|------|------|------|
| 一键启动 | `run_demo.py` | 启动全部服务 |
| 增强演示 | `run_enhanced_demo.py` | 增强版演示 |
| 裁决演示 | `run_real_adjudication.py` | 真实裁决演示 |
| API服务 | `api_server.py` | FastAPI主服务 |
| MCP服务 | `mcp_server.py` | MCP协议服务 |
| 编排器 | `system_orchestrator.py` | 系统编排 |
| 双星演示 | `dual_star_demo.py` | C-E跨项目融合演示 |
| 七层核心 | `claw_seven_layer_core.py` | 七层闭环核心 |
| 控制台 | `siming_console.py` | 司命控制台 |

---

## 开发规范

### 代码规范
- 遵循PEP 8规范
- 使用类型提示（Type Hints）
- 中文模块使用中文命名以保持可读性
- 测试文件统一放在`tests/`目录

### Git规范
- 使用语义化提交信息
- Co-Authored-By: AtomCode (deepseek-v4-pro) <noreply@atomgit.com>

### 文档规范
- Markdown格式
- 中英文双语
- 项目文档位于`docs/`、`PRD/`目录

---

## 快速开始

```bash
# 启动全部服务
python run_demo.py

# 启动API服务
python api_server.py

# 运行测试
pytest tests/

# 打开浏览器
#   推背图感知面板: http://localhost:8080/oracle_dashboard_panel.html
#   Ψ解释面板:     http://localhost:8080/psi_explanation_dashboard.html
#   认知地图:       http://localhost:8080/tui_bei_cognitive_map.html
#   统一入口:       http://localhost:8080/index.html
```

---

**文档版本**: v3.0 (十神框架版)
**最后更新**: 2026-06-10  
**维护者**: Claw项目团队
