"""Read infrastructure.existing_systems into flags the scorer can use."""

from __future__ import annotations

import re

from stacksense.kb import RETIRED


def parse_systems(systems: list[str]) -> dict:
    blob = " \n ".join(systems)
    low = blob.lower()
    version = None
    match = re.search(r"sql server\s*(20\d{2})", low)
    if match:
        version = match.group(1)
    return {
        "entra": bool(re.search(r"entra|\bazure ad\b|azure active directory", low)),
        "okta": "okta" in low,
        "auth0": "auth0" in low or "auth 0" in low,
        "keycloak": "keycloak" in low,
        "active_directory": bool(re.search(r"active directory|\bldap\b", low)) and "azure ad" not in low and "entra" not in low,
        "sqlserver": bool(re.search(r"sql server|\bmssql\b", low)),
        "sqlserver_version": version,
        "postgres": "postgres" in low,
        "mysql": ("mysql" in low) or ("mariadb" in low),
        "mongo": "mongo" in low,
        "oracle": bool(re.search(r"oracle database|oracle db", low)),
        "m365": bool(re.search(r"microsoft 365|office 365|\bm365\b", low)),
        "sharepoint": "sharepoint" in low,
        "fauna": "fauna" in low,
        "realm": ("realm" in low) or ("device sync" in low),
    }


def eol_hits(systems: list[str]) -> list[dict]:
    """First, longest pattern win per system string."""
    ordered = sorted(RETIRED, key=lambda row: len(row["pattern"]), reverse=True)
    hits = []
    for system in systems:
        low = system.lower()
        for row in ordered:
            if row["pattern"] in low:
                hits.append({
                    "system": system,
                    "name": row["name"],
                    "severity": row["severity"],
                    "note": row["note"],
                    "source": row["source"],
                    "pattern": row["pattern"],
                })
                break
    return hits
