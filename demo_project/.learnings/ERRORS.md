# Capability Evolver — 错误记录

## ERR-20260724-001 — Agent误用 npm install

- **触发时间**: 2026-07-24 10:30
- **上下文**: Agent 在 Node.js 项目中执行 `npm install` 安装依赖
- **判断依据**: 项目根目录存在 `pnpm-lock.yaml`，明确指示使用 pnpm 作为包管理器
- **分类**: 错误
- **详情**: Agent 未检测 `pnpm-lock.yaml` 文件，直接使用了 npm 命令。项目已配置 pnpm 作为包管理器，使用 npm 会导致 lock 文件不一致。
- **包管理器检测逻辑**: 
  1. 检查 `pnpm-lock.yaml` → 使用 pnpm
  2. 检查 `yarn.lock` → 使用 yarn
  3. 检查 `package-lock.json` → 使用 npm
  4. 检查 `package.json` 中 `packageManager` 字段
- **纠正措施**: 已添加 pre-commit hook 检测包管理器一致性

## ERR-20260724-002 — Agent 遗漏鉴权中间件

- **触发时间**: 2026-07-24 11:00
- **上下文**: Agent 新增 API 端点 `/api/v2/cognitive/analyze` 时未添加 JWT 鉴权中间件
- **判断依据**: 项目中 `/api/v2/` 路径前缀的端点均需鉴权（参考 `tengod/api_server.py` 中 `AuthMiddleware`）
- **分类**: 错误（已纠正）
- **纠正措施**: 在所有 API 端点注册时强制检查鉴权中间件
- **中间件检查规则**: 
  1. 新增 `/api/v2/*` 端点 → 自动添加 AuthMiddleware
  2. 新增 `/api/admin/*` 端点 → 自动添加 AdminAuthMiddleware
  3. 只有 `/api/health` 和 `/api/stats` 为公开端点

## ERR-20260724-003 — Agent 绕过数据访问层

- **触发时间**: 2026-07-24 11:30
- **上下文**: Agent 在实现新功能时直接调用 `prisma.user.findMany()` 而非使用项目封装的数据访问层
- **判断依据**: 项目 `tengod/database.py` 提供了统一的 `get_db()` 入口，封装了连接池、重试、缓存等逻辑
- **分类**: 知识盲区
- **数据访问层入口**: 
  - `tengod/database.py` → `get_db()` 函数
  - 所有数据库操作必须通过此入口，禁止直接使用 Prisma Client
- **纠正措施**: 已在 CLAUDE.md 中添加数据访问层规则

## ERR-20260724-004 — 类型检查最佳实践

- **触发时间**: 2026-07-24 12:00
- **上下文**: Agent 发现提交前运行 `tsc --noEmit` 可捕获未在 CI 中发现的类型错误
- **判断依据**: 项目 CI 中未配置 TypeScript 类型检查步骤
- **分类**: 最佳实践
- **建议**: 添加 pre-commit hook 运行 `tsc --noEmit`
- **实施**: 待添加到 `.pre-commit-config.yaml`

## ERR-20260724-005 — 自动测试触发

- **触发时间**: 2026-07-24 12:30
- **上下文**: 用户多次要求修改代码后运行测试，说明期望自动化测试流程
- **判断依据**: 用户反馈 "修改后请运行测试" 出现频率高
- **分类**: 功能请求
- **建议**: 实现文件保存后自动触发相关测试的机制
- **设计**: 使用文件监听器监听 `.py` 文件变更，自动运行对应测试文件