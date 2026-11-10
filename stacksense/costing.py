"""Order-of-magnitude monthly USD bands.

Figures are rounded from public price pages checked in November 2026,
not a quote. See knowledge/CATALOG.md and the report for the pages.
"""

from __future__ import annotations

import math

BANDS = ("tiny", "small", "mid", "large")


def band_for(users: int, peak: int, data_gb: float, rps: int | None) -> str:
    level = 0
    if users > 5_000 or peak > 100 or data_gb > 20:
        level = 1
    if users > 40_000 or peak > 1_000 or data_gb > 100:
        level = 2
    if users > 200_000 or peak > 5_000 or data_gb > 1_000:
        level = 3
    if rps is not None:
        if rps > 200 and level < 1:
            level = 1
        if rps > 1_000 and level < 2:
            level = 2
        if rps > 5_000:
            level = 3
    return BANDS[level]


def provider_for(host_id: str) -> str:
    if host_id.startswith("aws"):
        return "aws"
    if host_id.startswith("gcp") or host_id == "gcp_run":
        return "gcp"
    if host_id.startswith("azure"):
        return "azure"
    if host_id.startswith("do"):
        return "do"
    if host_id == "docker_compose":
        return "self"
    if host_id in {"cloudflare_pages", "github_pages", "workers", "netlify"}:
        return "edge"
    if host_id == "vercel":
        return "vercel"
    if host_id == "netlify":
        return "netlify"
    return "other"


HOST_BAND = {
    "cloudflare_pages": {"tiny": (0, 0), "small": (0, 0), "mid": (0, 0), "large": (0, 20)},
    "github_pages": {"tiny": (0, 0), "small": (0, 0), "mid": (0, 0), "large": (0, 0)},
    "netlify": {"tiny": (0, 0), "small": (0, 19), "mid": (19, 99), "large": (99, 200)},
    "vercel": {"tiny": (20, 40), "small": (20, 80), "mid": (80, 300), "large": (300, 800)},
    "workers": {"tiny": (0, 5), "small": (5, 25), "mid": (25, 80), "large": (80, 200)},
    "do_app": {"tiny": (5, 12), "small": (12, 50), "mid": (50, 156), "large": (156, 392)},
    "do_droplet": {"tiny": (6, 18), "small": (18, 48), "mid": (48, 96), "large": (96, 192)},
    "aws_ecs": {"tiny": (15, 40), "small": (40, 140), "mid": (120, 400), "large": (300, 900)},
    "aws_lambda": {"tiny": (0, 5), "small": (5, 40), "mid": (40, 200), "large": (200, 800)},
    "aws_ec2": {"tiny": (8, 25), "small": (25, 80), "mid": (80, 250), "large": (250, 700)},
    "aws_eks": {"tiny": (73, 160), "small": (160, 320), "mid": (320, 700), "large": (700, 1600)},
    "gcp_run": {"tiny": (0, 20), "small": (20, 90), "mid": (90, 300), "large": (250, 800)},
    "gcp_vm": {"tiny": (8, 25), "small": (25, 80), "mid": (80, 250), "large": (250, 700)},
    "azure_appservice": {"tiny": (0, 13), "small": (13, 55), "mid": (55, 200), "large": (200, 550)},
    "azure_vm": {"tiny": (15, 40), "small": (40, 110), "mid": (110, 280), "large": (280, 650)},
    "docker_compose": {"tiny": (0, 0), "small": (0, 0), "mid": (0, 0), "large": (0, 0)},
}

# Managed Postgres-class, single node, approximate monthly USD.
PG_BAND = {
    "do": {"tiny": (15, 16), "small": (15, 31), "mid": (61, 122), "large": (122, 244)},
    "aws": {"tiny": (15, 35), "small": (30, 90), "mid": (90, 250), "large": (250, 800)},
    "gcp": {"tiny": (15, 35), "small": (30, 90), "mid": (90, 250), "large": (250, 800)},
    "azure": {"tiny": (15, 40), "small": (30, 100), "mid": (100, 280), "large": (280, 800)},
    "self": {"tiny": (0, 0), "small": (0, 0), "mid": (0, 0), "large": (0, 0)},
    "vercel": {"tiny": (0, 19), "small": (19, 69), "mid": (69, 200), "large": (200, 500)},
    "edge": {"tiny": (0, 0), "small": (0, 0), "mid": (0, 0), "large": (0, 0)},
    "other": {"tiny": (15, 30), "small": (15, 60), "mid": (60, 180), "large": (180, 400)},
    "netlify": {"tiny": (0, 0), "small": (0, 0), "mid": (0, 0), "large": (0, 0)},
}

CACHE_BAND = {
    "do": {"tiny": (0, 0), "small": (15, 15), "mid": (15, 60), "large": (60, 120)},
    "aws": {"tiny": (12, 25), "small": (15, 40), "mid": (40, 120), "large": (120, 300)},
    "gcp": {"tiny": (12, 25), "small": (15, 40), "mid": (40, 120), "large": (120, 300)},
    "azure": {"tiny": (12, 30), "small": (16, 50), "mid": (50, 140), "large": (140, 320)},
    "self": {"tiny": (0, 0), "small": (0, 0), "mid": (0, 0), "large": (0, 0)},
    "other": {"tiny": (0, 15), "small": (15, 40), "mid": (40, 100), "large": (100, 200)},
}

ML_BAND = {
    "tiny": (0, 40),
    "small": (20, 80),
    "mid": (80, 250),
    "large": (200, 700),
}


def _pair(table: dict, key: str, name: str) -> tuple[int, int]:
    row = table.get(key) or table.get("other") or table.get("tiny")
    if isinstance(row, dict):
        return row[name]
    return row


def storage_cost(provider: str, data_gb: float) -> tuple[int, int, str]:
    gb = max(0.0, float(data_gb))
    if provider == "do":
        extra = 0 if gb <= 250 else math.ceil((gb - 250) * 0.02)
        return 5, 5 + extra, "DigitalOcean Spaces is about 5 USD per month and includes 250 GiB."
    if provider == "self":
        return 0, 0, "Object storage is MinIO on disks you already pay for."
    if provider == "edge":
        return 0, 0, "No separate object store on this host."
    lo = max(1, round(gb * 0.023))
    hi = max(8, round(gb * 0.04 + 15))
    return lo, hi, "Object storage is priced near 0.023 USD per GB-month plus requests. Egress is the part that moves the top of the band."


def sms_cost(users_launch: int, users_year: int) -> tuple[int, int, str]:
    active = min(users_year, max(users_launch * 3, users_year // 5 if users_year else 0))
    hi = 8 + round(active * 0.004)
    lo = 0 if users_launch < 1_000 else min(20, hi)
    return lo, max(lo, hi), (
        "SMS OTP is usage priced. The band assumes a fraction of users request a code each month, "
        "about 0.004 USD per active user, and ignores promotional SMS."
    )


def estimate(ctx: dict, picked: dict) -> dict:
    """picked keys: host_id, db_id, db_existing, supporting_layers (set), ha (bool)."""
    scale = ctx["scale"]
    name = band_for(
        scale["users_12_months"],
        scale["peak_concurrent_users"],
        scale["data_volume_gb_12_months"],
        ctx["requirements"]["expected_rps_peak"],
    )
    provider = provider_for(picked["host_id"])
    notes: list[str] = []
    lo_sum = 0
    hi_sum = 0

    def add(lo: int, hi: int, note: str) -> None:
        nonlocal lo_sum, hi_sum
        lo_sum += int(lo)
        hi_sum += int(hi)
        notes.append(note)

    host_id = picked["host_id"]
    if host_id in HOST_BAND:
        hlo, hhi = HOST_BAND[host_id][name]
        if host_id == "vercel" and ctx["budget"]["monthly_infra_usd"] == 0 and ctx["team"]["size"] <= 2 and not ctx["requirements"]["payments"]:
            hlo = 0
        add(hlo, hhi, f"Compute ({host_id}, {name} band) about {hlo} to {hhi} USD.")
    else:
        add(0, 0, "No compute line for this host.")

    db_id = picked["db_id"]
    if db_id in {None, "none"}:
        add(0, 0, "No database process.")
    elif picked.get("db_existing") and db_id == "sqlserver":
        add(0, 0, "The SQL Server licence is treated as already owned. This band is the incremental infra only.")
    elif db_id == "sqlite":
        add(0, 0, "SQLite runs in-process. No extra database bill.")
    elif db_id == "d1":
        add(0, 5, "Cloudflare D1 stays inside the free or lowest paid tier at this size.")
    elif db_id == "dynamodb":
        dynamo = {"tiny": (0, 5), "small": (5, 40), "mid": (40, 200), "large": (200, 1000)}[name]
        add(dynamo[0], dynamo[1], f"DynamoDB on demand, {name} band.")
    elif db_id == "clickhouse":
        base = PG_BAND.get(provider, PG_BAND["other"])[name]
        add(base[0], base[1] + 40, "ClickHouse on a small cluster. The top of the band is disk.")
    else:
        base = PG_BAND.get(provider, PG_BAND["other"])[name]
        lo, hi = base
        if picked.get("ha") and provider not in {"self", "edge"}:
            lo *= 2
            hi *= 2
            notes_ha = " High availability doubles the database line."
        else:
            notes_ha = ""
        engine = "PostgreSQL" if db_id == "postgresql" else db_id
        add(lo, hi, f"{engine} ({provider}, {name} band) about {lo} to {hi} USD.{notes_ha}")

    layers = set(picked.get("supporting_layers") or [])
    if "cache" in layers:
        clo, chi = CACHE_BAND.get(provider, CACHE_BAND["other"])[name]
        if provider == "self":
            add(0, 0, "Cache runs as Valkey on the same machines.")
        elif clo == 0 and chi == 0:
            add(0, 0, "No separate cache bill at this size.")
        else:
            add(clo, chi, f"Managed cache ({provider}) about {clo} to {chi} USD.")

    if "storage" in layers:
        slo, shi, snote = storage_cost(provider, scale["data_volume_gb_12_months"])
        add(slo, shi, snote)

    if "cdn" in layers and provider == "aws":
        add(0, 30 if name in {"tiny", "small"} else 80, "CloudFront for public web assets only. Private objects stay off the CDN.")
    elif "cdn" in layers and provider in {"edge", "vercel", "netlify"}:
        add(0, 0, "CDN is included with the host.")

    if "payments" in layers:
        add(0, 0, "Payment gateway fees are a percentage of volume and are not in this infra band.")

    if "auth" in layers and ctx["requirements"]["auth"] == "phone_otp":
        sms_lo, sms_hi, sms_note = sms_cost(scale["users_at_launch"], scale["users_12_months"])
        add(sms_lo, sms_hi, sms_note)

    if "ml" in layers:
        mlo, mhi = ML_BAND[name]
        add(mlo, mhi, f"Model inference ({name} band) about {mlo} to {mhi} USD, before you retrain.")

    if "observability" in layers and provider == "aws":
        add(5, 25 if name in {"tiny", "small"} else 80, "CloudWatch logs and metrics. The top of the band is chatty debug logs.")
    elif "observability" in layers and provider == "azure":
        add(5, 40, "Application Insights ingestion on a light sampling rate.")
    elif "observability" in layers and provider == "gcp":
        add(0, 30, "Cloud Monitoring on a light sampling rate.")
    elif "observability" in layers and provider == "self":
        add(0, 0, "Prometheus and Grafana run beside the app.")

    if "ci_cd" in layers:
        add(0, 0, "CI minutes are assumed inside the free tier for this team size.")

    if "queue" in layers and provider == "aws":
        add(0, 5, "SQS at this volume is close to free.")

    # Round up so the band never claims a fraction of a dollar.
    lo_sum = int(math.floor(lo_sum))
    hi_sum = int(math.ceil(max(hi_sum, lo_sum)))
    notes.append(
        f"Scale band is {name}: {scale['users_12_months']} users at 12 months, "
        f"peak {scale['peak_concurrent_users']}, {scale['data_volume_gb_12_months']} GB stored."
    )
    notes.append("This is an order-of-magnitude band, not an invoice. Taxes, support plans, and human time are excluded.")
    return {"min": lo_sum, "max": hi_sum, "assumptions": notes, "band": name, "provider": provider}
