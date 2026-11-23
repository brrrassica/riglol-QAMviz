from __future__ import annotations
import json, hashlib, datetime
from pathlib import Path

def write_manifest(out_dir: str | Path, manifest: dict) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / "session.json"
    p.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return p

def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()