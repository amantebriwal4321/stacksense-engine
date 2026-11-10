const ENUMS = {
  type: ["content_site", "web_app", "saas_b2b", "ecommerce", "marketplace", "social", "realtime_collab", "fintech", "healthtech", "data_analytics", "iot", "ai_ml_product", "internal_tool", "gaming", "api_platform", "other"],
  traffic_pattern: ["steady", "spiky", "seasonal"],
  workload: ["read_heavy", "balanced", "write_heavy"],
  experience: ["beginner", "intermediate", "senior", "mixed"],
  cloud_preference: ["any", "aws", "gcp", "azure", "none"],
  deployment_model: ["managed_cloud", "self_hosted_cloud_vm", "on_premise", "air_gapped"],
  data_residency: ["none", "india", "eu", "us", "other"],
  auth: ["none", "email_password", "social", "phone_otp", "enterprise_sso"],
  ml_features: ["none", "inference_api", "llm_rag", "training"],
  availability: ["99", "99.9", "99.95", "99.99"],
  geographic_spread: ["", "local", "national", "multi_region"],
  vendor_lock_in_tolerance: ["low", "medium", "high"],
  sensitivity: ["", "public", "internal", "confidential", "restricted"],
};
const PLATFORMS = ["web", "android", "ios", "desktop", "api_only"];
const BOOLS = ["realtime", "offline_support", "full_text_search", "file_media_storage", "payments", "multi_tenant", "seo_critical"];
const COMPLIANCE = ["gdpr", "dpdp", "hipaa", "pci_dss", "rbi_localisation", "soc2", "iso27001"];
const PRIORITIES = ["cost", "time_to_market", "scalability", "performance", "maintainability", "security"];

const form = document.getElementById("form");
let lastResult = null;
let bundle = null;
let bundleIndex = 0;

function fillSelect(name, values, selected) {
  const el = form.elements[name];
  el.innerHTML = values.map((v) => `<option value="${v}">${v || "(derive)"}</option>`).join("");
  if (selected != null) el.value = selected;
}

function checks(id, names, group) {
  document.getElementById(id).innerHTML = names.map((name) =>
    `<label><input type="checkbox" data-group="${group}" value="${name}"> ${name}</label>`
  ).join("");
}

fillSelect("type", ENUMS.type, "content_site");
fillSelect("traffic_pattern", ENUMS.traffic_pattern, "steady");
fillSelect("workload", ENUMS.workload, "read_heavy");
fillSelect("experience", ENUMS.experience, "beginner");
fillSelect("cloud_preference", ENUMS.cloud_preference, "any");
fillSelect("deployment_model", ENUMS.deployment_model, "managed_cloud");
fillSelect("data_residency", ENUMS.data_residency, "none");
fillSelect("auth", ENUMS.auth, "none");
fillSelect("ml_features", ENUMS.ml_features, "none");
fillSelect("availability", ENUMS.availability, "99");
fillSelect("geographic_spread", ENUMS.geographic_spread, "");
fillSelect("vendor_lock_in_tolerance", ENUMS.vendor_lock_in_tolerance, "medium");
fillSelect("sensitivity", ENUMS.sensitivity, "");
checks("platforms", PLATFORMS, "platform");
checks("bools", BOOLS, "bool");
checks("compliance", COMPLIANCE, "compliance");
document.querySelector('input[data-group="platform"][value="web"]').checked = true;
document.querySelector('input[data-group="bool"][value="seo_critical"]').checked = true;
document.getElementById("priorities").innerHTML = PRIORITIES.map((key) =>
  `<label>${key}</label><input name="prio_${key}" type="number" min="1" max="5" value="3">`
).join("");

function checked(group) {
  return [...document.querySelectorAll(`input[data-group="${group}"]:checked`)].map((el) => el.value);
}

function setChecked(group, values) {
  const want = new Set(values || []);
  document.querySelectorAll(`input[data-group="${group}"]`).forEach((el) => {
    el.checked = want.has(el.value);
  });
}

function num(name) {
  const raw = form.elements[name].value;
  if (raw === "") return null;
  return Number(raw);
}

function collect() {
  const languages = form.elements.languages.value.split(",").map((s) => s.trim()).filter(Boolean);
  const licences = form.elements.existing_licences.value.split(",").map((s) => s.trim()).filter(Boolean);
  const systems = form.elements.existing_systems.value.split("\n").map((s) => s.trim()).filter(Boolean);
  const body = {
    project: {
      name: form.elements.name.value,
      type: form.elements.type.value,
      description: form.elements.description.value,
      platforms: checked("platform"),
    },
    scale: {
      users_at_launch: num("users_at_launch"),
      users_12_months: num("users_12_months"),
      peak_concurrent_users: num("peak_concurrent_users"),
      traffic_pattern: form.elements.traffic_pattern.value,
      workload: form.elements.workload.value,
      data_volume_gb_12_months: num("data_volume_gb_12_months"),
    },
    team: {
      size: num("size"),
      experience: form.elements.experience.value,
      languages,
      has_devops: form.elements.has_devops.checked,
      vendor_lock_in_tolerance: form.elements.vendor_lock_in_tolerance.value,
    },
    budget: {
      monthly_infra_usd: num("monthly_infra_usd"),
      existing_licences: licences,
    },
    timeline: { mvp_weeks: num("mvp_weeks") },
    infrastructure: {
      cloud_preference: form.elements.cloud_preference.value,
      deployment_model: form.elements.deployment_model.value,
      data_residency: form.elements.data_residency.value,
      existing_systems: systems,
    },
    requirements: {
      realtime: false, offline_support: false, full_text_search: false,
      file_media_storage: false, payments: false, multi_tenant: false, seo_critical: false,
      auth: form.elements.auth.value,
      ml_features: form.elements.ml_features.value,
      availability: form.elements.availability.value,
      p95_latency_ms: num("p95_latency_ms"),
    },
    compliance: checked("compliance"),
    priorities: Object.fromEntries(PRIORITIES.map((key) => [key, num("prio_" + key)])),
    operations: { on_call: form.elements.on_call.checked },
  };
  BOOLS.forEach((key) => {
    body.requirements[key] = checked("bool").includes(key);
  });
  const spread = form.elements.geographic_spread.value;
  if (spread) body.scale.geographic_spread = spread;
  const rps = num("expected_rps_peak");
  if (rps != null) body.requirements.expected_rps_peak = rps;
  const sensitivity = form.elements.sensitivity.value;
  if (sensitivity) body.data = { sensitivity };
  if (lastScenarioId) body.scenario_id = lastScenarioId;
  return body;
}

let lastScenarioId = null;

function applyScenario(data) {
  lastScenarioId = data.scenario_id || null;
  const p = data.project || {};
  form.elements.name.value = p.name || "";
  if (p.type) form.elements.type.value = p.type;
  form.elements.description.value = p.description || "";
  setChecked("platform", p.platforms || []);
  const s = data.scale || {};
  ["users_at_launch", "users_12_months", "peak_concurrent_users", "data_volume_gb_12_months"].forEach((key) => {
    if (s[key] != null) form.elements[key].value = s[key];
  });
  if (s.traffic_pattern) form.elements.traffic_pattern.value = s.traffic_pattern;
  if (s.workload) form.elements.workload.value = s.workload;
  form.elements.geographic_spread.value = s.geographic_spread || "";
  const t = data.team || {};
  if (t.size != null) form.elements.size.value = t.size;
  if (t.experience) form.elements.experience.value = t.experience;
  form.elements.languages.value = (t.languages || []).join(", ");
  form.elements.has_devops.checked = !!t.has_devops;
  if (t.vendor_lock_in_tolerance) form.elements.vendor_lock_in_tolerance.value = t.vendor_lock_in_tolerance;
  const b = data.budget || {};
  if (b.monthly_infra_usd != null) form.elements.monthly_infra_usd.value = b.monthly_infra_usd;
  form.elements.existing_licences.value = (b.existing_licences || []).join(", ");
  if (data.timeline && data.timeline.mvp_weeks != null) form.elements.mvp_weeks.value = data.timeline.mvp_weeks;
  const i = data.infrastructure || {};
  ["cloud_preference", "deployment_model", "data_residency"].forEach((key) => {
    if (i[key]) form.elements[key].value = i[key];
  });
  form.elements.existing_systems.value = (i.existing_systems || []).join("\n");
  const r = data.requirements || {};
  setChecked("bool", BOOLS.filter((key) => r[key]));
  ["auth", "ml_features", "availability"].forEach((key) => {
    if (r[key]) form.elements[key].value = r[key];
  });
  form.elements.p95_latency_ms.value = r.p95_latency_ms == null ? "" : r.p95_latency_ms;
  form.elements.expected_rps_peak.value = r.expected_rps_peak == null ? "" : r.expected_rps_peak;
  setChecked("compliance", data.compliance || []);
  const pr = data.priorities || {};
  PRIORITIES.forEach((key) => {
    form.elements["prio_" + key].value = pr[key] == null ? 3 : pr[key];
  });
  form.elements.on_call.checked = !!(data.operations && data.operations.on_call);
  form.elements.sensitivity.value = (data.data && data.data.sensitivity) || "";
}

function esc(text) {
  return String(text ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function render(result) {
  lastResult = result;
  const root = document.getElementById("result");
  if (Array.isArray(result)) {
    bundle = result;
    root.innerHTML = `<h1>${result.length} scenarios</h1><p>The file was a list. Showing the first. Use the buttons to move.</p>
      <p><button type="button" id="prev">Previous</button> <button type="button" id="next">Next</button></p><div id="one"></div>`;
    document.getElementById("prev").onclick = () => showBundle(-1);
    document.getElementById("next").onclick = () => showBundle(1);
    bundleIndex = 0;
    document.getElementById("one").innerHTML = oneResult(result[0]);
    return;
  }
  bundle = null;
  root.innerHTML = oneResult(result);
}

function showBundle(step) {
  bundleIndex = (bundleIndex + step + bundle.length) % bundle.length;
  document.getElementById("one").innerHTML = oneResult(bundle[bundleIndex]);
  lastResult = bundle[bundleIndex];
}

function oneResult(result) {
  const status = result.status || "unknown";
  const klass = status === "ok" ? "ok" : status === "ok_with_warnings" ? "warn" : "bad";
  const stack = result.stack;
  let layers = "";
  if (stack) {
    layers = ["frontend", "backend", "database", "hosting"].map((key) => layerCard(key, stack[key])).join("");
  }
  const supporting = (stack && stack.supporting || []).map((item) => `
    <article>
      <div><span class="tag">${esc(item.layer)}</span><strong>${esc(item.choice)}</strong></div>
      <p>${esc(item.justification)}</p>
    </article>`).join("");
  const warnings = (result.warnings || []).map((w) => `
    <div class="warn ${esc(w.severity)}"><b>${esc(w.severity)} ${esc(w.code)}</b><div>${esc(w.message)}</div></div>`).join("");
  const errors = (result.validation_errors || []).map((e) => `<li><code>${esc(e.field)}</code> ${esc(e.message)}</li>`).join("");
  const assumptions = (result.assumptions || []).map((a) => `<li>${esc(a)}</li>`).join("");
  const cost = result.estimated_monthly_cost_usd || { min: 0, max: 0, assumptions: [] };
  return `
    <div class="badges">
      <span class="badge ${klass}">${esc(status)}</span>
      <span class="badge">${esc(result.architecture_style || "")}</span>
      <span class="badge">${esc(result.deployment_region || "no region")}</span>
      <span class="badge">${esc(result.scenario_id || "ad hoc")}</span>
    </div>
    <h1>${esc((stack && result.summary) ? titleFrom(result) : "No stack")}</h1>
    <p class="summary">${esc(result.summary || "")}</p>
    ${stack ? `<div class="layers">${layers}</div>` : `<div class="card"><h2>Validation</h2><ul>${errors || "<li>None</li>"}</ul></div>`}
    ${stack ? `<div class="card"><h2>Monthly cost, USD</h2><p class="cost">${cost.min} to ${cost.max} <small>order of magnitude</small></p><ul class="assumptions">${(cost.assumptions || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>` : ""}
    <div class="card"><h2>Warnings</h2><div class="warn-list">${warnings || '<p class="empty">None</p>'}</div></div>
    ${supporting ? `<div class="card"><h2>Supporting</h2><div class="support">${supporting}</div></div>` : ""}
    ${errors && stack ? "" : ""}
    <div class="card"><h2>Assumptions</h2><ul class="assumptions">${assumptions || "<li>None</li>"}</ul></div>
    ${errors ? `<div class="card"><h2>Validation errors</h2><ul>${errors}</ul></div>` : ""}
  `;
}

function titleFrom(result) {
  const line = result.summary || "";
  const cut = line.indexOf(" should ");
  return cut > 0 ? line.slice(0, cut) : (result.scenario_id || "Recommendation");
}

function layerCard(key, comp) {
  if (!comp) return "";
  const alts = (comp.alternatives || []).map((a) => `<li><strong>${esc(a.choice)}</strong>: ${esc(a.why_not)}</li>`).join("");
  const trades = (comp.tradeoffs || []).map((t) => `<li>${esc(t)}</li>`).join("");
  return `<article class="layer"><div class="k">${key}</div><h3>${esc(comp.choice)}</h3><p>${esc(comp.justification)}</p>
    ${alts ? `<ul>${alts}</ul>` : ""} ${trades ? `<ul>${trades}</ul>` : ""}</article>`;
}

async function recommend(body) {
  const res = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  render(data);
}

document.getElementById("run").onclick = () => recommend(collect());
document.getElementById("export").onclick = () => {
  const payload = lastResult || { status: "invalid_input", summary: "Nothing to export yet." };
  const blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], { type: "application/json" });
  const a = document.createElement("a");
  const sid = payload.scenario_id || "stacksense";
  a.href = URL.createObjectURL(blob);
  a.download = `${sid}_output.json`;
  a.click();
};
document.getElementById("import").onchange = async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  const text = await file.text();
  let data;
  try { data = JSON.parse(text); } catch (err) {
    render({ status: "invalid_input", summary: "That file is not JSON.", validation_errors: [{ field: "(file)", message: String(err) }], warnings: [], assumptions: [], stack: null, architecture_style: "other", estimated_monthly_cost_usd: { min: 0, max: 0, assumptions: [] } });
    return;
  }
  if (Array.isArray(data)) {
    if (data[0]) applyScenario(data[0]);
    recommend(data);
    return;
  }
  applyScenario(data);
  recommend(data);
};
document.getElementById("llm").onchange = () => {
  const on = document.getElementById("llm").checked;
  document.getElementById("llm-note").textContent = on
    ? "Ticked, and still no model call. Explanations stay the engine text. Untick to match the default judges will use."
    : "Off. This build has no model client. The stack does not change if you tick it.";
};

const params = new URLSearchParams(location.search);
const scenario = params.get("scenario");
if (params.get("view") === "result") document.getElementById("layout").classList.add("result-only");
if (scenario) {
  fetch("/scenarios/" + scenario + ".json").then((r) => r.json()).then((data) => {
    applyScenario(data);
    if (params.get("autorun") === "1" || params.get("view") === "result") recommend(data);
  }).catch(() => {
    document.getElementById("result").textContent = "Could not load " + scenario;
  });
}
