# 七杀 · 品质裁决

> 十神之一，主理裁决、测试与质量监控。
> 承担系统输出的品质裁定与测试评估职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `quality_judge.py` | 多维度加权评分，支持 S/A/B/C/D 五级评定 |
| `test_runner.py` | 轻量级测试运行器，输出汇总报告 |
| `__init__.py` | 模块导出 |

## 快速开始

### 质量裁决

```python
from tengod.七杀_品质裁决 import QualityJudge

judge = QualityJudge()
judge.add_score("功能完整性", 85, weight=0.4)
judge.add_score("代码质量", 92, weight=0.3)
judge.add_score("测试覆盖率", 75, weight=0.2)
judge.add_score("文档完善度", 80, weight=0.1)

print(f"总分: {judge.total_weighted()}")
print(f"等级: {judge.grade().value}")
print(judge.report())
```

### 测试运行

```python
from tengod.七杀_品质裁决 import TestRunner

runner = TestRunner()

def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 5 - 3 == 2

runner.add_case("addition", test_addition)
runner.add_case("subtraction", test_subtraction)
runner.run()
print(runner.summary())
```

## 核心特性

- **多维评分**：支持加权评分与五级评定（S/A/B/C/D）
- **轻量测试**：无外部依赖的测试运行器
- **详细报告**：自动汇总通过率、耗时、错误信息
- **可扩展性**：易于集成到 CI/CD 流程
