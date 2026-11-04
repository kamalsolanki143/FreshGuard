package cache

import (
	"sync"
	"time"
)

// Ledger tracks verification freshness metadata across cache IDs and response text hashes.
type Ledger struct {
	mu           sync.RWMutex
	byCacheID    map[string]FreshnessMetadata
	byTextHash   map[string]FreshnessMetadata
	autoEvictAge time.Duration
}

// NewLedger creates an initialized thread-safe Ledger.
func NewLedger(autoEvictAge time.Duration) *Ledger {
	if autoEvictAge <= 0 {
		autoEvictAge = 30 * 24 * time.Hour // Keep entries up to 30 days by default
	}
	return &Ledger{
		byCacheID:    make(map[string]FreshnessMetadata),
		byTextHash:   make(map[string]FreshnessMetadata),
		autoEvictAge: autoEvictAge,
	}
}

// Put saves or updates freshness metadata.
func (l *Ledger) Put(meta FreshnessMetadata) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if meta.CacheID != "" {
		l.byCacheID[meta.CacheID] = meta
	}
	if meta.ResponseHash != "" {
		l.byTextHash[meta.ResponseHash] = meta
	}
}

// Get retrieves metadata by CacheID or falling back to ResponseHash.
func (l *Ledger) Get(cacheID string, responseHash string) (FreshnessMetadata, bool) {
	l.mu.RLock()
	defer l.mu.RUnlock()

	if cacheID != "" {
		if meta, ok := l.byCacheID[cacheID]; ok {
			return meta, true
		}
	}
	if responseHash != "" {
		if meta, ok := l.byTextHash[responseHash]; ok {
			return meta, true
		}
	}

	return FreshnessMetadata{}, false
}

// Delete removes metadata associated with a CacheID and its hash.
func (l *Ledger) Delete(cacheID string) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if meta, ok := l.byCacheID[cacheID]; ok {
		delete(l.byCacheID, cacheID)
		if meta.ResponseHash != "" {
			delete(l.byTextHash, meta.ResponseHash)
		}
		return
	}
}

// Len returns the count of items in the ledger.
func (l *Ledger) Len() int {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return len(l.byCacheID)
}

