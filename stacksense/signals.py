"""Keyword signals from a free-text description.

This is a rule list, not a model. It only nudges scoring and warnings.
The same text always produces the same signals. It never calls a network.
"""

from __future__ import annotations


def extract(description: str) -> dict[str, bool]:
    text = (description or "").lower()
    return {
        "markdown": "markdown" in text,
        "ledger": ("ledger" in text) or ("double-entry" in text) or ("double entry" in text),
        "upi": "upi" in text,
        "kyc": "kyc" in text or "know your customer" in text,
        "low_end": any(token in text for token in ("2 gb", "2gb", "low-end", "low end", "low ram")),
        "poor_network": any(token in text for token in ("2g", "3g", "intermittent", "patchy")),
        "per_seat": ("per seat" in text) or ("per-seat" in text),
        "gps": ("gps" in text) or ("geotag" in text) or ("geo-tag" in text),
        "chat": "chat" in text,
    }
