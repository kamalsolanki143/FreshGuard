package cache

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Ledger tracks verification freshness metadata across cache IDs and response text hashes.
type Ledger struct {
	mu           sync.RWMutex
	byCacheID    map[string]FreshnessMetadata
	byTextHash   map[string]FreshnessMetadata
	autoEvictAge time.Duration
	filePath     string
}

type ledgerStorageFile struct {
	Version   int                 `json:"version"`
	UpdatedAt time.Time           `json:"updated_at"`
	Entries   []FreshnessMetadata `json:"entries"`
}

// NewLedger creates an initialized in-memory thread-safe Ledger.
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

// NewFileBackedLedger creates a Ledger backed by a JSON persistence file.
func NewFileBackedLedger(filePath string, autoEvictAge time.Duration) (*Ledger, error) {
	l := NewLedger(autoEvictAge)
	l.filePath = filePath

	if filePath != "" {
		if err := l.LoadFromFile(filePath); err != nil {
			return nil, fmt.Errorf("failed to load ledger file: %w", err)
		}
	}
	return l, nil
}

// LoadFromFile reads existing metadata records from a JSON file.
func (l *Ledger) LoadFromFile(path string) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	l.filePath = path
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil // fresh file, nothing to load yet
		}
		return err
	}

	if len(data) == 0 {
		return nil
	}

	var storage ledgerStorageFile
	if err := json.Unmarshal(data, &storage); err != nil {
		return fmt.Errorf("invalid ledger json format: %w", err)
	}

	for _, entry := range storage.Entries {
		if entry.CacheID != "" {
			l.byCacheID[entry.CacheID] = entry
		}
		if entry.ResponseHash != "" {
			l.byTextHash[entry.ResponseHash] = entry
		}
	}

	return nil
}

// PersistToFile writes the current ledger state to disk atomically.
func (l *Ledger) PersistToFile() error {
	l.mu.RLock()
	filePath := l.filePath
	if filePath == "" {
		l.mu.RUnlock()
		return nil
	}

	// Deduplicate entries across maps
	seen := make(map[string]bool)
	var entries []FreshnessMetadata

	for _, meta := range l.byCacheID {
		key := meta.VerificationID
		if key == "" {
			key = meta.CacheID + ":" + meta.ResponseHash
		}
		if !seen[key] {
			seen[key] = true
			entries = append(entries, meta)
		}
	}
	for _, meta := range l.byTextHash {
		key := meta.VerificationID
		if key == "" {
			key = meta.CacheID + ":" + meta.ResponseHash
		}
		if !seen[key] {
			seen[key] = true
			entries = append(entries, meta)
		}
	}
	l.mu.RUnlock()

	storage := ledgerStorageFile{
		Version:   1,
		UpdatedAt: time.Now().UTC(),
		Entries:   entries,
	}

	data, err := json.MarshalIndent(storage, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal ledger: %w", err)
	}

	// Ensure parent directory exists
	dir := filepath.Dir(filePath)
	if dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create ledger directory: %w", err)
		}
	}

	// Atomic write via temp file
	tmpPath := fmt.Sprintf("%s.tmp.%d", filePath, time.Now().UnixNano())
	if err := os.WriteFile(tmpPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write ledger temp file: %w", err)
	}

	// On Windows, os.Rename fails if target exists, so remove target first
	_ = os.Remove(filePath)
	if err := os.Rename(tmpPath, filePath); err != nil {
		_ = os.Remove(tmpPath)
		return fmt.Errorf("failed to atomic rename ledger file: %w", err)
	}

	return nil
}

// Put saves or updates freshness metadata and persists if file-backed.
func (l *Ledger) Put(meta FreshnessMetadata) {
	l.mu.Lock()
	if meta.CacheID != "" {
		l.byCacheID[meta.CacheID] = meta
	}
	if meta.ResponseHash != "" {
		l.byTextHash[meta.ResponseHash] = meta
	}
	hasFile := l.filePath != ""
	l.mu.Unlock()

	if hasFile {
		_ = l.PersistToFile()
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
	hasFile := l.filePath != ""
	if meta, ok := l.byCacheID[cacheID]; ok {
		delete(l.byCacheID, cacheID)
		if meta.ResponseHash != "" {
			delete(l.byTextHash, meta.ResponseHash)
		}
	}
	l.mu.Unlock()

	if hasFile {
		_ = l.PersistToFile()
	}
}

// Len returns the count of items in the ledger.
func (l *Ledger) Len() int {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return len(l.byCacheID)
}
