"""Behaviour tests. They call the scorer. They do not store a canned stack."""

from __future__ import annotations

import json
import os
import unittest
from copy import deepcopy
from pathlib import Path

from stacksense.decide import recommend
from stacksense.kb import BACKEND, DATABASE, FRONTEND, HOSTING, RETIRED

ROOT = Path(__file__).resolve().parents[1]


def load_public():
    return json.loads((ROOT / "scenarios" / "public.json").read_text())


BANNED = (
    "Fauna", "Realm", "Create React App", "AngularJS", "Dynamic Links",
    "Gatsby Cloud", "IoT Core", "Parse.com", "Heroku",
)


def choices(result: dict) -> dict:
    stack = result["stack"]
    return {
        "status": result["status"],
        "architecture_style": result["architecture_style"],
        "frontend": stack["frontend"]["choice"],
        "backend": stack["backend"]["choice"],
        "database": stack["database"]["choice"],
        "hosting": stack["hosting"]["choice"],
        "supporting": [(item["layer"], item["choice"]) for item in stack.get("supporting") or []],
        "min": result["estimated_monthly_cost_usd"]["min"],
        "max": result["estimated_monthly_cost_usd"]["max"],
        "codes": [item["code"] for item in result["warnings"]],
    }


def base(**over):
    body = {
        "project": {"name": "Sample", "type": "web_app", "platforms": ["web"], "description": ""},
        "scale": {
            "users_at_launch": 100, "users_12_months": 1000, "peak_concurrent_users": 20,
            "traffic_pattern": "steady", "workload": "balanced", "data_volume_gb_12_months": 2,
        },
        "team": {"size": 2, "experience": "intermediate", "languages": ["javascript"], "has_devops": False},
        "budget": {"monthly_infra_usd": 80},
        "timeline": {"mvp_weeks": 8},
        "infrastructure": {
            "cloud_preference": "any", "deployment_model": "managed_cloud",
            "data_residency": "none", "existing_systems": [],
        },
        "requirements": {
            "realtime": False, "offline_support": False, "full_text_search": False,
            "file_media_storage": False, "payments": False, "auth": "email_password",
            "multi_tenant": False, "ml_features": "none", "seo_critical": False,
            "availability": "99.9", "p95_latency_ms": None,
        },
        "compliance": [],
        "priorities": {k: 3 for k in ("cost", "time_to_market", "scalability", "performance", "maintainability", "security")},
    }
    # shallow overlay for tests that pass nested dicts wholesale
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(body.get(key), dict):
            merged = dict(body[key])
            merged.update(value)
            body[key] = merged
        else:
            body[key] = value
    return body


class SchemaTests(unittest.TestCase):
    def test_catalog_depth(self):
        self.assertGreaterEqual(len(FRONTEND), 8)
        self.assertGreaterEqual(len(BACKEND), 8)
        self.assertGreaterEqual(len(DATABASE), 6)
        self.assertGreaterEqual(len(HOSTING), 6)
        self.assertTrue(all(not row.get("deprecated") for row in FRONTEND + BACKEND + DATABASE + HOSTING))
        self.assertGreaterEqual(len(RETIRED), 8)

    def test_output_shape(self):
        result = recommend(load_public()[0])
        for key in (
            "status", "summary", "architecture_style", "stack",
            "estimated_monthly_cost_usd", "warnings", "assumptions", "validation_errors",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["validation_errors"], [])
        for layer in ("frontend", "backend", "database", "hosting"):
            comp = result["stack"][layer]
            self.assertTrue(comp["choice"])
            self.assertTrue(comp["justification"])
            self.assertGreaterEqual(len(comp["driven_by"]), 1)
            self.assertGreaterEqual(len(comp["alternatives"]), 1)
            self.assertIn("why_not", comp["alternatives"][0])
        cost = result["estimated_monthly_cost_usd"]
        self.assertLessEqual(cost["min"], cost["max"])
        self.assertIsInstance(cost["assumptions"], list)

    def test_deterministic_and_name_independent(self):
        raw = load_public()[1]
        first = recommend(raw)
        second = recommend(deepcopy(raw))
        self.assertEqual(first, second)
        mutated = deepcopy(raw)
        mutated["scenario_id"] = "HIDDEN-9"
        mutated["project"]["name"] = "Another Name"
        other = recommend(mutated)
        self.assertEqual(choices(first), choices(other))

    def test_no_retired_products_in_public_choices(self):
        for raw in load_public():
            result = recommend(raw)
            stack = result["stack"]
            names = [stack[key]["choice"] for key in ("frontend", "backend", "database", "hosting")]
            names += [item["choice"] for item in stack.get("supporting") or []]
            blob = " | ".join(names)
            for banned in BANNED:
                self.assertNotIn(banned, blob)
            self.assertNotIn("Kubernetes", blob)
            self.assertNotIn("EKS", blob)


class PublicScenarioTests(unittest.TestCase):
    def setUp(self):
        self.rows = {row["scenario_id"]: recommend(row) for row in load_public()}

    def test_p1_static_and_free(self):
        row = self.rows["P1"]
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["architecture_style"], "static")
        self.assertEqual(row["stack"]["backend"]["choice"], "None")
        self.assertEqual(row["stack"]["database"]["choice"], "None")
        self.assertIn("Astro", row["stack"]["frontend"]["choice"])
        self.assertEqual(row["estimated_monthly_cost_usd"]["max"], 0)
        self.assertNotIn("microservices", row["architecture_style"])

    def test_p2_india_marketplace(self):
        row = self.rows["P2"]
        blob = json.dumps(row["stack"])
        self.assertIn("BLR1", blob)
        self.assertIn("NestJS", row["stack"]["backend"]["choice"])
        self.assertIn("PostgreSQL", row["stack"]["database"]["choice"])
        self.assertIn("Expo", row["stack"]["frontend"]["choice"])
        self.assertTrue(any(item["layer"] == "payments" and "Razorpay" in item["choice"] for item in row["stack"]["supporting"]))
        self.assertNotEqual(row["architecture_style"], "microservices")
        self.assertLessEqual(row["estimated_monthly_cost_usd"]["min"], 150)
        self.assertIn("DPDP", row["warnings"][0]["code"] + "".join(w["code"] for w in row["warnings"]))

    def test_p3_eu_realtime(self):
        row = self.rows["P3"]
        blob = json.dumps(row)
        self.assertIn("Frankfurt", blob)
        self.assertIn("Go", row["stack"]["backend"]["choice"])
        self.assertIn("React", row["stack"]["frontend"]["choice"])
        self.assertTrue(any(item["layer"] == "realtime" for item in row["stack"]["supporting"]))
        names = " ".join(item["choice"] for item in row["stack"]["supporting"])
        self.assertIn("Stripe", names)
        self.assertNotIn("Razorpay", names)

    def test_p4_aws_india_fintech(self):
        row = self.rows["P4"]
        blob = json.dumps(row["stack"])
        self.assertIn("ap-south-1", blob)
        self.assertIn("Spring Boot", row["stack"]["backend"]["choice"])
        self.assertIn("PostgreSQL", row["stack"]["database"]["choice"])
        self.assertIn("ECS", row["stack"]["hosting"]["choice"])
        self.assertIn("Compose", row["stack"]["frontend"]["choice"])
        joined = json.dumps(row["stack"]["supporting"])
        self.assertIn("Razorpay", joined)
        self.assertIn("SageMaker", joined)
        self.assertIn("RBI_BACKUPS", "".join(w["code"] for w in row["warnings"]))
        self.assertNotIn("DigitalOcean", blob)
        self.assertLess(row["estimated_monthly_cost_usd"]["min"], 6000)

    def test_p5_reuses_entra_and_sqlserver(self):
        row = self.rows["P5"]
        blob = json.dumps(row)
        self.assertIn("SQL Server 2019", row["stack"]["database"]["choice"])
        self.assertIn("Entra", blob)
        self.assertIn("Razor Pages", row["stack"]["frontend"]["choice"])
        self.assertIn("Azure App Service", row["stack"]["hosting"]["choice"])
        self.assertIn("Central India", blob)
        self.assertIn("EOL_EXISTING_SYSTEM", "".join(w["code"] for w in row["warnings"]))
        self.assertNotEqual(row["architecture_style"], "microservices")

    def test_p6_offline_android(self):
        row = self.rows["P6"]
        blob = json.dumps(row["stack"])
        self.assertIn("Expo", row["stack"]["frontend"]["choice"])
        self.assertIn("FastAPI", row["stack"]["backend"]["choice"])
        self.assertIn("SQLite on the device", blob)
        self.assertIn("BLR1", blob)
        self.assertNotIn("Realm", " ".join(item["choice"] for item in row["stack"]["supporting"]))
        codes = "".join(w["code"] for w in row["warnings"])
        self.assertIn("LOW_END_DEVICE", codes)
        self.assertIn("LOW_BANDWIDTH_MEDIA", codes)


class EdgeTests(unittest.TestCase):
    def test_invalid_values_do_not_crash(self):
        result = recommend({
            "project": {"type": "Web_App", "platforms": ["Web", 3]},
            "scale": {"users_at_launch": -1, "users_12_months": "many"},
            "team": {"size": True, "experience": "Beginner", "languages": "python"},
            "budget": {"monthly_infra_usd": -4},
            "timeline": {"mvp_weeks": 0},
            "priorities": {"cost": 0, "security": 9, "nope": 3},
            "compliance": "gdpr",
        })
        self.assertEqual(result["status"], "invalid_input")
        self.assertIsNone(result["stack"])
        fields = {item["field"] for item in result["validation_errors"]}
        self.assertIn("project.type", fields)
        self.assertIn("scale.users_at_launch", fields)
        self.assertIn("priorities.cost", fields)
        self.assertIn("budget.monthly_infra_usd", fields)

    def test_missing_required(self):
        result = recommend({"project": {"description": "hello"}})
        self.assertEqual(result["status"], "invalid_input")
        self.assertTrue(result["validation_errors"])

    def test_garbage_and_list_root(self):
        self.assertEqual(recommend("nope")["status"], "invalid_input")
        self.assertEqual(recommend([])["status"], "invalid_input")
        self.assertEqual(recommend(None)["status"], "invalid_input")

    def test_defaults_recorded(self):
        raw = base()
        raw.pop("priorities")
        result = recommend(raw)
        self.assertEqual(result["status"] in {"ok", "ok_with_warnings", "infeasible"}, True)
        joined = " ".join(result["assumptions"])
        self.assertIn("priorities", joined)
        self.assertIn("operations.on_call", joined)

    def test_budget_zero_fintech_is_explicit(self):
        raw = base(
            project={"name": "Big", "type": "fintech", "platforms": ["web", "android"], "description": "upi loans ledger"},
            scale={"users_at_launch": 100000, "users_12_months": 1000000, "peak_concurrent_users": 20000, "data_volume_gb_12_months": 400, "traffic_pattern": "spiky", "workload": "balanced"},
            team={"size": 6, "experience": "senior", "languages": ["java", "kotlin"], "has_devops": True},
            budget={"monthly_infra_usd": 0},
            timeline={"mvp_weeks": 20},
            infrastructure={"cloud_preference": "aws", "deployment_model": "managed_cloud", "data_residency": "india", "existing_systems": []},
            requirements={"payments": True, "auth": "phone_otp", "ml_features": "inference_api", "availability": "99.95", "realtime": False, "offline_support": False, "full_text_search": False, "file_media_storage": True, "multi_tenant": False, "seo_critical": False, "p95_latency_ms": 300},
            compliance=["rbi_localisation", "pci_dss", "dpdp"],
        )
        result = recommend(raw)
        self.assertEqual(result["status"], "infeasible")
        self.assertIsNotNone(result["stack"])
        self.assertIn("BUDGET_EXCEEDED", [w["code"] for w in result["warnings"]])
        self.assertIn("ap-south-1", json.dumps(result["stack"]))
        self.assertGreater(result["estimated_monthly_cost_usd"]["min"], 0)

    def test_airgap_drops_saas(self):
        raw = base(
            infrastructure={"deployment_model": "air_gapped", "cloud_preference": "any", "data_residency": "india", "existing_systems": ["SQL Server 2012", "Fauna"]},
            requirements={"auth": "social", "payments": True, "realtime": False, "offline_support": False, "full_text_search": False, "file_media_storage": False, "multi_tenant": False, "ml_features": "none", "seo_critical": False, "availability": "99", "p95_latency_ms": None},
            budget={"monthly_infra_usd": 0},
        )
        result = recommend(raw)
        blob = json.dumps(result["stack"])
        self.assertEqual(result["status"], "infeasible")
        self.assertIn("Docker Compose", result["stack"]["hosting"]["choice"])
        for banned in ("Razorpay", "Stripe", "Vercel", "Cloudflare", "Firebase", "Fauna", "Auth.js"):
            self.assertNotIn(banned, blob)
        self.assertNotIn("SQL Server 2012", result["stack"]["database"]["choice"])
        codes = [w["code"] for w in result["warnings"]]
        self.assertIn("AIRGAP_PAYMENTS", codes)
        self.assertIn("AIRGAP_SOCIAL_AUTH", codes)
        self.assertIn("EOL_NOT_REUSED", codes)

    def test_skill_php_stays_on_php(self):
        raw = base(
            project={"name": "Shop", "type": "ecommerce", "platforms": ["web"], "description": ""},
            team={"size": 2, "experience": "intermediate", "languages": ["php", "sql"], "has_devops": False},
            requirements={"auth": "email_password", "payments": True, "seo_critical": True, "realtime": False, "offline_support": False, "full_text_search": False, "file_media_storage": False, "multi_tenant": False, "ml_features": "none", "availability": "99.9", "p95_latency_ms": None},
        )
        result = recommend(raw)
        self.assertIn("Laravel", result["stack"]["backend"]["choice"])
        self.assertNotIn("Spring", result["stack"]["backend"]["choice"])
        self.assertNotIn("SKILL_GAP", [w["code"] for w in result["warnings"]])

    def test_hipaa_avoids_hosts_without_baa(self):
        raw = base(
            project={"name": "Clinic", "type": "healthtech", "platforms": ["web"], "description": ""},
            infrastructure={"cloud_preference": "any", "deployment_model": "managed_cloud", "data_residency": "us", "existing_systems": []},
            compliance=["hipaa"],
            team={"size": 4, "experience": "senior", "languages": ["python"], "has_devops": True},
            budget={"monthly_infra_usd": 800},
        )
        result = recommend(raw)
        host = result["stack"]["hosting"]["choice"]
        self.assertNotIn("DigitalOcean", host)
        self.assertNotIn("Vercel", host)
        self.assertNotIn("Cloudflare", host)
        self.assertTrue(any(token in host for token in ("Amazon", "Google", "Azure")))

    def test_lock_in_low_skips_dynamodb(self):
        raw = base(
            team={"size": 4, "experience": "senior", "languages": ["java"], "has_devops": True, "vendor_lock_in_tolerance": "low"},
            infrastructure={"cloud_preference": "aws", "deployment_model": "managed_cloud", "data_residency": "us", "existing_systems": []},
            budget={"monthly_infra_usd": 400},
        )
        result = recommend(raw)
        self.assertNotIn("DynamoDB", result["stack"]["database"]["choice"])

    def test_llm_flag_does_not_change_stack(self):
        raw = load_public()[2]
        os.environ["STACKSENSE_LLM"] = "on"
        try:
            on = choices(recommend(raw))
        finally:
            os.environ["STACKSENSE_LLM"] = "off"
        off = choices(recommend(raw))
        self.assertEqual(on, off)

    def test_unknown_field_is_assumption_not_error(self):
        raw = base()
        raw["judge_secret"] = {"hello": 1}
        result = recommend(raw)
        self.assertEqual(result["validation_errors"], [])
        self.assertTrue(any("judge_secret" in line for line in result["assumptions"]))


if __name__ == "__main__":
    unittest.main()
