# 太极 · 阴阳调和

> 十神扩展之一，主理调和、平衡与状态切换。
> 承担系统的阴阳平衡与动态调节职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `balancer.py` | 阴阳平衡器，支持状态切换、回调机制、历史追踪 |

## 快速开始

```python
from tengod.太极_阴阳调和 import TaiChiBalancer, YinYang

balancer = TaiChiBalancer(initial_state=YinYang.BALANCED)

# 获取当前状态
print(balancer.get_state().value)  # balanced

# 切换状态
balancer.toggle("手动切换")
print(balancer.get_state().value)  # yang

# 回归平衡
balancer.balance("系统稳定")

# 基于指标评估
metrics = {"activity": 0.8, "load": 0.6}
balancer.evaluate(metrics)

# 注册回调
def on_yang(old, new):
    print(f"切换到阳态: {old.value} -> {new.value}")

balancer.register_callback(YinYang.YANG, on_yang)

# 查看历史
print(balancer.get_history())

# 统计
print(balancer.stats())
```

## 核心特性

- **三态模型**：阴态、阳态、平衡态
- **动态切换**：一键 toggle 或基于指标自动评估
- **回调机制**：状态变化时触发注册的回调
- **历史追踪**：记录所有状态转换及其原因