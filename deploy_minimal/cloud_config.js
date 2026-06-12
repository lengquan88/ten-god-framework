/**
 * cloud_config.js — 云部署API地址配置
 * 
 * 将此文件添加到 CloudStudio 前端目录中。
 * 修改 API_BASE_URL 为实际后端地址即可切换。
 * 
 * 使用方式:
 *   <script src="cloud_config.js"></script>
 *   前端所有 API 调用通过 window.CLOUD_CONFIG.API_BASE_URL 获取地址
 */

window.CLOUD_CONFIG = {
  // ── API 后端地址 ─────────────────────────────
  // 本地:  'http://localhost:8000'
  // 服务器: 'http://你的服务器IP:8000'
  // HTTPS: 'https://你的域名/api'
  API_BASE_URL: 'http://localhost:8000',

  // ── 认证 ─────────────────────────────────────
  API_KEY: 'spirit-p444-dev-key',

  // ── 超时 (毫秒) ──────────────────────────────
  TIMEOUT: 10000,

  // ── 默认评估参数 ─────────────────────────────
  DEFAULT_QI: 'qi_main',
  RETURN_EXPLAIN: true,

  // ── 版本 ─────────────────────────────────────
  VERSION: '2.0.0',
  BUILD: '2026-06-07',
};

// 挂载到 SpiritAPI 命名空间
window.SpiritAPI = {
  baseUrl: window.CLOUD_CONFIG.API_BASE_URL,
  apiKey: window.CLOUD_CONFIG.API_KEY,

  async evaluate(rootQuestion, answers, qiStyle, returnExplain) {
    const resp = await fetch(`${this.baseUrl}/evaluate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        root_question: rootQuestion,
        answers: Array.isArray(answers) ? answers : [answers],
        qi_style: qiStyle || window.CLOUD_CONFIG.DEFAULT_QI,
        return_explain: returnExplain !== undefined ? returnExplain : window.CLOUD_CONFIG.RETURN_EXPLAIN
      })
    });
    return resp.json();
  },

  async health() {
    const resp = await fetch(`${this.baseUrl}/health`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` }
    });
    return resp.json();
  },

  async reload() {
    const resp = await fetch(`${this.baseUrl}/reload`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: '{}'
    });
    return resp.json();
  }
};
