"""Strict input validation for the standard scenario schema, plus extras.

Unknown keys are ignored and recorded. Wrong types, bad enums, and
out-of-range numbers become field errors. The engine does not guess.
"""

from __future__ import annotations

import math
from typing import Any

PROJECT_TYPES = {
    "content_site", "web_app", "saas_b2b", "ecommerce", "marketplace", "social",
    "realtime_collab", "fintech", "healthtech", "data_analytics", "iot",
    "ai_ml_product", "internal_tool", "gaming", "api_platform", "other",
}
PLATFORMS = {"web", "android", "ios", "desktop", "api_only"}
TRAFFIC = {"steady", "spiky", "seasonal"}
WORKLOAD = {"read_heavy", "balanced", "write_heavy"}
EXPERIENCE = {"beginner", "intermediate", "senior", "mixed"}
CLOUDS = {"any", "aws", "gcp", "azure", "none"}
DEPLOYMENTS = {"managed_cloud", "self_hosted_cloud_vm", "on_premise", "air_gapped"}
RESIDENCY = {"none", "india", "eu", "us", "other"}
AUTH = {"none", "email_password", "social", "phone_otp", "enterprise_sso"}
ML = {"none", "inference_api", "llm_rag", "training"}
AVAILABILITY = {"99", "99.9", "99.95", "99.99"}
COMPLIANCE = {"gdpr", "dpdp", "hipaa", "pci_dss", "rbi_localisation", "soc2", "iso27001"}
PRIORITY_KEYS = (
    "cost", "time_to_market", "scalability", "performance", "maintainability", "security",
)
SPREADS = {"local", "national", "multi_region"}
LOCK = {"low", "medium", "high"}
SENSITIVITY = {"public", "internal", "confidential", "restricted"}

# Fields a standard file may omit. The message is what we record.
OPTIONAL_DEFAULTS = {
    "project.name": "",
    "project.description": "",
    "scale.peak_concurrent_users": None,  # filled from users later
    "scale.traffic_pattern": "steady",
    "scale.workload": "balanced",
    "scale.data_volume_gb_12_months": 0,
    "scale.geographic_spread": None,  # derived
    "team.has_devops": False,
    "team.vendor_lock_in_tolerance": "medium",
    "budget.existing_licences": [],
    "infrastructure.cloud_preference": "any",
    "infrastructure.deployment_model": "managed_cloud",
    "infrastructure.data_residency": "none",
    "infrastructure.existing_systems": [],
    "requirements.realtime": False,
    "requirements.offline_support": False,
    "requirements.full_text_search": False,
    "requirements.file_media_storage": False,
    "requirements.payments": False,
    "requirements.auth": "none",
    "requirements.multi_tenant": False,
    "requirements.ml_features": "none",
    "requirements.seo_critical": False,
    "requirements.availability": "99.9",
    "requirements.p95_latency_ms": None,
    "requirements.expected_rps_peak": None,
    "compliance": [],
    "operations.on_call": False,
    "data.sensitivity": None,  # derived
}


class Bag:
    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.assumptions: list[str] = []

    def err(self, field: str, message: str) -> None:
        self.errors.append({"field": field, "message": message})

    def assume(self, text: str) -> None:
        if text not in self.assumptions:
            self.assumptions.append(text)


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return False
    return True


def _obj(bag: Bag, raw: Any, field: str) -> dict | None:
    if raw is None:
        bag.err(field, "Missing object.")
        return None
    if not isinstance(raw, dict):
        bag.err(field, "Must be an object.")
        return None
    return raw


def _note_unknown(bag: Bag, obj: dict, allowed: set[str], prefix: str) -> None:
    for key in obj:
        if key not in allowed:
            bag.assume(f"Ignored unknown field {prefix}.{key}.")


def _enum(bag: Bag, obj: dict, key: str, path: str, allowed: set[str], default: str | None) -> str | None:
    if key not in obj or obj[key] is None:
        if default is None:
            bag.err(path, "Missing value.")
            return None
        bag.assume(f"{path} defaulted to {default}.")
        return default
    value = obj[key]
    if not isinstance(value, str):
        bag.err(path, f"Must be a string, one of: {', '.join(sorted(allowed))}.")
        return None
    if value not in allowed:
        bag.err(path, f"Unknown value '{value}'. Allowed: {', '.join(sorted(allowed))}.")
        return None
    return value


def _bool(bag: Bag, obj: dict, key: str, path: str, default: bool | None) -> bool | None:
    if key not in obj or obj[key] is None:
        if default is None:
            bag.err(path, "Missing boolean.")
            return None
        shown = "true" if default else "false"
        bag.assume(f"{path} defaulted to {shown}.")
        return default
    value = obj[key]
    if not _is_bool(value):
        bag.err(path, "Must be a boolean.")
        return None
    return value


def _int(bag: Bag, obj: dict, key: str, path: str, *, minimum: int, default: int | None = None,
         required: bool = False) -> int | None:
    if key not in obj or obj[key] is None:
        if required or default is None:
            bag.err(path, f"Missing integer >= {minimum}.")
            return None
        bag.assume(f"{path} defaulted to {default}.")
        return default
    value = obj[key]
    if not _is_int(value):
        bag.err(path, f"Must be an integer >= {minimum}.")
        return None
    if value < minimum:
        bag.err(path, f"Must be an integer >= {minimum}.")
        return None
    return value


def _number(bag: Bag, obj: dict, key: str, path: str, *, minimum: float, default: float | None = None,
            required: bool = False) -> float | None:
    if key not in obj or obj[key] is None:
        if required or default is None:
            bag.err(path, f"Missing number >= {minimum}.")
            return None
        bag.assume(f"{path} defaulted to {default}.")
        return default
    value = obj[key]
    if not _is_number(value):
        bag.err(path, f"Must be a number >= {minimum}.")
        return None
    if value < minimum:
        bag.err(path, f"Must be a number >= {minimum}.")
        return None
    return float(value)


def _string_list(bag: Bag, obj: dict, key: str, path: str, *, default: list[str] | None,
                 lower: bool = False, enum: set[str] | None = None, allow_empty: bool = True) -> list[str] | None:
    if key not in obj or obj[key] is None:
        if default is None:
            bag.err(path, "Missing list.")
            return None
        if default == [] and key not in obj:
            bag.assume(f"{path} defaulted to an empty list.")
        return list(default)
    value = obj[key]
    if not isinstance(value, list):
        bag.err(path, "Must be a list of strings.")
        return None
    out: list[str] = []
    changed_case = False
    for index, item in enumerate(value):
        if not isinstance(item, str):
            bag.err(f"{path}[{index}]", "Must be a string.")
            continue
        text = item.strip()
        if text == "":
            bag.err(f"{path}[{index}]", "Must be a non-empty string.")
            continue
        if enum is not None and text not in enum:
            if lower and text.lower() in enum and text != text.lower():
                bag.err(f"{path}[{index}]", f"Unknown value '{item}'. Enum values are lower-case, for example '{text.lower()}'.")
            else:
                bag.err(f"{path}[{index}]", f"Unknown value '{text}'. Allowed: {', '.join(sorted(enum))}.")
            continue
        if lower and text != text.lower():
            changed_case = True
            text = text.lower()
        if text not in out:
            out.append(text)
    if changed_case:
        bag.assume(f"{path} values were lower-cased.")
    if not allow_empty and not out and not any(e["field"].startswith(path) for e in bag.errors):
        bag.err(path, "Must be a non-empty list.")
    return out


def _priorities(bag: Bag, raw: Any) -> dict[str, int]:
    result = {key: 3 for key in PRIORITY_KEYS}
    if raw is None:
        bag.assume("priorities defaulted to 3 for every key.")
        return result
    if not isinstance(raw, dict):
        bag.err("priorities", "Must be an object of integers from 1 to 5.")
        return result
    for key in raw:
        if key not in PRIORITY_KEYS:
            bag.assume(f"Ignored unknown field priorities.{key}.")
    missing = [key for key in PRIORITY_KEYS if key not in raw or raw[key] is None]
    if missing:
        bag.assume("priorities." + ", priorities.".join(missing) + " defaulted to 3.")
    for key in PRIORITY_KEYS:
        if key not in raw or raw[key] is None:
            continue
        value = raw[key]
        if not _is_int(value) or value < 1 or value > 5:
            bag.err(f"priorities.{key}", "Must be an integer from 1 to 5.")
            continue
        result[key] = value
    return result


def _latency(bag: Bag, req: dict) -> int | None:
    if "p95_latency_ms" not in req or req["p95_latency_ms"] is None:
        return None
    value = req["p95_latency_ms"]
    if not _is_int(value) or value <= 0:
        bag.err("requirements.p95_latency_ms", "Must be an integer > 0, or null.")
        return None
    return value


def _rps(bag: Bag, req: dict) -> int | None:
    if "expected_rps_peak" not in req or req["expected_rps_peak"] is None:
        return None
    value = req["expected_rps_peak"]
    if not _is_int(value) or value < 0:
        bag.err("requirements.expected_rps_peak", "Must be an integer >= 0.")
        return None
    return value


def validate(raw: Any) -> tuple[dict | None, list[dict[str, str]], list[str]]:
    """Return (normalized, errors, assumptions). normalized is None when errors exist."""
    bag = Bag()
    if not isinstance(raw, dict):
        bag.err("(root)", "Input must be a JSON object in the standard scenario schema.")
        return None, bag.errors, bag.assumptions

    for key in raw:
        if key not in {
            "scenario_id", "project", "scale", "team", "budget", "timeline",
            "infrastructure", "requirements", "compliance", "priorities",
            "operations", "data",
        }:
            bag.assume(f"Ignored unknown field {key}.")

    scenario_id = raw.get("scenario_id")
    if scenario_id is not None and not isinstance(scenario_id, str):
        bag.err("scenario_id", "Must be a string when present.")
        scenario_id = None

    project_raw = _obj(bag, raw.get("project"), "project") or {}
    if isinstance(raw.get("project"), dict):
        _note_unknown(bag, project_raw, {"name", "type", "description", "platforms"}, "project")
    name = project_raw.get("name", None)
    if name is None:
        name = ""
        if "project" in raw:
            bag.assume("project.name defaulted to an empty string.")
    elif not isinstance(name, str):
        bag.err("project.name", "Must be a string.")
        name = ""
    description = project_raw.get("description", None)
    if description is None:
        description = ""
        if isinstance(raw.get("project"), dict):
            bag.assume("project.description defaulted to an empty string.")
    elif not isinstance(description, str):
        bag.err("project.description", "Must be a string.")
        description = ""
    ptype = _enum(bag, project_raw, "type", "project.type", PROJECT_TYPES, None)
    platforms = _string_list(
        bag, project_raw, "platforms", "project.platforms",
        default=None, lower=True, enum=PLATFORMS, allow_empty=False,
    ) or []

    scale_raw = _obj(bag, raw.get("scale"), "scale") or {}
    if isinstance(raw.get("scale"), dict):
        _note_unknown(bag, scale_raw, {
            "users_at_launch", "users_12_months", "peak_concurrent_users",
            "traffic_pattern", "workload", "data_volume_gb_12_months", "geographic_spread",
        }, "scale")
    users_launch = _int(bag, scale_raw, "users_at_launch", "scale.users_at_launch", minimum=0, required=True)
    users_year = _int(bag, scale_raw, "users_12_months", "scale.users_12_months", minimum=0, required=True)
    if "peak_concurrent_users" not in scale_raw or scale_raw.get("peak_concurrent_users") is None:
        peak = None
    else:
        peak = _int(bag, scale_raw, "peak_concurrent_users", "scale.peak_concurrent_users", minimum=0, required=True)
    traffic = _enum(bag, scale_raw, "traffic_pattern", "scale.traffic_pattern", TRAFFIC, "steady")
    workload = _enum(bag, scale_raw, "workload", "scale.workload", WORKLOAD, "balanced")
    if "data_volume_gb_12_months" not in scale_raw or scale_raw.get("data_volume_gb_12_months") is None:
        data_gb = 0.0
        if "scale" in raw:
            bag.assume("scale.data_volume_gb_12_months defaulted to 0.")
    else:
        data_gb = _number(bag, scale_raw, "data_volume_gb_12_months", "scale.data_volume_gb_12_months", minimum=0, required=True)
    if "geographic_spread" not in scale_raw or scale_raw.get("geographic_spread") is None:
        spread = None
    else:
        spread = _enum(bag, scale_raw, "geographic_spread", "scale.geographic_spread", SPREADS, None)

    team_raw = _obj(bag, raw.get("team"), "team") or {}
    if isinstance(raw.get("team"), dict):
        _note_unknown(bag, team_raw, {
            "size", "experience", "languages", "has_devops", "vendor_lock_in_tolerance",
        }, "team")
    team_size = _int(bag, team_raw, "size", "team.size", minimum=1, required=True)
    experience = _enum(bag, team_raw, "experience", "team.experience", EXPERIENCE, None)
    languages = _string_list(
        bag, team_raw, "languages", "team.languages",
        default=None, lower=True, allow_empty=True,
    )
    if languages is None:
        languages = []
    has_devops = _bool(bag, team_raw, "has_devops", "team.has_devops", False)
    lock = _enum(bag, team_raw, "vendor_lock_in_tolerance", "team.vendor_lock_in_tolerance", LOCK, "medium")

    budget_raw = _obj(bag, raw.get("budget"), "budget") or {}
    if isinstance(raw.get("budget"), dict):
        _note_unknown(bag, budget_raw, {"monthly_infra_usd", "existing_licences"}, "budget")
    money = _number(bag, budget_raw, "monthly_infra_usd", "budget.monthly_infra_usd", minimum=0, required=True)
    licences = _string_list(
        bag, budget_raw, "existing_licences", "budget.existing_licences",
        default=[], lower=True, allow_empty=True,
    ) or []

    time_raw = _obj(bag, raw.get("timeline"), "timeline") or {}
    if isinstance(raw.get("timeline"), dict):
        _note_unknown(bag, time_raw, {"mvp_weeks"}, "timeline")
    weeks = _int(bag, time_raw, "mvp_weeks", "timeline.mvp_weeks", minimum=1, required=True)

    if "infrastructure" not in raw:
        infra_raw = {}
    else:
        infra_raw = _obj(bag, raw.get("infrastructure"), "infrastructure") or {}
    if isinstance(raw.get("infrastructure"), dict):
        _note_unknown(bag, infra_raw, {
            "cloud_preference", "deployment_model", "data_residency", "existing_systems",
        }, "infrastructure")
    cloud = _enum(bag, infra_raw, "cloud_preference", "infrastructure.cloud_preference", CLOUDS, "any")
    deploy = _enum(bag, infra_raw, "deployment_model", "infrastructure.deployment_model", DEPLOYMENTS, "managed_cloud")
    residency = _enum(bag, infra_raw, "data_residency", "infrastructure.data_residency", RESIDENCY, "none")
    existing = _string_list(
        bag, infra_raw, "existing_systems", "infrastructure.existing_systems",
        default=[], lower=False, allow_empty=True,
    ) or []

    req_raw = raw.get("requirements", None)
    if req_raw is None:
        req_raw = {}
    req_obj = _obj(bag, req_raw, "requirements") or {}
    if isinstance(raw.get("requirements"), dict):
        _note_unknown(bag, req_obj, {
            "realtime", "offline_support", "full_text_search", "file_media_storage",
            "payments", "auth", "multi_tenant", "ml_features", "seo_critical",
            "availability", "p95_latency_ms", "expected_rps_peak",
        }, "requirements")
    realtime = _bool(bag, req_obj, "realtime", "requirements.realtime", False)
    offline = _bool(bag, req_obj, "offline_support", "requirements.offline_support", False)
    search = _bool(bag, req_obj, "full_text_search", "requirements.full_text_search", False)
    files = _bool(bag, req_obj, "file_media_storage", "requirements.file_media_storage", False)
    payments = _bool(bag, req_obj, "payments", "requirements.payments", False)
    auth = _enum(bag, req_obj, "auth", "requirements.auth", AUTH, "none")
    multi = _bool(bag, req_obj, "multi_tenant", "requirements.multi_tenant", False)
    ml = _enum(bag, req_obj, "ml_features", "requirements.ml_features", ML, "none")
    seo = _bool(bag, req_obj, "seo_critical", "requirements.seo_critical", False)
    availability = _enum(bag, req_obj, "availability", "requirements.availability", AVAILABILITY, "99.9")
    latency = _latency(bag, req_obj if isinstance(raw.get("requirements"), dict) or raw.get("requirements") is None else {})
    if isinstance(raw.get("requirements"), dict):
        rps = _rps(bag, req_obj)
    else:
        rps = None

    if "compliance" not in raw or raw.get("compliance") is None:
        if "compliance" not in raw:
            bag.assume("compliance defaulted to an empty list.")
        else:
            bag.err("compliance", "Must be a list of strings.")
        compliance: list[str] = []
    else:
        compliance = _string_list(
            bag, raw, "compliance", "compliance",
            default=None, lower=True, enum=COMPLIANCE, allow_empty=True,
        ) or []

    priorities = _priorities(bag, raw.get("priorities") if "priorities" in raw else None)
    if "priorities" not in raw:
        # _priorities already records the default when raw is None. Passing None
        # happens for a missing key too. The message is enough.
        pass

    operations_raw = raw.get("operations", None)
    if operations_raw is None:
        on_call = False
        bag.assume("operations.on_call defaulted to false.")
    else:
        operations_obj = _obj(bag, operations_raw, "operations") or {}
        if isinstance(operations_raw, dict):
            _note_unknown(bag, operations_obj, {"on_call"}, "operations")
        on_call = _bool(bag, operations_obj, "on_call", "operations.on_call", False)

    data_raw = raw.get("data", None)
    sensitivity: str | None
    if data_raw is None:
        sensitivity = None
    else:
        data_obj = _obj(bag, data_raw, "data") or {}
        if isinstance(data_raw, dict):
            _note_unknown(bag, data_obj, {"sensitivity"}, "data")
        if "sensitivity" not in data_obj or data_obj.get("sensitivity") is None:
            sensitivity = None
            bag.assume("data.sensitivity left unset and will be derived.")
        else:
            sensitivity = _enum(bag, data_obj, "sensitivity", "data.sensitivity", SENSITIVITY, None)

    if bag.errors:
        return None, bag.errors, bag.assumptions

    assert users_launch is not None and users_year is not None
    assert team_size is not None and weeks is not None and money is not None
    assert ptype and experience and platforms is not None

    if peak is None:
        peak = max(1, users_launch // 10) if users_launch else 1
        bag.assume(
            f"scale.peak_concurrent_users defaulted to {peak} "
            "(about a tenth of users at launch, minimum 1)."
        )

    if spread is None:
        if residency in {"india", "eu", "us"}:
            spread = "national"
            bag.assume(f"scale.geographic_spread defaulted to national because data_residency is {residency}.")
        elif users_year >= 100_000:
            spread = "multi_region"
            bag.assume("scale.geographic_spread defaulted to multi_region because the 12 month user count is high and residency is open.")
        elif users_year >= 10_000:
            spread = "national"
            bag.assume("scale.geographic_spread defaulted to national.")
        else:
            spread = "local"
            bag.assume("scale.geographic_spread defaulted to local.")

    if sensitivity is None:
        if "hipaa" in compliance or "pci_dss" in compliance or "rbi_localisation" in compliance:
            sensitivity = "restricted"
            bag.assume("data.sensitivity defaulted to restricted because a strict compliance regime is set.")
        elif "dpdp" in compliance or "gdpr" in compliance:
            sensitivity = "confidential"
            bag.assume("data.sensitivity defaulted to confidential because a privacy law is set.")
        elif ptype == "internal_tool":
            sensitivity = "internal"
            bag.assume("data.sensitivity defaulted to internal for an internal tool.")
        elif ptype == "content_site" and auth == "none":
            sensitivity = "public"
            bag.assume("data.sensitivity defaulted to public for a content site with no auth.")
        elif ptype in {"fintech", "healthtech"}:
            sensitivity = "restricted"
            bag.assume("data.sensitivity defaulted to restricted because the project type handles sensitive records.")
        else:
            sensitivity = "internal"
            bag.assume("data.sensitivity defaulted to internal.")

    if rps is None:
        assumed = max(1, int(peak) // 10)
        bag.assume(
            f"requirements.expected_rps_peak was not set. Capacity uses peak concurrency ({peak}), "
            f"which is roughly {assumed} requests per second if about one in ten connected users acts at once."
        )

    normalized = {
        "scenario_id": scenario_id,
        "project": {
            "name": name.strip(),
            "type": ptype,
            "description": description,
            "platforms": platforms,
        },
        "scale": {
            "users_at_launch": users_launch,
            "users_12_months": users_year,
            "peak_concurrent_users": peak,
            "traffic_pattern": traffic,
            "workload": workload,
            "data_volume_gb_12_months": data_gb if data_gb is not None else 0,
            "geographic_spread": spread,
        },
        "team": {
            "size": team_size,
            "experience": experience,
            "languages": languages,
            "has_devops": bool(has_devops),
            "vendor_lock_in_tolerance": lock or "medium",
        },
        "budget": {
            "monthly_infra_usd": money,
            "existing_licences": licences,
        },
        "timeline": {"mvp_weeks": weeks},
        "infrastructure": {
            "cloud_preference": cloud,
            "deployment_model": deploy,
            "data_residency": residency,
            "existing_systems": existing,
        },
        "requirements": {
            "realtime": bool(realtime),
            "offline_support": bool(offline),
            "full_text_search": bool(search),
            "file_media_storage": bool(files),
            "payments": bool(payments),
            "auth": auth,
            "multi_tenant": bool(multi),
            "ml_features": ml,
            "seo_critical": bool(seo),
            "availability": availability,
            "p95_latency_ms": latency,
            "expected_rps_peak": rps,
        },
        "compliance": compliance,
        "priorities": priorities,
        "operations": {"on_call": bool(on_call)},
        "data": {"sensitivity": sensitivity},
    }
    return normalized, [], bag.assumptions
