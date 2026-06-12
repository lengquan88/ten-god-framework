# 正官 · 法度调度

> 十神之一，主理法度、秩序与系统调度。
> 承担统一 API 接口、任务调度、规则执行的职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `task_scheduler.py` | 基于优先级的任务调度器，支持并发控制、失败重试 |
| `api_router.py` | 简易 API 路由器，支持 GET/POST/PUT/DELETE 与中间件 |
| `__init__.py` | 模块导出 |

## 快速开始

### 任务调度

```python
from tengod.正官_法度调度 import TaskScheduler, TaskPriority

scheduler = TaskScheduler(max_workers=4)

def my_task(x, y):
    return x + y

scheduler.submit("task-1", my_task, args=(1, 2), priority=TaskPriority.HIGH)
scheduler.run_all()

status = scheduler.get_status("task-1")
print(f"任务状态: {status}")
```

### API 路由

```python
from tengod.正官_法度调度 import APIRouter

router = APIRouter(prefix="/api/v1")

@router.get("/hello")
def hello():
    return {"message": "Hello, World!"}

@router.post("/echo")
def echo(data: dict):
    return {"received": data}

# 分发请求
result = router.dispatch("/hello", "GET")
```

## 核心特性

- **优先级调度**：四级优先级（CRITICAL > HIGH > NORMAL > LOW）
- **并发控制**：通过 `max_workers` 限制同时执行的任务数
- **失败重试**：支持配置最大重试次数
- **状态追踪**：实时查询任务状态与统计信息
- **中间件机制**：API 路由支持中间件扩展
