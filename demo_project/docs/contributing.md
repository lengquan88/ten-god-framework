# 贡献指南 (Contributing)

## 代码风格
- 遵循 PEP 8，建议使用 `black` / `ruff`
- 为新模块添加类型注解（type hints）

## 分支与提交
- 基于 `main` 创建新分支，例如 `feature/new-engine`
- 提交信息简洁描述变更内容

## 测试
```bash
python -m pytest tests/ -q
```
新增功能必须包含对应测试。

## Pull Request 流程
1. Fork 本仓库
2. 在分支上提交变更
3. 打开 PR，描述变更动机、影响范围与验证方式
4. 通过 CI 后由维护者 review 合并
