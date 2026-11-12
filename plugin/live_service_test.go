package main

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"github.com/kamalsolanki143/FreshGuard/plugin/cache"
	"github.com/kamalsolanki143/FreshGuard/plugin/client"
	"github.com/kamalsolanki143/FreshGuard/plugin/hooks"
	"github.com/kamalsolanki143/FreshGuard/plugin/schemas"
)

// getFreePort asks the kernel for a free open TCP port.
func getFreePort(t *testing.T) int {
	addr, err := net.ResolveTCPAddr("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("failed to resolve tcp addr: %v", err)
	}
	l, err := net.ListenTCP("tcp", addr)
	if err != nil {
		t.Fatalf("failed to listen on random port: %v", err)
	}
	defer l.Close()
	return l.Addr().(*net.TCPAddr).Port
}

// TestLive_GoPlugin_To_PythonService executes an end-to-end integration test
// between the Go plugin and the live Python FastAPI verification service.
func TestLive_GoPlugin_To_PythonService(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping live python service test in short mode")
	}

	port := getFreePort(t)
	baseURL := fmt.Sprintf("http://127.0.0.1:%d", port)

	// Resolve absolute path to verification-service directory
	repoRoot, err := filepath.Abs("..")
	if err != nil {
		t.Fatalf("failed to determine repo root: %v", err)
	}
	pythonServiceDir := filepath.Join(repoRoot, "verification-service")

	// Start uvicorn running app.main:app
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cmd := exec.CommandContext(ctx, "python", "-m", "uvicorn", "app.main:app",
		"--host", "127.0.0.1",
		"--port", fmt.Sprintf("%d", port),
		"--log-level", "warning",
	)
	cmd.Dir = pythonServiceDir
	cmd.Env = append(os.Environ(),
		"ENVIRONMENT=development",
		"API_AUTH_MODE=disabled",
		"LLM_PROVIDER=mock",
		"DATABASE_URL=sqlite+aiosqlite:///./test_live.db",
	)

	if err := cmd.Start(); err != nil {
		t.Fatalf("failed to start python verification service: %v", err)
	}
	defer func() {
		cancel()
		_ = cmd.Wait()
		_ = os.Remove(filepath.Join(pythonServiceDir, "test_live.db"))
	}()

	// Wait for service /health endpoint to become ready
	healthURL := baseURL + "/health"
	httpClient := &http.Client{Timeout: 500 * time.Millisecond}
	ready := false
	for i := 0; i < 30; i++ {
		resp, err := httpClient.Get(healthURL)
		if err == nil && resp.StatusCode == http.StatusOK {
			_ = resp.Body.Close()
			ready = true
			break
		}
		if resp != nil {
			_ = resp.Body.Close()
		}
		time.Sleep(200 * time.Millisecond)
	}

	if !ready {
		t.Fatalf("python verification service failed to become healthy on %s within timeout", healthURL)
	}

	// Initialize Go Verification Client pointing to real service
	cfg := client.Config{
		BaseURL:     baseURL,
		Timeout:     5 * time.Second,
		MaxRetries:  1,
		BackoffBase: 50 * time.Millisecond,
		FailOpen:    true,
	}
	vClient, err := client.NewClient(cfg, nil)
	if err != nil {
		t.Fatalf("failed to create go verification client: %v", err)
	}

	// 1. Test POST /v1/verifications with live service
	reqID := "live-test-req-001"
	verifyReq := client.VerificationRequest{
		RequestID:  reqID,
		Text:       "Python 3.12 was released recently and ChatGPT Plus costs $20/month.",
		Mode:       "blocking",
		Categories: []string{client.CategorySoftwareVersion, client.CategoryPricing},
	}

	vResp, err := vClient.Verify(context.Background(), verifyReq)
	if err != nil {
		t.Fatalf("live verification failed: %v", err)
	}

	if vResp.RequestID != reqID {
		t.Errorf("expected request_id %s, got %s", reqID, vResp.RequestID)
	}
	if vResp.Status != client.StatusCompleted {
		t.Errorf("expected status completed, got %s", vResp.Status)
	}
	if vResp.VerificationID == "" {
		t.Error("expected non-empty verification_id from live service")
	}

	// 2. Test GET /v1/verifications/{id} retrieval from live service database
	getResp, err := vClient.GetVerification(context.Background(), vResp.VerificationID, reqID)
	if err != nil {
		t.Fatalf("live verification retrieval failed: %v", err)
	}
	if getResp.VerificationID != vResp.VerificationID {
		t.Errorf("expected retrieved verification_id %s, got %s", vResp.VerificationID, getResp.VerificationID)
	}

	// 3. Test Full Bifrost Plugin Hook Pipeline with live service
	pluginCfg := hooks.PluginConfig{
		VerificationServiceURL: baseURL,
		Timeout:                5 * time.Second,
		MaxRetries:             1,
		FailOpen:               true,
		EnableCacheEviction:    false,
		ReverifyOnCacheHit:     true,
	}

	ledger := cache.NewLedger(0)
	evaluator := cache.NewEvaluator(cache.NewDefaultPolicy(), ledger)
	plugin := hooks.NewPlugin(pluginCfg, vClient, evaluator, nil)

	bCtx := schemas.NewBifrostContext(context.Background(), "bifrost-live-req")
	bReq := &schemas.BifrostRequest{
		ID:    "bifrost-live-req",
		Model: "gpt-4o",
		Messages: []schemas.ChatMessage{
			{Role: "user", Content: "What is OpenAI leadership?"},
		},
	}

	// PreLLMHook
	bReq, shortCircuit, err := plugin.PreLLMHook(bCtx, bReq)
	if err != nil || shortCircuit != nil {
		t.Fatalf("PreLLMHook error: %v", err)
	}

	// PostLLMHook (Cache Miss)
	providerResp := &schemas.BifrostResponse{
		ID:    "resp-live-test",
		Model: "gpt-4o",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Sam Altman is CEO of OpenAI.",
				},
			},
		},
	}

	outResp, bifrostErr, err := plugin.PostLLMHook(bCtx, providerResp, nil)
	if err != nil || bifrostErr != nil {
		t.Fatalf("PostLLMHook error: %v, %v", err, bifrostErr)
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

	// PostLLMHook (Cache Hit)
	cacheHitResp := &schemas.BifrostResponse{
		ID:    "resp-live-cached",
		Model: "gpt-4o",
		Choices: []schemas.BifrostChoice{
			{
				Message: schemas.ChatMessage{
					Role:    "assistant",
					Content: "Sam Altman is CEO of OpenAI.",
				},
			},
		},
		ExtraFields: map[string]any{
			"cache_debug": map[string]any{
				"cache_hit": true,
				"cache_id":  "cache-sam-altman",
			},
		},
	}

	outHitResp, _, err := plugin.PostLLMHook(bCtx, cacheHitResp, nil)
	if err != nil {
		t.Fatalf("PostLLMHook on cache hit error: %v", err)
	}

	fgHit := outHitResp.ExtraFields["freshguard"].(map[string]any)
	if fgHit["is_fresh"] != true {
		t.Errorf("expected is_fresh true on fresh cache hit, got %v", fgHit["is_fresh"])
	}
}

