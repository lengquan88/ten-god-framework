# 项目加固规格 · 检查清单

## 测试体系
- [ ] tests/ 目录结构创建完成（含 __init__.py 和子目录）
- [ ] conftest.py 提供 mock fixture
- [ ] api_server 测试覆盖 4 个核心端点
- [ ] topo_semantic 测试覆盖 4 个核心算子
- [ ] advanced_spirit_evaluator 测试覆盖评估流程
- [ ] memory_immortal 测试覆盖胶囊/图谱/遗忘曲线
- [ ] deepseek_client 测试覆盖初始化和参数构建
- [ ] `make test` 可运行全部测试

## 自动化脚本
- [ ] Makefile 包含 install  目标
- [ ] Makefile 包含 test     目标（调用 pytest）
- [ ] Makefile 包含 lint     目标（调用 flake8）
- [ ] Makefile 包含 format   目标（调用 black + isort）
- [ ] Makefile 包含 clean    目标
- [ ] Makefile 包含 run-api  目标
- [ ] Makefile 包含 run-console 目标

## 代码重构
- [ ] advanced_spirit_evaluator.py 拆分为子模块
- [ ] 拆分后保持原有导入兼容
- [ ] 重构后 A4 测试全部通过
- [ ] claw_seven_layer_core.py 职责分离
- [ ] 分离后保持原有 API 兼容
- [ ] 重构后已有行为正常

## 整体
- [ ] 所有测试通过（pytest tests/）
- [ ] 代码格式通过（black + isort）
- [ ] 原始 test_*.py 文件未被修改
