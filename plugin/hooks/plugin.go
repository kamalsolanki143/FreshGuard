package hooks

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/kamalsolanki143/FreshGuard/plugin/cache"
	"github.com/kamalsolanki143/FreshGuard/plugin/client"
	"github.com/kamalsolanki143/FreshGuard/plugin/schemas"
)

// PluginConfig represents the configuration options for FreshGuard plugin.
type PluginConfig struct {
	VerificationServiceURL string        `json:"verification_service_url"`
	Timeout                time.Duration `json:"timeout"`
	MaxRetries             int           `json:"max_retries"`
	FailOpen               bool          `json:"fail_open"`
	BifrostURL             string        `json:"bifrost_url"`
	EnableCacheEviction    bool          `json:"enable_cache_eviction"`
	ReverifyOnCacheHit     bool          `json:"reverify_on_cache_hit"`
	Categories             []string      `json:"categories"`
}

// DefaultPluginConfig returns the default configuration.
func DefaultPluginConfig() PluginConfig {
	return PluginConfig{
		VerificationServiceURL: "http://localhost:8000",
		Timeout:                3 * time.Second,
		MaxRetries:             2,
		FailOpen:               true,
		BifrostURL:             "http://localhost:8080",
		EnableCacheEviction:    true,
		ReverifyOnCacheHit:     true,
		Categories: []string{
			client.CategoryPricing,
			client.CategorySoftwareVersion,
			client.CategoryLeadership,
		},
	}
}

// FreshGuardPlugin implements Bifrost's schemas.LLMPlugin interface.
type FreshGuardPlugin struct {
	name      string
	config    PluginConfig
	client    client.VerificationServiceClient
	evaluator *cache.Evaluator
	evictor   cache.Evictor
}

// NewPlugin creates an initialized FreshGuardPlugin.
func NewPlugin(
	cfg PluginConfig,
	vClient client.VerificationServiceClient,
	evaluator *cache.Evaluator,
	evictor cache.Evictor,
) *FreshGuardPlugin {
	if cfg.Timeout <= 0 {
		cfg.Timeout = 3 * time.Second
	}
	if vClient == nil {
		c, _ := client.NewClient(client.Config{
			BaseURL:     cfg.VerificationServiceURL,
			Timeout:     cfg.Timeout,
			MaxRetries:  cfg.MaxRetries,
			FailOpen:    cfg.FailOpen,
		}, nil)
		vClient = c
	}
	if evaluator == nil {
		evaluator = cache.NewEvaluator(cache.NewDefaultPolicy(), cache.NewLedger(0))
	}
	if evictor == nil && cfg.BifrostURL != "" {
		evictor = cache.NewBifrostEvictor(cfg.BifrostURL, nil)
	}

	return &FreshGuardPlugin{
		name:      "freshguard",
		config:    cfg,
		client:    vClient,
		evaluator: evaluator,
		evictor:   evictor,
	}
}

// GetName returns the plugin's unique identifier in Bifrost.
func (p *FreshGuardPlugin) GetName() string {
	return p.name
}

// Init parses configuration and boots the plugin.
func (p *FreshGuardPlugin) Init(rawConfig any) error {
	cfg := DefaultPluginConfig()

	if rawConfig != nil {
		jsonBytes, err := json.Marshal(rawConfig)
		if err != nil {
			return fmt.Errorf("failed to parse freshguard plugin config: %w", err)
		}
		if err := json.Unmarshal(jsonBytes, &cfg); err != nil {
			return fmt.Errorf("failed to unmarshal freshguard plugin config: %w", err)
		}
	}

	p.config = cfg

	c, err := client.NewClient(client.Config{
		BaseURL:     cfg.VerificationServiceURL,
		Timeout:     cfg.Timeout,
		MaxRetries:  cfg.MaxRetries,
		FailOpen:    cfg.FailOpen,
	}, nil)
	if err != nil {
		return fmt.Errorf("failed to init verification client: %w", err)
	}
	p.client = c

	p.evaluator = cache.NewEvaluator(cache.NewDefaultPolicy(), cache.NewLedger(0))
	if cfg.BifrostURL != "" {
		p.evictor = cache.NewBifrostEvictor(cfg.BifrostURL, nil)
	}

	return nil
}

// PreLLMHook runs sequentially before requests reach LLM providers or semantic cache.
// It ensures request correlation IDs are generated and tagged.
func (p *FreshGuardPlugin) PreLLMHook(
	ctx *schemas.BifrostContext,
	req *schemas.BifrostRequest,
) (*schemas.BifrostRequest, *schemas.LLMPluginShortCircuit, error) {
	if ctx == nil {
		ctx = schemas.NewBifrostContext(context.Background(), "")
	}

	// Propagate or generate RequestID
	if ctx.RequestID == "" {
		if req != nil && req.ID != "" {
			ctx.RequestID = req.ID
		} else {
			ctx.RequestID = generateCorrelationID()
		}
	}

	ctx.Set("freshguard_request_id", ctx.RequestID)
	ctx.Set("freshguard_start_time", time.Now().UTC())

	return req, nil, nil
}

// PostLLMHook runs after LLM response or cache hit.
// Enforces freshness verification, prevents stale cache reuse, and updates metadata.
func (p *FreshGuardPlugin) PostLLMHook(
	ctx *schemas.BifrostContext,
	resp *schemas.BifrostResponse,
	bifrostErr *schemas.BifrostError,
) (*schemas.BifrostResponse, *schemas.BifrostError, error) {
	// If upstream had an unhandled error and no response was produced, pass through
	if resp == nil {
		return resp, bifrostErr, nil
	}

	if resp.ExtraFields == nil {
		resp.ExtraFields = make(map[string]any)
	}

	reqID := ""
	if ctx != nil {
		reqID = ctx.RequestID
	}
	if reqID == "" {
		reqID = resp.ID
	}

	// Check for Bifrost semantic cache hit indicators
	cacheID, isCacheHit := detectCacheHit(resp)
	responseText := extractResponseText(resp)

	// If response is empty, nothing to verify
	if strings.TrimSpace(responseText) == "" {
		return resp, bifrostErr, nil
	}

	now := time.Now().UTC()

	// --- PATH A: Cache Hit Evaluation ---
	if isCacheHit {
		evalRes := p.evaluator.EvaluateCacheHit(cacheID, responseText, now)

		if evalRes.IsFresh {
			// Response is confirmed fresh within valid TTL
			resp.ExtraFields["freshguard"] = map[string]any{
				"status":                  "cached_fresh",
				"is_fresh":                true,
				"reverification_required": false,
				"cache_id":                cacheID,
				"checked_at":              evalRes.Metadata.CheckedAt,
				"expires_at":              evalRes.Metadata.ExpiresAt,
				"claims":                  evalRes.Metadata.Claims,
			}
			return resp, nil, nil
		}

		// STALE, EXPIRED, OR MISSING METADATA:
		// Rule: Expired or missing metadata requires re-verification. Cache hit cannot silently inherit expired verdict.
		if p.config.EnableCacheEviction && evalRes.ShouldEvict && p.evictor != nil && cacheID != "" {
			// Trigger eviction of stale entry in Bifrost semantic cache
			_ = p.evictor.EvictByCacheID(ctx.Ctx, cacheID)
		}

		if p.config.ReverifyOnCacheHit {
			// Re-verify the cached text
			vResp, err := p.client.Verify(ctx.Ctx, client.VerificationRequest{
				RequestID:  reqID,
				Text:       responseText,
				Mode:       "blocking",
				Categories: p.config.Categories,
			})
			if err == nil && vResp != nil && vResp.Status == client.StatusCompleted {
				// Successfully re-verified! Update ledger
				newMeta := p.evaluator.RecordVerification(cacheID, responseText, vResp)
				resp.ExtraFields["freshguard"] = map[string]any{
					"status":                  "reverified",
					"is_fresh":                true,
					"reverification_required": false,
					"cache_id":                cacheID,
					"verification_id":         vResp.VerificationID,
					"checked_at":              newMeta.CheckedAt,
					"expires_at":              newMeta.ExpiresAt,
					"claims":                  newMeta.Claims,
				}
				return resp, nil, nil
			}
		}

		// Re-verification was not attempted, or failed: mark explicitly unverified/stale
		resp.ExtraFields["freshguard"] = map[string]any{
			"status":                  "stale_cache_hit",
			"is_fresh":                false,
			"reverification_required": true,
			"reason":                  evalRes.Reason,
			"cache_id":                cacheID,
			"verdict":                 evalRes.Verdict,
		}
		return resp, nil, nil
	}

	// --- PATH B: Cache Miss (Fresh Provider Response) ---
	vResp, err := p.client.Verify(ctx.Ctx, client.VerificationRequest{
		RequestID:  reqID,
		Text:       responseText,
		Mode:       "blocking",
		Categories: p.config.Categories,
	})

	if err != nil || vResp == nil || vResp.Status == client.StatusFailed {
		// Verification failed or timed out
		if p.config.FailOpen {
			// Fail-open: serve the response but clearly annotate as unverified
			errMsg := "verification service unavailable or timed out"
			if err != nil {
				errMsg = err.Error()
			}
			resp.ExtraFields["freshguard"] = map[string]any{
				"status":                  "unverified",
				"is_fresh":                false,
				"reverification_required": true,
				"error":                   errMsg,
			}
			return resp, nil, nil
		}

		// Fail-closed: block unverified response
		return nil, &schemas.BifrostError{
			Code:           "VERIFICATION_FAILED",
			Message:        fmt.Sprintf("FreshGuard verification failed: %v", err),
			StatusCode:     502,
			AllowFallbacks: false,
		}, nil
	}

	// Record metadata for downstream cache hits
	meta := p.evaluator.RecordVerification(cacheID, responseText, vResp)

	resp.ExtraFields["freshguard"] = map[string]any{
		"status":                  "verified",
		"is_fresh":                true,
		"reverification_required": false,
		"verification_id":         vResp.VerificationID,
		"checked_at":              meta.CheckedAt,
		"expires_at":              meta.ExpiresAt,
		"policy_ttl":              meta.PolicyTTL.String(),
		"claims":                  meta.Claims,
	}

	return resp, nil, nil
}

// detectCacheHit inspects Bifrost ExtraFields (such as extra_fields.cache_debug) for cache hit indicators.
func detectCacheHit(resp *schemas.BifrostResponse) (string, bool) {
	if resp.ExtraFields == nil {
		return "", false
	}

	// Check cache_debug map
	if rawDebug, ok := resp.ExtraFields["cache_debug"]; ok {
		if debugMap, ok := rawDebug.(map[string]any); ok {
			if hit, ok := debugMap["cache_hit"].(bool); ok && hit {
				cacheID, _ := debugMap["cache_id"].(string)
				return cacheID, true
			}
		}
		if debugInfo, ok := rawDebug.(*schemas.CacheDebugInfo); ok && debugInfo != nil {
			if debugInfo.CacheHit {
				return debugInfo.CacheID, true
			}
		}
	}

	// Check direct cache_hit flag
	if hit, ok := resp.ExtraFields["cache_hit"].(bool); ok && hit {
		cacheID, _ := resp.ExtraFields["cache_id"].(string)
		return cacheID, true
	}

	return "", false
}

// extractResponseText extracts the generated message content from BifrostResponse Choices.
func extractResponseText(resp *schemas.BifrostResponse) string {
	if len(resp.Choices) == 0 {
		return ""
	}
	var sb strings.Builder
	for _, choice := range resp.Choices {
		if choice.Message.Content != "" {
			if sb.Len() > 0 {
				sb.WriteString("\n")
			}
			sb.WriteString(choice.Message.Content)
		}
	}
	return sb.String()
}

// generateCorrelationID produces a random hex string for request correlation.
func generateCorrelationID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

