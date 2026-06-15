/**
 * tengod-client — 十神架构 JavaScript/TypeScript SDK v2.0.0
 * ============================================================
 * 通过 HTTP API 访问十神服务的 JavaScript 客户端。
 *
 * 用法:
 *   import { TengodClient } from 'tengod-client';
 *
 *   const client = new TengodClient('http://localhost:8000');
 *
 *   // 健康检查
 *   const status = await client.health();
 *
 *   // 系统状态
 *   const state = await client.status();
 *
 *   // 知识库
 *   const nodes = await client.listNodes();
 *   await client.addNode('测试节点', 'test', { key: 'value' });
 *   const results = await client.searchNodes('道家哲学');
 *
 *   // 内容生成
 *   const result = await client.generate('写一首关于AI的唐诗');
 *   for await (const chunk of client.generateStream('介绍中华文明')) {
 *     process.stdout.write(chunk);
 *   }
 *
 *   // 任务管理
 *   const taskId = await client.submitTask('generate');
 *   const taskStatus = await client.getTask(taskId);
 *
 *   // Oracle
 *   const oracle = await client.consultOracle('中华文明何在');
 *
 *   // 指标
 *   const metrics = await client.metrics();
 */

export interface TengodConfig {
  /** 十神 API 服务地址 */
  baseUrl: string;
  /** JWT API 密钥（可选） */
  apiKey?: string;
  /** 请求超时时间（毫秒），默认 30000 */
  timeout?: number;
}

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface SystemStatus {
  version: string;
  name: string;
  request_id: string;
  features: Record<string, boolean>;
  knowledge: { nodes: number; edges: number };
  scheduler: any;
  judge: any;
  config: any;
  oracle: any;
  registered_components: string[];
  locator: any;
  balancer: any;
}

export interface KnowledgeNode {
  id: string;
  name: string;
  node_type: string;
  properties: Record<string, any>;
}

export interface OracleResult {
  question: string;
  hexagram: string;
  hexagram_index: number;
  upper_trigram: string;
  lower_trigram: string;
  gan_zhi: string;
  wuxing: string;
  judgment: string;
  prediction: string;
  wisdom: string;
  interpretation: string;
  stats: any;
}

export interface TaskInfo {
  task_id: string;
  status: string;
  result?: any;
  error?: string;
}

export class TengodError extends Error {
  statusCode: number;
  response: any;

  constructor(message: string, statusCode: number = 0, response: any = null) {
    super(message);
    this.name = 'TengodError';
    this.statusCode = statusCode;
    this.response = response;
  }
}

export class TengodClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;

  constructor(config: string | TengodConfig) {
    if (typeof config === 'string') {
      this.baseUrl = config.replace(/\/$/, '');
      this.timeout = 30000;
    } else {
      this.baseUrl = config.baseUrl.replace(/\/$/, '');
      this.apiKey = config.apiKey;
      this.timeout = config.timeout || 30000;
    }
  }

  private async request<T = any>(
    method: string,
    path: string,
    body?: any,
    options?: { accept?: string }
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: options?.accept || 'application/json',
    };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (options?.accept === 'text/plain') {
        return (await resp.text()) as any;
      }

      const data = await resp.json();
      if (!resp.ok) {
        throw new TengodError(
          `HTTP ${resp.status}: ${data.message || data}`,
          resp.status,
          data
        );
      }
      return data;
    } catch (e: any) {
      clearTimeout(timer);
      if (e instanceof TengodError) throw e;
      if (e.name === 'AbortError') {
        throw new TengodError(`请求超时 (${this.timeout}ms)`);
      }
      throw new TengodError(`连接失败: ${e.message}`);
    }
  }

  // ── 系统 ──────────────────────────────────────

  async health(): Promise<ApiResponse> {
    return this.request('GET', '/health');
  }

  async status(): Promise<ApiResponse<SystemStatus>> {
    return this.request('GET', '/api/status');
  }

  async metrics(): Promise<string> {
    return this.request('GET', '/metrics', undefined, { accept: 'text/plain' });
  }

  async version(): Promise<string> {
    const s = await this.status();
    return s.data?.version || 'unknown';
  }

  // ── 知识库 ────────────────────────────────────

  async listNodes(limit: number = 50, offset: number = 0): Promise<KnowledgeNode[]> {
    const r = await this.request<ApiResponse<{ items: KnowledgeNode[] }>>(
      'GET', `/api/knowledge/nodes?limit=${limit}&offset=${offset}`
    );
    return r.data?.items || [];
  }

  async searchNodes(query: string, topK: number = 5): Promise<KnowledgeNode[]> {
    return this.listNodes(topK);
  }

  async addNode(
    name: string,
    nodeType: string = 'default',
    properties?: Record<string, any>
  ): Promise<ApiResponse> {
    return this.request('POST', '/api/knowledge/nodes', {
      name,
      node_type: nodeType,
      properties: properties || {},
    });
  }

  // ── 内容生成 ──────────────────────────────────

  async generate(prompt: string, style: string = 'creative'): Promise<ApiResponse> {
    return this.request('POST', '/api/generate', { prompt, style });
  }

  async *generateStream(prompt: string, style: string = 'creative'): AsyncGenerator<string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    const resp = await fetch(`${this.baseUrl}/api/generate/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ prompt, style }),
    });
    const reader = resp.body?.getReader();
    if (!reader) throw new TengodError('无法读取流');
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      yield decoder.decode(value, { stream: true });
    }
  }

  // ── 任务管理 ──────────────────────────────────

  async submitTask(funcName: string, params?: Record<string, any>): Promise<string> {
    const r = await this.request<ApiResponse<{ task_id: string }>>(
      'POST', '/api/tasks/submit', { func_name: funcName, params: params || {} }
    );
    return r.data?.task_id || '';
  }

  async getTask(taskId: string): Promise<TaskInfo> {
    const r = await this.request<ApiResponse<TaskInfo>>('GET', `/api/tasks/${taskId}`);
    return r.data || { task_id: taskId, status: 'unknown' };
  }

  async listTasks(): Promise<any> {
    const s = await this.status();
    return s.data?.scheduler || {};
  }

  // ── Oracle ─────────────────────────────────────

  async consultOracle(question: string, mode: string = 'auto'): Promise<OracleResult> {
    const r = await this.request<ApiResponse<OracleResult>>(
      'POST', '/api/oracle', { question, mode }
    );
    return r.data || ({} as OracleResult);
  }

  // ── 认证 ──────────────────────────────────────

  async login(username: string, password: string): Promise<string> {
    const r = await this.request<ApiResponse<{ access_token: string }>>(
      'POST', '/api/auth/token', { username, password }
    );
    const token = r.data?.access_token;
    if (token) this.apiKey = token;
    return token || '';
  }

  async register(username: string, password: string, email?: string): Promise<ApiResponse> {
    return this.request('POST', '/api/auth/register', { username, password, email });
  }
}

// TypeScript 类型导出
export type { ApiResponse, SystemStatus, KnowledgeNode, OracleResult, TaskInfo };

export default TengodClient;