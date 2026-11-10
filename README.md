# StackSense

StackSense recommends a tech stack from a structured project brief. It picks a frontend, a backend, a database, a host, and the supporting pieces the brief actually needs (cache, queue, search, auth, storage, CDN, realtime, payments, ML, CI, observability). Every choice is a score over a curated catalog, after hard filters for cloud, residency, deployment, and compliance. The same JSON in is the same JSON out. A language model is not in that path, and this build does not ship one.

## Architecture

```
scenario JSON
    |
    v
[ validate ] -> [ hard constraints ] -> [ score the catalog ]
 defaults         residency, cloud       frontend, backend,
 errors           deploy, compliance     database, hosting
    |
    v
warnings, cost band, output JSON
```

`stacksense/validate.py` checks types, enums, ranges, and missing fields. Bad input returns `invalid_input` and a null stack. It does not crash.

`stacksense/decide.py` applies hard constraints first (data residency, compliance, deployment model, cloud preference). What survives is scored with weights taken from `priorities`. Ties break on a stable id, so there is no randomness.

`stacksense/kb.py` is the catalog: strengths, cost tier, ops burden, regions, and the doc URL behind each row. `stacksense/costing.py` turns the winner into a monthly USD band. `stacksense/existing.py` reads systems you already run and flags end of life.

`stacksense/cli.py` and `stacksense/server.py` are thin. They call the same function the tests call. The browser UI is static files under `web/`.

## Technology and versions

- Language: Python 3.11 or newer. Developed and tested on 3.12.3.
- Engine libraries: none. The standard library only.
- UI: HTML, CSS, and JavaScript. No build step.
- Container: Docker image `python:3.12-slim`, optional.
- Tests: `unittest` from the standard library.

Engine version is `1.0.0` (`stacksense/__init__.py`).

## Prerequisites

- Python 3.11+ on Linux, macOS, or Windows.
- A browser, if you want the form. The CLI does not need one.
- Docker and Docker Compose, only if you use the container path.

No API key, no paid account, no `pip install`.

## Setup and run

From the repo root:

```
python -m stacksense serve
```

Open http://127.0.0.1:8000

The form starts with a small content site so Recommend does something useful immediately. Import replaces it. Export downloads the result JSON.

Port and bind address:

```
STACKSENSE_HOST=127.0.0.1
STACKSENSE_PORT=8000
```

Windows (PowerShell) is the same command once `python` is on PATH. macOS and Linux too.

Container:

```
docker compose build
docker compose up
```

Then open http://127.0.0.1:8000 . This is Compose v2. The service listens on 8000. If your `python` command is missing, use `python3` everywhere below. On Windows the command is usually `python`.

## Run a scenario file

One scenario, one file:

```
python -m stacksense recommend scenarios/P2.json outputs/P2_output.json
```

All six public scenarios (the file is a JSON list, which the CLI accepts):

```
python -m stacksense recommend scenarios/public.json outputs
```

That writes `outputs/P1_output.json` through `outputs/P6_output.json`. A single object written to a directory uses `<scenario_id>_output.json`.

Exit codes: `0` for `ok` and `ok_with_warnings`, `2` for `infeasible`, `3` for `invalid_input`.

The UI import button takes the same files, including the list. The API is `POST /api/recommend` with the scenario JSON. `GET /api/health` reports the version and that no model was called.

Edge files live in `scenarios/edge/` (missing fields, bad types, a zero budget fintech, air gap, a dead SQL Server, a PHP only team).

Tests:

```
python -m unittest discover -s tests -v
```

## LLM off switch

Default is off.

```
STACKSENSE_LLM=off
```

The UI has a checkbox labelled "LLM wording". It defaults to off. Turning it on does not call a model, because this repo has no model client and no key. Explanations stay the sentences the scorer built. `STACKSENSE_LLM=on` changes nothing in the output JSON. `GET /api/health` shows `llm_called: false` either way.

There is a separate keyword pass over `project.description` (Markdown, UPI, ledger, low RAM, weak network, GPS, per seat). That pass is a fixed word list in `stacksense/signals.py`. It is not a model, and it runs whether the switch is on or off.

## Project structure

```
stacksense/          engine, CLI, HTTP server
  kb.py              catalog and retired-product list
  validate.py        schema, defaults, field errors
  decide.py          filters, scores, explanations
  costing.py         monthly USD band
  existing.py        existing systems and end of life
web/                 browser UI
scenarios/           P1 to P6, public.json, edge/
outputs/             generated P1_output.json to P6_output.json
knowledge/CATALOG.md generated table of the catalog
tests/               unittest
report/              report source and PDF
docs/screenshots/    UI captures
docs/demo_script.md  narration for a short demo
scripts/             submission folder builder
Dockerfile
docker-compose.yml
```

Extra inputs, all optional. A file with only the standard fields still runs. When they are missing, the assumption list says what was assumed.

- `scale.geographic_spread`: `local`, `national`, `multi_region`. A second region changes cost and is not allowed for RBI data outside India.
- `requirements.expected_rps_peak`: a tiny user count with a huge request rate should not land on a 512 MB box.
- `team.vendor_lock_in_tolerance`: `low` pushes portable Postgres over DynamoDB.
- `operations.on_call`: 99.95 and 99.99 without a human to page is a warning, not a plan.
- `data.sensitivity`: `public`, `internal`, `confidential`, `restricted`. Drives encryption, private buckets, and whether a CDN may see the bytes.
- `budget.existing_licences`: noted so a second directory or CI product is not assumed when you already pay for one.

## Credits

Runtime third party libraries: none.

Runtime third party APIs and datasets: none. Prices in `stacksense/costing.py` are order of magnitude notes taken from public price pages in November 2026. The engine does not fetch them.

Container base image, only if you use Docker: [python:3.12-slim](https://hub.docker.com/_/python) on Docker Hub.

The catalog cites the docs it was built from. The full table is `knowledge/CATALOG.md`. The ones that carry the recommendations:

- Astro, Next.js, Nuxt, SvelteKit, React, Vite, Angular, htmx, Eleventy, Expo, Flutter, Compose Multiplatform, Kotlin / Android, SwiftUI, Electron, Tauri
- NestJS, Fastify, FastAPI, Django, Spring Boot, ASP.NET Core and .NET 10, Laravel, Rails, Go, PocketBase, Cloudflare Workers
- PostgreSQL, MySQL, SQL Server and its lifecycle page, Azure SQL, MongoDB, SQLite, DynamoDB, CockroachDB, Firestore, Cloudflare D1, ClickHouse
- Cloudflare Pages, GitHub Pages, Netlify, Vercel, Amazon ECS, AWS Lambda, Cloud Run, Azure App Service, DigitalOcean App Platform and regional availability, Docker Compose
- Razorpay, Cashfree, Stripe, Mollie, MSG91, Twilio, Entra ID, Keycloak, Auth.js, SageMaker, Vertex AI, Azure Machine Learning, ONNX Runtime, pgvector, Yjs, Socket.IO, Valkey, ElastiCache, SQS, S3, Azure Blob, Spaces, MinIO, GitHub Actions, CloudWatch, Application Insights, Grafana, Prometheus, CloudFront, Mosquitto, expo-sqlite
- Retired, and refused: Create React App (Feb 2025), Fauna (30 May 2025), Atlas Device Sync / Realm SDKs (30 Sep 2025), Firebase Dynamic Links (25 Aug 2025), Google Cloud IoT Core, SQL Server releases past extended support. SQL Server 2019 is called out as extended support until 8 Jan 2030, not as a new build target.
- Rules the hard filters follow: [RBI storage of payment system data, 6 Apr 2018](https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11244), [DPDP Act 2023](https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf), [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj), [HHS HIPAA](https://www.hhs.gov/hipaa/for-professionals/index.html), [PCI SSC](https://www.pcisecuritystandards.org/document_library/), [ISO/IEC 27001](https://www.iso.org/standard/27001)

Screenshots and the report PDF were produced locally from this engine. They are not a library you need in order to run it.

## Demo and submission folder

`docs/demo_script.md` is the narration. `scripts/compose_demo.sh` rebuilds `demo/demo.mp4` from the screenshots of the running UI. The video has those lines burned in as captions. There is no voice track in this build.

The Drive folder from the problem statement:

```
bash scripts/package_submission.sh
```

That writes `dist/StackSense26_Aman_Tebriwal/` with `source/`, `outputs/`, and `Report_Aman_Tebriwal.pdf`, plus a zip. It skips git metadata, virtualenvs, and caches.
