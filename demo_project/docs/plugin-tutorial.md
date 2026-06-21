# 插件开发指南

Tengod 的插件子系统基于 `tengod.plugins` 模块，支持钩子（hooks）、权限（permissions）与隔离运行。

## 1. 插件元数据 (PluginMetadata)
- `id`: 唯一标识符（推荐反向域名，如 `com.example.reporter`）
- `hooks`: 插件响应的钩子集合（见下方 VALID_HOOKS）
- `permissions`: 申请的权限声明（见 VALID_PERMISSIONS）

## 2. 可用 Hooks
- `bazi:post_calc`           八字排盘完成后触发
- `report:post_gen`          报告生成完成后触发
- `search:post_query`        语义搜索后触发
- `analysis:post_trajectory` 轨迹分析完成后触发
- `ui:custom_component`      UI 组件注入点

## 3. 示例：最简插件
```python
from tengod.plugins import PluginMetadata, create_plugin_metadata, get_plugin_manager

def my_plugin_fn(payload, context):
    input_data = payload.get('input', {})
    return {'enhanced': True, 'summary': f'hello {input_data}'}

md = create_plugin_metadata(
    id='com.example.demo',
    name='Demo Plugin',
    version='1.0.0',
    author='you',
    description='演示插件',
    entry_point='module_name:my_plugin_fn',
    hooks=['report:post_gen'],
    permissions=['read:records'],
    runtime_fn=my_plugin_fn,
)

pm = get_plugin_manager()
pm.register(md)
results = pm.trigger('report:post_gen', {'report': '内容'})
for r in results:
    print(r)
```

## 4. 验证插件
- `PluginRegistry.validate_metadata(md)` 校验元数据
- `PluginSandbox` 提供进程隔离运行（entry_point 形如 `code://...`）
