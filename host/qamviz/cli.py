from __future__ import annotations
import argparse, json, os
from pathlib import Path
from .instruments.scope_rigol import doctor as scope_doctor, capture_channel, riglol
from .analysis import load_iq, sample_symbols, compute_evm
from .plots import plot_constellation, plot_iq_time
from .session import write_manifest, now_utc

DEFAULT_RESOURCE = "usb:0x1AB1:0x04CE"

def cmd_doctor(args):
    info = scope_doctor(args.resource)
    print(json.dumps(info, indent=2))
    return 0 if info.get("usb_list_rc", 1) == 0 else 1

def _pre_capture(resource: str):
    # Ensure YT mode for waveform capture; ignore errors.
    for c in [":TIM:MODE MAIN", ":RUN"]:
        riglol("scpi", "--usb", "--timeout", "10", resource, c, timeout=15)

def cmd_capture(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _pre_capture(args.resource)
    ch1 = out / "ch1.npy"
    ch2 = out / "ch2.npy"
    c1 = capture_channel(args.resource, "CHAN1", ch1, points=args.points)
    c2 = capture_channel(args.resource, "CHAN2", ch2, points=args.points)
    manifest = {
        "schema": "qamviz.session/0",
        "created_utc": now_utc(),
        "resource": args.resource,
        "captures": [c1, c2],
        "config": {"points": args.points, "sps": args.sps, "preset": args.preset},
    }
    if c1["rc"] != 0 or c2["rc"] != 0:
        manifest["status"] = "capture_failed"
        write_manifest(out, manifest)
        print(json.dumps(manifest, indent=2))
        return 1
    t, z = load_iq(str(ch1), str(ch2))
    plot_iq_time(t, z, out / "iq-time.png")
    syms = sample_symbols(z, sps=args.sps)
    metrics, sym_aligned, _ref = compute_evm(syms)
    plot_constellation(sym_aligned, out / "constellation.png", title=f"Constellation EVM={metrics['evm_percent']:.2f}% n={metrics['n']}")
    manifest["metrics"] = metrics
    manifest["artifacts"] = {
        "ch1": "ch1.npy", "ch2": "ch2.npy",
        "iq_time": "iq-time.png", "constellation": "constellation.png",
    }
    manifest["status"] = "ok"
    p = write_manifest(out, manifest)
    print(json.dumps({"ok": True, "out": str(out), "manifest": str(p), "metrics": metrics}, indent=2))
    return 0

def main(argv=None):
    ap = argparse.ArgumentParser(prog="qamviz")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("doctor", help="Check riglol and instrument identity")
    d.add_argument("--resource", default=DEFAULT_RESOURCE)
    d.set_defaults(func=cmd_doctor)

    c = sub.add_parser("capture", help="Capture CH1/CH2 and generate constellation/EVM artifacts")
    c.add_argument("--resource", default=DEFAULT_RESOURCE)
    c.add_argument("--out", required=True)
    c.add_argument("--points", type=int, default=1200)
    c.add_argument("--sps", type=int, default=8)
    c.add_argument("--preset", default="lab16qam")
    c.set_defaults(func=cmd_capture)

    args = ap.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())