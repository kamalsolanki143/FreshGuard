package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/kamalsolanki143/FreshGuard/plugin/cache"
	"github.com/kamalsolanki143/FreshGuard/plugin/client"
	"github.com/kamalsolanki143/FreshGuard/plugin/hooks"
	"github.com/kamalsolanki143/FreshGuard/plugin/schemas"
)

// FullGatewayTestHarness simulates a Bifrost gateway instance with FreshGuard plugin.
type FullGatewayTestHarness struct {
	plugin           *hooks.FreshGuardPlugin
	pythonSvcServer  *httptest.Server
	bifrostAPIServer *httptest.Server
	evictedCacheIDs  []string
	mu               sync.Mutex
	pythonReqCount   int32
}

func setupHarness(t *testing.T, failOpen bool) *FullGatewayTestHarness {
	harness := &FullGatewayTestHarness{
		evictedCacheIDs: make([]string, 0),
	}

	// 1. Mock Bifrost Management API (for cache eviction)
	harness.bifrostAPIServer = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodDelete {
			harness.mu.Lock()
			// Extract cacheID from URL /api/cache/clear/{cacheId}
			parts := r.URL.Path
			harness.evictedCacheIDs = append(harness.evictedCacheIDs, parts)
			harness.mu.Unlock()
			w.WriteHeader(http.StatusOK)
			return
		}
		w.WriteHeader(http.StatusNotFound)
	}))

	// 2. Mock Python Verification Service
	harness.pythonSvcServer = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&harness.pythonReqCount, 1)

		if r.Method != http.MethodPost || r.URL.Path != "/v1/verifications" {
			w.WriteHeader(http.StatusNotFound)
			return
		}

		var req client.VerificationRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			_ = json.NewEncoder(w).Encode(client.APIError{
				Code:      "INVALID_JSON",
				Message:   "Bad JSON payload",
				RequestID: req.RequestID,
				Retryable: false,
			})
			return
		}

		now := time.Now().UTC()
		var verdict = client.VerdictSupported
		if req.Text == "Contradicted claim text" {
			verdict = client.VerdictContradicted
		} else if req.Text == "Ambiguous claim text" {
			verdict = client.VerdictUnclear
		}

		resp := client.VerificationResponse{
			VerificationID: "ver-harness-" + req.RequestID,
			RequestID:      req.RequestID,
			Status:         client.StatusCompleted,
			CheckedAt:      &now,
			Claims: []client.Claim{
				{
					ClaimID:      "claim-1",
					Category:     client.CategoryPricing,
					Entity:       "TestEntity",
					Attribute:    "pricing",
					OriginalText: req.Text,
					Verdict:      verdict,
					Confidence:   0.95,
					CheckedAt:    now,
					Evidence: []client.Evidence{
						{
							EvidenceID:  "ev-1",
							SourceURL:   "https://example.com/pricing",
							SourceTitle: "Example Pricing",
							Snippet:     "Verified evidence snippet",
							RetrievedAt: now,
							SourceType:  "official_docs",
						},
					},
				},
			},
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(resp)
	}))

	// 3. Initialize FreshGuard Plugin
	cfg := hooks.PluginConfig{
		VerificationServiceURL: harness.pythonSvcServer.URL,
		Timeout:                2 * time.Second,
		MaxRetries:             1,
		FailOpen:               failOpen,
		BifrostURL:             harness.bifrostAPIServer.URL,
		EnableCacheEviction:    true,
		ReverifyOnCacheHit:     true,
		Categories: []string{
			client.CategoryPricing,
			client.CategorySoftwareVersion,
			client.CategoryLeadership,
		},
	}

	harness.plugin = hooks.NewPlugin(cfg, nil, nil, nil)
	return harness
}

func (h *FullGatewayTestHarness) Close() {
	h.pythonSvcServer.Close()
	h.bifrostAPIServer.Close()
}

// TestEndToEnd_CacheMiss_ThenCacheHit verifies the entire flow:
// 1. Initial request misses cache -> calls verification service -> attaches freshness metadata.
// 2. Second request hits cache -> Evaluator detects fresh metadata -> returns cached fresh response without re-calling verification service.
func TestEndToEnd_CacheMiss_ThenCacheHit(t *testing.T) {
	harness := setupHarness(t, true)
	defer harness.Close()

	// --- Step 1: Initial Cache Miss ---
	ctx1 := schemas.NewBifrostContext(context.Background(), "req-e2e-1")
	req1 := &schemas.BifrostRequest{
		ID:    "req-e2e-1",
		Model: "gpt-4",
		Messages: []schemas.ChatMessage{
			{Role: "user", Content: "What is the pricing of Example Pro?"},
		},
	}

	// PreLLMHook
	req1, shortCircuit, err := harness.plugin.PreLLMHook(ctx1, req1)
	if err != nil || shortCircuit != nil {
		t.Fatalf("unexpected PreLLMHook failure: %v", err)
	}

	// Simulate Provider LLM Response (Cache Miss)
	providerResp1 := &schemas.BifrostResponse{
		ID:    "resp-e2e-1",
		Model: "gpt-4",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Example Pro is $50/month.",
				},
			},
		},
		ExtraFields: map[string]any{
			"cache_debug": map[string]any{
				"cache_hit": false,
			},
		},
	}

	// PostLLMHook
	outResp1, bifrostErr, err := harness.plugin.PostLLMHook(ctx1, providerResp1, nil)
	if err != nil || bifrostErr != nil {
		t.Fatalf("unexpected PostLLMHook failure: %v", err)
	}

	fg1, ok := outResp1.ExtraFields["freshguard"].(map[string]any)
	if !ok || fg1["status"] != "verified" || fg1["is_fresh"] != true {
		t.Fatalf("expected verified fresh response on cache miss, got %v", fg1)
	}
	if atomic.LoadInt32(&harness.pythonReqCount) != 1 {
		t.Errorf("expected 1 call to Python verification service, got %d", harness.pythonReqCount)
	}

	// --- Step 2: Semantic Cache Hit (Immediately Afterwards) ---
	ctx2 := schemas.NewBifrostContext(context.Background(), "req-e2e-2")
	req2 := &schemas.BifrostRequest{
		ID:    "req-e2e-2",
		Model: "gpt-4",
		Messages: []schemas.ChatMessage{
			{Role: "user", Content: "How much does Example Pro cost?"},
		},
	}

	// PreLLMHook
	req2, shortCircuit, err = harness.plugin.PreLLMHook(ctx2, req2)
	if err != nil || shortCircuit != nil {
		t.Fatalf("unexpected PreLLMHook failure: %v", err)
	}

	// Simulate Bifrost Semantic Cache Hit
	cachedResp := &schemas.BifrostResponse{
		ID:    "resp-e2e-2",
		Model: "gpt-4",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Example Pro is $50/month.",
				},
			},
		},
		ExtraFields: map[string]any{
			"cache_debug": map[string]any{
				"cache_hit": true,
				"hit_type":  "semantic",
				"cache_id":  "cache-entry-50",
			},
		},
	}

	outResp2, bifrostErr, err := harness.plugin.PostLLMHook(ctx2, cachedResp, nil)
	if err != nil || bifrostErr != nil {
		t.Fatalf("unexpected PostLLMHook failure: %v", err)
	}

	fg2, ok := outResp2.ExtraFields["freshguard"].(map[string]any)
	if !ok {
		t.Fatalf("freshguard metadata missing on cache hit")
	}
	if fg2["is_fresh"] != true {
		t.Errorf("expected is_fresh true on unexpired cache hit, got %v", fg2["is_fresh"])
	}
	// Python service should NOT have been called again
	if atomic.LoadInt32(&harness.pythonReqCount) != 1 {
		t.Errorf("expected no additional call to Python service for fresh cache hit, got %d", harness.pythonReqCount)
	}
}

// TestEndToEnd_CacheHit_ExpiredTriggersEvictionAndReverification verifies:
// When an expired cache hit is intercepted, FreshGuard evicts the entry in Bifrost and re-verifies.
func TestEndToEnd_CacheHit_ExpiredTriggersEvictionAndReverification(t *testing.T) {
	harness := setupHarness(t, true)
	defer harness.Close()

	// Seed an expired entry (>24h old for pricing)
	expiredTime := time.Now().UTC().Add(-26 * time.Hour)
	evaluator := cache.NewEvaluator(cache.NewDefaultPolicy(), cache.NewLedger(0))
	evaluator.RecordVerification("expired-cache-id", "Old pricing response.", &client.VerificationResponse{
		VerificationID: "ver-old",
		RequestID:      "req-old",
		Status:         client.StatusCompleted,
		CheckedAt:      &expiredTime,
		Claims: []client.Claim{
			{
				ClaimID:   "c-old",
				Category:  client.CategoryPricing,
				Verdict:   client.VerdictSupported,
				CheckedAt: expiredTime,
			},
		},
	})

	cfg := hooks.PluginConfig{
		VerificationServiceURL: harness.pythonSvcServer.URL,
		Timeout:                2 * time.Second,
		MaxRetries:             1,
		FailOpen:               true,
		BifrostURL:             harness.bifrostAPIServer.URL,
		EnableCacheEviction:    true,
		ReverifyOnCacheHit:     true,
		Categories:             []string{client.CategoryPricing},
	}
	plugin := hooks.NewPlugin(cfg, nil, evaluator, nil)

	ctx := schemas.NewBifrostContext(context.Background(), "req-expired-check")
	resp := &schemas.BifrostResponse{
		ID: "resp-expired-check",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Old pricing response.",
				},
			},
		},
		ExtraFields: map[string]any{
			"cache_debug": map[string]any{
				"cache_hit": true,
				"cache_id":  "expired-cache-id",
			},
		},
	}

	outResp, bifrostErr, err := plugin.PostLLMHook(ctx, resp, nil)
	if err != nil || bifrostErr != nil {
		t.Fatalf("unexpected hook error: %v, %v", err, bifrostErr)
	}

	// 1. Verify eviction was triggered against Bifrost management API
	harness.mu.Lock()
	evictedCount := len(harness.evictedCacheIDs)
	harness.mu.Unlock()
	if evictedCount == 0 {
		t.Error("expected eviction endpoint to be called for expired cache hit")
	}

	// 2. Verify re-verification was performed
	fg := outResp.ExtraFields["freshguard"].(map[string]any)
	if fg["status"] != "reverified" {
		t.Errorf("expected status reverified, got %v", fg["status"])
	}
	if fg["is_fresh"] != true {
		t.Errorf("expected is_fresh true after reverification, got %v", fg["is_fresh"])
	}
}

// TestEndToEnd_FailOpenVsFailClosed verifies failure policies when the verification service is unreachable.
func TestEndToEnd_FailOpenVsFailClosed(t *testing.T) {
	// Unreachable server
	badConfig := hooks.PluginConfig{
		VerificationServiceURL: "http://127.0.0.1:59999", // dead port
		Timeout:                50 * time.Millisecond,
		MaxRetries:             0,
		FailOpen:               true,
	}

	// --- 1. Fail Open Test ---
	pluginFailOpen := hooks.NewPlugin(badConfig, nil, nil, nil)
	ctx1 := schemas.NewBifrostContext(context.Background(), "req-fo")
	resp1 := &schemas.BifrostResponse{
		ID: "resp-fo",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Provider response content.",
				},
			},
		},
	}

	outResp1, bifrostErr1, err1 := pluginFailOpen.PostLLMHook(ctx1, resp1, nil)
	if err1 != nil || bifrostErr1 != nil {
		t.Fatalf("expected fail-open to return response without error, got err=%v bifrostErr=%v", err1, bifrostErr1)
	}
	if outResp1 == nil {
		t.Fatal("expected original response to be preserved in fail-open mode")
	}
	fg1 := outResp1.ExtraFields["freshguard"].(map[string]any)
	if fg1["status"] != "unverified" || fg1["is_fresh"] != false {
		t.Errorf("expected unverified status in fail-open mode, got %v", fg1)
	}

	// --- 2. Fail Closed Test ---
	badConfig.FailOpen = false
	pluginFailClosed := hooks.NewPlugin(badConfig, nil, nil, nil)
	ctx2 := schemas.NewBifrostContext(context.Background(), "req-fc")
	resp2 := &schemas.BifrostResponse{
		ID: "resp-fc",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Provider response content.",
				},
			},
		},
	}

	outResp2, bifrostErr2, err2 := pluginFailClosed.PostLLMHook(ctx2, resp2, nil)
	if err2 != nil {
		t.Fatalf("unexpected go error: %v", err2)
	}
	if outResp2 != nil {
		t.Error("expected nil response in fail-closed mode")
	}
	if bifrostErr2 == nil || bifrostErr2.Code != "VERIFICATION_FAILED" {
		t.Fatalf("expected BifrostError VERIFICATION_FAILED in fail-closed mode, got %v", bifrostErr2)
	}
}

// TestEndToEnd_CorrelationIDTracking verifies request ID preservation through the lifecycle.
func TestEndToEnd_CorrelationIDTracking(t *testing.T) {
	harness := setupHarness(t, true)
	defer harness.Close()

	customID := "custom-corr-uuid-9999"
	ctx := schemas.NewBifrostContext(context.Background(), customID)
	req := &schemas.BifrostRequest{
		ID: customID,
		Messages: []schemas.ChatMessage{
			{Role: "user", Content: "What is OpenAI leadership?"},
		},
	}

	req, _, err := harness.plugin.PreLLMHook(ctx, req)
	if err != nil {
		t.Fatalf("PreLLMHook failed: %v", err)
	}
	if ctx.RequestID != customID {
		t.Errorf("expected correlation ID %s preserved, got %s", customID, ctx.RequestID)
	}

	resp := &schemas.BifrostResponse{
		ID: "resp-corr-test",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "OpenAI CEO is Sam Altman.",
				},
			},
		},
	}

	outResp, _, err := harness.plugin.PostLLMHook(ctx, resp, nil)
	if err != nil {
		t.Fatalf("PostLLMHook failed: %v", err)
	}

	fg := outResp.ExtraFields["freshguard"].(map[string]any)
	if fg["status"] != "verified" {
		t.Errorf("expected verified response, got %v", fg["status"])
	}
}

