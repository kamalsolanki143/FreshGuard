import re
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field


class PrefilterResult(BaseModel):
    """Output contract for rules-based prefiltering."""
    model_config = ConfigDict(extra="ignore")

    requires_verification: bool = Field(
        ...,
        description="Whether the text contains claims requiring real-time verification",
    )
    categories: List[str] = Field(
        default_factory=list,
        description="Identified categories of time-sensitive claims",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score calibrated between 0.0 and 1.0",
    )
    matched_signals: List[str] = Field(
        default_factory=list,
        description="Internal telemetry of detected signals",
    )


class CategoryRule:
    """Configurable rule definition for detecting a time-sensitive category."""

    def __init__(
        self,
        category: str,
        strong_patterns: List[str],
        moderate_keywords: List[str],
        base_confidence: float = 0.85,
    ):
        self.category = category
        self.strong_patterns = [re.compile(p, re.IGNORECASE) for p in strong_patterns]
        self.moderate_keywords = [k.lower() for k in moderate_keywords]
        self.base_confidence = base_confidence


class PrefilterEngine:
    """
    Lightweight, deterministic rules-based prefilter.
    Identifies potentially stale or time-sensitive claims before expensive LLM and Tavily calls.
    """

    DEFAULT_THRESHOLD: float = 0.60

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold = threshold
        self.rules = self._initialize_rules()
        self.timeless_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in [
                r"\b(?:is\s+defined\s+as|is\s+the\s+process\s+by\s+which)\b",
                r"\b(?:formula\s+for|law\s+of\s+physics|speed\s+of\s+light)\b",
                r"\b(?:photosynthesis|chemical\s+reaction|mitochondria)\b",
                r"\b(?:capital\s+of\s+[A-Z][a-z]+|boiling\s+point\s+of\s+water)\b",
                r"\b(?:was\s+founded\s+in\s+\d{4}|invented\s+in\s+\d{4}|created\s+in\s+\d{4})\b",
            ]
        ]

    def _initialize_rules(self) -> List[CategoryRule]:
        return [
            # 1. Software Versions
            CategoryRule(
                category="software_version",
                strong_patterns=[
                    r"\b(?:latest|current|newest|recent)\s+(?:stable\s+)?(?:release|version)\b",
                    r"\b(?:version|v)\s*\d+(\.\d+)+(?:-(?:alpha|beta|rc\d*))?\s+(?:is\s+(?:the\s+)?latest|released|available|out)\b",
                    r"\b(?:is\s+the\s+latest\s+stable\s+version)\b",
                    r"\b(?:python|node(?:\.js)?|go|rust|react|vue|angular|django|fastapi)\s+(?:version\s*)?\d+\.\d+\b",
                    r"\b(?:deprecated|end\s+of\s+life|lts\s+support)\b",
                ],
                moderate_keywords=["latest version", "new release", "stable version", "version update"],
                base_confidence=0.91,
            ),
            # 2. Pricing
            CategoryRule(
                category="pricing",
                strong_patterns=[
                    r"(?:\$|€|£|USD|EUR)\s*\d+(?:\.\d{2})?(?:\s*(?:\/|\s*per\s*)(?:month|mo|year|yr|user|seat|token|request|gb))?",
                    r"\b(?:costs?|priced?\s+at)\s+(?:\$|€|£|USD|EUR)?\s*\d+\b",
                    r"\b(?:pricing\s+tier|subscription\s+fee|per\s+month|billed\s+annually|free\s+tier|pro\s+plan)\b",
                ],
                moderate_keywords=["pricing", "subscription", "per month", "free plan", "costs"],
                base_confidence=0.89,
            ),
            # 3. Leadership
            CategoryRule(
                category="leadership",
                strong_patterns=[
                    r"\b(?:is\s+(?:the\s+)?(?:current\s+)?(?:CEO|CTO|CFO|COO|President|Director|Prime Minister))\b",
                    r"\b(?:current\s+CEO\s+of|chief\s+executive\s+officer\s+of)\b",
                    r"\b(?:stepped\s+down\s+as\s+CEO|appointed\s+(?:as\s+)?CEO|resigned\s+as\s+CEO)\b",
                ],
                moderate_keywords=["ceo of", "cto of", "chief executive", "current president"],
                base_confidence=0.88,
            ),
            # 4. Product Availability
            CategoryRule(
                category="product_availability",
                strong_patterns=[
                    r"\b(?:in\s+stock|out\s+of\s+stock|available\s+for\s+pre-?order)\b",
                    r"\b(?:sold\s+out|on\s+back-?order|waitlist\s+(?:is\s+)?open|now\s+shipping)\b",
                    r"\b(?:inventory\s+depleted|currently\s+unavailable)\b",
                ],
                moderate_keywords=["in stock", "out of stock", "pre-order", "sold out"],
                base_confidence=0.86,
            ),
            # 5. Recent Events
            CategoryRule(
                category="recent_events",
                strong_patterns=[
                    r"\b(?:yesterday|earlier\s+today|this\s+week|last\s+week|this\s+morning)\b",
                    r"\b(?:just\s+announced|recently\s+unveiled|breaking\s+news|newly\s+launched)\b",
                    r"\b(?:effective\s+(?:as\s+of\s+)?(?:today|this\s+month))\b",
                ],
                moderate_keywords=["recently announced", "just launched", "breaking news", "yesterday"],
                base_confidence=0.85,
            ),
            # 6. Current Statistics
            CategoryRule(
                category="statistics",
                strong_patterns=[
                    r"\b(?:market\s+cap\s+(?:is|of|reached)|inflation\s+rate\s+(?:is|rose|dropped|at))\b",
                    r"\b(?:unemployment\s+rate\s+is|stock\s+price\s+(?:of|is|trades?\s+at))\b",
                    r"\b(?:current\s+population\s+of|shares\s+(?:are\s+)?trading\s+at)\b",
                ],
                moderate_keywords=["market cap", "inflation rate", "stock price", "unemployment rate"],
                base_confidence=0.85,
            ),
        ]

    def is_timeless_fact(self, text: str) -> bool:
        """Checks if the text represents timeless scientific, mathematical, or historical fact."""
        return any(p.search(text) for p in self.timeless_patterns)

    def evaluate(self, text: Optional[str]) -> PrefilterResult:
        """
        Evaluates input text and returns whether verification is required.
        """
        if not text or not text.strip():
            return PrefilterResult(
                requires_verification=False,
                categories=[],
                confidence=0.0,
                matched_signals=["empty_input"],
            )

        clean_text = text.strip()
        detected_categories: Dict[str, float] = {}
        matched_signals: List[str] = []

        # Check each category rule
        for rule in self.rules:
            strong_matches = [
                pattern.pattern for pattern in rule.strong_patterns if pattern.search(clean_text)
            ]
            if strong_matches:
                score = rule.base_confidence
                # Slight bump for multiple strong pattern corroborations
                if len(strong_matches) > 1:
                    score = min(0.98, score + 0.05)
                detected_categories[rule.category] = score
                matched_signals.append(f"{rule.category}:strong_pattern")
                continue

            # Check moderate keywords
            lower_text = clean_text.lower()
            keyword_matches = [k for k in rule.moderate_keywords if k in lower_text]
            if keyword_matches:
                score = rule.base_confidence - 0.20
                if score >= self.threshold:
                    detected_categories[rule.category] = score
                    matched_signals.append(f"{rule.category}:keyword")

        # False-positive reduction: Check if text is general educational knowledge
        if not detected_categories and self.is_timeless_fact(clean_text):
            return PrefilterResult(
                requires_verification=False,
                categories=["general_knowledge"],
                confidence=0.10,
                matched_signals=["general_knowledge:timeless_fact"],
            )

        if not detected_categories:
            return PrefilterResult(
                requires_verification=False,
                categories=[],
                confidence=0.0,
                matched_signals=["no_time_sensitive_signals"],
            )

        # Filter categories that meet or exceed threshold
        qualified_categories = [
            cat for cat, score in detected_categories.items() if score >= self.threshold
        ]

        if not qualified_categories:
            return PrefilterResult(
                requires_verification=False,
                categories=[],
                confidence=round(max(detected_categories.values()), 2),
                matched_signals=matched_signals,
            )

        max_confidence = max(detected_categories[cat] for cat in qualified_categories)

        return PrefilterResult(
            requires_verification=True,
            categories=qualified_categories,
            confidence=round(max_confidence, 2),
            matched_signals=matched_signals,
        )
