package cache

import (
	"time"

	"github.com/kamalsolanki143/FreshGuard/plugin/client"
)

// FreshnessMetadata records verification decisions, TTLs, and evidence references.
type FreshnessMetadata struct {
	CacheID        string         `json:"cache_id,omitempty"`
	ResponseHash   string         `json:"response_hash"`
	VerificationID string         `json:"verification_id"`
	RequestID      string         `json:"request_id"`
	CheckedAt      time.Time      `json:"checked_at"`
	PolicyTTL      time.Duration  `json:"policy_ttl"`
	ExpiresAt      time.Time      `json:"expires_at"`
	Claims         []client.Claim `json:"claims"`
	Status         string         `json:"status"`
}

// NewFreshnessMetadata constructs and calculates expiration based on Policy.
func NewFreshnessMetadata(
	cacheID string,
	responseHash string,
	verificationID string,
	requestID string,
	checkedAt time.Time,
	claims []client.Claim,
	policy Policy,
) FreshnessMetadata {
	if checkedAt.IsZero() {
		checkedAt = time.Now().UTC()
	}

	ttl := policy.GetMinimumTTLForClaims(claims)
	expiresAt := checkedAt.Add(ttl)

	return FreshnessMetadata{
		CacheID:        cacheID,
		ResponseHash:   responseHash,
		VerificationID: verificationID,
		RequestID:      requestID,
		CheckedAt:      checkedAt,
		PolicyTTL:      ttl,
		ExpiresAt:      expiresAt,
		Claims:         claims,
		Status:         client.StatusCompleted,
	}
}

// IsExpired checks if the metadata has surpassed its TTL window.
func (m FreshnessMetadata) IsExpired(at time.Time) bool {
	if m.ExpiresAt.IsZero() {
		return true
	}
	return at.After(m.ExpiresAt) || at.Equal(m.ExpiresAt)
}

// HasContradictedClaims returns true if any verified claim was contradicted.
func (m FreshnessMetadata) HasContradictedClaims() bool {
	for _, c := range m.Claims {
		if c.Verdict == client.VerdictContradicted {
			return true
		}
	}
	return false
}

// HasSupportedClaims returns true if at least one claim is supported and none contradicted.
func (m FreshnessMetadata) HasSupportedClaims() bool {
	hasSupported := false
	for _, c := range m.Claims {
		if c.Verdict == client.VerdictContradicted {
			return false
		}
		if c.Verdict == client.VerdictSupported {
			hasSupported = true
		}
	}
	return hasSupported
}

