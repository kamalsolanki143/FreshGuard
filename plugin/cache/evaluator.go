package cache

import (
	"fmt"
	"time"

	"github.com/kamalsolanki143/FreshGuard/plugin/client"
)

// EvaluationVerdict defines the cache evaluation decision.
type EvaluationVerdict string

const (
	VerdictFresh           EvaluationVerdict = "FRESH"
	VerdictExpired         EvaluationVerdict = "EXPIRED"
	VerdictMissingMetadata EvaluationVerdict = "MISSING_METADATA"
	VerdictContradictedHit EvaluationVerdict = "CONTRADICTED"
)

// EvaluationResult captures the decision made when evaluating a cache hit.
type EvaluationResult struct {
	Verdict                EvaluationVerdict  `json:"verdict"`
	IsFresh                bool               `json:"is_fresh"`
	RequiresReverification bool               `json:"requires_reverification"`
	ShouldEvict            bool               `json:"should_evict"`
	Reason                 string             `json:"reason"`
	Metadata               *FreshnessMetadata `json:"metadata,omitempty"`
}

// Evaluator evaluates cache hits against FreshGuard policies.
type Evaluator struct {
	policy Policy
	ledger *Ledger
}

// NewEvaluator creates a new Evaluator.
func NewEvaluator(policy Policy, ledger *Ledger) *Evaluator {
	if ledger == nil {
		ledger = NewLedger(0)
	}
	return &Evaluator{
		policy: policy,
		ledger: ledger,
	}
}

// EvaluateCacheHit inspects a cache hit from Bifrost and determines its validity.
// Strict rules enforced:
// 1. Missing verification metadata must not be treated as fresh.
// 2. Expired metadata requires re-verification (does not mean false).
// 3. A cache hit must not silently inherit an expired Supported verdict.
func (e *Evaluator) EvaluateCacheHit(cacheID string, responseText string, at time.Time) EvaluationResult {
	if at.IsZero() {
		at = time.Now().UTC()
	}

	hash := HashText(responseText)
	meta, found := e.ledger.Get(cacheID, hash)
	if !found {
		return EvaluationResult{
			Verdict:                VerdictMissingMetadata,
			IsFresh:                false,
			RequiresReverification: true,
			ShouldEvict:            true,
			Reason:                 "No verification metadata found for cached response. Missing metadata must not be treated as fresh.",
			Metadata:               nil,
		}
	}

	// Check if already expired according to TTL
	if meta.IsExpired(at) {
		return EvaluationResult{
			Verdict:                VerdictExpired,
			IsFresh:                false,
			RequiresReverification: true,
			ShouldEvict:            true,
			Reason: fmt.Sprintf("Cached verification expired at %s (TTL was %v). Re-verification required; cache hit cannot silently inherit expired verdict.",
				meta.ExpiresAt.Format(time.RFC3339), meta.PolicyTTL),
			Metadata: &meta,
		}
	}

	// Check if cached response previously contained contradicted claims
	if meta.HasContradictedClaims() {
		return EvaluationResult{
			Verdict:                VerdictContradictedHit,
			IsFresh:                false,
			RequiresReverification: true,
			ShouldEvict:            true,
			Reason:                 "Cached response contains contradicted claims.",
			Metadata:               &meta,
		}
	}

	// Active and unexpired
	return EvaluationResult{
		Verdict:                VerdictFresh,
		IsFresh:                true,
		RequiresReverification: false,
		ShouldEvict:            false,
		Reason:                 fmt.Sprintf("Cache entry is fresh until %s", meta.ExpiresAt.Format(time.RFC3339)),
		Metadata:               &meta,
	}
}

// RecordVerification creates and stores metadata for a newly verified response.
func (e *Evaluator) RecordVerification(cacheID string, responseText string, vResp *client.VerificationResponse) FreshnessMetadata {
	hash := HashText(responseText)
	now := time.Now().UTC()
	checkedAt := now
	if vResp.CheckedAt != nil && !vResp.CheckedAt.IsZero() {
		checkedAt = *vResp.CheckedAt
	}

	meta := NewFreshnessMetadata(
		cacheID,
		hash,
		vResp.VerificationID,
		vResp.RequestID,
		checkedAt,
		vResp.Claims,
		e.policy,
	)

	e.ledger.Put(meta)
	return meta
}

