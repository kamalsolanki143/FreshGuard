package schemas

import (
	"context"
	"time"
)

// BifrostContext wraps context and request metadata passing through Bifrost.
type BifrostContext struct {
	Ctx         context.Context
	RequestID   string
	CreatedAt   time.Time
	ExtraFields map[string]any
}

// NewBifrostContext creates a new initialized BifrostContext.
func NewBifrostContext(ctx context.Context, requestID string) *BifrostContext {
	if ctx == nil {
		ctx = context.Background()
	}
	return &BifrostContext{
		Ctx:         ctx,
		RequestID:   requestID,
		CreatedAt:   time.Now().UTC(),
		ExtraFields: make(map[string]any),
	}
}

// Set stores a key-value pair in ExtraFields.
func (c *BifrostContext) Set(key string, val any) {
	if c.ExtraFields == nil {
		c.ExtraFields = make(map[string]any)
	}
	c.ExtraFields[key] = val
}

// Get retrieves a key-value pair from ExtraFields.
func (c *BifrostContext) Get(key string) (any, bool) {
	if c.ExtraFields == nil {
		return nil, false
	}
	val, ok := c.ExtraFields[key]
	return val, ok
}

// ChatMessage represents a single message in a chat completion request/response.
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
	Name    string `json:"name,omitempty"`
}

// BifrostRequest represents a normalized LLM request in Bifrost.
type BifrostRequest struct {
	ID          string         `json:"id"`
	Model       string         `json:"model"`
	Provider    string         `json:"provider"`
	Messages    []ChatMessage  `json:"messages"`
	Temperature *float64       `json:"temperature,omitempty"`
	Stream      bool           `json:"stream,omitempty"`
	ExtraFields map[string]any `json:"extra_fields,omitempty"`
}

// BifrostChoice represents a single generation choice in an LLM response.
type BifrostChoice struct {
	Index        int         `json:"index"`
	Message      ChatMessage `json:"message"`
	FinishReason string      `json:"finish_reason"`
}

// BifrostUsage represents token usage metadata.
type BifrostUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// BifrostResponse represents a normalized LLM response in Bifrost.
type BifrostResponse struct {
	ID          string         `json:"id"`
	Model       string         `json:"model"`
	Provider    string         `json:"provider"`
	Choices     []BifrostChoice `json:"choices"`
	Usage       BifrostUsage   `json:"usage"`
	CreatedAt   int64          `json:"created_at"`
	ExtraFields map[string]any `json:"extra_fields,omitempty"`
}

// CacheDebugInfo captures semantic cache hit information placed in ExtraFields by Bifrost semanticcache.
type CacheDebugInfo struct {
	CacheHit   bool    `json:"cache_hit"`
	HitType    string  `json:"hit_type"` // "direct" or "semantic"
	CacheID    string  `json:"cache_id"`
	Similarity float64 `json:"similarity"`
}

// BifrostStreamChunk represents a streaming chunk (SSE).
type BifrostStreamChunk struct {
	ID      string          `json:"id"`
	Choices []BifrostChoice `json:"choices"`
}

// BifrostError represents an error returned by Bifrost or upstream providers.
type BifrostError struct {
	Code           string `json:"code"`
	Message        string `json:"message"`
	StatusCode     int    `json:"status_code"`
	AllowFallbacks bool   `json:"allow_fallbacks"`
}

func (e *BifrostError) Error() string {
	if e == nil {
		return ""
	}
	return e.Message
}

// LLMPluginShortCircuit enables a plugin to halt the pipeline and return directly.
type LLMPluginShortCircuit struct {
	Response *BifrostResponse
	Stream   chan *BifrostStreamChunk
	Error    *BifrostError
}

// LLMPlugin is the core interface implemented by LLM plugins in Bifrost.
type LLMPlugin interface {
	GetName() string
	Init(config any) error
	PreLLMHook(ctx *BifrostContext, req *BifrostRequest) (*BifrostRequest, *LLMPluginShortCircuit, error)
	PostLLMHook(ctx *BifrostContext, resp *BifrostResponse, bifrostErr *BifrostError) (*BifrostResponse, *BifrostError, error)
}

