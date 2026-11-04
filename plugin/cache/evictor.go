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
	httpClient *http.Client
}

// NewBifrostEvictor creates a new Bifrost cache eviction client.
func NewBifrostEvictor(bifrostBaseURL string, httpClient *http.Client) *BifrostEvictor {
	if bifrostBaseURL == "" {
		bifrostBaseURL = "http://localhost:8080"
	}
	if httpClient == nil {
		httpClient = &http.Client{
			Timeout: 2 * time.Second,
		}
	}
	return &BifrostEvictor{
		baseURL:    strings.TrimRight(bifrostBaseURL, "/"),
		httpClient: httpClient,
	}
}

// EvictByCacheID calls Bifrost DELETE /api/cache/clear/{cacheId}
func (b *BifrostEvictor) EvictByCacheID(ctx context.Context, cacheID string) error {
	if cacheID == "" {
		return nil
	}

	endpoint := fmt.Sprintf("%s/api/cache/clear/%s", b.baseURL, url.PathEscape(cacheID))
	req, err := http.NewRequestWithContext(ctx, http.MethodDelete, endpoint, nil)
	if err != nil {
		return fmt.Errorf("failed to create eviction request: %w", err)
	}

	resp, err := b.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("bifrost eviction call failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusNoContent || resp.StatusCode == http.StatusNotFound {
		return nil
	}

	return fmt.Errorf("bifrost eviction returned unexpected status code: %d", resp.StatusCode)
}

// EvictByCacheKey calls Bifrost DELETE /api/cache/clear-by-key/{cacheKey}
func (b *BifrostEvictor) EvictByCacheKey(ctx context.Context, cacheKey string) error {
	if cacheKey == "" {
		return nil
	}

	endpoint := fmt.Sprintf("%s/api/cache/clear-by-key/%s", b.baseURL, url.PathEscape(cacheKey))
	req, err := http.NewRequestWithContext(ctx, http.MethodDelete, endpoint, nil)
	if err != nil {
		return fmt.Errorf("failed to create key eviction request: %w", err)
	}

	resp, err := b.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("bifrost key eviction call failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusNoContent || resp.StatusCode == http.StatusNotFound {
		return nil
	}

	return fmt.Errorf("bifrost key eviction returned unexpected status code: %d", resp.StatusCode)
}

