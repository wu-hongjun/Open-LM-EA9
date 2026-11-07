#!/usr/bin/env python3
"""Verify archived reference files against checksums.sha256 (standard library only)."""

import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    failures = []
    checked = 0
    expected_paths = set()
    for line in (root / "checksums.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Invalid checksum path: {name}")
        expected_paths.add(name)
        path = root / relative
        if not path.is_file():
            failures.append({"path": name, "error": "missing"})
            continue
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            failures.append({"path": name, "error": "hash-mismatch"})
        checked += 1
    excluded = {"checksums.sha256", "analysis/collection-verification.json"}
    def public_path(path):
        parts = path.relative_to(root).parts
        return parts[0] != "private" and "__pycache__" not in parts and path.name != ".DS_Store"
    observed_paths = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and public_path(p)}
    unexpected = sorted(observed_paths - expected_paths - excluded)
    failures.extend({"path": name, "error": "not-in-checksums"} for name in unexpected)
    for source in json.loads((root / "sources.json").read_text())["sources"]:
        for entry in source.get("symlinks", []):
            name = str(Path(source["local_path"]) / entry["path"])
            path = root / name
            if not path.is_symlink() or str(path.readlink()) != entry["target"]:
                failures.append({"path": name, "error": "symlink-mismatch"})
    git_metadata = [str(p.relative_to(root)) for p in root.rglob(".git") if public_path(p)]
    failures.extend({"path": name, "error": "embedded-git-metadata"} for name in git_metadata)
    report = {"schema_version": 1, "checked_files": checked,
              "scope": "Pinned public references; private vendor material and local caches excluded",
              "failure_count": len(failures), "failures": failures}
    (root / "analysis/collection-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
