package cache

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"time"

	"github.com/kamalsolanki143/FreshGuard/plugin/client"
)

// Default TTL policies as defined in FreshGuard specification.
const (
	DefaultTTLPrice            = 24 * time.Hour
	DefaultTTLSoftwareVersion  = 24 * time.Hour
	DefaultTTLLeadership       = 7 * 24 * time.Hour
	DefaultTTLDefault          = 24 * time.Hour
)

// Policy defines TTL rules per claim category.
type Policy struct {
	CategoryTTLs map[string]time.Duration `json:"category_ttls"`
	DefaultTTL   time.Duration            `json:"default_ttl"`
}

// NewDefaultPolicy returns the standard FreshGuard cache freshness policy.
func NewDefaultPolicy() Policy {
	return Policy{
		CategoryTTLs: map[string]time.Duration{
			client.CategoryPricing:         DefaultTTLPrice,
			client.CategorySoftwareVersion: DefaultTTLSoftwareVersion,
			client.CategoryLeadership:      DefaultTTLLeadership,
		},
		DefaultTTL: DefaultTTLDefault,
	}
}

// GetTTLForCategory returns the configured TTL for a specific category.
func (p Policy) GetTTLForCategory(category string) time.Duration {
	if ttl, ok := p.CategoryTTLs[strings.ToLower(strings.TrimSpace(category))]; ok && ttl > 0 {
		return ttl
	}
	if p.DefaultTTL > 0 {
		return p.DefaultTTL
	}
	return DefaultTTLDefault
}

// GetMinimumTTLForClaims calculates the shortest TTL among verified claims.
// This ensures that if a response contains both a pricing claim (24h) and a leadership claim (7d),
// the response freshness expires at 24h.
func (p Policy) GetMinimumTTLForClaims(claims []client.Claim) time.Duration {
	if len(claims) == 0 {
		return p.DefaultTTL
	}

	minTTL := time.Duration(0)
	for _, claim := range claims {
		ttl := p.GetTTLForCategory(claim.Category)
		if minTTL == 0 || ttl < minTTL {
			minTTL = ttl
		}
	}

	if minTTL == 0 {
		return p.DefaultTTL
	}
	return minTTL
}

// HashText creates a deterministic SHA-256 hash of response text for cache correlation.
func HashText(text string) string {
	h := sha256.New()
	h.Write([]byte(strings.TrimSpace(text)))
	return hex.EncodeToString(h.Sum(nil))
}

