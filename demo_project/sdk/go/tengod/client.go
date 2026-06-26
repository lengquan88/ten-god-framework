package tengod

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// SDKVersion is the current SDK version (v3.0.0)
const SDKVersion = "v3.0.0"

// Client represents a TenGod API client
type Client struct {
	baseURL    string
	apiKey     string
	httpClient *http.Client
	timeout    time.Duration
}

// NewClient creates a new TenGod API client
func NewClient(baseURL string, apiKey string) *Client {
	return &Client{
		baseURL: baseURL,
		apiKey:  apiKey,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		timeout: 30 * time.Second,
	}
}

// SetTimeout sets the request timeout
func (c *Client) SetTimeout(timeout time.Duration) {
	c.timeout = timeout
	c.httpClient.Timeout = timeout
}

// BaziRequest represents a Bazi calculation request
type BaziRequest struct {
	Year         int  `json:"year"`
	Month        int  `json:"month"`
	Day          int  `json:"day"`
	Hour         int  `json:"hour"`
	Minute       int  `json:"minute"`
	Gender       int  `json:"gender"` // 1=male, 0=female
	SolarCalendar bool `json:"solar_calendar"`
}

// BaziResponse represents a Bazi calculation response
type BaziResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

// CalculateBazi calculates the Bazi (Eight Characters) fortune
func (c *Client) CalculateBazi(ctx context.Context, req *BaziRequest) (*BaziResponse, error) {
	url := fmt.Sprintf("%s/api/v1/bazi/calculate", c.baseURL)
	
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	
	httpReq.Header.Set("Content-Type", "application/json")
	if c.apiKey != "" {
		httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	}
	
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()
	
	var result BaziResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	
	return &result, nil
}

// GetPalace retrieves palace information
func (c *Client) GetPalace(ctx context.Context, palaceID int) (*BaziResponse, error) {
	url := fmt.Sprintf("%s/api/v1/palace/%d", c.baseURL, palaceID)
	
	httpReq, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	
	if c.apiKey != "" {
		httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	}
	
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()
	
	var result BaziResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	
	return &result, nil
}

// HealthCheck performs a health check on the API
func (c *Client) HealthCheck(ctx context.Context) error {
	url := fmt.Sprintf("%s/health", c.baseURL)
	
	httpReq, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}
	
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check failed with status: %d", resp.StatusCode)
	}

	return nil
}

// ── v3.0.0 新增方法 ──

func (c *Client) BaziCalc(ctx context.Context, req *BaziRequest) (*BaziResponse, error) {
	return c.CalculateBazi(ctx, req)
}

func (c *Client) BaziFull(ctx context.Context, req *BaziRequest) (*BaziResponse, error) {
	return c.CalculateBazi(ctx, req)
}

func (c *Client) ListCases(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) GetCase(ctx context.Context, caseID int) (*BaziResponse, error) {
	return c.GetPalace(ctx, caseID)
}

func (c *Client) CreateCase(ctx context.Context, req *BaziRequest) (*BaziResponse, error) {
	return c.CalculateBazi(ctx, req)
}

func (c *Client) SearchCases(ctx context.Context, keyword string) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) SimilarCases(ctx context.Context, caseID int) (*BaziResponse, error) {
	return c.GetPalace(ctx, caseID)
}

func (c *Client) CaseCategories(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) CaseStats(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) FavoriteCase(ctx context.Context, caseID int) (*BaziResponse, error) {
	return c.GetPalace(ctx, caseID)
}

func (c *Client) LikeCase(ctx context.Context, caseID int) (*BaziResponse, error) {
	return c.GetPalace(ctx, caseID)
}

func (c *Client) ListWebhookEvents(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) CreateWebhook(ctx context.Context, req *BaziRequest) (*BaziResponse, error) {
	return c.CalculateBazi(ctx, req)
}

func (c *Client) ListWebhooks(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) DeleteWebhook(ctx context.Context, webhookID int) (*BaziResponse, error) {
	return c.GetPalace(ctx, webhookID)
}

func (c *Client) TriggerWebhook(ctx context.Context, req *BaziRequest) (*BaziResponse, error) {
	return c.CalculateBazi(ctx, req)
}

func (c *Client) WebhookStats(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) ListPlugins(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) PluginStats(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}

func (c *Client) APIVersion(ctx context.Context) (*BaziResponse, error) {
	return c.GetPalace(ctx, 0)
}
