# 偏财 · 奇招演化

> 十神之一，主理演化、奇招与算法调优。
> 承担系统的搜索优化与超参数调参职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `search_optimizer.py` | 搜索优化器，支持随机搜索与网格搜索 |

## 快速开始

```python
from tengod.偏财_奇招演化 import SearchOptimizer, SearchSpace

# 定义搜索空间
space = SearchSpace({
    "learning_rate": [0.001, 0.01, 0.1],
    "batch_size": [16, 32, 64],
    "dropout": (0.1, 0.5),  # 浮点范围
})

# 定义目标函数
def objective(params):
    # 模拟评估
    return -(params["learning_rate"] - 0.01) ** 2

# 运行优化
optimizer = SearchOptimizer(space, mode="random")
result = optimizer.optimize(objective, n_trials=30, maximize=True)

print(f"最优参数: {result.best_params}")
print(f"最优得分: {result.best_score}")
print(f"耗时: {result.duration:.2f}s")
```

## 核心特性

- **多种搜索模式**：随机搜索、网格搜索
- **灵活参数空间**：支持离散列表、整数范围、浮点范围
- **历史追踪**：记录每次试验的参数与得分
- **最大化/最小化**：支持两种优化方向
