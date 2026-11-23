from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path
from .instruments.scope_rigol import doctor as scope_doctor, capture_channel, riglol
from .analysis import load_iq, sync_and_sample, compute_evm, ideal_for, symbol_error_count
from .plots import plot_constellation, plot_iq_time
from .session import write_manifest, now_utc, sha256_text
from .config import get_preset, to_dict

DEFAULT_RESOURCE = "usb:0x1AB1:0x04CE"


def _git_head():
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def cmd_doctor(args):
    info = scope_doctor(args.resource)
    info["git_head"] = _git_head()
    print(json.dumps(info, indent=2))
    return 0 if info.get("usb_list_rc", 1) == 0 else 1


def _pre_capture(resource: str):
    for c in [":TIM:MODE MAIN", ":RUN"]:
        riglol("scpi", "--usb", "--timeout", "10", resource, c, timeout=15)


def _maybe_esp32_status(port: str | None):
    if not port:
        return None
    try:
        from .esp32_link import Esp32Link
        with Esp32Link(port=port) as link:
            st = link.status()
            return {"port": port, "ok": st.ok, "status": st.raw}
    except Exception as e:
        return {"port": port, "ok": False, "error": str(e)}


def cmd_capture(args):
    preset = get_preset(args.preset)
    preset.resource = args.resource
    if args.points:
        preset.points = args.points
    if args.sps:
        preset.sps = args.sps
    if args.seed is not None:
        preset.seed = args.seed
    if args.mode:
        preset.mode = args.mode
    if args.shape:
        preset.shape = args.shape

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _pre_capture(args.resource)
    ch1 = out / "ch1.npy"
    ch2 = out / "ch2.npy"
    c1 = capture_channel(args.resource, "CHAN1", ch1, points=preset.points, mode=preset.mode)
    c2 = capture_channel(args.resource, "CHAN2", ch2, points=preset.points, mode=preset.mode)
    manifest = {
        "schema": "qamviz.session/0.2",
        "created_utc": now_utc(),
        "git_head": _git_head(),
        "resource": args.resource,
        "config": to_dict(preset),
        "config_hash": sha256_text(json.dumps(to_dict(preset), sort_keys=True)),
        "esp32": _maybe_esp32_status(args.esp32_port),
        "captures": [c1, c2],
    }
    if c1["rc"] != 0 or c2["rc"] != 0:
        manifest["status"] = "capture_failed"
        write_manifest(out, manifest)
        print(json.dumps(manifest, indent=2))
        return 1

    t, z = load_iq(str(ch1), str(ch2))
    plot_iq_time(t, z, out / "iq-time.png")
    syms, sync_info = sync_and_sample(z, sps=preset.sps, modulation=preset.modulation, seed=preset.seed, shape=preset.shape)
    metrics, sym_aligned, _ref = compute_evm(syms, ideal=ideal_for(preset.modulation), modulation=preset.modulation)
    if sync_info.get("sync") == "training_corr":
        ser = symbol_error_count(sym_aligned, modulation=preset.modulation, seed=preset.seed,
                                 frame_pos0_at=sync_info.get("frame_pos0_at", 0))
        ser["ser_valid"] = True
        metrics.update({k: v for k, v in ser.items()})
    else:
        metrics.update({"symbol_errors": None, "symbol_total": int(len(sym_aligned)), "symbol_error_rate": None, "ser_valid": False, "ser_reason": "blind_sync"})
    plot_constellation(sym_aligned, out / "constellation.png",
                       title=f"{preset.modulation} EVM={metrics['evm_percent']:.2f}% n={metrics['n']}",
                       modulation=preset.modulation)
    manifest["sync"] = sync_info
    manifest["metrics"] = metrics
    manifest["artifacts"] = {"ch1": "ch1.npy", "ch2": "ch2.npy", "iq_time": "iq-time.png", "constellation": "constellation.png"}
    manifest["status"] = "ok"
    p = write_manifest(out, manifest)
    print(json.dumps({"ok": True, "out": str(out), "manifest": str(p), "metrics": metrics, "sync": sync_info}, indent=2))
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
    c.add_argument("--esp32-port", default=None)
    c.add_argument("--seed", type=int, default=None)
    c.add_argument("--mode", default="norm", choices=["norm", "raw"], help="Rigol capture mode (raw is scaffold; requires scope)")
    c.add_argument("--shape", default="rect", choices=["rect", "rrc"], help="Pulse shape assumption for matched filtering")
    c.set_defaults(func=cmd_capture)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())