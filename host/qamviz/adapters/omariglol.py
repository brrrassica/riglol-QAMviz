"""omariglol adapter for riglol-QAMviz (M3 scaffolding).

Provides workspace/measure helpers around the `riglol` CLI. This module
intentionally uses `riglol measure --json` (true parallel fan-out in
omariglol-core) and does NOT use `Workspace.batch_query()` for parallelism.

Full M3 evidence requires a tagged omariglol release containing f1cb86f and
attached instruments; this module is testable with mock measure JSON.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _riglol_bin() -> str:
    return os.environ.get("RIGLOL_BIN") or shutil.which("riglol") or os.path.expanduser("~/projects/omariglol/bin/riglol")


def riglol(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    cmd = [_riglol_bin(), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def workspace_create(name: str) -> dict[str, Any]:
    p = riglol("workspace", "create", name, timeout=30)
    return {"rc": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip(), "name": name}


def workspace_show(name: str) -> dict[str, Any]:
    p = riglol("workspace", "show", name, timeout=30)
    return {"rc": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip(), "name": name}


def measure_json(workspace: str | None = None, command: str | None = None, timeout: int = 60) -> dict[str, Any]:
    args = ["measure", "--json"]
    if workspace:
        args += ["--workspace", workspace]
    if command:
        args += ["--command", command]
    p = riglol(*args, timeout=timeout)
    out: dict[str, Any] = {
        "rc": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
        "argv": [_riglol_bin(), *args],
    }
    if p.returncode == 0 and p.stdout.strip():
        try:
            out["report"] = json.loads(p.stdout)
        except Exception as e:
            out["parse_error"] = str(e)
    return out


def parse_measure_report(report: dict[str, Any]) -> dict[str, Any]:
    """Normalize a measure report into dashboard/evidence-friendly rows."""
    results = report.get("results", []) or []
    rows = []
    for r in results:
        rows.append({
            "instrument_id": r.get("instrument_id"),
            "label": r.get("label"),
            "address": r.get("address"),
            "instrument_type": r.get("instrument_type"),
            "command": r.get("command"),
            "value": r.get("value"),
            "error": r.get("error"),
            "elapsed_ms": r.get("elapsed_ms"),
            "is_measurement": r.get("is_measurement"),
            "ok": r.get("error") is None,
        })
    elapsed = [float(r.get("elapsed_ms", 0.0) or 0.0) for r in rows]
    overall = float(report.get("elapsed_ms", 0.0) or 0.0)
    max_elapsed = max(elapsed) if elapsed else 0.0
    sum_elapsed = sum(elapsed)
    return {
        "workspace": report.get("workspace"),
        "overall_elapsed_ms": overall,
        "max_instrument_elapsed_ms": max_elapsed,
        "sum_instrument_elapsed_ms": sum_elapsed,
        # Concurrency proof heuristic: overall should be close to max, not sum.
        "parallelism_ratio": (overall / max_elapsed) if max_elapsed > 0 else None,
        "rows": rows,
        "ok_count": sum(1 for r in rows if r["ok"]),
        "fail_count": sum(1 for r in rows if not r["ok"]),
        "measured_count": sum(1 for r in rows if r["ok"] and r.get("is_measurement")),
    }


def save_measure_evidence(report: dict[str, Any], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "qamviz.measure-evidence/0.1",
        "raw_report": report,
        "summary": parse_measure_report(report),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out


def dashboard_evidence_payload(report: dict[str, Any]) -> dict[str, Any]:
    summary = parse_measure_report(report)
    return {
        "type": "omariglol.measure",
        "workspace": summary["workspace"],
        "overall_elapsed_ms": summary["overall_elapsed_ms"],
        "max_instrument_elapsed_ms": summary["max_instrument_elapsed_ms"],
        "parallelism_ratio": summary["parallelism_ratio"],
        "rows": [
            {
                "label": r["label"],
                "type": r["instrument_type"],
                "command": r["command"],
                "value": r["value"],
                "error": r["error"],
                "elapsed_ms": r["elapsed_ms"],
                "ok": r["ok"],
            }
            for r in summary["rows"]
        ],
    }