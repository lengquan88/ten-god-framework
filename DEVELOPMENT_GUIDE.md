# DemoApp 开发指南

> 十神架构开发规范与快速上手手册
> v1.0 — 2026-06-12

## 🎯 项目概览

DemoApp 是基于**十神架构**的 Python 项目，每个业务子模块映射为"十神"之一：

| 十神 | 职责 | 典型应用 |
|------|------|----------|
| **比肩** | 架构协同 | 核心编排、组件注册 |
| **劫财** | 攻防边界 | 权限校验、安全防护 |
| **食神** | 创生输出 | 内容生成、LLM 集成 |
| **伤官** | 破界创新 | 算法调优、因果推理 |
| **正财** | 知识固化 | 数据存储、知识图谱 |
| **偏财** | 奇招演化 | 搜索优化、超参调参 |
| **正官** | 法度调度 | 任务调度、API 路由 |
| **七杀** | 品质裁决 | 质量评估、测试运行 |
| **正印** | 滋养守护 | 配置管理、环境初始化 |
| **偏印** | 桥接通变 | 协议适配、格式转换 |

## 📁 目录结构

```
demo_project/
├── tengod/                          # 十神子包
│   ├── 比肩_架构协同/
│   ├── 劫财_攻防边界/
│   ├── 食神_创生输出/
│   ├── 伤官_破界创新/
│   ├── 正财_知识固化/
│   ├── 偏财_奇招演化/
│   ├── 正官_法度调度/
│   ├── 七杀_品质裁决/
│   ├── 正印_滋养守护/
│   ├── 偏印_桥接通变/
│   ├── core.py                      # 核心调度器
│   └── __init__.py                  # 包入口
├── tests/                           # 单元测试
│   ├── test_tengod.py               # 子模块测试
│   ├── test_core.py                 # 核心调度器测试
│   └── test_auth.py                 # 鉴权测试
├── tengod_scan.py                   # 全域扫描工具
├── init_tengod.py                   # 初始化脚本
└── README.md
```

## 🚀 快速开始

### 1. 一键使用核心

```python
import sys
sys.path.insert(0, '/path/to/demo_project')

from tengod import get_core

core = get_core()

# 质量裁决
report = core.evaluate(
    {"功能完整性": 85, "代码质量": 92, "测试覆盖率": 75},
    weights={"功能完整性": 0.4, "代码质量": 0.4, "测试覆盖率": 0.2},
)
print(f"等级: {report['grade']}, 总分: {report['total']}")

# 创新思维
core.innovate("combine", "AI", "区块链", "IoT")
core.innovate("transfer", "游戏化", "教育")
core.innovate("reverse", "用户点击越多越好")

# 内容生成
md = core.generate("项目进展报告", format="markdown")
json_data = core.generate("配置", format="json")

# 超参搜索
best = core.search(
    {"lr": [0.001, 0.01, 0.1], "batch": [16, 32, 64]},
    objective=lambda p: -((p["lr"] - 0.01) ** 2),
    n_trials=30,
)

# 批量任务调度
def my_task(): return 42
core.schedule_and_run({"task-1": my_task, "task-2": my_task})

# 导出完整状态
state = core.export_state()
```

### 2. 单独使用子模块

每个子包都暴露简洁的 API：

```python
from tengod.比肩_架构协同 import component, get_registry
from tengod.正官_法度调度 import TaskScheduler, TaskPriority
from tengod.七杀_品质裁决 import QualityJudge, Grade
```

详见各子包下的 `README.md`。

## 🧪 运行测试

```bash
# 运行所有十神子模块测试
python tests/test_tengod.py

# 运行核心调度器测试
python tests/test_core.py

# 全域扫描
python tengod_scan.py
```

预期结果：
- `test_tengod.py`: 12/12 通过
- `test_core.py`: 6/6 通过

## 📊 全域扫描

```bash
python tengod_scan.py
# 输出：
# === 十神全域扫描报告 ===
# 扫描时间: 2026-06-12T...
# 项目文件: 9 个 .py 文件, 674 行代码
# 十神归类: 8/9 已归类 (88.9%)
# ...
```

## 🛠️ 添加新的十神子模块

### 步骤 1：创建子包目录

```bash
mkdir demo_project/tengod/新十神_职责描述
```

### 步骤 2：实现核心文件

```python
# demo_project/tengod/新十神_职责描述/__init__.py
from .core_module import MainClass

__all__ = ["MainClass"]
__version__ = "1.0.0"
```

### 步骤 3：注册到 core.py

在 `demo_project/tengod/core.py` 中：

```python
_new = _safe_import("新十神_职责描述")
self.new_module = _new.MainClass() if _new else None
```

### 步骤 4：编写测试

```python
# tests/test_tengod.py
def test_new_god():
    from 新十神_职责描述 import MainClass
    obj = MainClass()
    assert obj is not None
```

### 步骤 5：更新 GODS 字典

在 `tengod_scan.py` 的 `GODS_RAW` 中添加新十神的关键词。

## 📐 开发规范

1. **中文路径子包**：每个十神子包都使用 `十神名_职责描述` 格式命名
2. **每个子包至少一个 README.md**：说明模块职责与使用方式
3. **每个子包有单元测试**：通过 `tests/test_*.py` 验证
4. **统一导入路径**：所有子包通过 `tengod.<子包名>` 访问
5. **懒加载机制**：使用 `_safe_import` 而非顶层 import，便于降级

## 🔧 进阶工具

未来可从 [Claw 项目](https://github.com/your-org/claw) 复制以下进阶引擎：

| 工具 | 职责 |
|------|------|
| `tengod_omni_map.py` | 全知地图（系统依赖可视化） |
| `tengod_auto_healer.py` | 自愈引擎（异常自恢复） |
| `fix_all_chains.py` | 一键修复（链式问题处理） |
| `shenke_daemon.py` | 守护进程（持续监控） |
| `shenke_optimizer.py` | 优化智能体（自调优） |
| `tengod_causal.py` | 因果历史（回溯分析） |
| `tengod_doctrine.py` | 道标系统（系统规约） |

## 📝 版本

- v1.0.0 (2026-06-12) — 完整十神子模块 + 核心调度器

## 📜 许可证

MIT License
