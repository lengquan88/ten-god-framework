# ERRORS — 错误记录

> 记录在推进 ten-god-framework 过程中遇到的真实阻滞点，供后续避坑使用。

---

## ER-001 · Git 推送 · 网络层面无法连接 github.com:443

- **日期**: 2026-06-13
- **症状**:
  ```
  fatal: unable to access 'https://github.com/...': Could not connect to server
  ```
- **环境**: Windows 11 · PowerShell · WorkBuddy 内置终端
- **根因** (待验证):
  1. 公司/家庭网络出口防火墙拦截 443 的 HTTPS 请求
  2. DNS 污染 / 解析失败
  3. 代理未正确透传 HTTPS 请求
- **临时方案**: 切换到 Agent 自身可访问 GitHub 的沙箱环境执行 git push
- **长期方案**:
  - 在本地配置 git config http.proxy 指向可用代理
  - 或改用 SSH 通道 (git@github.com:lengquan88/ten-god-framework.git)

---

## ER-002 · Git 推送 · 认证层面 · GitHub MCP token 为只读

- **日期**: 2026-06-13
- **症状**:
  ```
  403 Resource not accessible by integration
  ```
- **根因**: MCP Agent 绑定的是 GitHub Integration 只读 token，无法写仓库
- **临时方案**: 使用带 x-access-token:<PAT> 的 HTTPS URL 直接 push
- **长期方案**: 在 Agent 工具层新增一个写权限 MCP 端点，供明确的 PR/推送场景调用

---

## ER-003 · 会话状态丢失 · 上下文继承断层

- **日期**: 2026-06-13
- **症状**: 上一轮会话的 Engram 架构上下文在本轮丢失，需要重新定位代码结构
- **根因**: 跨 session 的长期记忆尚未与 engram 持久化机制打通
- **临时方案**: 每次手动 grep 关键文件并重建状态
- **长期方案**: 让每次结束前调用 addEngram() 写入本次的"结构快照 + 模块列表"，下次会话启动时 buildEngramContext() 自动还原

---

## 备注

- 所有错误都不是代码错误。当前的阻滞点集中在 Git 网络层面 + 工具层权限 + Agent 会话记忆，与 ten-god-framework 的核心逻辑无关。
