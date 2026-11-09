#!/usr/bin/env python3
"""Validate categorized role sources and deploy managed, flat Codex copies."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ".deployment-manifest.json"
REQUIRED = ("name", "description", "model", "model_reasoning_effort", "developer_instructions")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def collect(source):
    roles = {}
    for path in sorted(source.rglob("*.toml")):
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError(f"Source must stay within agents/: {path}")
        data = path.read_bytes()
        role = tomllib.loads(data.decode("utf-8"))
        for key in REQUIRED:
            if not isinstance(role.get(key), str) or not role[key].strip():
                raise ValueError(f"Missing/non-string {key}: {path}")
        name = role["name"]
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", name) or path.stem != name:
            raise ValueError(f"Name must match a safe filename: {path}")
        if path.name in roles:
            raise ValueError(f"Duplicate agent name: {name}")
        roles[path.name] = data
    if not roles:
        raise ValueError("No role sources; refusing to remove all deployed roles")
    return roles


def deploy(source, target, check=False):
    source, target = source.resolve(), target.absolute()
    if target.is_symlink() or target.resolve() != target:
        raise ValueError("Target must not contain symlinks")
    if source == target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("Source and target directories must not overlap")
    roles = collect(source)
    manifest = target / MANIFEST
    if manifest.is_symlink():
        raise ValueError("Manifest must not be a symlink")
    previous = {}
    if manifest.exists():
        history = json.loads(manifest.read_text())
        if history.get("version") != 1 or not isinstance(history.get("files"), dict):
            raise ValueError("Invalid deployment manifest")
        previous = history["files"]
        for name, sha in previous.items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]*\.toml", name):
                raise ValueError(f"Invalid managed filename: {name}")
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise ValueError(f"Invalid managed hash: {name}")

    writes, deletes, conflicts = [], [], []
    for name in sorted(set(roles) | set(previous)):
        path = target / name
        desired = roles.get(name)
        if path.is_symlink() or (path.exists() and not path.is_file()):
            conflicts.append(f"Not a regular file: {path}")
            continue
        current = path.read_bytes() if path.exists() else None
        if current is not None and current != desired:
            if name not in previous or digest(current) != previous[name]:
                conflicts.append(f"Unmanaged or locally edited copy: {path}")
                continue
        if desired is None:
            if current is not None:
                deletes.append(path)
        elif current != desired:
            writes.append((path, desired))

    # Validate every source and destination before making any changes.
    if conflicts:
        raise ValueError("\n".join(conflicts))
    new_manifest = {"version": 1, "files": {name: digest(data) for name, data in roles.items()}}
    manifest_text = json.dumps(new_manifest, indent=2, sort_keys=True) + "\n"
    metadata_changed = not manifest.exists() or manifest.read_text() != manifest_text
    changed = bool(writes or deletes or metadata_changed)
    if check:
        return changed, len(roles), len(writes), len(deletes)

    target.mkdir(parents=True, exist_ok=True)
    for path, data in writes:
        path.write_bytes(data)
    for path in deletes:
        path.unlink()
    if metadata_changed:
        manifest.write_text(manifest_text)
    return changed, len(roles), len(writes), len(deletes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check only; exit 1 when deployment is stale")
    args = parser.parse_args()
    try:
        changed, count, writes, deletes = deploy(ROOT / "agents", ROOT / ".codex/agents", args.check)
    except (OSError, ValueError) as exc:
        print(f"Deployment refused: {exc}", file=sys.stderr)
        return 2
    status = "STALE" if args.check and changed else "OK"
    print(f"{status}: {count} roles; {writes} writes, {deletes} removals" + (" (check only)" if args.check else ""))
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
