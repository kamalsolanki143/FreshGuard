package cache

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/kamalsolanki143/FreshGuard/plugin/client"
)

func TestPolicy_GetTTL(t *testing.T) {
	policy := NewDefaultPolicy()

	if ttl := policy.GetTTLForCategory(client.CategoryPricing); ttl != 24*time.Hour {
		t.Errorf("expected 24h for pricing, got %v", ttl)
	}
	if ttl := policy.GetTTLForCategory(client.CategorySoftwareVersion); ttl != 24*time.Hour {
		t.Errorf("expected 24h for software_version, got %v", ttl)
	}
	if ttl := policy.GetTTLForCategory(client.CategoryLeadership); ttl != 7*24*time.Hour {
		t.Errorf("expected 7d for leadership, got %v", ttl)
	}
	if ttl := policy.GetTTLForCategory("unknown"); ttl != 24*time.Hour {
		t.Errorf("expected 24h for default, got %v", ttl)
	}
}

func TestPolicy_GetMinimumTTLForClaims(t *testing.T) {
	policy := NewDefaultPolicy()

	claims := []client.Claim{
		{Category: client.CategoryLeadership},
		{Category: client.CategoryPricing}, // 24h should win
	}

	ttl := policy.GetMinimumTTLForClaims(claims)
	if ttl != 24*time.Hour {
		t.Errorf("expected minimum TTL 24h, got %v", ttl)
	}
}

func TestFreshnessMetadata_Expiration(t *testing.T) {
	policy := NewDefaultPolicy()
	now := time.Now().UTC()

	meta := NewFreshnessMetadata(
		"cache-1",
		"hash-1",
		"ver-1",
		"req-1",
		now.Add(-25*time.Hour), // verified 25 hours ago
		[]client.Claim{{Category: client.CategoryPricing}},
		policy,
	)

	if !meta.IsExpired(now) {
		t.Error("expected metadata to be expired after 25h for pricing claim")
	}

	freshMeta := NewFreshnessMetadata(
		"cache-2",
		"hash-2",
		"ver-2",
		"req-2",
		now.Add(-10*time.Hour), // verified 10 hours ago
		[]client.Claim{{Category: client.CategoryPricing}},
		policy,
	)

	if freshMeta.IsExpired(now) {
		t.Error("expected metadata to be fresh after 10h for pricing claim")
	}
}

func TestEvaluator_CacheHitDecisions(t *testing.T) {
	policy := NewDefaultPolicy()
	ledger := NewLedger(0)
	evaluator := NewEvaluator(policy, ledger)
	now := time.Now().UTC()

	// 1. Missing metadata test
	resMissing := evaluator.EvaluateCacheHit("missing-cache-id", "some uncached text", now)
	if resMissing.IsFresh {
		t.Error("missing metadata must NOT be treated as fresh")
	}
	if !resMissing.RequiresReverification {
		t.Error("missing metadata must require reverification")
	}
	if resMissing.Verdict != VerdictMissingMetadata {
		t.Errorf("expected VerdictMissingMetadata, got %s", resMissing.Verdict)
	}

	// 2. Fresh entry test
	vRespFresh := &client.VerificationResponse{
		VerificationID: "ver-fresh",
		RequestID:      "req-fresh",
		Status:         client.StatusCompleted,
		CheckedAt:      &now,
		Claims: []client.Claim{
			{
				ClaimID:   "c-1",
				Category:  client.CategoryLeadership,
				Verdict:   client.VerdictSupported,
				CheckedAt: now,
			},
		},
	}
	evaluator.RecordVerification("cache-fresh-id", "OpenAI CEO is Sam Altman.", vRespFresh)

	resFresh := evaluator.EvaluateCacheHit("cache-fresh-id", "OpenAI CEO is Sam Altman.", now.Add(2*time.Hour))
	if !resFresh.IsFresh {
		t.Error("fresh entry should be marked fresh")
	}
	if resFresh.RequiresReverification {
		t.Error("fresh entry should not require reverification")
	}
	if resFresh.Verdict != VerdictFresh {
		t.Errorf("expected VerdictFresh, got %s", resFresh.Verdict)
	}

	// 3. Expired entry test (simulating 8 days later for leadership)
	resExpired := evaluator.EvaluateCacheHit("cache-fresh-id", "OpenAI CEO is Sam Altman.", now.Add(8*24*time.Hour))
	if resExpired.IsFresh {
		t.Error("expired entry must NOT be marked fresh")
	}
	if !resExpired.RequiresReverification {
		t.Error("expired entry must require reverification")
	}
	if resExpired.Verdict != VerdictExpired {
		t.Errorf("expected VerdictExpired, got %s", resExpired.Verdict)
	}
	if !resExpired.ShouldEvict {
		t.Error("expired entry should be marked for eviction")
	}

	// 4. Contradicted claims test
	vRespContradicted := &client.VerificationResponse{
		VerificationID: "ver-contra",
		RequestID:      "req-contra",
		Status:         client.StatusCompleted,
		CheckedAt:      &now,
		Claims: []client.Claim{
			{
				ClaimID:   "c-2",
				Category:  client.CategoryPricing,
				Verdict:   client.VerdictContradicted,
				CheckedAt: now,
			},
		},
	}
	evaluator.RecordVerification("cache-contra-id", "GPT-4 is free.", vRespContradicted)

	resContra := evaluator.EvaluateCacheHit("cache-contra-id", "GPT-4 is free.", now.Add(1*time.Hour))
	if resContra.IsFresh {
		t.Error("contradicted cached claims must not be marked fresh")
	}
	if resContra.Verdict != VerdictContradictedHit {
		t.Errorf("expected VerdictContradictedHit, got %s", resContra.Verdict)
	}
}

func TestBifrostEvictor(t *testing.T) {
	var evictedID string
	var evictedKey string

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodDelete {
			t.Errorf("expected DELETE, got %s", r.Method)
		}
		if r.URL.Path == "/api/cache/clear/test-cache-123" {
			evictedID = "test-cache-123"
			w.WriteHeader(http.StatusOK)
			return
		}
		if r.URL.Path == "/api/cache/clear-by-key/test-key-456" {
			evictedKey = "test-key-456"
			w.WriteHeader(http.StatusNoContent)
			return
		}
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	evictor := NewBifrostEvictor(server.URL, nil)

	err := evictor.EvictByCacheID(context.Background(), "test-cache-123")
	if err != nil {
		t.Fatalf("unexpected error evicting by ID: %v", err)
	}
	if evictedID != "test-cache-123" {
		t.Errorf("expected evictedID test-cache-123, got %s", evictedID)
	}

	err = evictor.EvictByCacheKey(context.Background(), "test-key-456")
	if err != nil {
		t.Fatalf("unexpected error evicting by Key: %v", err)
	}
	if evictedKey != "test-key-456" {
		t.Errorf("expected evictedKey test-key-456, got %s", evictedKey)
	}
}

