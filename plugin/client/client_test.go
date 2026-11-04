package client

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"
)

func TestClient_Verify_Success(t *testing.T) {
	expectedReqID := "test-req-123"
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("expected POST, got %s", r.Method)
		}
		if r.URL.Path != "/v1/verifications" {
			t.Errorf("expected /v1/verifications, got %s", r.URL.Path)
		}
		if r.Header.Get("X-Request-ID") != expectedReqID {
			t.Errorf("expected X-Request-ID header %s, got %s", expectedReqID, r.Header.Get("X-Request-ID"))
		}

		var req VerificationRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Fatalf("failed to decode request body: %v", err)
		}
		if req.Text != "GPT-4 costs $20/month." {
			t.Errorf("unexpected text: %s", req.Text)
		}

		now := time.Now().UTC()
		resp := VerificationResponse{
			VerificationID: "ver-001",
			RequestID:      expectedReqID,
			Status:         StatusCompleted,
			CheckedAt:      &now,
			Claims: []Claim{
				{
					ClaimID:      "claim-1",
					Category:     CategoryPricing,
					Entity:       "OpenAI GPT-4",
					Attribute:    "monthly_cost",
					OriginalText: "GPT-4 costs $20/month.",
					Verdict:      VerdictSupported,
					Confidence:   0.98,
					CheckedAt:    now,
					Evidence: []Evidence{
						{
							EvidenceID:  "ev-1",
							SourceURL:   "https://openai.com/pricing",
							SourceTitle: "OpenAI Pricing",
							Snippet:     "ChatGPT Plus is $20/month.",
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
	defer server.Close()

	cfg := Config{
		BaseURL:     server.URL,
		Timeout:     2 * time.Second,
		MaxRetries:  1,
		BackoffBase: 10 * time.Millisecond,
	}
	c, err := NewClient(cfg, nil)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	resp, err := c.Verify(context.Background(), VerificationRequest{
		RequestID: expectedReqID,
		Text:      "GPT-4 costs $20/month.",
		Mode:      "blocking",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if resp.VerificationID != "ver-001" {
		t.Errorf("expected verification_id ver-001, got %s", resp.VerificationID)
	}
	if len(resp.Claims) != 1 {
		t.Fatalf("expected 1 claim, got %d", len(resp.Claims))
	}
	if resp.Claims[0].Verdict != VerdictSupported {
		t.Errorf("expected verdict supported, got %s", resp.Claims[0].Verdict)
	}
}

func TestClient_Verify_RetrySuccessOn503(t *testing.T) {
	var attempts int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count := atomic.AddInt32(&attempts, 1)
		if count == 1 {
			w.WriteHeader(http.StatusServiceUnavailable)
			_ = json.NewEncoder(w).Encode(APIError{
				Code:      "SERVICE_UNAVAILABLE",
				Message:   "Temporary provider overload",
				RequestID: "req-retry",
				Retryable: true,
			})
			return
		}

		now := time.Now().UTC()
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(VerificationResponse{
			VerificationID: "ver-recovered",
			RequestID:      "req-retry",
			Status:         StatusCompleted,
			CheckedAt:      &now,
		})
	}))
	defer server.Close()

	cfg := Config{
		BaseURL:     server.URL,
		Timeout:     2 * time.Second,
		MaxRetries:  2,
		BackoffBase: 10 * time.Millisecond,
	}
	c, err := NewClient(cfg, nil)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	resp, err := c.Verify(context.Background(), VerificationRequest{
		RequestID: "req-retry",
		Text:      "Anthropic CEO is Dario Amodei.",
	})
	if err != nil {
		t.Fatalf("expected retry to succeed, got: %v", err)
	}

	if resp.VerificationID != "ver-recovered" {
		t.Errorf("unexpected verification ID: %s", resp.VerificationID)
	}
	if atomic.LoadInt32(&attempts) != 2 {
		t.Errorf("expected 2 attempts, got %d", attempts)
	}
}

func TestClient_Verify_Timeout(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(100 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	cfg := Config{
		BaseURL:     server.URL,
		Timeout:     20 * time.Millisecond,
		MaxRetries:  0,
		BackoffBase: 5 * time.Millisecond,
	}
	c, err := NewClient(cfg, nil)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 25*time.Millisecond)
	defer cancel()

	_, err = c.Verify(ctx, VerificationRequest{
		RequestID: "req-timeout",
		Text:      "Testing timeout.",
	})
	if err == nil {
		t.Fatal("expected timeout error, got nil")
	}
}

func TestClient_Verify_MalformedJSON(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte("{invalid-json-body"))
	}))
	defer server.Close()

	cfg := Config{
		BaseURL:     server.URL,
		Timeout:     1 * time.Second,
		MaxRetries:  0,
		BackoffBase: 5 * time.Millisecond,
	}
	c, err := NewClient(cfg, nil)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	_, err = c.Verify(context.Background(), VerificationRequest{
		RequestID: "req-bad-json",
		Text:      "Test",
	})
	if err == nil {
		t.Fatal("expected malformed json error, got nil")
	}
}

func TestClient_GetVerification(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/verifications/ver-async-1" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		now := time.Now().UTC()
		_ = json.NewEncoder(w).Encode(VerificationResponse{
			VerificationID: "ver-async-1",
			RequestID:      "req-async-1",
			Status:         StatusCompleted,
			CheckedAt:      &now,
		})
	}))
	defer server.Close()

	cfg := Config{
		BaseURL:     server.URL,
		Timeout:     1 * time.Second,
		MaxRetries:  0,
		BackoffBase: 5 * time.Millisecond,
	}
	c, err := NewClient(cfg, nil)
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	res, err := c.GetVerification(context.Background(), "ver-async-1", "req-async-1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res.Status != StatusCompleted {
		t.Errorf("expected status completed, got %s", res.Status)
	}
}

