"""Command line entry points."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from stacksense import __version__
from stacksense.decide import recommend
from stacksense.kb import catalog_markdown


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "help"}:
        _print_help()
        return 0
    cmd = args[0]
    if cmd == "version":
        print(__version__)
        return 0
    if cmd == "catalog":
        target = Path(args[1]) if len(args) > 1 else Path("knowledge/CATALOG.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(catalog_markdown(), encoding="utf-8")
        print(f"wrote {target}")
        return 0
    if cmd == "serve":
        from stacksense.server import serve
        serve()
        return 0
    if cmd == "recommend":
        return _recommend_cli(args[1:])
    print(f"unknown command: {cmd}", file=sys.stderr)
    _print_help()
    return 1


def _print_help() -> None:
    print(
        "\n".join([
            "StackSense, a deterministic stack picker.",
            "",
            "  python -m stacksense recommend INPUT.json OUTPUT.json",
            "  python -m stacksense recommend INPUT.json OUTPUT_DIR",
            "  python -m stacksense recommend scenarios/public.json outputs",
            "  python -m stacksense serve",
            "  python -m stacksense catalog",
            "",
            "Exit codes: 0 ok or warnings, 2 infeasible, 3 invalid input, 1 usage error.",
            "STACKSENSE_LLM defaults to off. This build has no model client either way.",
        ])
    )


def _load(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"_error": f"Could not read {path}: {exc}"}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        return {"_error": f"Invalid JSON in {path}: {exc.msg} at line {exc.lineno}."}


def _recommend_cli(args: list[str]) -> int:
    if len(args) < 2:
        print("usage: python -m stacksense recommend INPUT.json OUTPUT.json", file=sys.stderr)
        return 1
    source = Path(args[0])
    dest = Path(args[1])
    raw = _load(source)
    if isinstance(raw, dict) and "_error" in raw and len(raw) == 1:
        result = {
            "scenario_id": None,
            "engine_version": __version__,
            "status": "invalid_input",
            "summary": raw["_error"],
            "architecture_style": "other",
            "deployment_region": None,
            "stack": None,
            "estimated_monthly_cost_usd": {"min": 0, "max": 0, "assumptions": []},
            "warnings": [],
            "assumptions": [],
            "validation_errors": [{"field": "(file)", "message": raw["_error"]}],
        }
        _write_one(dest, result)
        return 3
    if isinstance(raw, list):
        results = [recommend(item) for item in raw]
        _write_many(dest, results)
        return _exit_for(results)
    result = recommend(raw)
    _write_one(dest, result)
    return _exit_for([result])


def _exit_for(results: list[dict]) -> int:
    statuses = {item.get("status") for item in results}
    if "invalid_input" in statuses:
        return 3
    if "infeasible" in statuses:
        return 2
    return 0


def _write_one(dest: Path, result: dict) -> None:
    if dest.exists() and dest.is_dir():
        _write_many(dest, [result])
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {dest} ({result.get('status')})")


def _write_many(dest: Path, results: list[dict]) -> None:
    if dest.suffix == ".json":
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {dest}")
        return
    dest.mkdir(parents=True, exist_ok=True)
    for result in results:
        sid = result.get("scenario_id") or "result"
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(sid))
        path = dest / f"{safe}_output.json"
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        fe = (result.get("stack") or {}).get("frontend", {}) if result.get("stack") else {}
        be = (result.get("stack") or {}).get("backend", {}) if result.get("stack") else {}
        print(f"wrote {path} ({result.get('status')}) {fe.get('choice', '')} / {be.get('choice', '')}")


if __name__ == "__main__":
    sys.exit(main())
