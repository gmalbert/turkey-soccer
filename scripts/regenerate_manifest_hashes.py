"""Regenerate cache_manifest.json hashes from git's LF-normalized blobs.

Text artifacts were committed as LF (per .gitattributes) but the manifest was
built from CRLF working-tree copies on Windows, so hashes mismatched on Linux
CI. Binary artifacts (.pkl) are read from disk; text artifacts are read from
`git show HEAD:<path>` so hashes match what CI checks out.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "precomputed" / "cache_manifest.json"

TEXT_SUFFIXES = {".csv", ".json"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _lf_blob(path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        capture_output=True,
        check=True,
        cwd=ROOT,
    )
    return result.stdout


manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
updated = []

for name, item in manifest["artifacts"].items():
    path = item["path"]
    suffix = Path(path).suffix
    if suffix in TEXT_SUFFIXES:
        data = _lf_blob(path)
    else:
        data = (ROOT / path).read_bytes()
    item["bytes"] = len(data)
    item["sha256"] = _sha256(data)
    updated.append(f"{name}: {len(data)} bytes {item['sha256'][:12]}")

MANIFEST.write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)

print("Updated artifacts:")
for line in updated:
    print(f"  {line}")
