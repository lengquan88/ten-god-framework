# 项目加固规格 · 任务清单

> 三大方向：测试体系 · 自动化脚本 · 代码重构

---

## 阶段 A：测试体系（可并行）

- [ ] 任务 A1：创建 tests/ 目录结构和 conftest.py
  - [ ] A1.1 创建 `tests/__init__.py`
  - [ ] A1.2 创建 `tests/conftest.py`（含 mock DEEPSEEK_API_KEY fixture、共享测试数据）
  - [ ] A1.3 创建 `tests/test_api/`、`tests/test_topo/`、`tests/test_memory/` 子目录

- [ ] 任务 A2：编写 api_server 测试
  - [ ] A2.1 测试 /health 健康检查端点
  - [ ] A2.2 测试 /status 系统状态端点
  - [ ] A2.3 测试 /protocols 协议列表端点
  - [ ] A2.4 测试 /process 输入处理端点的请求验证

- [ ] 任务 A3：编写 topo_semantic 核心算子测试
  - [ ] A3.1 测试 TopoSemanticMatcher 初始化与基本匹配
  - [ ] A3.2 测试 PsiSelfReferentialPersistence 自指涉计算
  - [ ] A3.3 测试 ZuowangAttention 坐忘注意力（零向量场景）
  - [ ] A3.4 测试 EmbeddingProvider 三后端选择逻辑

- [ ] 任务 A4：编写 advanced_spirit_evaluator 测试
  - [ ] A4.1 测试 evaluate() 基础评估流程
  - [ ] A4.2 测试空文本/边界输入处理
  - [ ] A4.3 测试神似得分在预期范围内

- [ ] 任务 A5：编写 memory_immortal 测试
  - [ ] A5.1 测试 MemoryCapsule 创建与序列化
  - [ ] A5.2 测试 MasterGraph 添加/检索节点
  - [ ] A5.3 测试 ForgettingCurve 衰减计算

- [ ] 任务 A6：编写 deepseek_client 测试
  - [ ] A6.1 测试客户端初始化（无 API Key 警告）
  - [ ] A6.2 测试请求参数构建（model/messages/temperature）

## 阶段 B：自动化脚本（可并行）

- [ ] 任务 B1：创建 Makefile
  - [ ] B1.1 定义 install / test / lint / format / clean / run-api / run-console 等目标
  - [ ] B1.2 集成调用 pytest、black、isort、flake8

## 阶段 C：代码重构（依赖 A4 测试先写，确保重构可验证）

- [ ] 任务 C1：重构 advanced_spirit_evaluator.py（2468 行）
  - [ ] C1.1 分析并提取意图匹配逻辑到 `spirit_evaluator/intention_matcher.py`
  - [ ] C1.2 分析并提取语义评分逻辑到 `spirit_evaluator/semantic_scorer.py`
  - [ ] C1.3 在 `advanced_spirit_evaluator.py` 中保留兼容导入，确保外部引用不变
  - [ ] C1.4 运行 A4 测试验证重构前后行为一致

- [ ] 任务 C2：重构 claw_seven_layer_core.py（〜2000 行）
  - [ ] C2.1 分析并提取负反馈检测层到独立模块
  - [ ] C2.2 分析并提取反事实沙箱层到独立模块
  - [ ] C2.3 在 `claw_seven_layer_core.py` 中保留兼容导入
  - [ ] C2.4 运行已有测试验证重构前后行为一致

# 任务依赖关系
- [A2/A3/A5/A6] 依赖 [A1]（需要 conftest.py）
- [A4] 依赖 [A1]
- [C1] 依赖 [A4]（先写测试，确保重构可验证）
- [C2] 依赖 [C1]（类似模式）
- [B1] 无依赖，可随时并行
