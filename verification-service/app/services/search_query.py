from typing import Dict, List, Optional
from app.schemas.claims import ClaimCategory, ExtractedClaim


class SearchQueryGenerator:
    """
    Generates targeted web search queries and identifies authoritative domain preferences
    from structured claim attributes.
    """

    AUTHORITATIVE_DOMAINS: Dict[str, List[str]] = {
        "python": ["python.org"],
        "openai": ["openai.com"],
        "nvidia": ["nvidia.com"],
        "microsoft": ["microsoft.com"],
        "google": ["google.com", "blog.google"],
        "apple": ["apple.com"],
        "stripe": ["stripe.com"],
        "amazon": ["amazon.com", "aws.amazon.com"],
        "aws": ["aws.amazon.com"],
        "go": ["go.dev"],
        "golang": ["go.dev"],
        "rust": ["rust-lang.org"],
        "node": ["nodejs.org"],
        "nodejs": ["nodejs.org"],
        "react": ["react.dev"],
        "fastapi": ["fastapi.tiangolo.com"],
        "github": ["github.com"],
        "meta": ["meta.com", "about.meta.com"],
    }

    @classmethod
    def get_authoritative_domains(cls, entity: str) -> List[str]:
        """Returns known authoritative domains for the given entity if available."""
        clean_entity = entity.strip().lower()
        return cls.AUTHORITATIVE_DOMAINS.get(clean_entity, [])

    @classmethod
    def generate_query(cls, claim: ExtractedClaim) -> str:
        """
        Builds a precision search query from the claim's entity, attribute, category, and text.
        """
        entity = claim.entity.strip()
        attribute = claim.attribute.strip().replace("_", " ")
        category = claim.category

        if category == ClaimCategory.SOFTWARE_VERSION:
            return f"{entity} latest stable version release notes official"
        elif category == ClaimCategory.PRICING:
            return f"{entity} {attribute} price cost pricing official"
        elif category == ClaimCategory.LEADERSHIP:
            return f"{entity} current {attribute} official leadership"
        elif category == ClaimCategory.PRODUCT_AVAILABILITY:
            return f"{entity} stock availability buy now official"
        elif category == ClaimCategory.RECENT_EVENTS:
            return f"{entity} {attribute} announcement latest news"
        elif category == ClaimCategory.CURRENT_STATISTICS or category.value == "statistics":
            return f"{entity} {attribute} latest data statistics"
        else:
            return f"{entity} {claim.text}"
