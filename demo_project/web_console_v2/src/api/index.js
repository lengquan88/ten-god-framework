import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：注入 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tengod_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  },
)

// ── 健康检查 ──
export const getHealth = () => api.get('/health/full')

// ── 八字 API ──
export const calcBazi = (data) => api.post('/bazi/calc', data)
export const calcFullBazi = (data) => api.post('/bazi/full', data)
export const getBaziReport = (data) => api.post('/bazi/report', data)

// ── 紫微 API ──
export const calcZiwei = (data) => api.post('/ziwei/calc', data)

// ── 奇门 API ──
export const calcQimen = (data) => api.post('/qimen/calc', data)

// ── 六爻 API ──
export const castLiuyao = (data) => api.post('/liuyao/cast', data)

// ── 知识库 ──
export const searchKnowledge = (q) => api.get('/knowledge/search', { params: { q } })
export const getWuxing = (element) => api.get(`/knowledge/wuxing/${element}`)

// ── AI 解读 ──
export const aiAnalyze = (data) => api.post('/v2/ai/analyze', data)

// ── 案例库 ──
export const listCases = (params) => api.get('/v2/cases', { params })
export const getCase = (id) => api.get(`/v2/cases/${id}`)
export const createCase = (data) => api.post('/v2/cases', data)
export const updateCase = (id, data) => api.put(`/v2/cases/${id}`, data)
export const deleteCase = (id) => api.delete(`/v2/cases/${id}`)
export const getSimilarCases = (params) => api.get('/v2/cases/similar', { params })
export const exportCases = () => api.get('/v2/cases/export')
export const importCases = (data) => api.post('/v2/cases/import', data)

// ── 对话 ──
export const listConversations = () => api.get('/v2/conversations')
export const getConversation = (id) => api.get(`/v2/conversations/${id}`)
export const deleteConversation = (id) => api.delete(`/v2/conversations/${id}`)

// ── 反馈 ──
export const listFeedback = (params) => api.get('/v2/feedback', { params })
export const getFeedbackStats = () => api.get('/v2/feedback/stats')

// ── 管理 ──
export const getDbStats = () => api.get('/v2/admin/db-stats')
export const backupDb = () => api.post('/v2/admin/backup')
export const restoreDb = (data) => api.post('/v2/admin/restore', data)

// ── 认证 ──
export const login = (data) => api.post('/auth/login', data)
export const register = (data) => api.post('/auth/register', data)

export default api