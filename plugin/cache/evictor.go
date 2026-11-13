package cache

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Evictor defines the interface for invalidating cache entries in Bifrost.
type Evictor interface {
	EvictByCacheID(ctx context.Context, cacheID string) error
	EvictByCacheKey(ctx context.Context, cacheKey string) error
}

// BifrostEvictor interacts with Bifrost's cache management endpoints.
type BifrostEvictor struct {
	baseURL    string
	virtualKey string
	authToken  string
	httpClient *http.Client
}

// EvictorOption configures a BifrostEvictor.
type EvictorOption func(*BifrostEvictor)

// WithVirtualKey sets the Bifrost virtual key header (x-bf-vk).
func WithVirtualKey(vk string) EvictorOption {
	return func(b *BifrostEvictor) {
		b.virtualKey = vk
	}
}

// WithAuthToken sets the Authorization Bearer token header.
func WithAuthToken(token string) EvictorOption {
	return func(b *BifrostEvictor) {
		b.authToken = token
	}
}

// NewBifrostEvictor creates a new Bifrost cache eviction client with optional configuration.
func NewBifrostEvictor(bifrostBaseURL string, httpClient *http.Client, opts ...EvictorOption) *BifrostEvictor {
	if bifrostBaseURL == "" {
		bifrostBaseURL = "http://localhost:8080"
	}
	if httpClient == nil {
		httpClient = &http.Client{
			Timeout: 3 * time.Second,
		}
	}
	evictor := &BifrostEvictor{
		baseURL:    strings.TrimRight(bifrostBaseURL, "/"),
		httpClient: httpClient,
	}
	for _, opt := range opts {
		opt(evictor)
	}
	return evictor
}

// EvictByCacheID calls Bifrost DELETE /api/cache/clear/{cacheId} with fallback to POST.
func (b *BifrostEvictor) EvictByCacheID(ctx context.Context, cacheID string) error {
	if cacheID == "" {
		return nil
	}

	endpoint := fmt.Sprintf("%s/api/cache/clear/%s", b.baseURL, url.PathEscape(cacheID))
	return b.executeEviction(ctx, endpoint)
}

// EvictByCacheKey calls Bifrost DELETE /api/cache/clear-by-key/{cacheKey} with fallback to POST.
func (b *BifrostEvictor) EvictByCacheKey(ctx context.Context, cacheKey string) error {
	if cacheKey == "" {
		return nil
	}

	endpoint := fmt.Sprintf("%s/api/cache/clear-by-key/%s", b.baseURL, url.PathEscape(cacheKey))
	return b.executeEviction(ctx, endpoint)
}

func (b *BifrostEvictor) executeEviction(ctx context.Context, endpoint string) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodDelete, endpoint, nil)
	if err != nil {
		return fmt.Errorf("failed to create eviction request: %w", err)
	}
	b.applyHeaders(req)

	resp, err := b.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("bifrost eviction call failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusNoContent || resp.StatusCode == http.StatusNotFound {
		return nil
	}

	// If router does not allow DELETE, fallback to POST
	if resp.StatusCode == http.StatusMethodNotAllowed {
		fallbackReq, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, nil)
		if err == nil {
			b.applyHeaders(fallbackReq)
			fallbackResp, err := b.httpClient.Do(fallbackReq)
			if err == nil {
				defer fallbackResp.Body.Close()
				if fallbackResp.StatusCode == http.StatusOK || fallbackResp.StatusCode == http.StatusNoContent || fallbackResp.StatusCode == http.StatusNotFound {
					return nil
				}
			}
		}
	}

	return fmt.Errorf("bifrost eviction returned unexpected status code: %d", resp.StatusCode)
}

func (b *BifrostEvictor) applyHeaders(req *http.Request) {
	if b.virtualKey != "" {
		req.Header.Set("x-bf-vk", b.virtualKey)
	}
	if b.authToken != "" {
		req.Header.Set("Authorization", "Bearer "+b.authToken)
		req.Header.Set("x-bifrost-setup-token", b.authToken)
	}
}
