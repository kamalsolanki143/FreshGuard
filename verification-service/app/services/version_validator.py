import re
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set, Tuple
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from app.schemas.claims import ClaimCategory, ClaimVerdict, ClaimVerdictResult, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceMinimal

logger = logging.getLogger("freshguard.version_validator")


class VersionValidator:
    """
    Deterministic software version validator using packaging.version.Version.
    Performs mathematical version comparisons, distinguishes stable from prerelease,
    and validates version claims without using LLMs.
    """

    # Matches semver / PEP 440 versions like 3.12, 3.12.1, 18, 22.0.0, 2.0.0rc1, v1.9.0
    VERSION_REGEX = re.compile(
        r"\bv?(\d+(?:\.\d+)*(?:[a-zA-Z0-9\.\-_]+)?)\b",
        re.IGNORECASE,
    )

    # Patterns indicating latest stable assertions in evidence
    LATEST_PATTERNS = [
        re.compile(r"(?:latest|current|newest)\s+(?:stable\s+)?(?:release|version)\s*(?:is\s*)?v?(\d+(?:\.\d+)*(?:[a-zA-Z0-9\.\-_]+)?)", re.IGNORECASE),
        re.compile(r"v?(\d+(?:\.\d+)*(?:[a-zA-Z0-9\.\-_]+)?)\s+(?:is\s+the\s+)?(?:latest|current)\s+stable", re.IGNORECASE),
        re.compile(r"(?:stable\s+version|latest\s+version):\s*v?(\d+(?:\.\d+)*(?:[a-zA-Z0-9\.\-_]+)?)", re.IGNORECASE),
    ]

    # Specifier pattern e.g. ">= 1.5", "== 2.0", "~= 3.1"
    SPECIFIER_REGEX = re.compile(
        r"(?:>=|<=|==|!=|>|<|~=)\s*v?(\d+(?:\.\d+)*(?:[a-zA-Z0-9\.\-_]+)?)",
        re.IGNORECASE,
    )


    @classmethod
    def safe_parse_version(cls, version_str: str) -> Optional[Version]:
        """Safely parses a version string into packaging.version.Version."""
        if not version_str or not isinstance(version_str, str):
            return None
        clean_str = version_str.strip().lstrip("vV")
        # Strip trailing punctuation
        clean_str = re.sub(r"[,\.:;]+$", "", clean_str)
        try:
            return Version(clean_str)
        except (InvalidVersion, TypeError):
            return None

    @classmethod
    def extract_versions(cls, text: str) -> List[Version]:
        """Extracts and parses all valid versions from a text snippet."""
        if not text:
            return []
        candidates = cls.VERSION_REGEX.findall(text)
        parsed = []
        for cand in candidates:
            v = cls.safe_parse_version(cand)
            if v is not None:
                parsed.append(v)
        return parsed

    @classmethod
    def extract_latest_stable_version(cls, text: str) -> Optional[Version]:
        """
        Extracts the explicit latest stable version stated in evidence,
        filtering out prereleases.
        """
        if not text:
            return None
        for pattern in cls.LATEST_PATTERNS:
            match = pattern.search(text)
            if match:
                v = cls.safe_parse_version(match.group(1))
                if v is not None and not v.is_prerelease:
                    return v
        return None

    def validate_claim(
        self,
        claim: ExtractedClaim,
        evidence_list: List[EvidenceItem],
    ) -> ClaimVerdictResult:
        """
        Deterministically evaluates a software version claim against retrieved evidence.
        """
        checked_time = datetime.now(timezone.utc)
        all_ev_ids = [e.evidence_id for e in evidence_list if e.evidence_id]
        attached_evidence = [EvidenceMinimal(title=e.title, url=str(e.url)) for e in evidence_list[:2]]

        # 1. Guard: Check category
        if claim.category != ClaimCategory.SOFTWARE_VERSION and "version" not in claim.attribute.lower():
            return ClaimVerdictResult(
                claim_id=claim.claim_id,
                verdict=ClaimVerdict.UNCLEAR,
                confidence=0.0,
                reason="Claim is not a software version claim.",
                evidence_ids=[],
                evidence=[],
                checked_at=checked_time,
            )

        # 2. Guard: Missing evidence
        if not evidence_list:
            return ClaimVerdictResult(
                claim_id=claim.claim_id,
                verdict=ClaimVerdict.UNCLEAR,
                confidence=0.0,
                reason="Missing evidence to verify software version.",
                evidence_ids=[],
                evidence=[],
                checked_at=checked_time,
            )

        # 3. Entity check: Filter evidence matching entity name
        entity_lower = claim.entity.lower().strip()
        entity_tokens = {entity_lower, entity_lower.replace(".js", "").replace("js", "").strip()}
        entity_evidence = [
            e for e in evidence_list
            if any(tok in e.title.lower() or tok in (e.content or "").lower() for tok in entity_tokens if len(tok) >= 2)
        ]
        if not entity_evidence:
            return ClaimVerdictResult(
                claim_id=claim.claim_id,
                verdict=ClaimVerdict.UNCLEAR,
                confidence=0.10,
                reason=f"No retrieved evidence corresponds to software entity '{claim.entity}'.",
                evidence_ids=all_ev_ids,
                evidence=attached_evidence,
                checked_at=checked_time,
            )

        # 4. Extract version mentioned in the claim
        claim_versions = self.extract_versions(claim.text)
        if not claim_versions:
            return ClaimVerdictResult(
                claim_id=claim.claim_id,
                verdict=ClaimVerdict.UNCLEAR,
                confidence=0.20,
                reason="No valid, parseable version number found in the claim statement.",
                evidence_ids=all_ev_ids,
                evidence=attached_evidence,
                checked_at=checked_time,
            )
        claimed_version = claim_versions[0]

        # 5. Check for Version Requirements / Specifiers (e.g. ">= 1.5")
        spec_match = self.SPECIFIER_REGEX.search(claim.text)
        if spec_match:
            spec_str = re.sub(r"[,\.:;]+$", "", spec_match.group(0).strip())
            try:
                spec = SpecifierSet(spec_str)

                # Find versions in evidence
                found_versions = []
                for ev in entity_evidence:
                    found_versions.extend(self.extract_versions(ev.content or ""))
                if found_versions:
                    matching = [v for v in found_versions if spec.contains(v)]
                    if matching:
                        return ClaimVerdictResult(
                            claim_id=claim.claim_id,
                            verdict=ClaimVerdict.SUPPORTED,
                            confidence=0.95,
                            reason=f"Evidence contains version {matching[0]} which satisfies requirement '{spec_str}'.",
                            evidence_ids=[entity_evidence[0].evidence_id or "ev_01"],
                            evidence=[EvidenceMinimal(title=entity_evidence[0].title, url=str(entity_evidence[0].url))],
                            checked_at=checked_time,
                        )
                    else:
                        return ClaimVerdictResult(
                            claim_id=claim.claim_id,
                            verdict=ClaimVerdict.CONTRADICTED,
                            confidence=0.90,
                            reason=f"Found versions ({', '.join(str(v) for v in found_versions[:3])}) do not satisfy requirement '{spec_str}'.",
                            evidence_ids=[entity_evidence[0].evidence_id or "ev_01"],
                            evidence=[EvidenceMinimal(title=entity_evidence[0].title, url=str(entity_evidence[0].url))],
                            checked_at=checked_time,
                        )
            except (InvalidSpecifier, ValueError):
                pass

        # 6. Check for Release Sequence Comparison (e.g. "Version 4.0 was released after 3.9")
        if len(claim_versions) >= 2 and ("after" in claim.text.lower() or "newer than" in claim.text.lower()):
            v1, v2 = claim_versions[0], claim_versions[1]
            if v1 > v2:
                return ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.SUPPORTED,
                    confidence=0.98,
                    reason=f"Version {v1} is deterministically greater than {v2}.",
                    evidence_ids=all_ev_ids[:1],
                    evidence=attached_evidence[:1],
                    checked_at=checked_time,
                )
            else:
                return ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.CONTRADICTED,
                    confidence=0.98,
                    reason=f"Version {v1} is not greater than {v2}.",
                    evidence_ids=all_ev_ids[:1],
                    evidence=attached_evidence[:1],
                    checked_at=checked_time,
                )

        # 7. Check for "Latest Stable Version" claims
        is_latest_claim = (
            "latest" in claim.text.lower()
            or "current" in claim.text.lower()
            or "latest_version" in claim.attribute.lower()
        )

        if is_latest_claim:
            latest_evidence_versions: List[Tuple[Version, EvidenceItem]] = []
            for ev in entity_evidence:
                # First try explicit latest pattern
                explicit_latest = self.extract_latest_stable_version(ev.content or "")
                if explicit_latest:
                    latest_evidence_versions.append((explicit_latest, ev))
                else:
                    # Look at all stable versions in snippet
                    snippet_versions = [
                        v for v in self.extract_versions(ev.content or "")
                        if not v.is_prerelease
                    ]
                    if snippet_versions:
                        latest_evidence_versions.append((max(snippet_versions), ev))

            if not latest_evidence_versions:
                return ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.UNCLEAR,
                    confidence=0.30,
                    reason="Evidence does not contain verified stable release version numbers.",
                    evidence_ids=all_ev_ids,
                    evidence=attached_evidence,
                    checked_at=checked_time,
                )

            # Check for conflicting versions across sources
            unique_evidence_versions = {v for v, _ in latest_evidence_versions}
            max_evidence_version = max(unique_evidence_versions)

            # Check if authoritative source confirms or refutes
            matching_ev = next(ev for v, ev in latest_evidence_versions if v == max_evidence_version)
            ev_minimal = [EvidenceMinimal(title=matching_ev.title, url=str(matching_ev.url))]

            # Compare claimed version with evidence
            # Handle major.minor equivalence if claimed is 3.12 and latest is 3.12.0
            if (
                claimed_version == max_evidence_version
                or (claimed_version.major == max_evidence_version.major
                    and claimed_version.minor == max_evidence_version.minor
                    and (claimed_version.micro == 0 or max_evidence_version.micro == 0)
                    and len(claimed_version.release) <= 2)
            ):
                return ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.SUPPORTED,
                    confidence=0.96,
                    reason=f"Evidence confirms that {claimed_version} is the latest stable version.",
                    evidence_ids=[matching_ev.evidence_id or "ev_01"],
                    evidence=ev_minimal,
                    checked_at=checked_time,
                )
            elif max_evidence_version > claimed_version:
                return ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.CONTRADICTED,
                    confidence=0.97,
                    reason=f"A newer stable version ({max_evidence_version}) is available, superseding {claimed_version}.",
                    evidence_ids=[matching_ev.evidence_id or "ev_01"],
                    evidence=ev_minimal,
                    corrected_value=str(max_evidence_version),
                    checked_at=checked_time,
                )
            else:
                # max_evidence_version < claimed_version (claimed version exceeds all known releases)
                return ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.CONTRADICTED,
                    confidence=0.90,
                    reason=f"Claimed version {claimed_version} exceeds the latest known released version ({max_evidence_version}).",
                    evidence_ids=[matching_ev.evidence_id or "ev_01"],
                    evidence=ev_minimal,
                    corrected_value=str(max_evidence_version),
                    checked_at=checked_time,
                )

        # 8. General version availability check
        found_versions = []
        for ev in entity_evidence:
            found_versions.extend(self.extract_versions(ev.content or ""))

        if claimed_version in found_versions:
            return ClaimVerdictResult(
                claim_id=claim.claim_id,
                verdict=ClaimVerdict.SUPPORTED,
                confidence=0.92,
                reason=f"Evidence confirms the existence of {claim.entity} version {claimed_version}.",
                evidence_ids=[entity_evidence[0].evidence_id or "ev_01"],
                evidence=[EvidenceMinimal(title=entity_evidence[0].title, url=str(entity_evidence[0].url))],
                checked_at=checked_time,
            )

        return ClaimVerdictResult(
            claim_id=claim.claim_id,
            verdict=ClaimVerdict.UNCLEAR,
            confidence=0.40,
            reason=f"Evidence does not contain definitive confirmation for version {claimed_version}.",
            evidence_ids=all_ev_ids,
            evidence=attached_evidence,
            checked_at=checked_time,
        )

    def validate_claims(
        self,
        claims: List[ExtractedClaim],
        evidence_map: Dict[str, List[EvidenceItem]],
    ) -> List[ClaimVerdictResult]:
        """Validates multiple software version claims independently."""
        results = []
        for claim in claims:
            ev_list = evidence_map.get(claim.claim_id, [])
            results.append(self.validate_claim(claim, ev_list))
        return results
