package cache

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
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

func TestBifrostEvictor_HeadersAndFallback(t *testing.T) {
	var capturedVK string
	var capturedAuth string
	deleteAttempted := false
	postSucceeded := false

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedVK = r.Header.Get("x-bf-vk")
		capturedAuth = r.Header.Get("Authorization")

		// Simulate server returning 405 Method Not Allowed on DELETE, but accepting POST
		if r.Method == http.MethodDelete {
			deleteAttempted = true
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		if r.Method == http.MethodPost {
			postSucceeded = true
			w.WriteHeader(http.StatusOK)
			return
		}
		w.WriteHeader(http.StatusBadRequest)
	}))
	defer server.Close()

	evictor := NewBifrostEvictor(
		server.URL,
		nil,
		WithVirtualKey("my-virtual-key"),
		WithAuthToken("secret-token"),
	)

	err := evictor.EvictByCacheID(context.Background(), "cache-vk-123")
	if err != nil {
		t.Fatalf("expected fallback to POST to succeed, got error: %v", err)
	}

	if !deleteAttempted {
		t.Error("expected initial DELETE attempt")
	}
	if !postSucceeded {
		t.Error("expected fallback POST to succeed")
	}
	if capturedVK != "my-virtual-key" {
		t.Errorf("expected x-bf-vk 'my-virtual-key', got '%s'", capturedVK)
	}
	if capturedAuth != "Bearer secret-token" {
		t.Errorf("expected Authorization 'Bearer secret-token', got '%s'", capturedAuth)
	}
}

func TestFileBackedLedger_Persistence(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "freshguard_ledger_test")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	filePath := filepath.Join(tmpDir, "freshguard_ledger.json")

	// 1. Create file-backed ledger and add entry
	ledger1, err := NewFileBackedLedger(filePath, 0)
	if err != nil {
		t.Fatalf("failed to create file-backed ledger: %v", err)
	}

	now := time.Now().UTC()
	meta := NewFreshnessMetadata(
		"cache-persist-1",
		"hash-persist-1",
		"ver-persist-1",
		"req-persist-1",
		now,
		[]client.Claim{
			{
				ClaimID:    "c-p1",
				Category:   client.CategoryPricing,
				Entity:     "Claude Pro",
				Verdict:    client.VerdictSupported,
				Confidence: 0.98,
				CheckedAt:  now,
			},
		},
		NewDefaultPolicy(),
	)

	ledger1.Put(meta)

	// Verify file exists on disk
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		t.Fatalf("expected ledger file to exist at %s", filePath)
	}

	// 2. Simulate plugin/server restart by creating a new ledger instance reading the same file
	ledger2, err := NewFileBackedLedger(filePath, 0)
	if err != nil {
		t.Fatalf("failed to load ledger file on simulated restart: %v", err)
	}

	loadedMeta, found := ledger2.Get("cache-persist-1", "hash-persist-1")
	if !found {
		t.Fatal("expected metadata to be found in restored ledger")
	}
	if loadedMeta.VerificationID != "ver-persist-1" {
		t.Errorf("expected verification ID ver-persist-1, got %s", loadedMeta.VerificationID)
	}
	if len(loadedMeta.Claims) != 1 || loadedMeta.Claims[0].Entity != "Claude Pro" {
		t.Errorf("unexpected restored claims: %+v", loadedMeta.Claims)
	}

	// 3. Verify deletion persists to disk
	ledger2.Delete("cache-persist-1")

	ledger3, err := NewFileBackedLedger(filePath, 0)
	if err != nil {
		t.Fatalf("failed to load ledger file after deletion: %v", err)
	}
	_, foundAfterDelete := ledger3.Get("cache-persist-1", "hash-persist-1")
	if foundAfterDelete {
		t.Error("expected metadata to be deleted across restarts")
	}
}

