# 劫财 · 攻防边界

> 十神之一，主理攻防、边界与守护。
> 承担系统的安全防护与权限校验职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `guard.py` | 守护器，支持权限校验、限流、审计日志 |

## 快速开始

```python
from tengod.劫财_攻防边界 import Guard, Permission

guard = Guard()

# 注册角色
guard.register_role("admin", {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN})
guard.register_role("viewer", {Permission.READ})

# 创建安全上下文
admin = guard.create_context("user-1", roles=["admin"])
viewer = guard.create_context("user-2", roles=["viewer"])

# 检查权限
print(guard.check(admin, Permission.DELETE))  # True
print(guard.check(viewer, Permission.WRITE))  # False

# 限流
if guard.rate_limit("user-1", max_requests=5):
    print("Request allowed")
else:
    print("Rate limited")

# 审计
print(guard.get_audit_log("user-1"))
```

## 核心特性

- **RBAC 模型**：基于角色的权限管理
- **装饰器保护**：`@guard.enforce(Permission.X)` 一行守护
- **滑动窗口限流**：可配置的限流策略
- **完整审计**：所有权限检查自动记录
