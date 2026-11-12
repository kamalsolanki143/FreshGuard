package client

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Verdict constants as defined in shared contracts.
const (
	VerdictSupported    = "supported"
	VerdictContradicted = "contradicted"
	VerdictUnclear      = "unclear"
)

// Status constants for verification lifecycle.
const (
	StatusAccepted  = "accepted"
	StatusCompleted = "completed"
	StatusFailed    = "failed"
)

// Category constants.
const (
	CategoryPricing         = "pricing"
	CategorySoftwareVersion = "software_version"
	CategoryLeadership      = "leadership"
)

// Evidence represents a piece of supporting or refuting evidence retrieved by Tavily.
type Evidence struct {
	EvidenceID  string    `json:"evidence_id"`
	SourceURL   string    `json:"source_url"`
	SourceTitle string    `json:"source_title"`
	Snippet     string    `json:"snippet"`
	PublishedAt *string   `json:"published_at,omitempty"`
	RetrievedAt time.Time `json:"retrieved_at"`
	SourceType  string    `json:"source_type"`
}

// Claim represents a structured time-sensitive statement extracted from an LLM response.
type Claim struct {
	ClaimID        string     `json:"claim_id"`
	Category       string     `json:"category"`
	Entity         string     `json:"entity"`
	Attribute      string     `json:"attribute"`
	OriginalText   string     `json:"original_text"`
	Verdict        string     `json:"verdict"`
	Confidence     float64    `json:"confidence"`
	Reason         string     `json:"reason,omitempty"`
	EvidenceIDs    []string   `json:"evidence_ids,omitempty"`
	CorrectedValue *string    `json:"corrected_value,omitempty"`
	CheckedAt      time.Time  `json:"checked_at"`
	Evidence       []Evidence `json:"evidence,omitempty"`
}

// APIError represents the safe cross-service error envelope.
type APIError struct {
	Code      string         `json:"code"`
	Message   string         `json:"message"`
	RequestID string         `json:"request_id"`
	Retryable bool           `json:"retryable"`
	Details   map[string]any `json:"details,omitempty"`
}

func (e *APIError) Error() string {
	if e == nil {
		return ""
	}
	return fmt.Sprintf("[%s] %s (request_id=%s, retryable=%t)", e.Code, e.Message, e.RequestID, e.Retryable)
}

// VerificationRequest payload submitted to POST /v1/verifications.
type VerificationRequest struct {
	RequestID  string   `json:"request_id"`
	Text       string   `json:"text"`
	Mode       string   `json:"mode"` // "blocking" or "async"
	Categories []string `json:"categories,omitempty"`
}

// VerificationResponse returned from POST /v1/verifications or GET /v1/verifications/{id}.
type VerificationResponse struct {
	VerificationID   string     `json:"verification_id"`
	RequestID        string     `json:"request_id"`
	Status           string     `json:"status"` // Lifecycle: "accepted", "completed", "failed"
	FreshnessStatus  *string    `json:"freshness_status,omitempty"` // "FRESH", "STALE", "UNCERTAIN", "NOT_REQUIRED"
	RequiresRefresh  bool       `json:"requires_refresh"`
	ClaimsChecked    int        `json:"claims_checked"`
	ProcessingTimeMs int        `json:"processing_time_ms"`
	ResultURL        string     `json:"result_url,omitempty"`
	CheckedAt        *time.Time `json:"checked_at,omitempty"`
	Claims           []Claim    `json:"claims,omitempty"`
	Error            *APIError  `json:"error,omitempty"`
}

// Config provides settings for VerificationClient.
type Config struct {
	BaseURL     string        `json:"base_url"`
	APIKey      string        `json:"api_key,omitempty"`
	Timeout     time.Duration `json:"timeout"`
	MaxRetries  int           `json:"max_retries"`
	BackoffBase time.Duration `json:"backoff_base"`
	FailOpen    bool          `json:"fail_open"`
}

// DefaultConfig provides production-ready defaults.
func DefaultConfig() Config {
	return Config{
		BaseURL:     "http://localhost:8000",
		Timeout:     3 * time.Second,
		MaxRetries:  2,
		BackoffBase: 100 * time.Millisecond,
		FailOpen:    true,
	}
}

// VerificationServiceClient defines the interface for communicating with Ayush's verification engine.
type VerificationServiceClient interface {
	Verify(ctx context.Context, req VerificationRequest) (*VerificationResponse, error)
	GetVerification(ctx context.Context, verificationID string, requestID string) (*VerificationResponse, error)
}

// Client implements VerificationServiceClient with bounded timeouts, retries, and correlation propagation.
type Client struct {
	httpClient *http.Client
	config     Config
}

// NewClient instantiates a new Client.
func NewClient(cfg Config, httpClient *http.Client) (*Client, error) {
	if cfg.BaseURL == "" {
		cfg.BaseURL = "http://localhost:8000"
	}
	parsedURL, err := url.Parse(cfg.BaseURL)
	if err != nil || parsedURL.Scheme == "" {
		return nil, fmt.Errorf("invalid verification service base_url: %s", cfg.BaseURL)
	}

	if cfg.Timeout <= 0 {
		cfg.Timeout = 3 * time.Second
	}
	if cfg.BackoffBase <= 0 {
		cfg.BackoffBase = 100 * time.Millisecond
	}

	if httpClient == nil {
		httpClient = &http.Client{
			Timeout: cfg.Timeout,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 20,
				IdleConnTimeout:     90 * time.Second,
			},
		}
	}

	return &Client{
		httpClient: httpClient,
		config:     cfg,
	}, nil
}

// Verify sends a verification request to the Python verification service with bounded retries.
func (c *Client) Verify(ctx context.Context, req VerificationRequest) (*VerificationResponse, error) {
	if req.RequestID == "" {
		return nil, errors.New("request_id is required")
	}
	if strings.TrimSpace(req.Text) == "" {
		return nil, errors.New("verification text cannot be empty")
	}
	if req.Mode == "" {
		req.Mode = "blocking"
	}

	endpoint := strings.TrimRight(c.config.BaseURL, "/") + "/v1/verifications"
	bodyBytes, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal verification request: %w", err)
	}

	var lastErr error
	maxAttempts := 1 + c.config.MaxRetries
	if maxAttempts < 1 {
		maxAttempts = 1
	}

	for attempt := 0; attempt < maxAttempts; attempt++ {
		if attempt > 0 {
			backoff := c.calculateBackoff(attempt)
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(backoff):
			}
		}

		httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(bodyBytes))
		if err != nil {
			return nil, fmt.Errorf("failed to construct http request: %w", err)
		}
		httpReq.Header.Set("Content-Type", "application/json")
		httpReq.Header.Set("Accept", "application/json")
		httpReq.Header.Set("X-Request-ID", req.RequestID)
		if c.config.APIKey != "" {
			httpReq.Header.Set("X-API-Key", c.config.APIKey)
		}

		resp, err := c.httpClient.Do(httpReq)
		if err != nil {
			lastErr = err
			// Network error or timeout is retryable
			continue
		}

		respBody, readErr := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		if readErr != nil {
			lastErr = fmt.Errorf("failed to read response body: %w", readErr)
			continue
		}

		if resp.StatusCode >= 200 && resp.StatusCode < 300 {
			var vResp VerificationResponse
			if err := json.Unmarshal(respBody, &vResp); err != nil {
				return nil, fmt.Errorf("malformed json from verification service: %w", err)
			}
			return &vResp, nil
		}

		// Handle error responses
		var apiErr APIError
		if err := json.Unmarshal(respBody, &apiErr); err == nil && apiErr.Code != "" {
			if apiErr.Retryable && attempt < maxAttempts-1 {
				lastErr = &apiErr
				continue
			}
			return nil, &apiErr
		}

		// Generic HTTP error
		isRetryable := resp.StatusCode == http.StatusTooManyRequests ||
			resp.StatusCode == http.StatusBadGateway ||
			resp.StatusCode == http.StatusServiceUnavailable ||
			resp.StatusCode == http.StatusGatewayTimeout

		lastErr = &APIError{
			Code:      fmt.Sprintf("HTTP_%d", resp.StatusCode),
			Message:   fmt.Sprintf("verification service returned status %d", resp.StatusCode),
			RequestID: req.RequestID,
			Retryable: isRetryable,
		}

		if !isRetryable {
			return nil, lastErr
		}
	}

	return nil, fmt.Errorf("verification service request failed after %d attempts: %w", maxAttempts, lastErr)
}

// GetVerification polls or retrieves a verification result by ID.
func (c *Client) GetVerification(ctx context.Context, verificationID string, requestID string) (*VerificationResponse, error) {
	if verificationID == "" {
		return nil, errors.New("verification_id is required")
	}

	endpoint := fmt.Sprintf("%s/v1/verifications/%s", strings.TrimRight(c.config.BaseURL, "/"), url.PathEscape(verificationID))
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create get request: %w", err)
	}
	httpReq.Header.Set("Accept", "application/json")
	if requestID != "" {
		httpReq.Header.Set("X-Request-ID", requestID)
	}
	if c.config.APIKey != "" {
		httpReq.Header.Set("X-API-Key", c.config.APIKey)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to get verification %s: %w", verificationID, err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		var vResp VerificationResponse
		if err := json.Unmarshal(respBody, &vResp); err != nil {
			return nil, fmt.Errorf("malformed json from verification service: %w", err)
		}
		return &vResp, nil
	}

	var apiErr APIError
	if err := json.Unmarshal(respBody, &apiErr); err == nil && apiErr.Code != "" {
		return nil, &apiErr
	}

	return nil, &APIError{
		Code:      fmt.Sprintf("HTTP_%d", resp.StatusCode),
		Message:   fmt.Sprintf("verification retrieval returned status %d", resp.StatusCode),
		RequestID: requestID,
		Retryable: false,
	}
}

// calculateBackoff computes exponential backoff with 20% jitter.
func (c *Client) calculateBackoff(attempt int) time.Duration {
	multiplier := 1 << (attempt - 1)
	base := float64(c.config.BackoffBase) * float64(multiplier)
	jitter := base * (rand.Float64()*0.4 - 0.2) // +/- 20%
	d := time.Duration(base + jitter)
	if d < 10*time.Millisecond {
		d = 10 * time.Millisecond
	}
	return d
}

