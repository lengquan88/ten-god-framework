# Capability Evolver — 知识积累

## LRN-20260724-001 — 包管理器自动检测

- **触发时间**: 2026-07-24 10:45
- **来源**: ERR-20260724-001
- **知识**: 在执行 Node.js 项目命令前，应自动检测项目使用的包管理器
- **检测逻辑**:
  ```python
  def detect_package_manager(project_path):
      if os.path.exists(os.path.join(project_path, 'pnpm-lock.yaml')):
          return 'pnpm'
      elif os.path.exists(os.path.join(project_path, 'yarn.lock')):
          return 'yarn'
      elif os.path.exists(os.path.join(project_path, 'package-lock.json')):
          return 'npm'
      return 'npm'  # default
  ```
- **提升至**: CLAUDE.md

## LRN-20260724-002 — API 端点鉴权规则

- **触发时间**: 2026-07-24 11:15
- **来源**: ERR-20260724-002
- **知识**: 新增 API 端点时，必须根据路径前缀自动添加鉴权中间件
- **规则**:
  - `/api/v2/*` → JWT 鉴权
  - `/api/admin/*` → Admin 鉴权
  - `/api/health`, `/api/stats` → 公开
- **提升至**: CLAUDE.md

## LRN-20260724-003 — 数据访问层封装

- **触发时间**: 2026-07-24 11:45
- **来源**: ERR-20260724-003
- **知识**: 所有数据库操作必须通过 `tengod/database.py` 的 `get_db()` 入口
- **原因**: 统一管理连接池、重试、缓存、事务
- **提升至**: CLAUDE.md

## LRN-20260724-004 — TypeScript 类型检查

- **触发时间**: 2026-07-24 12:15
- **来源**: ERR-20260724-004
- **知识**: pre-commit hook 应包含 `tsc --noEmit` 类型检查
- **配置**:
  ```yaml
  - repo: local
    hooks:
      - id: tsc
        name: TypeScript check
        entry: npx tsc --noEmit
        language: system
        files: \.ts$
  ```
- **提升至**: CLAUDE.md, .pre-commit-config.yaml

## LRN-20260724-005 — 自动测试触发

- **触发时间**: 2026-07-24 12:45
- **来源**: ERR-20260724-005
- **知识**: 开发环境应配置文件监听器，自动运行相关测试
- **设计**: 使用 `pytest-watch` 或 `nodemon` 监听文件变更
- **提升至**: 待实施