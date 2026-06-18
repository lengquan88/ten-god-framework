// Package tengod 提供十神架构 HTTP API 的 Go 客户端 SDK v3.0.0
//
// 用法:
//
//	import "github.com/tengod/tengod-client-go"
//
//	client := tengod.NewClient("http://localhost:8000", "")
//
//	// 健康检查
//	status, err := client.Health()
//
//	// 系统状态
//	state, err := client.Status()
//
//	// 知识库
//	nodes, err := client.ListNodes(50, 0)
//	err = client.AddNode("测试节点", "test", map[string]any{"key": "value"})
//
//	// 内容生成
//	result, err := client.Generate("写一首关于AI的唐诗", "creative")
//
//	// Oracle
//	oracle, err := client.ConsultOracle("中华文明何在", "auto")

package tengod

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// Client 十神架构 HTTP API 客户端
type Client struct {
	BaseURL string
	APIKey  string
	Timeout time.Duration
	client  *http.Client
}

// ApiResponse 标准 API 响应
type ApiResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

// SystemStatus 系统状态
type SystemStatus struct {
	Version              string            `json:"version"`
	Name                 string            `json:"name"`
	RequestID            string            `json:"request_id"`
	Features             map[string]bool   `json:"features"`
	Knowledge            KnowledgeStats    `json:"knowledge"`
	RegisteredComponents []string          `json:"registered_components"`
}

// KnowledgeStats 知识库统计
type KnowledgeStats struct {
	Nodes int `json:"nodes"`
	Edges int `json:"edges"`
}

// KnowledgeNode 知识节点
type KnowledgeNode struct {
	ID         string         `json:"id"`
	Name       string         `json:"name"`
	NodeType   string         `json:"node_type"`
	Properties map[string]any `json:"properties"`
}

// OracleResult Oracle 推演结果
type OracleResult struct {
	Question      string `json:"question"`
	Hexagram      string `json:"hexagram"`
	HexagramIndex int    `json:"hexagram_index"`
	UpperTrigram  string `json:"upper_trigram"`
	LowerTrigram  string `json:"lower_trigram"`
	GanZhi        string `json:"gan_zhi"`
	Wuxing        string `json:"wuxing"`
	Judgment      string `json:"judgment"`
	Prediction    string `json:"prediction"`
	Wisdom        string `json:"wisdom"`
}

// TaskInfo 任务信息
type TaskInfo struct {
	TaskID string `json:"task_id"`
	Status string `json:"status"`
}

// TengodError SDK 错误
type TengodError struct {
	Message    string
	StatusCode int
	Response   string
}

func (e *TengodError) Error() string {
	return fmt.Sprintf("tengod: %s (status=%d)", e.Message, e.StatusCode)
}

// NewClient 创建新的十神客户端
func NewClient(baseURL string, apiKey string) *Client {
	baseURL = strings.TrimRight(baseURL, "/")
	return &Client{
		BaseURL: baseURL,
		APIKey:  apiKey,
		Timeout: 30 * time.Second,
		client:  &http.Client{Timeout: 30 * time.Second},
	}
}

func (c *Client) request(method, path string, body any, result any) error {
	url := c.BaseURL + path

	var reqBody io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return &TengodError{Message: fmt.Sprintf("序列化错误: %v", err)}
		}
		reqBody = bytes.NewReader(data)
	}

	req, err := http.NewRequest(method, url, reqBody)
	if err != nil {
		return &TengodError{Message: fmt.Sprintf("创建请求失败: %v", err)}
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	if c.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.APIKey)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return &TengodError{Message: fmt.Sprintf("请求失败: %v", err)}
	}
	defer resp.Body.Close()

	respData, err := io.ReadAll(resp.Body)
	if err != nil {
		return &TengodError{Message: fmt.Sprintf("读取响应失败: %v", err)}
	}

	if resp.StatusCode >= 400 {
		return &TengodError{
			Message:    fmt.Sprintf("HTTP %d: %s", resp.StatusCode, string(respData)),
			StatusCode: resp.StatusCode,
			Response:   string(respData),
		}
	}

	if result != nil {
		if err := json.Unmarshal(respData, result); err != nil {
			return &TengodError{Message: fmt.Sprintf("解析响应失败: %v", err)}
		}
	}

	return nil
}

// ── 系统 ─────────────────────────────────────────────

// Health 健康检查
func (c *Client) Health() (*ApiResponse, error) {
	var result ApiResponse
	err := c.request("GET", "/health", nil, &result)
	return &result, err
}

// Status 获取系统状态
func (c *Client) Status() (*SystemStatus, error) {
	var wrapper struct {
		Data SystemStatus `json:"data"`
	}
	err := c.request("GET", "/api/status", nil, &wrapper)
	if err != nil {
		return nil, err
	}
	return &wrapper.Data, nil
}

// Metrics 获取 Prometheus 指标
func (c *Client) Metrics() (string, error) {
	url := c.BaseURL + "/metrics"
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", &TengodError{Message: fmt.Sprintf("创建请求失败: %v", err)}
	}
	req.Header.Set("Accept", "text/plain")
	if c.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.APIKey)
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return "", &TengodError{Message: fmt.Sprintf("请求失败: %v", err)}
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	return string(data), err
}

// Version 获取服务版本
func (c *Client) Version() (string, error) {
	s, err := c.Status()
	if err != nil {
		return "", err
	}
	return s.Version, nil
}

// ── 知识库 ───────────────────────────────────────────

// ListNodes 列出知识节点
func (c *Client) ListNodes(limit, offset int) ([]KnowledgeNode, error) {
	var wrapper struct {
		Data struct {
			Items []KnowledgeNode `json:"items"`
		} `json:"data"`
	}
	path := fmt.Sprintf("/api/knowledge/nodes?limit=%d&offset=%d", limit, offset)
	err := c.request("GET", path, nil, &wrapper)
	if err != nil {
		return nil, err
	}
	return wrapper.Data.Items, nil
}

// AddNode 添加知识节点
func (c *Client) AddNode(name, nodeType string, properties map[string]any) error {
	body := map[string]any{
		"name":       name,
		"node_type":  nodeType,
		"properties": properties,
	}
	return c.request("POST", "/api/knowledge/nodes", body, nil)
}

// ── 内容生成 ─────────────────────────────────────────

// Generate 生成内容
func (c *Client) Generate(prompt, style string) (*ApiResponse, error) {
	var result ApiResponse
	body := map[string]string{"prompt": prompt, "style": style}
	err := c.request("POST", "/api/generate", body, &result)
	return &result, err
}

// ── 任务管理 ─────────────────────────────────────────

// SubmitTask 提交异步任务
func (c *Client) SubmitTask(funcName string, params map[string]any) (string, error) {
	var wrapper struct {
		Data struct {
			TaskID string `json:"task_id"`
		} `json:"data"`
	}
	body := map[string]any{"func_name": funcName, "params": params}
	err := c.request("POST", "/api/tasks/submit", body, &wrapper)
	if err != nil {
		return "", err
	}
	return wrapper.Data.TaskID, nil
}

// GetTask 查询任务状态
func (c *Client) GetTask(taskID string) (*TaskInfo, error) {
	var wrapper struct {
		Data TaskInfo `json:"data"`
	}
	err := c.request("GET", "/api/tasks/"+taskID, nil, &wrapper)
	if err != nil {
		return nil, err
	}
	return &wrapper.Data, nil
}

// ── Oracle ────────────────────────────────────────────

// ConsultOracle 推背图 Oracle 咨询
func (c *Client) ConsultOracle(question, mode string) (*OracleResult, error) {
	var wrapper struct {
		Data OracleResult `json:"data"`
	}
	body := map[string]string{"question": question, "mode": mode}
	err := c.request("POST", "/api/oracle", body, &wrapper)
	if err != nil {
		return nil, err
	}
	return &wrapper.Data, nil
}

// ── 认证 ─────────────────────────────────────────────

// Login 登录获取 JWT token
func (c *Client) Login(username, password string) (string, error) {
	var wrapper struct {
		Data struct {
			AccessToken string `json:"access_token"`
		} `json:"data"`
	}
	body := map[string]string{"username": username, "password": password}
	err := c.request("POST", "/api/auth/token", body, &wrapper)
	if err != nil {
		return "", err
	}
	if wrapper.Data.AccessToken != "" {
		c.APIKey = wrapper.Data.AccessToken
	}
	return wrapper.Data.AccessToken, nil
}

// ── 八字排盘（阶段二十扩展） ─────────────────────────

// BaziInput 八字排盘输入
type BaziInput struct {
	Year    int    `json:"year"`
	Month   int    `json:"month"`
	Day     int    `json:"day"`
	Hour    int    `json:"hour"`
	Minute  int    `json:"minute"`
	Gender  string `json:"gender"`
}

// BaziFull 完整八字排盘
func (c *Client) BaziFull(year, month, day, hour, minute int, gender string) (map[string]any, error) {
	body := BaziInput{Year: year, Month: month, Day: day, Hour: hour, Minute: minute, Gender: gender}
	var wrapper struct {
		Code int            `json:"code"`
		Data map[string]any `json:"data"`
	}
	err := c.request("POST", "/api/bazi/full", body, &wrapper)
	if err != nil {
		return nil, err
	}
	return wrapper.Data, nil
}

// BaziCalc 基础八字排盘
func (c *Client) BaziCalc(year, month, day, hour int) (map[string]any, error) {
	body := map[string]int{"year": year, "month": month, "day": day, "hour": hour}
	var wrapper struct {
		Code int            `json:"code"`
		Data map[string]any `json:"data"`
	}
	err := c.request("POST", "/api/bazi/calc", body, &wrapper)
	if err != nil {
		return nil, err
	}
	return wrapper.Data, nil
}

// ── 命例案例库（阶段二十扩展） ───────────────────────

// Case 命例案例
type Case struct {
	ID          int      `json:"id"`
	Title       string   `json:"title"`
	Category    string   `json:"category"`
	Summary     string   `json:"summary"`
	Tags        []string `json:"tags"`
	ViewCount   int      `json:"view_count"`
	IsPublic    bool     `json:"is_public"`
	IsFeatured  bool     `json:"is_featured"`
}

// ListCases 列出命例案例
func (c *Client) ListCases(category string, limit, offset int) ([]Case, error) {
	path := fmt.Sprintf("/api/cases?limit=%d&offset=%d", limit, offset)
	if category != "" {
		path += "&category=" + category
	}
	var wrapper struct {
		Total int    `json:"total"`
		Cases []Case `json:"cases"`
	}
	err := c.request("GET", path, nil, &wrapper)
	if err != nil {
		return nil, err
	}
	return wrapper.Cases, nil
}

// GetCase 获取案例详情
func (c *Client) GetCase(caseID int) (*Case, error) {
	var case_ Case
	err := c.request("GET", fmt.Sprintf("/api/cases/%d", caseID), nil, &case_)
	if err != nil {
		return nil, err
	}
	return &case_, nil
}

// CreateCase 创建命例案例
func (c *Client) CreateCase(recordID int, title, category, summary string, tags []string) (map[string]any, error) {
	body := map[string]any{
		"record_id": recordID,
		"title":     title,
		"category":  category,
		"summary":   summary,
		"tags":      tags,
	}
	var result map[string]any
	err := c.request("POST", "/api/cases", body, &result)
	return result, err
}

// SearchCases 多维度搜索案例
func (c *Client) SearchCases(keyword, category, dayMaster, geju string, limit int) ([]Case, error) {
	body := map[string]any{"limit": limit}
	if keyword != "" {
		body["keyword"] = keyword
	}
	if category != "" {
		body["category"] = category
	}
	if dayMaster != "" {
		body["day_master"] = dayMaster
	}
	if geju != "" {
		body["geju"] = geju
	}
	var wrapper struct {
		Cases []Case `json:"cases"`
	}
	err := c.request("POST", "/api/cases/search", body, &wrapper)
	if err != nil {
		return nil, err
	}
	return wrapper.Cases, nil
}

// SimilarCases 获取相似案例推荐
func (c *Client) SimilarCases(caseID, limit int) ([]Case, error) {
	var wrapper struct {
		Cases []Case `json:"cases"`
	}
	err := c.request("GET", fmt.Sprintf("/api/cases/%d/similar?limit=%d", caseID, limit), nil, &wrapper)
	if err != nil {
		return nil, err
	}
	return wrapper.Cases, nil
}

// CaseCategories 获取案例分类列表
func (c *Client) CaseCategories() ([]string, error) {
	var wrapper struct {
		Categories []string `json:"categories"`
	}
	err := c.request("GET", "/api/cases/categories/list", nil, &wrapper)
	return wrapper.Categories, err
}

// CaseStats 案例库统计
func (c *Client) CaseStats() (map[string]any, error) {
	var result map[string]any
	err := c.request("GET", "/api/cases/stats/summary", nil, &result)
	return result, err
}

// FavoriteCase 收藏案例
func (c *Client) FavoriteCase(caseID int) error {
	return c.request("POST", fmt.Sprintf("/api/cases/%d/favorite", caseID), nil, nil)
}

// LikeCase 点赞案例
func (c *Client) LikeCase(caseID int) error {
	return c.request("POST", fmt.Sprintf("/api/cases/%d/like", caseID), nil, nil)
}

// ── Webhook（阶段二十扩展） ──────────────────────────

// WebhookSubscription Webhook 订阅
type WebhookSubscription struct {
	ID             int      `json:"id"`
	URL            string   `json:"url"`
	Events         []string `json:"events"`
	IsActive       bool     `json:"is_active"`
	Description    string   `json:"description"`
	TotalDelivered int      `json:"total_delivered"`
	TotalFailed    int      `json:"total_failed"`
}

// ListWebhookEvents 列出 Webhook 事件类型
func (c *Client) ListWebhookEvents() ([]map[string]string, error) {
	var wrapper struct {
		Events []map[string]string `json:"events"`
	}
	err := c.request("GET", "/api/webhooks/events", nil, &wrapper)
	return wrapper.Events, err
}

// CreateWebhook 创建 Webhook 订阅
func (c *Client) CreateWebhook(url string, events []string, secret, description string) (*WebhookSubscription, error) {
	body := map[string]any{
		"url":         url,
		"events":      events,
		"secret":      secret,
		"description": description,
	}
	var sub WebhookSubscription
	err := c.request("POST", "/api/webhooks", body, &sub)
	if err != nil {
		return nil, err
	}
	return &sub, nil
}

// ListWebhooks 列出 Webhook 订阅
func (c *Client) ListWebhooks(activeOnly bool) ([]WebhookSubscription, error) {
	path := fmt.Sprintf("/api/webhooks?active_only=%v", activeOnly)
	var wrapper struct {
		Subscriptions []WebhookSubscription `json:"subscriptions"`
	}
	err := c.request("GET", path, nil, &wrapper)
	return wrapper.Subscriptions, err
}

// DeleteWebhook 删除 Webhook 订阅
func (c *Client) DeleteWebhook(subID int) error {
	return c.request("DELETE", fmt.Sprintf("/api/webhooks/%d", subID), nil, nil)
}

// TriggerWebhook 触发 Webhook 事件
func (c *Client) TriggerWebhook(eventType string, payload map[string]any) (int, error) {
	body := map[string]any{"event_type": eventType, "payload": payload}
	var wrapper struct {
		Triggered int `json:"triggered"`
	}
	err := c.request("POST", "/api/webhooks/trigger", body, &wrapper)
	return wrapper.Triggered, err
}

// WebhookStats Webhook 统计
func (c *Client) WebhookStats() (map[string]any, error) {
	var result map[string]any
	err := c.request("GET", "/api/webhooks/stats/summary", nil, &result)
	return result, err
}

// ── 插件系统（阶段二十扩展） ─────────────────────────

// ListPlugins 列出插件
func (c *Client) ListPlugins(state string) ([]map[string]any, error) {
	path := "/api/plugins"
	if state != "" {
		path += "?state=" + state
	}
	var wrapper struct {
		Plugins []map[string]any `json:"plugins"`
	}
	err := c.request("GET", path, nil, &wrapper)
	return wrapper.Plugins, err
}

// PluginStats 插件统计
func (c *Client) PluginStats() (map[string]any, error) {
	var result map[string]any
	err := c.request("GET", "/api/plugins/stats/summary", nil, &result)
	return result, err
}

// ── 系统版本（阶段二十扩展） ─────────────────────────

// APIVersion 获取 API 版本信息
func (c *Client) APIVersion() (map[string]any, error) {
	var result map[string]any
	err := c.request("GET", "/api/version", nil, &result)
	return result, err
}