#!/usr/bin/env python3
"""Validate categorized role sources and deploy managed, flat copies for Codex and Claude Code."""

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

# Claude Code defaults derived from the Codex fields. Override per role with a trailing [claude] table.
CLAUDE_MODEL_MAP = {"gpt-6.1-sol": "opus", "gpt-6-luna": "sonnet"}
CLAUDE_EFFORTS = ("low", "medium", "high", "xhigh", "max")
CLAUDE_KEYS = {"model", "effort", "tools"}
CLAUDE_TABLE = re.compile(rb"^\[claude\][ \t]*\r?$", re.M)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def split_claude(path, data, role):
    """Return (codex_bytes, claude_settings). The [claude] table must be the last table in the file."""
    if "claude" not in role:
        return data, {}
    matches = list(CLAUDE_TABLE.finditer(data))
    if len(matches) != 1:
        raise ValueError(f"Claude settings must be a single trailing [claude] table: {path}")
    codex = data[: matches[0].start()].rstrip() + b"\n"
    expected = {k: v for k, v in role.items() if k != "claude"}
    if tomllib.loads(codex.decode("utf-8")) != expected:
        raise ValueError(f"[claude] must be the last table in the file: {path}")
    settings = role["claude"]
    if not isinstance(settings, dict):
        raise ValueError(f"[claude] must be a table: {path}")
    unknown = set(settings) - CLAUDE_KEYS
    if unknown:
        raise ValueError(f"Unknown [claude] keys {sorted(unknown)}: {path}")
    return codex, settings


def claude_frontmatter(path, role, settings):
    model = settings.get("model", CLAUDE_MODEL_MAP.get(role["model"]))
    if not isinstance(model, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.\[\]-]*", model):
        raise ValueError(f"No Claude model mapping for {role['model']!r}; set [claude] model: {path}")
    effort = settings.get("effort", role["model_reasoning_effort"])
    if effort not in CLAUDE_EFFORTS:
        raise ValueError(f"Claude effort must be one of {CLAUDE_EFFORTS}; set [claude] effort: {path}")
    lines = [
        "---",
        f"name: {role['name']}",
        f"description: {json.dumps(role['description'].strip(), ensure_ascii=False)}",
        f"model: {model}",
        f"effort: {effort}",
    ]
    if "tools" in settings:
        tools = settings["tools"]
        if (
            not isinstance(tools, list)
            or not tools
            or not all(isinstance(t, str) and re.fullmatch(r"[A-Za-z][\w*()., :-]*", t) for t in tools)
        ):
            raise ValueError(f"[claude] tools must be a non-empty list of tool names: {path}")
        lines.append(f"tools: {', '.join(tools)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def render_codex(path, data, role, settings):
    return data


def render_claude(path, data, role, settings):
    head = claude_frontmatter(path, role, settings)
    return (head + role["developer_instructions"].strip() + "\n").encode("utf-8")


# runtime -> (deploy directory relative to the repository root, file extension, renderer)
RUNTIMES = {
    "codex": (".codex/agents", ".toml", render_codex),
    "claude": (".claude/agents", ".md", render_claude),
}


def collect(source):
    """Parse and validate every source. Returns {name: (path, codex_bytes, role, claude_settings)}."""
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
        if name in roles:
            raise ValueError(f"Duplicate agent name: {name}")
        codex, settings = split_claude(path, data, role)
        roles[name] = (path, codex, role, settings)
    if not roles:
        raise ValueError("No role sources; refusing to remove all deployed roles")
    return roles


def plan(roles, target, runtime):
    """Compute writes/deletes for one target without touching the filesystem."""
    _, ext, render = RUNTIMES[runtime]
    if target.is_symlink() or target.resolve() != target:
        raise ValueError(f"Target must not contain symlinks: {target}")
    rendered = {name + ext: render(path, codex, role, settings) for name, (path, codex, role, settings) in roles.items()}
    manifest = target / MANIFEST
    if manifest.is_symlink():
        raise ValueError(f"Manifest must not be a symlink: {manifest}")
    previous = {}
    if manifest.exists():
        history = json.loads(manifest.read_text())
        if history.get("version") != 1 or not isinstance(history.get("files"), dict):
            raise ValueError(f"Invalid deployment manifest: {manifest}")
        previous = history["files"]
        for name, sha in previous.items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]*" + re.escape(ext), name):
                raise ValueError(f"Invalid managed filename: {name}")
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise ValueError(f"Invalid managed hash: {name}")

    writes, deletes, conflicts = [], [], []
    for name in sorted(set(rendered) | set(previous)):
        path = target / name
        desired = rendered.get(name)
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

    new_manifest = {"version": 1, "files": {name: digest(data) for name, data in rendered.items()}}
    manifest_text = json.dumps(new_manifest, indent=2, sort_keys=True) + "\n"
    metadata_changed = not manifest.exists() or manifest.read_text() != manifest_text
    return {
        "target": target,
        "writes": writes,
        "deletes": deletes,
        "conflicts": conflicts,
        "manifest": (manifest, manifest_text) if metadata_changed else None,
        "count": len(rendered),
    }


def deploy_many(source, targets, check=False):
    """Deploy to {runtime: target_dir}. Every target is validated before any file is written."""
    source = source.resolve()
    targets = {runtime: Path(t).absolute() for runtime, t in targets.items()}
    for target in targets.values():
        if source == target or source.is_relative_to(target) or target.is_relative_to(source):
            raise ValueError("Source and target directories must not overlap")
    roles = collect(source)
    plans = {runtime: plan(roles, target, runtime) for runtime, target in targets.items()}
    conflicts = [c for p in plans.values() for c in p["conflicts"]]
    if conflicts:
        raise ValueError("\n".join(conflicts))
    if not check:
        for p in plans.values():
            p["target"].mkdir(parents=True, exist_ok=True)
            for path, data in p["writes"]:
                path.write_bytes(data)
            for path in p["deletes"]:
                path.unlink()
            if p["manifest"]:
                p["manifest"][0].write_text(p["manifest"][1])
    return {
        runtime: (bool(p["writes"] or p["deletes"] or p["manifest"]), p["count"], len(p["writes"]), len(p["deletes"]))
        for runtime, p in plans.items()
    }


def deploy(source, target, check=False, runtime="codex"):
    """Deploy to a single target. Returns (changed, roles, writes, deletes)."""
    return deploy_many(source, {runtime: target}, check)[runtime]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check only; exit 1 when any deployment is stale")
    parser.add_argument(
        "--runtime",
        choices=sorted(RUNTIMES),
        action="append",
        help="Deploy only this runtime (repeatable). Default: all runtimes",
    )
    args = parser.parse_args()
    runtimes = args.runtime or list(RUNTIMES)
    try:
        results = deploy_many(ROOT / "agents", {r: ROOT / RUNTIMES[r][0] for r in runtimes}, args.check)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"Deployment refused: {exc}", file=sys.stderr)
        return 2
    stale = False
    for runtime, (changed, count, writes, deletes) in results.items():
        stale |= args.check and changed
        status = "STALE" if args.check and changed else "OK"
        suffix = " (check only)" if args.check else ""
        print(f"{status} [{runtime}] {RUNTIMES[runtime][0]}: {count} roles; {writes} writes, {deletes} removals{suffix}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
