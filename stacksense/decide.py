"""Pick a stack with filters and weighted scores. No randomness, no network."""

from __future__ import annotations

from stacksense import __version__
from stacksense.costing import estimate
from stacksense.existing import eol_hits, parse_systems
from stacksense.kb import (
    BACKEND,
    DATABASE,
    FRONTEND,
    HOSTING,
    BACKEND_BY_ID,
    DATABASE_BY_ID,
    HOSTING_BY_ID,
)
from stacksense.signals import extract
from stacksense.validate import validate

CORE_LANGS = {
    "javascript", "typescript", "python", "java", "csharp", "php", "go",
    "kotlin", "ruby", "swift", "dart", "rust", "elixir", "scala",
}

SERVER_TYPES = {
    "web_app", "saas_b2b", "ecommerce", "marketplace", "social", "realtime_collab",
    "fintech", "healthtech", "data_analytics", "iot", "ai_ml_product",
    "internal_tool", "gaming", "api_platform",
}
COMPLEX_TYPES = {"fintech", "marketplace", "ecommerce", "healthtech", "saas_b2b", "ai_ml_product"}

INTERACT_NEED = {
    "content_site": 2, "internal_tool": 3, "web_app": 3, "saas_b2b": 4,
    "ecommerce": 4, "marketplace": 4, "fintech": 3, "healthtech": 3,
    "social": 4, "realtime_collab": 5, "gaming": 4, "data_analytics": 3,
    "iot": 2, "api_platform": 1, "ai_ml_product": 3, "other": 3,
}

REGION_LABEL = {
    "aws": {
        "india": "ap-south-1 (Mumbai)",
        "eu": "eu-central-1 (Frankfurt)",
        "us": "us-east-1 (N. Virginia)",
        "none": "us-east-1 (N. Virginia)",
        "other": "ap-southeast-1 (Singapore)",
    },
    "gcp": {
        "india": "asia-south1 (Mumbai)",
        "eu": "europe-west1 (Belgium)",
        "us": "us-central1 (Iowa)",
        "none": "us-central1 (Iowa)",
        "other": "asia-southeast1 (Singapore)",
    },
    "azure": {
        "india": "Central India (Pune)",
        "eu": "West Europe (Netherlands)",
        "us": "East US",
        "none": "East US",
        "other": "Southeast Asia (Singapore)",
    },
    "do": {
        "india": "BLR1 (Bangalore)",
        "eu": "FRA1 (Frankfurt)",
        "us": "NYC1 (New York)",
        "none": "NYC1 (New York)",
        "other": "SGP1 (Singapore)",
    },
    "self": {
        "india": "your India facility",
        "eu": "your EU facility",
        "us": "your US facility",
        "none": "your own facility",
        "other": "your own facility",
    },
    "edge": {key: "the global edge" for key in ("india", "eu", "us", "none", "other")},
}

DB_PRODUCT = {
    ("postgresql", "aws"): "Amazon RDS for PostgreSQL",
    ("postgresql", "gcp"): "Cloud SQL for PostgreSQL",
    ("postgresql", "azure"): "Azure Database for PostgreSQL",
    ("postgresql", "do"): "DigitalOcean Managed PostgreSQL",
    ("postgresql", "self"): "PostgreSQL on your machines",
    ("postgresql", "vercel"): "Neon PostgreSQL",
    ("mysql", "aws"): "Amazon RDS for MySQL",
    ("mysql", "gcp"): "Cloud SQL for MySQL",
    ("mysql", "azure"): "Azure Database for MySQL",
    ("mysql", "do"): "DigitalOcean Managed MySQL",
    ("mysql", "self"): "MySQL on your machines",
    ("mongodb", "aws"): "MongoDB on Amazon EC2 or Atlas in-region",
    ("mongodb", "self"): "MongoDB on your machines",
    ("mongodb", "do"): "DigitalOcean Managed MongoDB",
    ("mongodb", "gcp"): "MongoDB on Compute Engine",
    ("mongodb", "azure"): "MongoDB on Azure",
}


def recommend(raw: object) -> dict:
    try:
        return _recommend(raw)
    except Exception:
        return _failed()


def _failed() -> dict:
    return {
        "scenario_id": None,
        "engine_version": __version__,
        "status": "invalid_input",
        "summary": "The engine hit an unexpected error and stopped before choosing a stack.",
        "architecture_style": "other",
        "deployment_region": None,
        "stack": None,
        "estimated_monthly_cost_usd": {
            "min": 0,
            "max": 0,
            "assumptions": ["No estimate, because scoring did not finish."],
        },
        "warnings": [],
        "assumptions": [],
        "validation_errors": [{
            "field": "(engine)",
            "message": "Unexpected error while scoring. No stack was produced.",
        }],
    }


def _invalid(raw: object, errors: list[dict], assumptions: list[str]) -> dict:
    scenario_id = raw.get("scenario_id") if isinstance(raw, dict) else None
    if not isinstance(scenario_id, str):
        scenario_id = None
    count = len(errors)
    noun = "problem" if count == 1 else "problems"
    return {
        "scenario_id": scenario_id,
        "engine_version": __version__,
        "status": "invalid_input",
        "summary": f"The input has {count} {noun}. No stack was produced.",
        "architecture_style": "other",
        "deployment_region": None,
        "stack": None,
        "estimated_monthly_cost_usd": {
            "min": 0,
            "max": 0,
            "assumptions": ["No estimate, because the input is invalid."],
        },
        "warnings": [],
        "assumptions": assumptions,
        "validation_errors": errors,
    }


class Ctx:
    def __init__(self, norm: dict, assumptions: list[str]) -> None:
        self.n = norm
        self.assumptions = list(assumptions)
        self.signals = extract(norm["project"]["description"])
        self.existing = parse_systems(norm["infrastructure"]["existing_systems"])
        self.eol = eol_hits(norm["infrastructure"]["existing_systems"])
        self.warnings: list[dict] = []
        self.relaxed = False
        self.effective_residency = norm["infrastructure"]["data_residency"]
        self.effective_deploy = norm["infrastructure"]["deployment_model"]
        self.auth = norm["requirements"]["auth"]
        self.payments = norm["requirements"]["payments"]

    def warn(self, code: str, severity: str, message: str, fields: list[str]) -> None:
        self.warnings.append({
            "code": code,
            "severity": severity,
            "message": message,
            "fields": fields,
        })

    @property
    def budget(self) -> float:
        return self.n["budget"]["monthly_infra_usd"]

    @property
    def languages(self) -> list[str]:
        return self.n["team"]["languages"]

    @property
    def devops(self) -> bool:
        return self.n["team"]["has_devops"]

    @property
    def peak(self) -> int:
        return self.n["scale"]["peak_concurrent_users"]

    @property
    def users(self) -> int:
        return self.n["scale"]["users_12_months"]

    @property
    def ptype(self) -> str:
        return self.n["project"]["type"]

    @property
    def platforms(self) -> list[str]:
        return self.n["project"]["platforms"]


def _recommend(raw: object) -> dict:
    norm, errors, assumptions = validate(raw)
    if errors or norm is None:
        return _invalid(raw, errors, assumptions)
    ctx = Ctx(norm, assumptions)
    _apply_hard_constraints(ctx)
    _warn_scale(ctx)
    _warn_eol(ctx)
    fe = choose_frontend(ctx)
    be = choose_backend(ctx, fe)
    needs_be = be["id"] != "none"
    ml_split = _ml_is_split(ctx)
    arch = choose_architecture(ctx, needs_be, be, ml_split)
    if arch == "serverless" and be["record"].get("long_lived") and be["id"] not in {"workers", "none"}:
        if ctx.peak > 40 or ctx.n["requirements"]["realtime"]:
            arch = "monolith" if ctx.ptype not in COMPLEX_TYPES else "modular_monolith"
            ctx.assumptions.append(
                "Serverless was dropped because the chosen server is long-lived and the peak is not a short request spike."
            )
    host = choose_hosting(ctx, fe, be, arch)
    db = choose_database(ctx, host, needs_be)
    supporting = choose_supporting(ctx, fe, be, db, host, arch)
    _warn_skill(ctx, fe, be)
    _warn_timeline(ctx, arch, fe)
    _warn_availability(ctx, db)
    _warn_product_risks(ctx, host, db)
    cost = _cost_with_budget(ctx, host, db, supporting)
    status = _status(ctx, cost)
    summary = _summary(ctx, arch, fe, be, db, host)
    return _output(ctx, status, summary, arch, host, fe, be, db, supporting, cost)


def _apply_hard_constraints(ctx: Ctx) -> None:
    cloud = ctx.n["infrastructure"]["cloud_preference"]
    deploy = ctx.n["infrastructure"]["deployment_model"]
    residency = ctx.n["infrastructure"]["data_residency"]
    compliance = set(ctx.n["compliance"])

    if cloud == "none" and deploy == "managed_cloud":
        ctx.effective_deploy = "on_premise"
        ctx.relaxed = True
        ctx.warn(
            "CLOUD_NONE_CONFLICT",
            "critical",
            "cloud_preference none and deployment_model managed_cloud cannot both be true. The engine relaxed managed_cloud and kept the workload on machines you control.",
            ["infrastructure.cloud_preference", "infrastructure.deployment_model"],
        )
        ctx.assumptions.append("Relaxed infrastructure.deployment_model from managed_cloud to on_premise because cloud_preference is none.")
    elif cloud not in {"any", "none"} and deploy in {"on_premise", "air_gapped"}:
        ctx.relaxed = True
        ctx.effective_deploy = deploy
        ctx.warn(
            "CLOUD_VS_DEPLOYMENT",
            "critical",
            f"cloud_preference is {cloud} but deployment_model is {deploy}. The engine kept the workload on your machines and did not place it on {cloud}.",
            ["infrastructure.cloud_preference", "infrastructure.deployment_model"],
        )
        ctx.assumptions.append(
            f"Relaxed infrastructure.cloud_preference {cloud} because deployment_model is {deploy}."
        )
    else:
        ctx.effective_deploy = deploy

    effective = residency
    if "rbi_localisation" in compliance and residency not in {"india"}:
        if residency != "none":
            ctx.relaxed = True
            ctx.warn(
                "RBI_RESIDENCY_CONFLICT",
                "critical",
                f"RBI payment-data rules require storage in India, which conflicts with data_residency {residency}. The engine pinned storage to India and this input is infeasible until those two are aligned.",
                ["compliance", "infrastructure.data_residency"],
            )
            ctx.assumptions.append(
                f"Relaxed infrastructure.data_residency from {residency} to india because rbi_localisation is set."
            )
        else:
            ctx.assumptions.append(
                "data_residency was none and rbi_localisation is set, so storage is pinned to India."
            )
            ctx.warn(
                "RBI_PINNED_INDIA",
                "warning",
                "RBI localisation is set and data_residency was none. Payment data is pinned to an India region. Say so in your architecture review.",
                ["compliance", "infrastructure.data_residency"],
            )
        effective = "india"
    elif "gdpr" in compliance and residency == "none":
        effective = "eu"
        ctx.assumptions.append(
            "GDPR is set and data_residency was none, so the engine pins hosting to an EU region."
        )
        ctx.warn(
            "GDPR_REGION",
            "info",
            "GDPR is in the list and no residency was set. The stack is placed in the EU. A transfer tool is still your job if any processor sits outside that region.",
            ["compliance", "infrastructure.data_residency"],
        )
    elif "hipaa" in compliance and residency == "none":
        effective = "us"
        ctx.assumptions.append("HIPAA is set and data_residency was none, so the engine pins hosting to a US region.")
    elif "gdpr" in compliance and residency not in {"eu", "none"}:
        ctx.warn(
            "GDPR_TRANSFER",
            "warning",
            f"GDPR is set and data_residency is {residency}. The engine did not move the pin. If any user is in the EU you need a lawful transfer, or change the residency.",
            ["compliance", "infrastructure.data_residency"],
        )

    if residency == "other" and effective == "other":
        ctx.warn(
            "RESIDENCY_OTHER",
            "warning",
            "data_residency other does not name a country. The engine uses a documented fallback region and you should replace it with the real one before buying anything.",
            ["infrastructure.data_residency"],
        )

    ctx.effective_residency = effective

    air = ctx.effective_deploy == "air_gapped"
    if air and ctx.auth == "social":
        ctx.auth = "email_password"
        ctx.relaxed = True
        ctx.dropped_auth = "social"
        ctx.warn(
            "AIRGAP_SOCIAL_AUTH",
            "critical",
            "Social login needs a public identity provider. An air-gapped network cannot reach one. The engine fell back to local accounts.",
            ["infrastructure.deployment_model", "requirements.auth"],
        )
        ctx.assumptions.append("Relaxed requirements.auth from social to local accounts because deployment_model is air_gapped.")
    if air and ctx.auth == "phone_otp":
        ctx.auth = "email_password"
        ctx.relaxed = True
        ctx.warn(
            "AIRGAP_PHONE_OTP",
            "critical",
            "Phone OTP needs an SMS provider on the public network. An air-gapped deployment cannot use one. The engine fell back to local accounts.",
            ["infrastructure.deployment_model", "requirements.auth"],
        )
        ctx.assumptions.append("Relaxed requirements.auth from phone_otp to local accounts because deployment_model is air_gapped.")
    if air and ctx.payments:
        ctx.payments = False
        ctx.relaxed = True
        ctx.warn(
            "AIRGAP_PAYMENTS",
            "critical",
            "Taking payment needs a payment gateway on the public network. An air-gapped deployment cannot reach one, so payments are dropped.",
            ["infrastructure.deployment_model", "requirements.payments"],
        )
        ctx.assumptions.append("Relaxed requirements.payments because deployment_model is air_gapped.")


def _warn_scale(ctx: Ctx) -> None:
    launch = ctx.n["scale"]["users_at_launch"]
    year = ctx.users
    peak = ctx.peak
    if year and launch > year:
        ctx.warn(
            "SCALE_SHRINKS",
            "warning",
            f"users_at_launch ({launch}) is higher than users_12_months ({year}). The engine sizes for the 12 month figure and assumes the product shrinks or the launch number counts a one-off spike.",
            ["scale.users_at_launch", "scale.users_12_months"],
        )
    if year and peak > year:
        ctx.warn(
            "SCALE_PEAK",
            "warning",
            f"peak_concurrent_users ({peak}) is higher than the whole 12 month user base ({year}). Check the units. The engine still uses the peak for capacity.",
            ["scale.peak_concurrent_users", "scale.users_12_months"],
        )


def _warn_eol(ctx: Ctx) -> None:
    for hit in ctx.eol:
        ctx.warn(
            "EOL_EXISTING_SYSTEM",
            hit["severity"],
            f"{hit['system']}: {hit['note']}",
            ["infrastructure.existing_systems"],
        )
    # Description only. Do not let a keyword change the stack by itself beyond the warning.
    described = eol_hits([ctx.n["project"]["description"]]) if ctx.n["project"]["description"] else []
    for hit in described:
        if any(existing["pattern"] == hit["pattern"] for existing in ctx.eol):
            continue
        ctx.warn(
            "EOL_IN_DESCRIPTION",
            hit["severity"],
            f"The description mentions {hit['name']}. {hit['note']} The engine will not select it.",
            ["project.description"],
        )


def _people(ctx: Ctx) -> str:
    n = ctx.n["team"]["size"]
    word = "engineer" if n == 1 else "engineers"
    return f"{n} {ctx.n['team']['experience']} {word}"


def _article(phrase: str) -> str:
    return "an" if phrase[:1].lower() in "aeiou" else "a"


def _pname(ctx: Ctx) -> str:
    return ctx.n["project"]["name"] or "This project"


def _commas(value: int | float) -> str:
    if isinstance(value, float) and not value.is_integer():
        return str(value)
    return f"{int(value):,}"


def skill_points(languages: list[str], team: list[str], require_all: bool = False) -> int:
    required = [lang for lang in languages if lang in CORE_LANGS]
    if not required:
        return 4
    have = set(team)
    if require_all:
        if set(required) <= have:
            return 5
        if set(required) & have:
            return 2
        return 1
    if any(lang in have for lang in required):
        return 5
    return 1


def _domain_fit(plan: dict, ptype: str) -> int:
    parts = plan.get("parts") or []
    if not parts:
        return 2
    fits = [5 if ptype in part.get("domains", []) else 2 for part in parts]
    return min(fits)


def _part_skill(part: dict, ctx: Ctx) -> int:
    require_all = "+" in str(part.get("id", ""))
    return skill_points(part.get("languages", []), ctx.languages, require_all)


def delivery_points(complexity: int, ctx: Ctx) -> int:
    weeks = ctx.n["timeline"]["mvp_weeks"] * 1.0
    exp = ctx.n["team"]["experience"]
    if exp == "beginner":
        weeks *= 0.75
    elif exp == "senior":
        weeks *= 1.15
    need = {1: 2, 2: 4, 3: 8, 4: 14, 5: 22}.get(complexity, 22)
    if weeks >= need:
        return 5
    if weeks >= need * 0.7:
        return 3
    return 1


def cost_points(tier: int, budget: float) -> int:
    typical = {0: 0, 1: 40, 2: 250, 3: 1500}.get(tier, 250)
    if budget <= 0:
        return 5 if tier == 0 else 1
    if typical <= budget:
        return 5
    if typical <= budget * 1.5:
        return 3
    return 1


def _paths(*items: str) -> list[str]:
    out = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def _sum(contrib: dict) -> int:
    return int(sum(contrib.values()))


def _ranked(plans: list[dict], score_fn) -> list[dict]:
    scored = []
    for plan in plans:
        contrib = score_fn(plan)
        scored.append(( _sum(contrib), plan["id"], contrib, plan))
    scored.sort(key=lambda row: (-row[0], row[1]))
    out = []
    for total, _pid, contrib, plan in scored:
        plan = dict(plan)
        plan["score"] = total
        plan["contrib"] = contrib
        out.append(plan)
    return out


def _why(winner: dict, loser: dict, ctx: Ctx) -> str:
    gaps = []
    keys = set(winner["contrib"]) | set(loser["contrib"])
    for key in keys:
        gaps.append((winner["contrib"].get(key, 0) - loser["contrib"].get(key, 0), key))
    gaps.sort(key=lambda item: (-item[0], item[1]))
    key = gaps[0][1] if gaps else "domain"
    name = loser["name"]
    if key == "skill":
        missing = []
        for part in loser.get("parts") or []:
            required = [lang for lang in part.get("languages", []) if lang in CORE_LANGS]
            if required and not any(lang in ctx.languages for lang in required):
                missing.extend(required)
        missing = sorted(set(missing))
        if missing:
            listed = ", ".join(missing)
            return f"{name} needs {listed}, and this team does not list them."
        return f"{name} lines up less well with the languages this team already writes."
    if key == "seo":
        return f"{name} is a weaker fit for public pages that have to rank."
    if key == "ops":
        if not ctx.devops:
            return f"{name} needs more day-2 operations work than a team with no operator should take on."
        return f"{name} costs more operator time than this team needs to spend."
    if key == "cost":
        return f"{name} is a worse fit for a monthly infra budget of {int(ctx.budget)} USD."
    if key == "scale":
        return (
            f"{name} does not match a 12 month target of {_commas(ctx.users)} users "
            f"and a peak of {_commas(ctx.peak)}."
        )
    if key == "delivery":
        return f"{name} is more project than {ctx.n['timeline']['mvp_weeks']} weeks allows here."
    if key == "low_end":
        return f"{name} is heavier on a low-RAM phone."
    if key == "offline":
        return f"{name} has a weaker offline story."
    if key == "lock":
        return f"{name} is harder to leave, and vendor lock-in tolerance is {ctx.n['team']['vendor_lock_in_tolerance']}."
    if key == "compliance":
        return f"{name} does not sit cleanly inside the residency or compliance pin."
    if key == "performance":
        return f"{name} is a weaker match for the latency target and the live workload."
    if key == "affinity":
        return f"{name} is a looser fit for this team and for this kind of product."
    tradeoff = ""
    if loser.get("tradeoffs"):
        line = loser["tradeoffs"][0]
        if "Markdown" in line and not ctx.signals.get("markdown"):
            line = ""
        tradeoff = (" " + line) if line else ""
    label = ctx.ptype.replace("_", " ")
    article = "an" if label[:1] in "aeiou" else "a"
    return f"{name} is a weaker match for {article} {label} with these priorities.{tradeoff}"


def _alts(ranked: list[dict], ctx: Ctx, rejected: list[dict] | None = None, limit: int = 2) -> list[dict]:
    rejected = list(rejected or [])
    rejected.sort(key=lambda item: ("cloud_preference is" in item["why_not"], item["choice"]))
    alts = []
    if ranked:
        winner = ranked[0]
        for loser in ranked[1:1 + limit]:
            alts.append({"choice": loser["name"], "why_not": _why(winner, loser, ctx)})
    if len(alts) < 1:
        for item in rejected or []:
            if any(alt["choice"] == item["choice"] for alt in alts):
                continue
            alts.append({"choice": item["choice"], "why_not": item["why_not"]})
            if len(alts) >= limit:
                break
    if not alts:
        alts.append({
            "choice": "A custom build of the same layer",
            "why_not": "There was no second maintained candidate left after the hard constraints.",
        })
    return alts


def _plan_from_parts(parts: list[dict], pid: str, name: str) -> dict:
    web = [part for part in parts if "web" in part.get("platforms", []) and part["id"] not in {"flutter", "expo"}]
    mobile = [part for part in parts if set(part.get("platforms", [])) & {"android", "ios"}]
    languages: list[str] = []
    domains: list[str] = []
    tradeoffs: list[str] = []
    for part in parts:
        for lang in part.get("languages", []):
            if lang not in languages:
                languages.append(lang)
        for domain in part.get("domains", []):
            if domain not in domains:
                domains.append(domain)
        for line in part.get("tradeoffs", []):
            if line not in tradeoffs:
                tradeoffs.append(line)
    complexity = max(part.get("complexity", 3) for part in parts)
    if len(parts) > 1:
        complexity = min(5, complexity + 1)
    return {
        "id": pid,
        "name": name,
        "parts": parts,
        "languages": languages,
        "seo": max(part.get("seo", 1) for part in (web or parts)),
        "interactivity": max(part.get("interactivity", 1) for part in (web or parts)),
        "offline": max(part.get("offline", 1) for part in (mobile or parts)),
        "low_end": min(part.get("low_end", 3) for part in (mobile or parts)),
        "ops_burden": max(part.get("ops_burden", 2) for part in parts),
        "complexity": complexity,
        "performance": min(part.get("performance", 3) for part in parts),
        "security": min(part.get("security", 3) for part in parts),
        "users_ceiling": min(part.get("users_ceiling", 10**6) for part in parts),
        "cost_tier": max(part.get("cost_tier", 1) for part in parts),
        "lock_in": max(part.get("lock_in", 1) for part in parts),
        "domains": domains,
        "blurb": " ".join(part.get("blurb", "") for part in parts),
        "tradeoffs": tradeoffs[:3],
    }


def _single_frontend(row: dict) -> dict:
    return _plan_from_parts([row], row["id"], row["name"])


def choose_frontend(ctx: Ctx) -> dict:
    needed = set(ctx.platforms)
    rejected: list[dict] = []
    if needed <= {"api_only"}:
        plan = {
            "id": "none",
            "name": "None",
            "parts": [],
            "languages": [],
            "seo": 1, "interactivity": 1, "offline": 1, "low_end": 5,
            "ops_burden": 1, "complexity": 1, "performance": 5, "security": 4,
            "users_ceiling": 10**9, "cost_tier": 0, "lock_in": 1, "domains": [],
            "blurb": "No client is shipped.",
            "tradeoffs": ["Someone will ask for a console later. A small internal page can wait."],
            "score": 1,
            "contrib": {"domain": 1},
        }
        plan["runners"] = []
        plan["rejected"] = [{
            "choice": "React (Vite)",
            "why_not": "platforms is api_only, so there is no client to build.",
        }]
        return plan

    client = needed - {"api_only"}
    web_rows = [
        row for row in FRONTEND
        if "web" in row["platforms"] and row["id"] not in {"flutter", "expo", "electron", "tauri"}
    ]
    plans: list[dict] = []
    mobile = client & {"android", "ios"}
    desk = "desktop" in client

    def mobile_rows(target: set[str]) -> list[dict]:
        found = []
        for row in FRONTEND:
            plats = set(row["platforms"])
            if target <= plats and target & plats and row["id"] not in {"electron", "tauri"}:
                if target <= (plats & {"android", "ios", "web", "desktop"}):
                    found.append(row)
        if target == {"android", "ios"}:
            found.append({
                **_plan_placeholder_native(),
            })
        return found

    if "web" in client and not mobile and not desk:
        plans = [_single_frontend(row) for row in web_rows]
    elif mobile and "web" not in client and not desk:
        plans = [_single_frontend(row) for row in mobile_rows(mobile)]
    elif desk and "web" not in client and not mobile:
        plans = [_single_frontend(row) for row in FRONTEND if "desktop" in row["platforms"]]
    elif "web" in client and mobile:
        mobs = [row for row in mobile_rows(mobile) if row["id"] != "flutter"]
        # Flutter can cover web and the phones as one codebase.
        for row in FRONTEND:
            if row["id"] == "flutter" and mobile <= set(row["platforms"]):
                plans.append(_single_frontend(row))
        for web in web_rows:
            if web["id"] in {"eleventy"} and ctx.n["requirements"]["seo_critical"] is False and ctx.ptype != "content_site":
                continue
            for mob in mobs:
                if mob["id"] in {"htmx", "astro", "eleventy", "razor_pages", "blazor", "angular", "nuxt", "sveltekit", "nextjs", "react_vite"}:
                    continue
                pid = f"{web['id']}+{mob['id']}"
                short = {
                    "expo": "Expo",
                    "compose_mp": "Compose Multiplatform",
                    "kotlin_android": "Kotlin and Jetpack Compose",
                    "swiftui": "SwiftUI",
                    "flutter": "Flutter",
                }.get(mob["id"], mob["name"])
                if mob["id"] == "expo" and mobile == {"android", "ios"}:
                    short = "Expo (Android and iOS)"
                elif mob["id"] == "expo" and mobile == {"android"}:
                    short = "Expo (Android)"
                elif mob["id"] == "expo" and mobile == {"ios"}:
                    short = "Expo (iOS)"
                elif mob["id"] == "compose_mp":
                    short = "Compose Multiplatform (Android and iOS)"
                label = f"{web['name']} (web) + {short}"
                plans.append(_plan_from_parts([web, mob], pid, label))
        if desk:
            # Keep the set smaller: pair the web rows later is enough. Desktop adds Electron if JS exists.
            pass
    elif "web" in client and desk:
        desks = [row for row in FRONTEND if row["id"] in {"electron", "tauri"}]
        for web in web_rows:
            if web["interactivity"] < 3 and ctx.ptype not in {"content_site", "internal_tool"}:
                continue
            for item in desks:
                plans.append(_plan_from_parts(
                    [web, item], f"{web['id']}+{item['id']}", f"{web['name']} + {item['name']}",
                ))
    else:
        plans = [_single_frontend(row) for row in web_rows]

    if not plans:
        plans = [_single_frontend(FRONTEND[0])]
        rejected.append({
            "choice": "A hand-built client",
            "why_not": "No catalog client covered every platform, so the closest web client is a starting point.",
        })

    ranked = _ranked(plans, lambda plan: _score_frontend(plan, ctx))
    winner = ranked[0]
    winner["runners"] = ranked
    winner["rejected"] = rejected
    return winner


def _plan_placeholder_native() -> dict:
    return {
        "id": "kotlin_android+swiftui",
        "name": "Kotlin (Android) + SwiftUI (iOS)",
        "languages": ["kotlin", "swift"],
        "platforms": ["android", "ios"],
        "seo": 1, "interactivity": 4, "offline": 5, "low_end": 5,
        "ops_burden": 3, "complexity": 5, "performance": 5, "security": 5,
        "users_ceiling": 5_000_000, "cost_tier": 0, "lock_in": 2,
        "domains": ["fintech", "healthtech", "marketplace"],
        "blurb": "Two fully native clients.",
        "tradeoffs": ["Two UI codebases, and Swift is a separate skill."],
        "sources": [],
    }


def _score_frontend(plan: dict, ctx: Ctx) -> dict:
    pr = ctx.n["priorities"]
    if plan["parts"]:
        skill = min(_part_skill(part, ctx) for part in plan["parts"])
    else:
        skill = 4
    contrib = {
        "skill": skill * (pr["time_to_market"] + pr["maintainability"]) // 2,
        "delivery": delivery_points(plan["complexity"], ctx) * pr["time_to_market"],
        "cost": cost_points(plan["cost_tier"], ctx.budget) * pr["cost"],
        "scale": (5 if ctx.users <= plan["users_ceiling"] else 1) * pr["scalability"],
        "performance": plan["performance"] * max(1, pr["performance"] // 2),
        "ops": (6 - plan["ops_burden"]) * max(1, pr["maintainability"] // 2),
        "domain": _domain_fit(plan, ctx.ptype) * 3,
    }
    if skill == 1:
        contrib["skill"] -= 15
    if ctx.n["requirements"]["seo_critical"] and "web" in ctx.platforms:
        contrib["seo"] = plan["seo"] * 4
    need = INTERACT_NEED.get(ctx.ptype, 3)
    if "web" in ctx.platforms and plan["interactivity"] < need:
        contrib["domain"] -= (need - plan["interactivity"]) * 6
    if ctx.n["requirements"]["offline_support"]:
        contrib["offline"] = plan["offline"] * 4
    if ctx.signals["low_end"] and set(ctx.platforms) & {"android", "ios"}:
        contrib["low_end"] = plan["low_end"] * 4
    if ctx.n["team"]["experience"] == "beginner" and plan["complexity"] >= 4:
        contrib["delivery"] -= 8
    if ctx.n["team"]["size"] == 1 and plan["complexity"] >= 4:
        contrib["delivery"] -= 6
    affinity = 0
    ids = {part.get("id") for part in plan["parts"]}
    if "csharp" in ctx.languages and ids & {"razor_pages", "blazor"}:
        affinity += 14
    if "kotlin" in ctx.languages and ids & {"compose_mp", "kotlin_android"} and ctx.ptype in {"fintech", "healthtech"}:
        affinity += 12
    if ctx.ptype == "content_site" and "astro" in ids:
        affinity += 6
    if ctx.ptype in {"fintech", "marketplace", "ecommerce", "saas_b2b"} and "nextjs" in ids:
        affinity += 3
    if ctx.signals["markdown"] and "astro" in ids:
        affinity += 4
    contrib["affinity"] = affinity
    if ctx.n["team"]["vendor_lock_in_tolerance"] == "low":
        contrib["lock"] = (6 - plan["lock_in"]) * 2
    return contrib


def _needs_backend_flags(ctx: Ctx) -> bool:
    req = ctx.n["requirements"]
    platforms = set(ctx.platforms)
    if platforms & {"android", "ios", "desktop", "api_only"}:
        return True
    if ctx.auth != "none" or ctx.payments or req["realtime"] or req["file_media_storage"]:
        return True
    if req["full_text_search"] or req["multi_tenant"] or req["offline_support"] or req["ml_features"] != "none":
        return True
    if ctx.ptype in SERVER_TYPES:
        return True
    return False


def choose_backend(ctx: Ctx, frontend: dict) -> dict:
    rejected: list[dict] = []
    if not _needs_backend_flags(ctx):
        plan = _backend_none()
        plan["runners"] = [plan]
        plan["rejected"] = [{
            "choice": "NestJS",
            "why_not": "There is no write path, account system, or private data, so a server would only add a bill and a process to patch.",
        }]
        return plan

    fe_ids = {part.get("id") for part in frontend.get("parts", [])}
    rows = []
    for row in BACKEND:
        if row["id"] == "workers" and not _workers_ok(ctx):
            rejected.append({
                "choice": row["name"],
                "why_not": "Cloudflare Workers cannot pin personal data to the required region, and the free tier is only for a small non-regulated API.",
            })
            continue
        if row["id"] == "pocketbase" and not _pocketbase_ok(ctx):
            continue
        if ctx.effective_deploy == "air_gapped" and not row["air_gap"]:
            rejected.append({"choice": row["name"], "why_not": "It is a hosted service, and this deployment is air-gapped."})
            continue
        if ctx.effective_deploy == "on_premise" and row["saas_only"]:
            rejected.append({"choice": row["name"], "why_not": "On-prem deployment cannot depend on this hosted runtime."})
            continue
        rows.append(row)

    plans = [_backend_plan(row) for row in rows]
    # A split realtime path is a candidate only when both skills exist and the room is large.
    if (
        ctx.n["requirements"]["realtime"]
        and ctx.peak >= 2_000
        and "go" in ctx.languages
        and ({"typescript", "javascript"} & set(ctx.languages))
        and ctx.n["team"]["size"] >= 4
        and ctx.n["timeline"]["mvp_weeks"] >= 10
    ):
        go = BACKEND_BY_ID["go_http"]
        nest = BACKEND_BY_ID["nestjs"]
        plans.append(_plan_from_parts(
            [go, nest],
            "go_http+nestjs",
            "Go sync service (net/http) + NestJS API",
        ))

    ranked = _ranked(plans, lambda plan: _score_backend(plan, ctx, fe_ids))
    winner = ranked[0]
    winner["runners"] = ranked
    winner["rejected"] = rejected
    return winner


def _backend_none() -> dict:
    return {
        "id": "none",
        "name": "None",
        "parts": [],
        "languages": [],
        "ops_burden": 1, "complexity": 1, "performance": 5, "security": 4,
        "users_ceiling": 10**9, "cost_tier": 0, "lock_in": 1, "domains": ["content_site"],
        "blurb": "Static output does not need an application server.",
        "tradeoffs": ["Any future account or form handler means adding a server later."],
        "holds_socket": False, "long_lived": False, "saas_only": False, "air_gap": True,
        "score": 1, "contrib": {"domain": 1},
    }


def _backend_plan(row: dict) -> dict:
    plan = _plan_from_parts([row], row["id"], row["name"])
    plan["holds_socket"] = row["holds_socket"]
    plan["long_lived"] = row["long_lived"]
    plan["record"] = row
    return plan


def _score_backend(plan: dict, ctx: Ctx, fe_ids: set) -> dict:
    pr = ctx.n["priorities"]
    parts = plan["parts"]
    skill = min(_part_skill(part, ctx) for part in parts) if parts else 1
    holds = all(part.get("holds_socket", plan.get("holds_socket", False)) for part in parts) if parts else False
    # Combined plans carry holds_socket on the child rows via the original dicts.
    if parts and all(BACKEND_BY_ID.get(part["id"], part).get("holds_socket", False) for part in parts):
        holds = True
    contrib = {
        "skill": skill * (pr["time_to_market"] + pr["maintainability"]) // 2,
        "delivery": delivery_points(plan["complexity"], ctx) * pr["time_to_market"],
        "cost": cost_points(plan["cost_tier"], ctx.budget) * pr["cost"],
        "scale": (5 if ctx.users <= plan["users_ceiling"] else 1) * pr["scalability"],
        "performance": plan["performance"] * pr["performance"],
        "ops": (6 - plan["ops_burden"]) * (pr["maintainability"] + (0 if ctx.devops else 2)),
        "domain": (5 if ctx.ptype in plan["domains"] else 2) * 3,
    }
    if skill == 1:
        contrib["skill"] -= 15
    if ctx.n["requirements"]["realtime"] and not holds:
        contrib["performance"] -= 20
    if ctx.n["team"]["experience"] == "beginner" and plan["complexity"] >= 4:
        contrib["delivery"] -= 8
    affinity = 0
    ids = {part["id"] for part in parts}
    if "php" in ctx.languages and "laravel" in ids:
        affinity += 16
    if "ruby" in ctx.languages and "rails" in ids:
        affinity += 16
    if "csharp" in ctx.languages and "aspnet" in ids:
        affinity += 16
    if "python" in ctx.languages and ids & {"fastapi", "django"}:
        affinity += 8
    if ({"java", "kotlin"} & set(ctx.languages)) and "spring_boot" in ids:
        affinity += 10
        if ctx.ptype in {"fintech", "healthtech"} or ctx.signals["ledger"]:
            affinity += 12
    if "go" in ctx.languages and "go_http" in ids and (
        ctx.n["requirements"]["realtime"] or ctx.ptype in {"gaming", "iot", "realtime_collab", "api_platform"}
    ):
        affinity += 10
    if fe_ids & {"nextjs", "expo", "react_vite"} and "nestjs" in ids:
        affinity += 10
    if fe_ids & {"razor_pages", "blazor"} and "aspnet" in ids:
        affinity += 30
    if ctx.ptype in {"data_analytics", "ai_ml_product"} and "fastapi" in ids:
        affinity += 8
    if ctx.n["requirements"]["ml_features"] != "none" and "fastapi" in ids and "python" in ctx.languages:
        affinity += 4
    if ctx.ptype == "internal_tool" and "django" in ids and "nestjs" not in fe_ids:
        affinity += 4
    contrib["affinity"] = affinity
    if ctx.n["team"]["vendor_lock_in_tolerance"] == "low":
        contrib["lock"] = (6 - plan["lock_in"]) * 2
    return contrib


def _workers_ok(ctx: Ctx) -> bool:
    if ctx.budget > 0 and ctx.n["priorities"]["cost"] < 5:
        return False
    if ctx.budget > 25:
        return False
    if ctx.effective_deploy != "managed_cloud":
        return False
    if ctx.n["infrastructure"]["cloud_preference"] not in {"any"}:
        return False
    if ctx.effective_residency != "none":
        return False
    if ctx.n["compliance"]:
        return False
    if ctx.n["data"]["sensitivity"] in {"confidential", "restricted"}:
        return False
    if ctx.payments or ctx.n["requirements"]["realtime"]:
        return False
    if ctx.ptype in {"fintech", "healthtech", "gaming"}:
        return False
    if ctx.users > 20_000 or ctx.peak > 300 or ctx.n["scale"]["data_volume_gb_12_months"] > 5:
        return False
    if not ({"javascript", "typescript"} & set(ctx.languages)):
        return False
    return True


def _pocketbase_ok(ctx: Ctx) -> bool:
    if ctx.payments or ctx.ptype in {"fintech", "healthtech"} or ctx.signals["ledger"]:
        return False
    if ctx.users > 8_000 or ctx.peak > 150:
        return False
    if ctx.n["requirements"]["availability"] in {"99.95", "99.99"}:
        return False
    if ctx.n["requirements"]["multi_tenant"]:
        return False
    return True


def _ml_is_split(ctx: Ctx) -> bool:
    ml = ctx.n["requirements"]["ml_features"]
    if ml == "none":
        return False
    if ctx.effective_deploy in {"air_gapped", "on_premise"}:
        return False
    if not ctx.devops or ctx.n["team"]["size"] < 5:
        return False
    if ctx.n["timeline"]["mvp_weeks"] < 12:
        return False
    return ctx.n["infrastructure"]["cloud_preference"] in {"aws", "gcp", "azure", "any"}


def choose_architecture(ctx: Ctx, needs_be: bool, backend: dict, ml_split: bool) -> str:
    if not needs_be:
        return "static"
    team = ctx.n["team"]["size"]
    weeks = ctx.n["timeline"]["mvp_weeks"]
    exp = ctx.n["team"]["experience"]
    pr = ctx.n["priorities"]
    if (
        team >= 12 and ctx.devops and exp == "senior" and ctx.users >= 500_000 and weeks >= 24
        and pr["scalability"] >= 4 and ctx.ptype in {"saas_b2b", "fintech", "ecommerce", "marketplace", "social", "api_platform"}
    ):
        return "microservices"
    if ml_split or "+" in backend["id"]:
        return "hybrid"
    if (
        team >= 8 and ctx.devops and exp == "senior" and ctx.users >= 200_000 and weeks >= 20
        and pr["scalability"] >= 4 and ctx.ptype in COMPLEX_TYPES
    ):
        return "service_oriented"
    if ctx.ptype in COMPLEX_TYPES and team >= 3:
        return "modular_monolith"
    if ctx.ptype == "realtime_collab" and team >= 4:
        return "modular_monolith"
    if _serverless_shape(ctx) and backend["id"] in {"workers", "fastify", "fastapi", "nestjs", "none"}:
        return "serverless"
    return "monolith"


def _serverless_shape(ctx: Ctx) -> bool:
    req = ctx.n["requirements"]
    if ctx.effective_deploy != "managed_cloud":
        return False
    if req["realtime"] or req["offline_support"]:
        return False
    if req["availability"] in {"99.95", "99.99"}:
        return False
    if ctx.peak >= 400:
        return False
    if ctx.ptype in {"fintech", "healthtech", "gaming", "realtime_collab", "iot"}:
        return False
    if ctx.signals["ledger"]:
        return False
    if ctx.n["scale"]["traffic_pattern"] == "spiky" and not ctx.devops:
        return True
    if ctx.budget == 0 and not ctx.devops:
        return True
    return False


def _personal(ctx: Ctx) -> bool:
    if ctx.n["data"]["sensitivity"] in {"confidential", "restricted"}:
        return True
    req = ctx.n["requirements"]
    if ctx.auth != "none" or ctx.payments or req["file_media_storage"] or req["multi_tenant"]:
        return True
    if ctx.n["compliance"]:
        return True
    return False


def choose_hosting(ctx: Ctx, frontend: dict, backend: dict, arch: str) -> dict:
    cloud = ctx.n["infrastructure"]["cloud_preference"]
    deploy = ctx.effective_deploy
    residency = ctx.effective_residency
    personal = _personal(ctx) or backend["id"] != "none"
    rejected: list[dict] = []
    options = []
    eks_ok = (
        cloud == "aws" and ctx.devops and ctx.n["team"]["experience"] == "senior"
        and ctx.n["team"]["size"] >= 10 and ctx.users >= 1_000_000
        and ctx.n["priorities"]["scalability"] >= 5
        and ctx.n["requirements"]["availability"] in {"99.95", "99.99"}
    )
    for row in HOSTING:
        reason = _host_reject_reason(row, ctx, cloud, deploy, residency, personal, arch, backend, eks_ok)
        if reason:
            if row["id"] in {"aws_eks", "aws_lambda", "vercel", "aws_ec2", "azure_vm", "do_droplet"}:
                rejected.append({"choice": row["name"], "why_not": reason})
            continue
        options.append(row)
    if not options:
        options = [HOSTING_BY_ID["docker_compose"]]
        ctx.relaxed = True
        ctx.warn(
            "NO_HOST",
            "critical",
            "No catalog host satisfied the hard constraints. The engine fell back to Docker Compose on machines you control.",
            ["infrastructure.deployment_model", "infrastructure.cloud_preference", "infrastructure.data_residency"],
        )

    fe_ids = {part.get("id") for part in frontend.get("parts", [])}
    ranked_rows = []
    for row in options:
        contrib = _score_host(row, ctx, arch, fe_ids, backend)
        ranked_rows.append((_sum(contrib), row["id"], contrib, row))
    ranked_rows.sort(key=lambda item: (-item[0], item[1]))
    plans = []
    for total, _pid, contrib, row in ranked_rows:
        plans.append({"id": row["id"], "name": row["name"], "record": row, "score": total, "contrib": contrib,
                      "parts": [row], "tradeoffs": row["tradeoffs"], "languages": [], "lock_in": row["lock_in"]})
    winner = plans[0]
    winner["runners"] = plans
    winner["rejected"] = rejected
    winner["region"] = _region_label(winner["id"], ctx)
    winner["choice"] = _host_choice(winner, ctx)
    return winner


def _host_reject_reason(row, ctx, cloud, deploy, residency, personal, arch, backend, eks_ok) -> str | None:
    if deploy == "air_gapped":
        if row["id"] != "docker_compose":
            return "An air-gapped network cannot depend on this public host."
        return None
    if deploy == "on_premise":
        if row["id"] != "docker_compose":
            return "deployment_model on_premise keeps the process off this public host."
        return None
    if row["id"] == "docker_compose":
        return "deployment_model is not on-prem or air-gapped, so a laptop-style compose file is not the host."
    if deploy == "self_hosted_cloud_vm" and row["kind"] != "vm":
        return "deployment_model is self_hosted_cloud_vm, so a PaaS would split the operating model."
    if deploy == "managed_cloud" and row["kind"] == "vm":
        return "deployment_model is managed_cloud, so the team should not own the OS."
    if cloud not in {"any", "none"} and cloud not in row["clouds"] and "any" not in row["clouds"]:
        return f"cloud_preference is {cloud}."
    if cloud not in {"any", "none"} and cloud not in row["clouds"]:
        return f"cloud_preference is {cloud}, and this host is a different vendor."
    if cloud == "any" and row["id"] in {"gcp_vm", "azure_vm"}:
        return "A single-vendor VM is a worse default than a neutral PaaS when no cloud was named."
    if residency not in row["regions"]:
        return f"It has no {residency} region the engine can defend."
    if personal and not row["personal"] and row["kind"] != "static":
        return "It cannot be the system of record for personal data in the pinned region."
    if ctx.n["requirements"].get("availability") and "hipaa" in ctx.n["compliance"] and not row["baa"]:
        return "HIPAA needs a vendor that will sign a BAA. This one will not, on a normal plan."
    if "hipaa" in ctx.n["compliance"] and not row["baa"]:
        return "HIPAA needs a BAA. This host does not offer one."
    if row["id"] == "aws_eks" and not eks_ok:
        return (
            "Kubernetes is not justified. The team, the user count, or the calendar does not clear the bar. "
            "ECS runs the same containers without a cluster to babysit."
        )
    if row["kind"] == "static" and arch != "static":
        return "A static host cannot run this API."
    if arch == "static" and row["kind"] != "static":
        return "The site has no server, so a container platform is extra moving parts."
    if row["id"] == "aws_lambda":
        long_lived = backend["id"] in {"spring_boot", "aspnet", "go_http", "django", "rails", "laravel"} or "+" in backend["id"]
        if arch != "serverless" or long_lived or ctx.n["requirements"]["realtime"] or ctx.signals["ledger"]:
            return "Lambda cold starts and the 15 minute cap fight a long-lived server, sockets, or a ledger."
    if row["id"] == "vercel":
        if backend["id"] not in {"nestjs", "fastify", "workers", "none"}:
            return "Vercel hosts JavaScript. This API is a different runtime, so the process would not actually run there."
        if residency == "india" or set(ctx.n["compliance"]) & {"dpdp", "rbi_localisation", "hipaa"}:
            return "Vercel is not the place to pin Indian personal data or PHI."
        if ctx.n["requirements"]["realtime"] and ctx.peak > 200:
            return "Vercel is a poor home for a large websocket fan-out."
        if ctx.n["data"]["sensitivity"] == "restricted":
            return "Restricted data needs a cloud that will sign the relevant agreements in-region."
    if row["id"] == "workers" and backend["id"] != "workers":
        return "Cloudflare Workers is a JavaScript runtime, not a place to park this API."
    if row["id"] == "netlify" and (personal or arch != "static"):
        return "Netlify is being treated as a static host here, not as the system of record."
    if ctx.n["requirements"]["realtime"] and ctx.peak > row["concurrent_ceiling"] > 0:
        return f"The peak of {_commas(ctx.peak)} sockets is past what this host should hold."
    return None


def _score_host(row: dict, ctx: Ctx, arch: str, fe_ids: set, backend: dict) -> dict:
    pr = ctx.n["priorities"]
    ops_weight = pr["maintainability"] + pr["time_to_market"] // 2
    if not ctx.devops:
        ops_weight += 3
    if ctx.peak > row["concurrent_ceiling"] > 0:
        scale_pts = 1
    else:
        scale_pts = row["scale"]
    contrib = {
        "ops": (6 - row["ops_burden"]) * ops_weight,
        "scale": scale_pts * pr["scalability"],
        "cost": cost_points(row["cost_tier"], ctx.budget) * pr["cost"],
        "performance": (row["ws"] if ctx.n["requirements"]["realtime"] else 3) * max(1, pr["performance"] // (1 if ctx.n["requirements"]["realtime"] else 2)),
    }
    if arch == "serverless" and row["serverless"]:
        contrib["affinity"] = 8
    else:
        contrib["affinity"] = 0
    if "csharp" in ctx.languages and row["id"] == "azure_appservice":
        contrib["affinity"] += 12
    if "nextjs" in fe_ids and row["id"] == "vercel":
        contrib["affinity"] += 8
    if backend["id"] == "workers" and row["id"] == "workers":
        contrib["affinity"] += 20
    if ctx.n["team"]["vendor_lock_in_tolerance"] == "low":
        contrib["lock"] = (6 - row["lock_in"]) * 3
    elif ctx.n["team"]["vendor_lock_in_tolerance"] == "medium":
        contrib["lock"] = (6 - row["lock_in"])
    if row["id"] == "cloudflare_pages":
        contrib["scale"] += 2
    return contrib


def _region_family(host_id: str) -> str:
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
    if host_id == "vercel":
        return "vercel"
    return "edge"


def _region_label(host_id: str, ctx: Ctx) -> str:
    family = _region_family(host_id)
    if host_id == "vercel":
        if ctx.effective_residency == "eu":
            return "Frankfurt (eu-central-1)"
        return "the US"
    table = REGION_LABEL.get(family, REGION_LABEL["edge"])
    return table.get(ctx.effective_residency, table.get("none", "unspecified region"))


def _host_choice(winner: dict, ctx: Ctx) -> str:
    region = winner["region"]
    if winner["id"] == "vercel":
        return f"Vercel ({region})"
    if winner["id"] in {"cloudflare_pages", "github_pages"}:
        return f"{winner['name']} ({region})"
    if winner["id"] == "docker_compose":
        place = REGION_LABEL["self"].get(ctx.effective_residency, "your own facility")
        return f"Docker Compose on machines in {place}"
    return f"{winner['name']} in {region}"


def choose_database(ctx: Ctx, host: dict, needs_be: bool) -> dict:
    rejected: list[dict] = []
    if not needs_be and not ctx.n["requirements"]["file_media_storage"]:
        plan = {
            "id": "none",
            "name": "None",
            "choice": "None",
            "record": {"tradeoffs": ["A form or an account later means adding a database."], "blurb": "Content lives in the repository."},
            "runners": [],
            "rejected": [{"choice": "PostgreSQL", "why_not": "There is no dynamic data to store. Markdown in git is the source of truth."}],
            "contrib": {"domain": 1},
            "parts": [],
            "tradeoffs": ["A form or an account later means adding a database."],
            "existing": False,
            "ha": False,
        }
        return plan

    reused = _reuse_database(ctx, rejected)
    if reused is not None:
        return reused

    acid = _needs_acid(ctx)
    cloud = ctx.n["infrastructure"]["cloud_preference"]
    rows = []
    for row in DATABASE:
        reason = _db_reject(row, ctx, acid, cloud, host)
        if reason:
            if row["id"] in {"dynamodb", "firestore", "d1", "cockroach", "clickhouse", "mongodb", "sqlite"}:
                rejected.append({"choice": row["name"], "why_not": reason})
            continue
        rows.append(row)
    if not rows:
        rows = [DATABASE_BY_ID["postgresql"]]
    ranked = []
    for row in rows:
        contrib = _score_db(row, ctx, host)
        ranked.append((_sum(contrib), row["id"], contrib, row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    plans = [{
        "id": row["id"], "name": row["name"], "record": row, "score": total, "contrib": contrib,
        "parts": [row], "tradeoffs": row["tradeoffs"],
    } for total, _pid, contrib, row in ranked]
    winner = plans[0]
    winner["runners"] = plans
    winner["rejected"] = rejected
    winner["existing"] = False
    winner["ha"] = _wants_ha(ctx) and winner["id"] not in {"sqlite", "d1"}
    winner["choice"] = _db_choice(winner, host, ctx)
    return winner


def _needs_acid(ctx: Ctx) -> bool:
    if ctx.payments or ctx.signals["ledger"] or ctx.ptype in {"fintech", "healthtech"}:
        return True
    if ctx.n["requirements"]["multi_tenant"] and ctx.ptype in {"saas_b2b", "fintech", "ecommerce"}:
        return True
    return False


def _db_reject(row: dict, ctx: Ctx, acid: bool, cloud: str, host: dict) -> str | None:
    if ctx.effective_deploy == "air_gapped" and not row["air_gap"]:
        return "Air-gapped deployment cannot use this hosted database."
    if ctx.effective_deploy == "on_premise" and row["saas_only"]:
        return "On-prem deployment cannot use this hosted database."
    if cloud not in {"any", "none"} and cloud not in row["clouds"]:
        return f"cloud_preference is {cloud}."
    if row["id"] == "d1" and host["id"] != "workers":
        return "D1 only makes sense next to Cloudflare Workers, and it cannot hold regulated data."
    if row["id"] == "azure_sql" and cloud != "azure":
        return "Azure SQL is an Azure product."
    if row["id"] == "dynamodb":
        if cloud != "aws" and host["id"] not in {"aws_ecs", "aws_lambda", "aws_ec2", "aws_eks"}:
            return "DynamoDB only runs on AWS."
        if acid:
            return "A ledger or payment record wants real transactions. DynamoDB is the wrong shape."
        if ctx.n["team"]["vendor_lock_in_tolerance"] == "low":
            return "Lock-in tolerance is low, and DynamoDB is an AWS-only data model."
    if row["id"] == "firestore":
        if cloud != "gcp":
            return "Firestore is a Google Cloud database."
        if acid or ctx.effective_residency == "india" and "rbi_localisation" in ctx.n["compliance"]:
            return "Firestore is a poor ledger, and it is not the system of record for RBI data."
    if row["id"] == "cockroach":
        spread = ctx.n["scale"]["geographic_spread"]
        if ctx.users < 200_000 or not ctx.devops or ctx.n["team"]["size"] < 5 or spread != "multi_region":
            return "CockroachDB is a multi-region system. This load fits a single Postgres primary."
        if "rbi_localisation" in ctx.n["compliance"]:
            return "Multi-region writes fight RBI localisation."
    if row["id"] == "clickhouse":
        if ctx.ptype != "data_analytics" or ctx.n["scale"]["data_volume_gb_12_months"] < 400:
            return "ClickHouse is an analytical store. Transactional product data stays in Postgres."
    if row["id"] == "mongodb" and acid:
        return "The product needs ACID transactions (payments, a ledger, or health records). MongoDB is not the system of record."
    if row["id"] == "sqlite":
        if ctx.peak > 120 or ctx.users > 8_000 or ctx.n["requirements"]["availability"] in {"99.95", "99.99"}:
            return "SQLite has one writer. This peak or availability target needs a server database."
        if ctx.n["requirements"]["realtime"] and ctx.peak > 40:
            return "Realtime across more than one app process will corrupt or block a single SQLite file."
        if ctx.n["requirements"]["multi_tenant"] and ctx.users > 2_000:
            return "Multi-tenant growth past a single node is a bad SQLite bet."
    if row["id"] == "d1" and (acid or ctx.payments or ctx.n["compliance"]):
        return "D1 is a small edge SQLite. It is not a regulated system of record."
    return None


def _score_db(row: dict, ctx: Ctx, host: dict) -> dict:
    pr = ctx.n["priorities"]
    contrib = {
        "skill": skill_points(row["languages"], ctx.languages) * (pr["maintainability"]) // 1,
        "delivery": delivery_points(row["complexity"], ctx) * pr["time_to_market"],
        "cost": cost_points(row["cost_tier"], ctx.budget) * pr["cost"],
        "scale": (5 if ctx.users <= row["users_ceiling"] else 1) * pr["scalability"],
        "performance": row["performance"] * max(1, pr["performance"] // 2),
        "ops": (6 - row["ops_burden"]) * (pr["maintainability"] + (0 if ctx.devops else 2)),
        "domain": (5 if ctx.ptype in row["domains"] else 2) * 3,
        "affinity": 0,
    }
    if row["id"] == "postgresql":
        contrib["affinity"] += 10
    if row["id"] == "mysql" and "php" in ctx.languages:
        contrib["affinity"] += 12
    if row["id"] == "azure_sql" and "csharp" in ctx.languages and ctx.n["infrastructure"]["cloud_preference"] == "azure":
        contrib["affinity"] += 14
    if row["id"] == "sqlserver" and "csharp" in ctx.languages:
        contrib["affinity"] += 6
    if row["id"] == "d1" and host["id"] == "workers":
        contrib["affinity"] += 24
    if row["acid"] and _needs_acid(ctx):
        contrib["domain"] += 8
    if ctx.n["requirements"]["full_text_search"] and row["id"] == "postgresql":
        contrib["affinity"] += 4
    if ctx.n["team"]["vendor_lock_in_tolerance"] == "low":
        contrib["lock"] = (6 - row["lock_in"]) * 3
    return contrib


def _reuse_database(ctx: Ctx, rejected: list[dict]) -> dict | None:
    critical = {hit["pattern"] for hit in ctx.eol if hit["severity"] == "critical"}
    if ctx.existing["fauna"] or "fauna" in " ".join(critical):
        ctx.warn(
            "EOL_NOT_REUSED",
            "critical",
            "Fauna shut down on 30 May 2025. It is not reused. New data goes to PostgreSQL.",
            ["infrastructure.existing_systems"],
        )
    if ctx.existing["sqlserver"]:
        sql_critical = any(hit["severity"] == "critical" and "sql server" in hit["pattern"] for hit in ctx.eol)
        if not sql_critical:
            version = ctx.existing["sqlserver_version"]
            label = f"Microsoft SQL Server {version} (existing)" if version else "Microsoft SQL Server (existing)"
            return {
                "id": "sqlserver",
                "name": label,
                "choice": label,
                "record": DATABASE_BY_ID["sqlserver"],
                "runners": [],
                "rejected": [{
                    "choice": "PostgreSQL",
                    "why_not": "A second database would split the system of record. The existing SQL Server already stores the company's rows.",
                }, {
                    "choice": "Azure SQL Database",
                    "why_not": "Moving the data during a short MVP is a migration project, not a feature project.",
                }],
                "contrib": {"affinity": 20},
                "parts": [DATABASE_BY_ID["sqlserver"]],
                "tradeoffs": DATABASE_BY_ID["sqlserver"]["tradeoffs"],
                "existing": True,
                "ha": False,
            }
        ctx.warn(
            "EOL_NOT_REUSED",
            "critical",
            "The existing SQL Server release is past extended support. It is not the target engine. Plan a move to SQL Server 2022 or PostgreSQL, and do not build new tables on the dead instance.",
            ["infrastructure.existing_systems"],
        )
    if ctx.existing["postgres"]:
        return _existing_engine("postgresql", "PostgreSQL (existing)", ctx)
    if ctx.existing["mysql"] and not _needs_acid(ctx):
        return _existing_engine("mysql", "MySQL (existing)", ctx)
    if ctx.existing["mysql"] and _needs_acid(ctx):
        return _existing_engine("mysql", "MySQL (existing)", ctx)
    if ctx.existing["mongo"] and not _needs_acid(ctx) and not ctx.signals["ledger"]:
        return _existing_engine("mongodb", "MongoDB (existing)", ctx)
    if ctx.existing["mongo"] and (_needs_acid(ctx) or ctx.signals["ledger"]):
        ctx.warn(
            "MONGO_NOT_LEDGER",
            "warning",
            "An existing MongoDB was not reused as the system of record. Payments and ledgers need ACID transactions in PostgreSQL. Mongo can stay as a side store if you already have documents there.",
            ["infrastructure.existing_systems"],
        )
    return None


def _existing_engine(db_id: str, label: str, ctx: Ctx) -> dict:
    row = DATABASE_BY_ID[db_id]
    return {
        "id": db_id,
        "name": label,
        "choice": label,
        "record": row,
        "runners": [],
        "rejected": [{
            "choice": "A new PostgreSQL cluster",
            "why_not": "The existing engine already holds the data. A second cluster adds a migration the MVP does not need.",
        }],
        "contrib": {"affinity": 20},
        "parts": [row],
        "tradeoffs": row["tradeoffs"],
        "existing": True,
        "ha": False,
    }


def _wants_ha(ctx: Ctx) -> bool:
    return ctx.n["requirements"]["availability"] in {"99.95", "99.99"}


def _db_choice(winner: dict, host: dict, ctx: Ctx) -> str:
    if winner["existing"]:
        return winner["choice"]
    provider = _region_family(host["id"])
    if provider == "edge" and host["id"] == "vercel":
        provider = "vercel"
    if provider == "edge" and host["id"] == "workers":
        if winner["id"] == "d1":
            return "Cloudflare D1"
    phrase = DB_PRODUCT.get((winner["id"], provider))
    region = host["region"]
    ha = ", Multi-AZ" if winner.get("ha") and provider in {"aws", "gcp", "azure"} else ""
    if winner.get("ha") and provider == "azure":
        ha = ", zone redundant"
    if winner.get("ha") and provider == "do":
        ha = ", standby node"
    if winner["id"] == "sqlite":
        return "SQLite"
    if winner["id"] == "d1":
        return "Cloudflare D1"
    if winner["id"] == "dynamodb":
        return f"Amazon DynamoDB in {region}"
    if winner["id"] == "azure_sql":
        return f"Azure SQL Database in {region}{ha}"
    if winner["id"] == "firestore":
        return f"Cloud Firestore in {region}"
    if winner["id"] == "clickhouse":
        return f"ClickHouse in {region}"
    if phrase:
        return f"{winner['name']} ({phrase} in {region}{ha})"
    if provider == "self":
        return f"{winner['name']} on your machines"
    return f"{winner['name']} in {region}{ha}"


def choose_supporting(ctx, fe, be, db, host, arch) -> list[dict]:
    items = []
    provider = _region_family(host["id"])
    if provider == "edge" and host["id"] == "vercel":
        provider = "vercel"
    region = host["region"]
    req = ctx.n["requirements"]

    want_cache = (
        be["id"] != "none" and arch != "static" and (
            ctx.peak >= 500 or req["availability"] in {"99.95", "99.99"} or (req["realtime"] and ctx.peak >= 200)
        )
    )
    if want_cache and db["id"] != "sqlite":
        items.append(_cache_item(ctx, provider, region))

    want_queue = be["id"] != "none" and (
        ctx.payments or req["ml_features"] in {"inference_api", "training"} or (ctx.n["scale"]["workload"] == "write_heavy" and ctx.users >= 50_000)
    )
    if want_queue:
        items.append(_queue_item(ctx, provider, be))

    if req["full_text_search"] and db["id"] != "none":
        items.append(_search_item(ctx, db))

    if ctx.auth != "none":
        items.append(_auth_item(ctx, host, provider))

    if req["file_media_storage"] or (req["ml_features"] != "none" and be["id"] != "none"):
        items.append(_storage_item(ctx, provider, region))

    if _wants_cdn(ctx, arch, host):
        cdn = _cdn_item(ctx, provider)
        if cdn:
            items.append(cdn)

    if req["realtime"] and be["id"] != "none":
        items.append(_realtime_item(ctx, be))

    if ctx.payments:
        items.append(_payments_item(ctx))

    if req["ml_features"] != "none" and be["id"] != "none":
        items.append(_ml_item(ctx, provider, region))

    if ctx.n["team"]["size"] >= 2 or ctx.devops:
        items.append(_ci_item(ctx))

    if _wants_obs(ctx) and be["id"] != "none":
        items.append(_obs_item(ctx, provider))

    if req["offline_support"] and set(ctx.platforms) & {"android", "ios"}:
        items.append(_device_db_item(ctx))

    if ctx.ptype == "iot":
        items.append(_mqtt_item(ctx))

    order = ["cache", "queue", "search", "auth", "storage", "cdn", "realtime", "payments", "ml", "ci_cd", "observability", "other"]
    items.sort(key=lambda item: order.index(item["layer"]) if item["layer"] in order else 99)
    return items


def _component(choice, justification, driven, alts, tradeoffs, layer=None) -> dict:
    body = {
        "choice": choice,
        "justification": justification,
        "driven_by": driven,
        "alternatives": alts,
        "tradeoffs": tradeoffs,
    }
    if layer:
        return {"layer": layer, **body}
    return body


def _cache_item(ctx, provider, region) -> dict:
    if provider == "aws":
        choice, alt = "Amazon ElastiCache for Valkey", "Redis on ElastiCache"
    elif provider == "azure":
        choice, alt = "Azure Cache for Redis", "Valkey on a VM"
    elif provider == "gcp":
        choice, alt = "Memorystore for Redis", "Valkey on a VM"
    elif provider == "self":
        choice, alt = "Valkey on your machines", "No cache, hit the database for every read"
    else:
        choice, alt = f"Managed Valkey in {region}", "An in-process cache inside the API"
    return _component(
        choice,
        f"Peak concurrency is {_commas(ctx.peak)}. A small cache holds sessions, OTP attempts, and hot reads so the database is not the first thing to fall over.",
        _paths("scale.peak_concurrent_users", "requirements.availability", "requirements.realtime"),
        [{"choice": alt, "why_not": "The managed cache is the same protocol with backups and a patch cycle already solved." if provider != "self"
          else "Skipping the cache is fine at a tiny peak, and this peak is no longer tiny."}],
        ["Another process to watch. At a small size it can share a node with the queue."],
        "cache",
    )


def _queue_item(ctx, provider, be) -> dict:
    if provider == "aws":
        choice, why, alt = "Amazon SQS", "Webhook and payout work should leave the request path.", "A Postgres job table"
    elif provider == "azure":
        choice, why, alt = "Azure Service Bus", "Approvals and background work need a retry the web request does not have.", "Azure Storage Queues"
    elif provider == "gcp":
        choice, why, alt = "Google Cloud Pub/Sub", "Background work should retry without blocking the request.", "A Postgres job table"
    elif "nestjs" in be["id"] or "fastify" in be["id"]:
        choice, why, alt = "BullMQ on Valkey", "Node already speaks this queue, so webhooks get retries without a new vendor.", "Amazon SQS"
    else:
        choice, why, alt = "A PostgreSQL job table (SKIP LOCKED)", "The volume does not need a separate broker. A job table keeps the system of record in one place.", "RabbitMQ"
    return _component(
        choice,
        why + " Payments, scoring, or write spikes should retry on their own.",
        _paths("requirements.payments", "requirements.ml_features", "scale.workload", "scale.users_12_months"),
        [{"choice": alt, "why_not": "It adds a second system before the volume requires one." if alt != "Amazon SQS" or provider == "aws"
          else "The workload is not on AWS, so SQS would be a second cloud."}],
        ["Poison messages need a dead-letter view, or they vanish into retries."],
        "queue",
    )


def _search_item(ctx, db) -> dict:
    if db["id"] in {"sqlserver"}:
        choice = "SQL Server full-text search"
        alt = "OpenSearch"
        why = "The data already lives in SQL Server. Full-text search there avoids a second index to keep honest."
    elif ctx.n["scale"]["data_volume_gb_12_months"] >= 200 or ctx.users >= 200_000:
        choice = "OpenSearch"
        alt = "PostgreSQL full-text search"
        why = "The text volume is past the point where a database index stays comfortable."
    else:
        choice = "PostgreSQL full-text search" if db["id"] != "mysql" else "MySQL full-text search"
        alt = "Typesense"
        why = (
            f"full_text_search is true and the stored text is about {ctx.n['scale']['data_volume_gb_12_months']} GB. "
            "A database index answers that without another service to patch."
        )
    return _component(
        choice, why,
        _paths("requirements.full_text_search", "scale.data_volume_gb_12_months"),
        [{"choice": alt, "why_not": "A dedicated search box is the right upgrade once relevance or the index size hurts, and it is not the MVP constraint."}],
        ["Database search is good, not magical. Ranking tweaks are SQL, not a tuning UI."],
        "search",
    )


def _auth_item(ctx, host, provider) -> dict:
    air = ctx.effective_deploy in {"air_gapped", "on_premise"}
    wants_entra = ctx.auth == "enterprise_sso" and (
        ctx.existing["entra"] or (ctx.n["infrastructure"]["cloud_preference"] == "azure" and not air)
    )
    if wants_entra:
        if True:
            choice = "Microsoft Entra ID"
            why = "The directory already exists." if ctx.existing["entra"] else "The cloud is Azure, so the workforce directory should be Entra ID rather than a second login."
            if ctx.existing["entra"]:
                why = "Microsoft Entra ID is already in the environment. The app should trust that tenant over OpenID Connect instead of inventing accounts."
            return _component(
                choice, why,
                _paths("requirements.auth", "infrastructure.existing_systems", "infrastructure.cloud_preference"),
                [{"choice": "Keycloak", "why_not": "A second directory means two places to disable a leaver."}],
                ["Conditional access and guest users still need a tenant admin. The app only consumes the token."],
                "auth",
            )
    if ctx.existing["okta"]:
        return _component(
            "Okta",
            "Okta is already the directory. The app should be one more OIDC client, not a new user table.",
            _paths("requirements.auth", "infrastructure.existing_systems"),
            [{"choice": "A new Entra ID tenant", "why_not": "The company already pays for Okta."}],
            ["Okta outages become login outages. Cache the session, do not call Okta on every API hit."],
            "auth",
        )
    if ctx.auth == "enterprise_sso" or air and ctx.n["requirements"]["auth"] == "enterprise_sso":
        return _component(
            "Keycloak",
            "Enterprise SSO with no named directory yet. Keycloak runs next to the app, including on a private network, and speaks OIDC and SAML.",
            _paths("requirements.auth", "infrastructure.deployment_model"),
            [{"choice": "Auth0", "why_not": "A public SaaS directory is the wrong call on a private network, and it is a second vendor for a thing you can host."}],
            ["You patch Keycloak. That is the cost of not renting the directory."],
            "auth",
        )
    if ctx.auth == "phone_otp":
        india = ctx.effective_residency == "india" or ctx.signals["upi"]
        if india:
            choice, alt = "App-managed OTP via MSG91", "Twilio"
            why = "Phone OTP for users in India should use a domestic SMS route (DLT-registered). MSG91 is that route. Store only a hash of the code, in the India database."
        else:
            choice, alt = "App-managed OTP via Twilio", "MessageBird"
            why = "Phone OTP with the SMS leaving your app. The code and the attempt counter stay in your database, not in a second user store."
        return _component(
            choice, why,
            _paths("requirements.auth", "infrastructure.data_residency", "compliance"),
            [{"choice": alt, "why_not": "It works, and it is a worse fit for the residency of the phone numbers." if india
              else "A second global SMS vendor does not change the design."},
             {"choice": "Firebase Auth", "why_not": "The user record would sit in a Google project whose region story is easy to get wrong, and phone-auth pricing surprises small budgets."}],
            ["SMS cost scales with logins, not with servers. A noisy retry loop will blow the budget before the database does."],
            "auth",
        )
    if ctx.auth == "social":
        return _component(
            "Auth.js (self-hosted)",
            "Social login, with the profile row stored in our database. The OAuth client secret stays on the server.",
            _paths("requirements.auth", "infrastructure.data_residency", "compliance"),
            [{"choice": "Clerk", "why_not": "Clerk is fast to drop in and keeps user records on Clerk's side. That fights a residency or GDPR story we can avoid by holding the row ourselves."}],
            ["You own password-less session bugs. Keep the provider list short."],
            "auth",
        )
    return _component(
        "Email and password in the application database",
        "Accounts stay in the same database as the rest of the product, with a slow hash (Argon2id or bcrypt) and a normal session cookie or token.",
        _paths("requirements.auth"),
        [{"choice": "Amazon Cognito", "why_not": "A separate user pool is another system to back up, and it is the wrong shape once the cloud is not AWS or the network is private."}],
        ["You own reset flows, lockout, and breach notice. Use a known library, do not write the hash."],
        "auth",
    )


def _storage_item(ctx, provider, region) -> dict:
    private = ctx.n["data"]["sensitivity"] in {"confidential", "restricted"} or ctx.signals["kyc"] or "hipaa" in ctx.n["compliance"]
    if provider == "aws":
        choice = f"Amazon S3 in {region}" + (" with SSE-KMS" if private else "")
        alt = "MinIO on EC2"
    elif provider == "azure":
        choice = f"Azure Blob Storage in {region}"
        alt = "SharePoint via Microsoft Graph"
    elif provider == "gcp":
        choice = f"Cloud Storage in {region}"
        alt = "MinIO"
    elif provider == "self":
        choice = "MinIO"
        alt = "A shared folder"
    else:
        choice = f"DigitalOcean Spaces in {region}"
        alt = "Amazon S3 in ap-south-1"
    why = "Uploads have to live somewhere durable."
    if private:
        why += " The bucket is private. The app issues short-lived URLs. KYC, health, or customer files do not sit on a public CDN."
    elif ctx.signals["poor_network"]:
        why += " Clients should upload only after compressing, because the network in the description is weak."
    else:
        why += f" Keep the bucket in {region} so it matches the database pin."
    if ctx.existing["sharepoint"] and provider == "azure":
        alt = "SharePoint via Microsoft Graph"
    return _component(
        choice, why,
        _paths("requirements.file_media_storage", "infrastructure.data_residency", "data.sensitivity", "compliance"),
        [{"choice": alt, "why_not": "A second file system splits retention and access reviews. One bucket next to the app is enough."}],
        ["Lifecycle rules are part of the design. Nobody deletes old uploads unless you ask the bucket to."],
        "storage",
    )


def _wants_cdn(ctx, arch, host) -> bool:
    if ctx.effective_deploy in {"air_gapped", "on_premise"}:
        return False
    if arch == "static":
        return False
    if "web" not in ctx.platforms:
        return False
    if ctx.ptype == "internal_tool":
        return False
    if ctx.n["data"]["sensitivity"] == "restricted" and not ctx.n["requirements"]["seo_critical"]:
        # Still allow a CDN for the public shell on fintech. P4 seo is false and restricted.
        # A CDN of the static bundle is fine if we say private files bypass it. Include for aws/azure/gcp.
        return host["id"].startswith("aws") or host["id"].startswith("gcp") or host["id"].startswith("azure")
    if ctx.effective_residency == "india" and ctx.n["data"]["sensitivity"] in {"confidential", "restricted"}:
        return False
    return True


def _cdn_item(ctx, provider) -> dict | None:
    if provider == "aws":
        choice, alt = "Amazon CloudFront (static web bundle only)", "Cloudflare in front of the whole origin"
    elif provider == "gcp":
        choice, alt = "Cloud CDN", "Cloudflare"
    elif provider == "azure":
        choice, alt = "Azure Front Door for the public web bundle", "Cloudflare"
    else:
        return None
    return _component(
        choice,
        "Cache the public web bundle close to users. Private uploads and payment payloads go straight to the origin in the pinned region.",
        _paths("project.platforms", "requirements.seo_critical", "data.sensitivity"),
        [{"choice": alt, "why_not": "A global cache in front of personal data fights the residency pin."}],
        ["A bad cache key will serve one user's file to another. Private buckets stay unsigned-public."],
        "cdn",
    )


def _realtime_item(ctx, be) -> dict:
    if "go_http" in be["id"] or ctx.ptype == "realtime_collab":
        choice = "Yjs over WebSockets on the Go service, fan-out through Valkey"
        alt = "Liveblocks"
        why = (
            f"Live updates are required and the peak is {_commas(ctx.peak)}. "
            "A CRDT (Yjs) fits a shared board or any document several people edit. "
            "Valkey pub/sub lets more than one sync node see the same room."
        )
        if ctx.ptype != "realtime_collab":
            choice = "WebSockets on the Go service, fan-out through Valkey"
            why = f"The peak of {_commas(ctx.peak)} concurrent connections wants a small Go process, not a request-per-update design."
    elif "aspnet" in be["id"]:
        choice, alt = "SignalR", "A raw WebSocket handler"
        why = "The API is ASP.NET Core, and SignalR is the maintained realtime library in that stack."
    elif "spring" in be["id"]:
        choice, alt = "Spring WebSocket", "Socket.IO behind a Node sidecar"
        why = "Keep the socket in the JVM process so auth and the ledger share one session model."
    elif "fastapi" in be["id"]:
        choice, alt = "WebSockets in FastAPI", "A separate Node socket process"
        why = "The API is already Python. A second realtime runtime is not worth it at this peak."
    else:
        choice, alt = "Socket.IO on the API process", "A managed socket vendor (Ably or Pusher)"
        why = (
            f"realtime is true and the peak is {_commas(ctx.peak)}. "
            "One Socket.IO process on the API covers chat and job status. Add the Valkey adapter only when you run a second copy."
        )
    return _component(
        choice, why,
        _paths("requirements.realtime", "scale.peak_concurrent_users", "requirements.p95_latency_ms", "team.languages"),
        [{"choice": alt, "why_not": "A managed realtime vendor stores the hot path outside the region pin, and it is a new bill for a problem the API can hold."}],
        ["Sticky sessions or a pub/sub adapter are mandatory once you run two copies. One copy is a single point of failure."],
        "realtime",
    )


def _payments_item(ctx) -> dict:
    india = (
        ctx.effective_residency == "india"
        or "rbi_localisation" in ctx.n["compliance"]
        or "dpdp" in ctx.n["compliance"] and ctx.signals["upi"]
        or ctx.signals["upi"]
    )
    if india:
        choice, alt = "Razorpay", "Cashfree"
        why = (
            "Payments in India, including UPI, should go through an RBI-authorised payment aggregator. "
            "Razorpay is that aggregator. Card numbers and UPI secrets stay on their side, which keeps this app out of full PCI scope."
        )
    elif ctx.effective_residency == "eu" or "gdpr" in ctx.n["compliance"]:
        choice, alt = "Stripe", "Mollie"
        why = "Seat or card billing for users who can be in the EU. Stripe has the billing primitives. Card data stays at Stripe."
    else:
        choice, alt = "Stripe", "Braintree"
        why = "Card or seat billing. Stripe is the maintained default. Card data stays at the processor."
    if ctx.signals["per_seat"]:
        why += " The description prices per seat, so use the processor's subscription product rather than a home-grown renewals cron."
    return _component(
        choice, why,
        _paths("requirements.payments", "infrastructure.data_residency", "compliance", "project.description"),
        [{"choice": alt, "why_not": "Cashfree is the other large India aggregator. Razorpay was chosen for payouts and the docs a small team will actually read." if india else "Mollie is a strong EU processor. Stripe was chosen because per-seat billing is a product there, not a cron you write."}],
        ["Do not store PAN, CVV, or UPI PIN. If you do, PCI scope explodes and this recommendation no longer holds."],
        "payments",
    )


def _ml_item(ctx, provider, region) -> dict:
    kind = ctx.n["requirements"]["ml_features"]
    air = ctx.effective_deploy in {"air_gapped", "on_premise"}
    if kind == "llm_rag" and (air or ctx.effective_residency in {"india", "eu"} or ctx.n["compliance"]):
        return _component(
            "pgvector on PostgreSQL plus a self-hosted model",
            f"llm_rag is set and the data pin is {ctx.effective_residency}. Text should not be posted to a public model API by default. Keep embeddings in Postgres and run the model beside the API.",
            _paths("requirements.ml_features", "infrastructure.data_residency", "compliance"),
            [{"choice": "A public LLM API", "why_not": "Prompts and documents would leave the region. Turn that on only with a named processor and a lawful basis."}],
            ["Self-hosted models are an operations project. A small GPU is a different bill from the API nodes."],
            "ml",
        )
    if kind == "llm_rag":
        return _component(
            "pgvector on PostgreSQL, model provider left optional",
            "Retrieval lives in Postgres. Which model you call is a product choice and is not picked by this engine, because a model call can move text across a border.",
            _paths("requirements.ml_features"),
            [{"choice": "A bundled chat vendor", "why_not": "Locking the recommendation to one model vendor would pretend the data-flow decision was already made."}],
            ["You still need a retention story for prompts."],
            "ml",
        )
    if air or provider == "self" or not ctx.devops:
        return _component(
            "ONNX Runtime beside the API",
            "The model is loaded in a sidecar or in-process. That keeps inference inside the same network as the data, and it avoids a second control plane.",
            _paths("requirements.ml_features", "team.has_devops", "infrastructure.deployment_model"),
            [{"choice": "Amazon SageMaker", "why_not": "A managed endpoint is easier at larger scale and it is extra platform to learn for this team or this network."}],
            ["You own model rollback. Ship the model file with the build so it is versioned."],
            "ml",
        )
    if provider == "aws" or ctx.n["infrastructure"]["cloud_preference"] == "aws":
        choice = f"Amazon SageMaker endpoint in {region}"
        alt = "ONNX Runtime on ECS"
    elif provider == "gcp" or ctx.n["infrastructure"]["cloud_preference"] == "gcp":
        choice = f"Vertex AI endpoint in {region}"
        alt = "ONNX Runtime on Cloud Run"
    elif provider == "azure" or ctx.n["infrastructure"]["cloud_preference"] == "azure":
        choice = f"Azure Machine Learning online endpoint in {region}"
        alt = "ONNX Runtime on App Service"
    else:
        choice = "ONNX Runtime beside the API"
        alt = "A public inference API"
    return _component(
        choice,
        "inference is a separate scale problem from the API. A managed endpoint in the same region keeps training data and request payloads next to the ledger or the product database.",
        _paths("requirements.ml_features", "infrastructure.cloud_preference", "infrastructure.data_residency", "team.has_devops"),
        [{"choice": alt, "why_not": "It is the right fallback if the managed endpoint's minimum bill is hard to justify. It puts model ops back on the team."}],
        ["A real-time endpoint has a floor cost even at night. Serverless inference is cheaper if the model is small and the latency budget allows a cold start."],
        "ml",
    )


def _ci_item(ctx) -> dict:
    if ctx.effective_deploy in {"air_gapped", "on_premise"}:
        choice, alt = "Gitea Actions", "Jenkins"
        why = "CI has to run inside the same network as the deploy. A public GitHub runner cannot reach an air-gapped rack."
    else:
        choice, alt = "GitHub Actions", "Azure Pipelines" if ctx.n["infrastructure"]["cloud_preference"] == "azure" else "GitLab CI"
        why = "A short pipeline: test, then deploy with short-lived cloud credentials. Keep production secrets out of the repo."
    return _component(
        choice, why,
        _paths("team.size", "team.has_devops", "infrastructure.deployment_model"),
        [{"choice": alt, "why_not": "It is a fine CI. It is also a second account this team has not said they already run."}],
        ["A green pipeline is not a test plan. Someone still has to write the tests."],
        "ci_cd",
    )


def _wants_obs(ctx) -> bool:
    if ctx.n["requirements"]["availability"] in {"99.9", "99.95", "99.99"}:
        return True
    if ctx.devops or ctx.users >= 50_000:
        return True
    return False


def _obs_item(ctx, provider) -> dict:
    if provider == "aws":
        choice, alt = "Amazon CloudWatch", "Self-hosted Grafana"
    elif provider == "azure":
        choice, alt = "Azure Application Insights", "Self-hosted Grafana"
    elif provider == "gcp":
        choice, alt = "Google Cloud Monitoring", "Self-hosted Grafana"
    elif provider == "do":
        choice, alt = "DigitalOcean App Platform metrics", "A separate Grafana stack"
    else:
        choice, alt = "Prometheus and Grafana", "A SaaS log vendor"
    return _component(
        choice,
        f"Availability target is {ctx.n['requirements']['availability']}. You need a health check, a latency chart, and an alert that reaches a person. Keep the logs in the same region as the data.",
        _paths("requirements.availability", "team.has_devops", "scale.users_12_months"),
        [{"choice": alt, "why_not": "More moving parts, or a log vendor that may store text outside the pin."}],
        ["Log volume is a bill. Sample debug lines. Do not log OTP codes, tokens, or payment payloads."],
        "observability",
    )


def _device_db_item(ctx) -> dict:
    return _component(
        "SQLite on the device, with an outbound sync queue",
        "offline_support is true. The phone keeps survey or job rows locally and posts them when the network returns. SQLite is the maintained on-device store. Compress photos before they join the queue.",
        _paths("requirements.offline_support", "project.platforms", "project.description"),
        [{"choice": "MongoDB Realm and Atlas Device Sync",
          "why_not": "Atlas Device Sync and the Realm SDKs were removed on 30 September 2025. A new app should not start there."}],
        ["Conflicts are your code. Last-write-wins is a product decision, not a database feature."],
        "other",
    )


def _mqtt_item(ctx) -> dict:
    return _component(
        "Eclipse Mosquitto",
        "An IoT workload needs a broker. Mosquitto is the small, maintained one you can run next to the API, including on a private network.",
        _paths("project.type", "infrastructure.deployment_model"),
        [{"choice": "Google Cloud IoT Core", "why_not": "Cloud IoT Core was retired. Do not design against it."}],
        ["Devices need an identity per device. A shared password is not a fleet plan."],
        "other",
    )


def _warn_skill(ctx: Ctx, fe, be) -> None:
    missing = []
    for plan in (fe, be):
        for part in plan.get("parts") or []:
            required = [lang for lang in part.get("languages", []) if lang in CORE_LANGS]
            if required and not any(lang in ctx.languages for lang in required):
                missing.extend(required)
    missing = sorted(set(missing))
    if missing:
        ctx.warn(
            "SKILL_GAP",
            "warning",
            "The chosen stack uses " + ", ".join(missing) + ", which the team did not list. The trade-off is written on the component. Budget time to learn it, or switch to the alternative.",
            ["team.languages"],
        )
    elif not ctx.languages:
        ctx.warn(
            "SKILL_UNKNOWN",
            "info",
            "team.languages is empty, so the engine favoured lower complexity tools and could not reward a skill match.",
            ["team.languages"],
        )


def _warn_timeline(ctx: Ctx, arch: str, fe) -> None:
    base = {
        "static": 2, "serverless": 6, "monolith": 6, "modular_monolith": 8,
        "hybrid": 12, "service_oriented": 16, "microservices": 24, "other": 8,
    }.get(arch, 8)
    platforms = [p for p in ctx.platforms if p != "api_only"]
    if len(platforms) >= 3:
        base += 3
    elif "web" in platforms and ({"android", "ios"} & set(platforms)):
        base += 2
    if ctx.n["requirements"]["offline_support"]:
        base += 2
    if ctx.n["requirements"]["ml_features"] != "none":
        base += 3
    if ctx.n["team"]["experience"] == "mixed":
        base += 1
    weeks = ctx.n["timeline"]["mvp_weeks"]
    if weeks + 1 < base:
        ctx.warn(
            "TIMELINE_TIGHT",
            "warning",
            f"The MVP window is {weeks} weeks. A {arch.replace('_', ' ')} across {', '.join(platforms) or 'the stated platforms'} usually wants about {base} weeks for a team this size. Cut scope before you cut the hard constraints.",
            ["timeline.mvp_weeks", "project.platforms", "team.size"],
        )


def _warn_availability(ctx: Ctx, db) -> None:
    avail = ctx.n["requirements"]["availability"]
    if avail == "99.99" and (ctx.n["team"]["experience"] == "beginner" or ctx.n["team"]["size"] < 3 or not ctx.devops):
        ctx.warn(
            "AVAILABILITY_TEAM",
            "critical",
            "99.99 is about 52 minutes a year. A small or beginner team without an operator cannot honestly offer that. Lower the target or staff on-call before you promise it.",
            ["requirements.availability", "team.size", "team.experience", "team.has_devops"],
        )
    if avail in {"99.95", "99.99"} and not ctx.n["operations"]["on_call"]:
        ctx.warn(
            "AVAILABILITY_NEEDS_ONCALL",
            "warning",
            f"The target is {avail} and operations.on_call is false. The computers cannot page themselves. Name a human or lower the target.",
            ["requirements.availability", "operations.on_call"],
        )
    if avail in {"99.9", "99.95", "99.99"} and db.get("existing") and ctx.existing["sqlserver"]:
        ctx.warn(
            "AVAILABILITY_ONPREM",
            "warning",
            f"The target is {avail}, and the database is an existing on-prem SQL Server. The cloud app cannot be more available than that server. Confirm backups and a second replica before you publish the number.",
            ["requirements.availability", "infrastructure.existing_systems"],
        )
    latency = ctx.n["requirements"]["p95_latency_ms"]
    if latency is not None and latency <= 150 and ctx.n["requirements"]["realtime"] and ctx.peak >= 1_000:
        ctx.warn(
            "LATENCY_TARGET",
            "warning",
            f"p95_latency_ms is {latency} with realtime on and a peak of {_commas(ctx.peak)}. That is possible inside one region and unlikely across continents or through cold starts. Measure the fan-out before you sign the number.",
            ["requirements.p95_latency_ms", "requirements.realtime", "scale.peak_concurrent_users"],
        )


def _warn_product_risks(ctx: Ctx, host, db) -> None:
    compliance = set(ctx.n["compliance"])
    if "dpdp" in compliance:
        ctx.warn(
            "DPDP",
            "info",
            "DPDP applies. You still need a lawful purpose, a consent or legitimate-use record, a retention period, and a way for a person to access or erase their data. The region pin is not the whole duty.",
            ["compliance"],
        )
    if "gdpr" in compliance:
        ctx.warn(
            "GDPR",
            "info",
            "GDPR applies. Sign a DPA with each processor, keep a record of processing, and do not treat a vendor certificate as your compliance.",
            ["compliance"],
        )
    if "hipaa" in compliance:
        if host["record"].get("baa") and host["id"] != "docker_compose":
            ctx.warn(
                "HIPAA_BAA",
                "warning",
                "Sign the cloud BAA before any PHI is stored, and check the chosen region is in that BAA. A region that is merely 'available' is not enough.",
                ["compliance", "infrastructure.data_residency"],
            )
        else:
            ctx.warn(
                "HIPAA_SELF",
                "warning",
                "Self-hosted HIPAA means you are the one who implements access control, audit, and encryption. The compose file does not make you compliant.",
                ["compliance", "infrastructure.deployment_model"],
            )
    if "pci_dss" in compliance or ctx.payments:
        ctx.warn(
            "PCI_SCOPE",
            "info",
            "Keep card data at the payment aggregator and this app stays on the short PCI questionnaire. The moment you store PAN or CVV, stop and redesign.",
            ["compliance", "requirements.payments"],
        )
    if "rbi_localisation" in compliance:
        ctx.warn(
            "RBI_BACKUPS",
            "warning",
            "RBI wants the full payment record stored only in India. Backups, replicas, and log archives stay in India too (for AWS, ap-south-1 and ap-south-2). Do not add a Singapore standby.",
            ["compliance", "infrastructure.data_residency"],
        )
    if compliance & {"iso27001", "soc2"}:
        ctx.warn(
            "SHARED_RESPONSIBILITY",
            "info",
            "ISO 27001 or SOC 2 on the vendor does not certify this product. You still need access reviews, backups, and an owner for incidents.",
            ["compliance"],
        )
    if ctx.auth == "phone_otp":
        ctx.warn(
            "SMS_COST",
            "warning",
            "OTP SMS is usage priced and can pass the infra budget on its own. Cap retries, and watch the SMS bill as a separate line.",
            ["requirements.auth", "budget.monthly_infra_usd"],
        )
    if ctx.signals["low_end"]:
        ctx.warn(
            "LOW_END_DEVICE",
            "warning",
            "The description mentions low-RAM phones. Ship a release build, keep the screen count small, and test on a 2 GB device. A debug build is not the test.",
            ["project.description", "project.platforms"],
        )
    if ctx.signals["poor_network"] and ctx.n["requirements"]["file_media_storage"]:
        ctx.warn(
            "LOW_BANDWIDTH_MEDIA",
            "warning",
            "The network in the description is weak. Downscale photos on the device (1280 px on the long edge is enough) before they join the upload queue.",
            ["project.description", "requirements.file_media_storage", "requirements.offline_support"],
        )
    if ctx.signals["gps"] and ("dpdp" in compliance or ctx.n["data"]["sensitivity"] in {"confidential", "restricted"}):
        ctx.warn(
            "LOCATION_DATA",
            "info",
            "GPS points are personal data. Store the consent flag on the same row and set a retention period.",
            ["project.description", "compliance"],
        )
    if ctx.ptype in {"fintech", "healthtech"} and "hipaa" not in compliance and "rbi_localisation" not in compliance and ctx.ptype == "healthtech":
        ctx.warn(
            "HEALTH_WITHOUT_HIPAA",
            "info",
            "The project type is healthtech and HIPAA is not in the list. If any user is a US patient, add it. The engine did not invent the flag.",
            ["project.type", "compliance"],
        )
    if arch_is_small(ctx) and ctx.ptype != "content_site":
        ctx.warn(
            "OVERENGINEERING_AVOIDED",
            "info",
            f"Microservices and Kubernetes were not chosen. The team is {ctx.n['team']['size']} and the 12 month user count is {_commas(ctx.users)}. A single deployable is the design until those numbers move.",
            ["team.size", "scale.users_12_months", "team.has_devops"],
        )
    if ctx.n["scale"]["geographic_spread"] == "multi_region" and "rbi_localisation" in compliance:
        ctx.warn(
            "MULTI_REGION_INDIA",
            "warning",
            "geographic_spread is multi_region and RBI applies. The second region has to be inside India. A global active-active design is out.",
            ["scale.geographic_spread", "compliance"],
        )


def arch_is_small(ctx: Ctx) -> bool:
    return ctx.n["team"]["size"] < 8 and ctx.users < 100_000


def _cost_with_budget(ctx: Ctx, host, db, supporting) -> dict:
    def run(layers: list[dict]) -> dict:
        return estimate(ctx.n, {
            "host_id": host["id"],
            "db_id": db["id"],
            "db_existing": db.get("existing", False),
            "ha": db.get("ha", False),
            "supporting_layers": [item["layer"] for item in layers],
        })

    cost = run(supporting)
    if cost["min"] > ctx.budget:
        trimmed = list(supporting)
        optional = []
        if ctx.n["requirements"]["availability"] not in {"99.99"}:
            optional.append("observability")
        if not ctx.n["requirements"]["seo_critical"]:
            optional.append("cdn")
        if ctx.peak < 2_000:
            optional.append("cache")
        if not ctx.payments and ctx.n["requirements"]["ml_features"] == "none":
            optional.append("queue")
        removed = []
        for layer in optional:
            nxt = [item for item in trimmed if item["layer"] != layer]
            if len(nxt) == len(trimmed):
                continue
            trial = run(nxt)
            if trial["min"] < cost["min"]:
                trimmed = nxt
                cost = trial
                removed.append(layer)
            if cost["min"] <= ctx.budget:
                break
        if removed:
            supporting[:] = trimmed
            ctx.assumptions.append(
                "Dropped optional supporting pieces to chase the budget: " + ", ".join(removed) + "."
            )
    if cost["min"] > ctx.budget:
        ctx.warn(
            "BUDGET_EXCEEDED",
            "critical",
            f"The cheapest stack that still meets the hard constraints is about {cost['min']} to {cost['max']} USD per month. The stated budget is {int(ctx.budget)} USD. No cheaper compliant option is in the catalog. The budget was not used as permission to drop residency or compliance.",
            ["budget.monthly_infra_usd"],
        )
        ctx.assumptions.append(
            "Budget cannot buy the minimum compliant footprint. Status is infeasible. The stack shown is the cheapest one that still respects the hard constraints."
        )
        cost["blocked"] = True
    elif cost["max"] > ctx.budget:
        ctx.warn(
            "BUDGET_TIGHT",
            "warning",
            f"The low end of the band ({cost['min']} USD) fits inside {int(ctx.budget)} USD. The high end ({cost['max']} USD) does not. Treat the top as a risk, mostly SMS, egress, or a larger node, not as a surprise you can ignore.",
            ["budget.monthly_infra_usd"],
        )
        cost["blocked"] = False
    else:
        cost["blocked"] = False
    if cost["max"] == 0 and ctx.budget == 0:
        if host["record"]["kind"] == "static":
            message = (
                "The estimate is zero because the choice stays on a free static tier. "
                "A custom domain registrar, if you buy one, is outside this band. "
                "A traffic spike past the host's fairness limit is the thing to watch."
            )
        else:
            message = (
                "The estimate is zero because the processes sit on machines you already run, or in a local file. "
                "Power, disks, and the person who patches them are outside this band."
            )
        ctx.warn("FREE_TIER", "info", message, ["budget.monthly_infra_usd"])
    return cost


def _status(ctx: Ctx, cost: dict) -> str:
    if ctx.relaxed or cost.get("blocked"):
        return "infeasible"
    if any(item["severity"] in {"warning", "critical"} for item in ctx.warnings):
        return "ok_with_warnings"
    return "ok"


def _summary(ctx, arch, fe, be, db, host) -> str:
    style = {
        "static": "a static site",
        "monolith": "a monolith",
        "modular_monolith": "a modular monolith",
        "serverless": "a serverless shape",
        "service_oriented": "a small set of services",
        "microservices": "microservices",
        "hybrid": "a hybrid, with one extra managed path beside the main service",
        "other": "a custom shape",
    }.get(arch, arch)
    name = _pname(ctx)
    if arch == "static":
        return (
            f"{name} should be {style}: {fe['name']} built ahead of time, no application server, no database, on {host['choice']}. "
            f"The pages are read-heavy and the budget is {int(ctx.budget)} USD a month."
        )
    return (
        f"{name} should be {style} in {host['region']}. "
        f"Client: {fe['name']}. Server: {be['name']}. Data: {db['choice']}. Host: {host['choice']}."
    )


def _justify_frontend(ctx, fe) -> str:
    platforms = ", ".join(ctx.platforms)
    sentences = [
        f"{_pname(ctx)} is {_article(ctx.ptype.replace('_', ' '))} {ctx.ptype.replace('_', ' ')} on {platforms}.",
        (
            f"Twelve month target {_commas(ctx.users)} users, peak {_commas(ctx.peak)}, "
            f"MVP {ctx.n['timeline']['mvp_weeks']} weeks, {_people(ctx)}."
        ),
    ]
    if fe["id"] == "none":
        sentences.append("platforms is api_only, so the engine does not invent a client.")
    else:
        sentences.append(fe.get("blurb") or "The client matches the platform list and the team languages.")
        if ctx.n["requirements"]["seo_critical"] and "web" in ctx.platforms:
            sentences.append("seo_critical is true, so the public URL has to return real HTML.")
        if ctx.languages:
            sentences.append("Team languages: " + ", ".join(ctx.languages) + ".")
        if ctx.n["requirements"]["offline_support"]:
            sentences.append("offline_support is true, so the client keeps its own queue.")
        if ctx.signals["low_end"]:
            sentences.append("The description calls out weak phones, so a heavier toolkit had to earn its place.")
        if ctx.signals["markdown"] and fe["id"] == "astro":
            sentences.append("The copy is Markdown, which Astro can render at build time.")
    return " ".join(sentences)


def _justify_backend(ctx, be, fe) -> str:
    if be["id"] == "none":
        return (
            "No accounts, no writes, no private files, and no payments. "
            "A server would be a process to patch in exchange for nothing the page needs."
        )
    bits = [be.get("blurb") or be["name"]]
    bits.append(
        f"Peak {_commas(ctx.peak)}, workload {ctx.n['scale']['workload']}, "
        f"realtime {'on' if ctx.n['requirements']['realtime'] else 'off'}."
    )
    if ctx.signals["ledger"] or ctx.ptype == "fintech":
        bits.append("Money movement wants a boring server with transactions, not a function that forgets its connection pool.")
    if "go_http" in be["id"] and ctx.n["requirements"]["realtime"]:
        bits.append("The hot path is open sockets, which is the workload Go is being chosen for.")
    return " ".join(bits)


def _justify_database(ctx, db, host) -> str:
    if db["id"] == "none":
        return "The pages are generated from files in git. There is no row to store, so there is no database."
    if db.get("existing"):
        return (
            f"{db['choice']} is already in the environment. New product tables go there, over a private network path, "
            "instead of standing up a second system of record during the MVP."
        )
    bits = [db["record"].get("blurb", db["choice"])]
    bits.append(f"Placement follows the host pin: {host['region']}.")
    if db.get("ha"):
        bits.append(f"availability {ctx.n['requirements']['availability']} is why the database line is redundant, not a single node.")
    if ctx.signals["ledger"]:
        bits.append("A double-entry ledger needs commits that either land or do not. That is this engine, not a document store.")
    return " ".join(bits)


def _justify_host(ctx, host, arch) -> str:
    cloud = ctx.n["infrastructure"]["cloud_preference"]
    deploy = ctx.n["infrastructure"]["deployment_model"]
    bits = [
        f"cloud_preference is {cloud}, deployment_model is {deploy}, data_residency resolves to {ctx.effective_residency}.",
        f"The pin is {host['region']}.",
        host["record"].get("blurb", ""),
    ]
    if ctx.existing["sqlserver"] and host["id"] == "azure_appservice":
        bits.append("The app runs in Azure and reaches the on-prem SQL Server over a private path (Hybrid Connection or a site VPN). ExpressRoute is out of this budget.")
    if not ctx.devops and host["record"]["ops_burden"] <= 2:
        bits.append("team.has_devops is false, so a host with a small control surface beats a cluster.")
    if arch == "static":
        bits.append("There is no process to keep up. Static hosting is the whole platform.")
    return " ".join(bit for bit in bits if bit)


def _driven_frontend(ctx, fe) -> list[str]:
    return _paths(
        "project.type", "project.platforms", "team.languages", "team.experience",
        "team.size", "timeline.mvp_weeks",
        "requirements.seo_critical" if "web" in ctx.platforms else "",
        "requirements.offline_support" if ctx.n["requirements"]["offline_support"] else "",
        "scale.users_12_months", "budget.monthly_infra_usd",
        "project.description" if ctx.signals["markdown"] or ctx.signals["low_end"] else "",
    )


def _driven_backend(ctx, be) -> list[str]:
    if be["id"] == "none":
        return _paths("project.type", "requirements.auth", "requirements.payments", "budget.monthly_infra_usd")
    return _paths(
        "team.languages", "team.size", "team.has_devops", "project.type",
        "requirements.realtime", "scale.peak_concurrent_users", "priorities.performance",
        "requirements.ml_features" if ctx.n["requirements"]["ml_features"] != "none" else "",
        "project.description" if ctx.signals["ledger"] else "",
    )


def _driven_db(ctx, db) -> list[str]:
    if db.get("existing"):
        return _paths("infrastructure.existing_systems", "project.type", "requirements.payments")
    if db["id"] == "none":
        return _paths("project.type", "requirements.auth", "scale.data_volume_gb_12_months")
    return _paths(
        "project.type", "requirements.payments", "requirements.multi_tenant",
        "infrastructure.data_residency", "infrastructure.cloud_preference",
        "requirements.availability", "scale.users_12_months",
        "team.vendor_lock_in_tolerance",
        "project.description" if ctx.signals["ledger"] else "",
    )


def _driven_host(ctx) -> list[str]:
    return _paths(
        "infrastructure.cloud_preference", "infrastructure.deployment_model",
        "infrastructure.data_residency", "compliance", "budget.monthly_infra_usd",
        "team.has_devops", "requirements.availability", "scale.peak_concurrent_users",
    )


def _output(ctx, status, summary, arch, host, fe, be, db, supporting, cost) -> dict:
    sev = {"critical": 0, "warning": 1, "info": 2}
    warnings = sorted(ctx.warnings, key=lambda item: (sev[item["severity"]], item["code"], item["message"]))
    # De-duplicate identical codes keeping the first after sort. Identical code+message.
    deduped = []
    seen = set()
    for item in warnings:
        key = (item["code"], item["message"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    fe_comp = _component(
        fe["name"] if fe["id"] != "none" else "None",
        _justify_frontend(ctx, fe),
        _driven_frontend(ctx, fe),
        _alts(fe.get("runners") or [fe], ctx, fe.get("rejected")),
        (fe.get("tradeoffs") or ["No extra client trade-off beyond the ones in the alternatives."])[:3],
    )
    be_comp = _component(
        "None" if be["id"] == "none" else be["name"],
        _justify_backend(ctx, be, fe),
        _driven_backend(ctx, be),
        _alts(be.get("runners") or [be], ctx, be.get("rejected")),
        (be.get("tradeoffs") or ["No extra server trade-off beyond the ones in the alternatives."])[:3],
    )
    db_comp = _component(
        db["choice"],
        _justify_database(ctx, db, host),
        _driven_db(ctx, db),
        _alts(db.get("runners") or [], ctx, db.get("rejected")),
        (db.get("tradeoffs") or ["No extra data trade-off beyond the ones in the alternatives."])[:3],
    )
    host_comp = _component(
        host["choice"],
        _justify_host(ctx, host, arch),
        _driven_host(ctx),
        _alts(host.get("runners") or [host], ctx, host.get("rejected")),
        (host["record"].get("tradeoffs") or [])[:3],
    )
    return {
        "scenario_id": ctx.n["scenario_id"],
        "engine_version": __version__,
        "status": status,
        "summary": summary,
        "architecture_style": arch,
        "deployment_region": host["region"],
        "stack": {
            "frontend": fe_comp,
            "backend": be_comp,
            "database": db_comp,
            "hosting": host_comp,
            "supporting": supporting,
        },
        "estimated_monthly_cost_usd": {
            "min": cost["min"],
            "max": cost["max"],
            "assumptions": cost["assumptions"],
        },
        "warnings": deduped,
        "assumptions": ctx.assumptions,
        "validation_errors": [],
    }
