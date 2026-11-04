package hooks

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/kamalsolanki143/FreshGuard/plugin/cache"
	"github.com/kamalsolanki143/FreshGuard/plugin/client"
	"github.com/kamalsolanki143/FreshGuard/plugin/schemas"
)

// MockVerificationClient implements client.VerificationServiceClient for testing.
type MockVerificationClient struct {
	VerifyFunc func(ctx context.Context, req client.VerificationRequest) (*client.VerificationResponse, error)
}

func (m *MockVerificationClient) Verify(ctx context.Context, req client.VerificationRequest) (*client.VerificationResponse, error) {
	if m.VerifyFunc != nil {
		return m.VerifyFunc(ctx, req)
	}
	return nil, errors.New("not implemented")
}

func (m *MockVerificationClient) GetVerification(ctx context.Context, verificationID string, requestID string) (*client.VerificationResponse, error) {
	return nil, nil
}

// MockEvictor implements cache.Evictor for testing.
type MockEvictor struct {
	EvictedIDs  []string
	EvictedKeys []string
}

func (m *MockEvictor) EvictByCacheID(ctx context.Context, cacheID string) error {
	m.EvictedIDs = append(m.EvictedIDs, cacheID)
	return nil
}

func (m *MockEvictor) EvictByCacheKey(ctx context.Context, cacheKey string) error {
	m.EvictedKeys = append(m.EvictedKeys, cacheKey)
	return nil
}

func TestPlugin_GetName(t *testing.T) {
	p := NewPlugin(DefaultPluginConfig(), nil, nil, nil)
	if p.GetName() != "freshguard" {
		t.Errorf("expected plugin name freshguard, got %s", p.GetName())
	}
}

func TestPlugin_PreLLMHook_CorrelationID(t *testing.T) {
	p := NewPlugin(DefaultPluginConfig(), nil, nil, nil)

	// Test 1: Generate missing ID
	ctx1 := schemas.NewBifrostContext(context.Background(), "")
	req1 := &schemas.BifrostRequest{ID: ""}
	_, _, err := p.PreLLMHook(ctx1, req1)
	if err != nil {
		t.Fatalf("PreLLMHook error: %v", err)
	}
	if ctx1.RequestID == "" {
		t.Error("expected generated RequestID in context, got empty")
	}

	// Test 2: Preserve existing ID
	ctx2 := schemas.NewBifrostContext(context.Background(), "existing-123")
	_, _, err = p.PreLLMHook(ctx2, req1)
	if err != nil {
		t.Fatalf("PreLLMHook error: %v", err)
	}
	if ctx2.RequestID != "existing-123" {
		t.Errorf("expected existing-123, got %s", ctx2.RequestID)
	}
}

func TestPlugin_PostLLMHook_CacheMiss_Success(t *testing.T) {
	now := time.Now().UTC()
	mockClient := &MockVerificationClient{
		VerifyFunc: func(ctx context.Context, req client.VerificationRequest) (*client.VerificationResponse, error) {
			return &client.VerificationResponse{
				VerificationID: "ver-100",
				RequestID:      req.RequestID,
				Status:         client.StatusCompleted,
				CheckedAt:      &now,
				Claims: []client.Claim{
					{
						ClaimID:    "c-100",
						Category:   client.CategoryPricing,
						Entity:     "OpenAI GPT-4",
						Verdict:    client.VerdictSupported,
						Confidence: 0.99,
						CheckedAt:  now,
					},
				},
			}, nil
		},
	}

	evaluator := cache.NewEvaluator(cache.NewDefaultPolicy(), cache.NewLedger(0))
	evictor := &MockEvictor{}
	p := NewPlugin(DefaultPluginConfig(), mockClient, evaluator, evictor)

	ctx := schemas.NewBifrostContext(context.Background(), "req-100")
	resp := &schemas.BifrostResponse{
		ID: "resp-100",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "OpenAI GPT-4 pricing is $20/month.",
				},
			},
		},
	}

	outResp, bifrostErr, err := p.PostLLMHook(ctx, resp, nil)
	if err != nil || bifrostErr != nil {
		t.Fatalf("unexpected hook error: %v, %v", err, bifrostErr)
	}

	fg, ok := outResp.ExtraFields["freshguard"].(map[string]any)
	if !ok {
		t.Fatalf("freshguard metadata missing in ExtraFields")
	}
	if fg["status"] != "verified" {
		t.Errorf("expected status verified, got %v", fg["status"])
	}
	if fg["is_fresh"] != true {
		t.Errorf("expected is_fresh true, got %v", fg["is_fresh"])
	}
}

func TestPlugin_PostLLMHook_CacheMiss_FailOpen(t *testing.T) {
	mockClient := &MockVerificationClient{
		VerifyFunc: func(ctx context.Context, req client.VerificationRequest) (*client.VerificationResponse, error) {
			return nil, errors.New("verification service connection refused")
		},
	}

	cfg := DefaultPluginConfig()
	cfg.FailOpen = true
	p := NewPlugin(cfg, mockClient, nil, nil)

	ctx := schemas.NewBifrostContext(context.Background(), "req-failopen")
	resp := &schemas.BifrostResponse{
		ID: "resp-failopen",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Some unverified statement.",
				},
			},
		},
	}

	outResp, bifrostErr, err := p.PostLLMHook(ctx, resp, nil)
	if err != nil || bifrostErr != nil {
		t.Fatalf("expected fail-open to return response without error, got err=%v bifrostErr=%v", err, bifrostErr)
	}

	fg := outResp.ExtraFields["freshguard"].(map[string]any)
	if fg["status"] != "unverified" {
		t.Errorf("expected status unverified, got %v", fg["status"])
	}
	if fg["is_fresh"] != false {
		t.Errorf("expected is_fresh false, got %v", fg["is_fresh"])
	}
}

func TestPlugin_PostLLMHook_CacheMiss_FailClosed(t *testing.T) {
	mockClient := &MockVerificationClient{
		VerifyFunc: func(ctx context.Context, req client.VerificationRequest) (*client.VerificationResponse, error) {
			return nil, errors.New("timeout connecting to verification service")
		},
	}

	cfg := DefaultPluginConfig()
	cfg.FailOpen = false
	p := NewPlugin(cfg, mockClient, nil, nil)

	ctx := schemas.NewBifrostContext(context.Background(), "req-failclosed")
	resp := &schemas.BifrostResponse{
		ID: "resp-failclosed",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Some statement.",
				},
			},
		},
	}

	outResp, bifrostErr, err := p.PostLLMHook(ctx, resp, nil)
	if err != nil {
		t.Fatalf("unexpected go error: %v", err)
	}
	if outResp != nil {
		t.Error("expected nil response in fail-closed mode")
	}
	if bifrostErr == nil {
		t.Fatal("expected bifrost error in fail-closed mode, got nil")
	}
	if bifrostErr.Code != "VERIFICATION_FAILED" {
		t.Errorf("expected code VERIFICATION_FAILED, got %s", bifrostErr.Code)
	}
}

func TestPlugin_PostLLMHook_CacheHit_Fresh(t *testing.T) {
	now := time.Now().UTC()
	ledger := cache.NewLedger(0)
	evaluator := cache.NewEvaluator(cache.NewDefaultPolicy(), ledger)

	// Pre-seed fresh verification in ledger
	vResp := &client.VerificationResponse{
		VerificationID: "ver-fresh-hit",
		RequestID:      "req-original",
		Status:         client.StatusCompleted,
		CheckedAt:      &now,
		Claims: []client.Claim{
			{
				ClaimID:   "c-1",
				Category:  client.CategoryPricing,
				Verdict:   client.VerdictSupported,
				CheckedAt: now,
			},
		},
	}
	evaluator.RecordVerification("cache-entry-1", "Cached content is fresh.", vResp)

	p := NewPlugin(DefaultPluginConfig(), nil, evaluator, nil)

	ctx := schemas.NewBifrostContext(context.Background(), "req-cache-hit")
	resp := &schemas.BifrostResponse{
		ID: "resp-cache-hit",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Cached content is fresh.",
				},
			},
		},
		ExtraFields: map[string]any{
			"cache_debug": map[string]any{
				"cache_hit": true,
				"cache_id":  "cache-entry-1",
				"hit_type":  "direct",
			},
		},
	}

	outResp, bifrostErr, err := p.PostLLMHook(ctx, resp, nil)
	if err != nil || bifrostErr != nil {
		t.Fatalf("unexpected hook error: %v, %v", err, bifrostErr)
	}

	fg := outResp.ExtraFields["freshguard"].(map[string]any)
	if fg["status"] != "cached_fresh" {
		t.Errorf("expected status cached_fresh, got %v", fg["status"])
	}
	if fg["is_fresh"] != true {
		t.Errorf("expected is_fresh true, got %v", fg["is_fresh"])
	}
}

func TestPlugin_PostLLMHook_CacheHit_Expired_EvictsAndReverifies(t *testing.T) {
	staleTime := time.Now().UTC().Add(-30 * time.Hour) // 30 hours ago (TTL is 24h)
	ledger := cache.NewLedger(0)
	evaluator := cache.NewEvaluator(cache.NewDefaultPolicy(), ledger)

	// Pre-seed expired verification
	vRespOld := &client.VerificationResponse{
		VerificationID: "ver-old",
		RequestID:      "req-old",
		Status:         client.StatusCompleted,
		CheckedAt:      &staleTime,
		Claims: []client.Claim{
			{
				ClaimID:   "c-old",
				Category:  client.CategoryPricing,
				Verdict:   client.VerdictSupported,
				CheckedAt: staleTime,
			},
		},
	}
	evaluator.RecordVerification("stale-cache-id", "Pricing claim that has expired.", vRespOld)

	evictor := &MockEvictor{}

	now := time.Now().UTC()
	reverifiedCalled := false
	mockClient := &MockVerificationClient{
		VerifyFunc: func(ctx context.Context, req client.VerificationRequest) (*client.VerificationResponse, error) {
			reverifiedCalled = true
			return &client.VerificationResponse{
				VerificationID: "ver-new",
				RequestID:      req.RequestID,
				Status:         client.StatusCompleted,
				CheckedAt:      &now,
				Claims: []client.Claim{
					{
						ClaimID:   "c-new",
						Category:  client.CategoryPricing,
						Verdict:   client.VerdictSupported,
						CheckedAt: now,
					},
				},
			}, nil
		},
	}

	cfg := DefaultPluginConfig()
	cfg.EnableCacheEviction = true
	cfg.ReverifyOnCacheHit = true
	p := NewPlugin(cfg, mockClient, evaluator, evictor)

	ctx := schemas.NewBifrostContext(context.Background(), "req-stale-hit")
	resp := &schemas.BifrostResponse{
		ID: "resp-stale-hit",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Pricing claim that has expired.",
				},
			},
		},
		ExtraFields: map[string]any{
			"cache_debug": map[string]any{
				"cache_hit": true,
				"cache_id":  "stale-cache-id",
			},
		},
	}

	outResp, bifrostErr, err := p.PostLLMHook(ctx, resp, nil)
	if err != nil || bifrostErr != nil {
		t.Fatalf("unexpected hook error: %v, %v", err, bifrostErr)
	}

	// Verify eviction was called
	if len(evictor.EvictedIDs) != 1 || evictor.EvictedIDs[0] != "stale-cache-id" {
		t.Errorf("expected eviction for stale-cache-id, got %v", evictor.EvictedIDs)
	}

	// Verify re-verification was called
	if !reverifiedCalled {
		t.Error("expected re-verification to be executed on expired cache hit")
	}

	fg := outResp.ExtraFields["freshguard"].(map[string]any)
	if fg["status"] != "reverified" {
		t.Errorf("expected status reverified, got %v", fg["status"])
	}
	if fg["is_fresh"] != true {
		t.Errorf("expected is_fresh true after successful reverification, got %v", fg["is_fresh"])
	}
}

