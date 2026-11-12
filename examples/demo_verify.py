#!/usr/bin/env python3
"""FreshGuard Interactive Demonstration CLI

Allows developers and judges to submit candidate response text to the
FreshGuard Verification Service (or local pipeline) and inspect structured
claims, Tavily-retrieved evidence, calibrated confidence, verdicts, and
Bifrost semantic cache freshness policies.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict


def verify_text(
    endpoint: str,
    text: str,
    api_key: str = "",
    categories: list = None,
) -> Dict[str, Any]:
    url = endpoint.rstrip("/") + "/v1/verifications"
    payload = {
        "request_id": f"demo-{int(urllib.request.time.time())}",
        "text": text,
        "mode": "blocking",
        "categories": categories or ["pricing", "software_version", "leadership"],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    if api_key:
        req.add_header("X-API-Key", api_key)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            return {"error": json.loads(error_body), "http_status": e.code}
        except Exception:
            return {"error": error_body, "http_status": e.code}
    except Exception as e:
        return {"error": str(e)}


def print_result(res: Dict[str, Any]) -> None:
    print("\n" + "=" * 65)
    print(" 🛡️  FRESHGUARD VERIFICATION RESULT")
    print("=" * 65)

    if "error" in res:
        print(f"❌ Error: {res['error']}")
        return

    print(f"Job ID:           {res.get('verification_id', 'N/A')}")
    print(f"Request ID:       {res.get('request_id', 'N/A')}")
    print(f"Lifecycle Status: {res.get('status', 'N/A').upper()}")
    print(f"Freshness State:  {res.get('freshness_status', 'N/A')}")
    print(f"Requires Refresh: {res.get('requires_refresh', False)}")
    print(f"Claims Evaluated: {res.get('claims_checked', 0)}")
    print(f"Checked At:       {res.get('checked_at', 'N/A')}")

    claims = res.get("claims") or res.get("results") or []
    if not claims:
        print("\nℹ️  No time-sensitive claims identified in response text.")
        print("=" * 65 + "\n")
        return

    print(f"\n📋 Claims ({len(claims)} found):")
    for i, c in enumerate(claims, 1):
        verdict = c.get("verdict", "unclear").lower()
        badge = (
            "✅ SUPPORTED"
            if verdict == "supported"
            else ("❌ CONTRADICTED" if verdict == "contradicted" else "⚠️  UNCLEAR")
        )
        conf = c.get("confidence", 0.0)
        print(f"\n  [{i}] {badge} (Confidence: {conf * 100:.1f}%)")
        print(f"      Entity:    {c.get('entity', 'N/A')}")
        print(f"      Attribute: {c.get('attribute', 'N/A')}")
        print(f"      Category:  {c.get('category', 'N/A')}")
        print(f"      Claim:     \"{c.get('original_text') or c.get('text', 'N/A')}\"")
        if c.get("corrected_value"):
            print(f"      Corrected: {c.get('corrected_value')}")
        if c.get("reason"):
            print(f"      Reason:    {c.get('reason')}")

        ev_list = c.get("evidence", [])
        if ev_list:
            print(f"      Grounding Evidence ({len(ev_list)} references):")
            for ev in ev_list:
                title = ev.get("source_title") or ev.get("title") or "Source"
                url = ev.get("source_url") or ev.get("url") or ""
                snippet = ev.get("snippet") or ev.get("content") or ""
                if len(snippet) > 100:
                    snippet = snippet[:100] + "..."
                print(f"        • {title} ({url})")
                if snippet:
                    print(f"          \"{snippet}\"")

    print("\n" + "=" * 65 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FreshGuard Interactive Verification Demo"
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000",
        help="Verification service URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional X-API-Key header",
    )
    parser.add_argument(
        "--text",
        default="ChatGPT Plus pricing is $20 per month. Python 3.12 is the latest major release.",
        help="LLM response text to verify",
    )

    args = parser.parse_args()
    print(f"Connecting to FreshGuard Verification Service at {args.endpoint}...")
    print(f"Analyzing prompt:\n\"{args.text}\"")

    res = verify_text(args.endpoint, args.text, args.api_key)
    print_result(res)


if __name__ == "__main__":
    main()

