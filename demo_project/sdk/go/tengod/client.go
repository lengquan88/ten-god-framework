// Package tengod 提供十神架构 HTTP API 的 Go 客户端 SDK v2.0.0
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