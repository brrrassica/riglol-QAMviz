#!/usr/bin/env python3
"""M3 A/B readout scaffold: sequential riglol scpi vs parallel riglol measure --json.

Requires attached instruments and a tagged omariglol release containing f1cb86f.
This script is a scaffold; it records timing evidence to artifacts/ab-readout.md.
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, time
from pathlib import Path

RIGLOL = os.environ.get("RIGLOL_BIN") or shutil.which("riglol") or os.path.expanduser("~/projects/omariglol/bin/riglol")


def run(cmd, timeout=30):
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    dt = (time.perf_counter() - t0) * 1000.0
    return {"cmd": cmd, "rc": p.returncode, "elapsed_ms": dt, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, help="Workspace name/id for riglol measure")
    ap.add_argument("--scope-resource", default="usb:0x1AB1:0x04CE")
    ap.add_argument("--vna-resource", default="usb:0x0483:0x5740")
    ap.add_argument("--out", default="artifacts/ab-readout.md")
    args = ap.parse_args()

    seq = []
    t0 = time.perf_counter()
    seq.append(run([RIGLOL, "scpi", "--usb", "--timeout", "10", args.scope_resource, "*IDN?"], timeout=20))
    seq.append(run([RIGLOL, "scpi", "--usb", "--timeout", "10", args.vna_resource, "*IDN?"], timeout=20))
    seq_total = (time.perf_counter() - t0) * 1000.0

    par = run([RIGLOL, "measure", "--json", "--workspace", args.workspace], timeout=60)
    report = None
    if par["rc"] == 0:
        try:
            report = json.loads(par["stdout"])
        except Exception:
            pass

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# M3 A/B readout", "", "## Sequential (`riglol scpi --usb`)", "", f"Total wall time: {seq_total:.1f} ms", ""]
    for r in seq:
        lines.append(f"- `{' '.join(r['cmd'])}`: rc={r['rc']} elapsed={r['elapsed_ms']:.1f} ms value={r['stdout']!r}")
    lines += ["", "## Parallel (`riglol measure --json`)", "", f"Command elapsed: {par['elapsed_ms']:.1f} ms, rc={par['rc']}", ""]
    if report:
        lines.append(f"Workspace: {report.get('workspace')} overall_elapsed_ms={report.get('elapsed_ms')}")
        for r in report.get("results", []):
            lines.append(f"- {r.get('label')} [{r.get('instrument_type')}] cmd={r.get('command')} elapsed_ms={r.get('elapsed_ms')} value={r.get('value')!r} error={r.get('error')!r}")
    else:
        lines.append(f"Raw stdout: {par['stdout'][:500]}")
        if par["stderr"]:
            lines.append(f"Stderr: {par['stderr'][:500]}")
    lines += ["", "## Notes", "", "- Expect overall parallel time ~ max(per-instrument), not sum.", "- Full proof requires tagged omariglol release containing f1cb86f and attached instruments.", ""]
    out.write_text("\n".join(lines))
    print(json.dumps({"ok": par["rc"] == 0, "out": str(out), "sequential_total_ms": seq_total, "parallel_ms": par["elapsed_ms"]}, indent=2))


if __name__ == "__main__":
    main()