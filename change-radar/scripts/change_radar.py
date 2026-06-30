#!/usr/bin/env python3
"""Generate a risk, contract, and verification report for a code change."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "target",
    ".next",
    ".turbo",
}

RISK_LEVEL_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

RISK_RULES = [
    {
        "label": "Dependencies changed",
        "pattern": re.compile(r"(^|/)(package-lock|pnpm-lock|yarn\.lock|bun\.lockb|poetry\.lock|uv\.lock|Pipfile\.lock|go\.sum|Cargo\.lock|Gemfile\.lock)$|(^|/)(package\.json|pyproject\.toml|requirements.*\.txt|go\.mod|Cargo\.toml|Gemfile)$"),
        "level": "P1",
        "score": 22,
        "contracts": ["Dependency graph", "Install and runtime compatibility"],
        "actions": ["Verify dependency install, lockfile consistency, build, and runtime compatibility."],
        "manual": [],
    },
    {
        "label": "Runtime configuration changed",
        "pattern": re.compile(r"(^|/)(\.env|\.env\..*|config|settings|application\.ya?ml|application\.properties|docker-compose\.ya?ml|Dockerfile)(/|$)|(^|/)(vite|webpack|rollup|next|nuxt|tsconfig|eslint|prettier|babel|jest|vitest|pytest|ruff|mypy)\."),
        "level": "P1",
        "score": 20,
        "contracts": ["Runtime configuration", "Environment defaults"],
        "actions": ["Verify defaults, missing environment values, and local versus production behavior."],
        "manual": [],
    },
    {
        "label": "CI or deployment changed",
        "pattern": re.compile(r"(^|/)(\.github/workflows|\.gitlab-ci\.yml|Jenkinsfile|deploy|deployment|k8s|helm|terraform|infra|vercel\.json|netlify\.toml)(/|$)"),
        "level": "P1",
        "score": 24,
        "contracts": ["Build pipeline", "Deployment path"],
        "actions": ["Verify clean-checkout CI behavior, cache assumptions, and deployment ordering."],
        "manual": [],
    },
    {
        "label": "Database or persistence changed",
        "pattern": re.compile(r"(^|/)(migrations?|schema|models?|entities|repositories|prisma|drizzle|sequelize|typeorm|alembic)(/|$)|\.(sql)$"),
        "level": "P0",
        "score": 45,
        "contracts": ["Database schema", "Stored data compatibility"],
        "actions": ["Verify migration upgrade path, rollback story, seed data, and old/new code compatibility."],
        "manual": ["Review migration reversibility and data repair risk."],
    },
    {
        "label": "Public API or integration changed",
        "pattern": re.compile(r"(^|/)(api|routes|controllers|handlers|openapi|swagger|proto|graphql|schemas?)(/|$)|\.(proto|graphql|gql)$"),
        "level": "P1",
        "score": 25,
        "contracts": ["Public API shape", "Integration boundary"],
        "actions": ["Verify request/response shape, status codes, error bodies, clients, and docs."],
        "manual": [],
    },
    {
        "label": "Auth, security, or money path changed",
        "pattern": re.compile(r"auth|oauth|session|jwt|password|permission|acl|security|crypto|secret|token|billing|payment|stripe|checkout", re.IGNORECASE),
        "level": "P0",
        "score": 48,
        "contracts": ["Authorization boundary", "Security or payment invariant"],
        "actions": ["Verify negative cases, privilege boundaries, token lifetime, idempotency, and replay behavior."],
        "manual": ["Review abuse cases, least privilege, duplicate submission, and failure safety."],
    },
    {
        "label": "User interface changed",
        "pattern": re.compile(r"\.(tsx|jsx|vue|svelte|css|scss|less)$|(^|/)(components|pages|app|views|templates|styles)(/|$)"),
        "level": "P2",
        "score": 12,
        "contracts": ["User flow", "Visual and accessibility state"],
        "actions": ["Verify loading, empty, error, disabled, keyboard, and small viewport states."],
        "manual": ["Check affected UI states manually or with browser automation."],
    },
    {
        "label": "Executable source changed",
        "pattern": re.compile(r"\.(py|ts|js|mjs|cjs|go|rs|java|kt|kts|cs|rb|php|swift|c|cc|cpp|h|hpp)$"),
        "level": "P2",
        "score": 8,
        "contracts": ["Local runtime behavior"],
        "actions": ["Verify changed behavior with focused tests or a direct executable check."],
        "manual": [],
    },
    {
        "label": "Tests changed",
        "pattern": re.compile(r"(^|/)(tests?|spec|__tests__)(/|$)|(\.test|\.spec|_test|test_).*\."),
        "level": "P3",
        "score": 0,
        "contracts": ["Verification surface"],
        "actions": ["Review whether tests assert behavior rather than implementation details."],
        "manual": [],
    },
    {
        "label": "Generated or bundled artifact changed",
        "pattern": re.compile(r"(^|/)(generated|gen|vendor)(/|$)|(\.min\.js|\.snap)$"),
        "level": "P2",
        "score": 12,
        "contracts": ["Generated source of truth"],
        "actions": ["Verify the artifact was regenerated from source and not hand-edited accidentally."],
        "manual": [],
    },
    {
        "label": "Documentation changed",
        "pattern": re.compile(r"\.(md|mdx|rst|adoc)$|(^|/)(docs?|examples)(/|$)"),
        "level": "P3",
        "score": 0,
        "contracts": ["User-facing guidance"],
        "actions": ["Verify examples still match real commands and behavior."],
        "manual": [],
    },
]


def run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def git_lines(repo: Path, args: list[str]) -> list[str]:
    code, out, _ = run(["git", *args], repo)
    if code != 0 or not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def git_root(repo: Path) -> Path | None:
    code, out, _ = run(["git", "rev-parse", "--show-toplevel"], repo)
    if code != 0:
        return None
    return Path(out).resolve()


def current_branch(repo: Path) -> str:
    lines = git_lines(repo, ["branch", "--show-current"])
    if lines:
        return lines[0]
    head = git_lines(repo, ["rev-parse", "--short", "HEAD"])
    return head[0] if head else "unknown"


def dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip().replace(os.sep, "/")
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def changed_files(repo: Path, base: str, include_untracked: bool) -> list[str]:
    files: list[str] = []
    files.extend(git_lines(repo, ["diff", "--name-only", "--diff-filter=ACMRTUXB", base]))
    files.extend(git_lines(repo, ["diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB"]))
    if include_untracked:
        files.extend(git_lines(repo, ["ls-files", "--others", "--exclude-standard"]))
    return dedupe(files)


def diff_numstat(repo: Path, base: str) -> list[dict[str, int | str]]:
    stats: list[dict[str, int | str]] = []
    for line in git_lines(repo, ["diff", "--numstat", base]):
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added_raw, deleted_raw, path = parts
        added = 0 if added_raw == "-" else int(added_raw)
        deleted = 0 if deleted_raw == "-" else int(deleted_raw)
        stats.append({"path": path, "added": added, "deleted": deleted, "total": added + deleted})
    return stats


def git_added_lines(repo: Path, base: str) -> list[dict[str, str]]:
    code, out, _ = run(["git", "diff", "--unified=0", base], repo)
    if code != 0 or not out:
        return []
    current_path = ""
    added: list[dict[str, str]] = []
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:]
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append({"path": current_path, "line": line})
    return added


def normalize_diff_entry(entry: str | dict[str, str]) -> dict[str, str]:
    if isinstance(entry, dict):
        raw_line = entry.get("line", "")
        path = entry.get("path", "")
    else:
        raw_line = entry
        path = ""
    line = raw_line[1:].strip() if raw_line.startswith("+") else raw_line.strip()
    return {"path": path, "line": line, "raw": raw_line}


def walk_files(repo: Path, limit: int = 20000) -> list[str]:
    results: list[str] = []
    for path in repo.rglob("*"):
        if len(results) >= limit:
            break
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            results.append(path.relative_to(repo).as_posix())
    return results


def tracked_files(repo: Path) -> list[str]:
    files = git_lines(repo, ["ls-files"])
    return files if files else walk_files(repo)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def project_indicators(repo: Path) -> list[str]:
    indicators: list[str] = []
    checks = {
        "Node package": "package.json",
        "Python project": "pyproject.toml",
        "Python requirements": "requirements.txt",
        "Go module": "go.mod",
        "Rust crate": "Cargo.toml",
        "Java Maven": "pom.xml",
        "Java/Android Gradle": "build.gradle",
        "Gradle Kotlin": "build.gradle.kts",
        ".NET project": "*.csproj",
        "Ruby bundle": "Gemfile",
    }
    for label, pattern in checks.items():
        if "*" in pattern:
            if list(repo.glob(pattern)):
                indicators.append(label)
        elif (repo / pattern).exists():
            indicators.append(label)
    return indicators


def package_json_commands(repo: Path) -> list[str]:
    package = read_json(repo / "package.json")
    scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
    commands: list[str] = []
    if not isinstance(scripts, dict):
        return commands
    manager = "npm"
    if (repo / "pnpm-lock.yaml").exists():
        manager = "pnpm"
    elif (repo / "yarn.lock").exists():
        manager = "yarn"
    elif (repo / "bun.lockb").exists():
        manager = "bun"
    for name in ["typecheck", "lint", "test", "test:unit", "test:e2e", "build"]:
        if name in scripts:
            commands.append(f"{manager} run {name}")
    return commands


def file_contains(path: Path, needles: list[str]) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(needle in text for needle in needles)


def suggest_commands(repo: Path, files: list[str]) -> list[str]:
    commands: list[str] = []
    commands.extend(package_json_commands(repo))
    has_python = (repo / "pyproject.toml").exists() or any(path.endswith(".py") for path in files)
    has_pytest_config = (
        (repo / "pytest.ini").exists()
        or file_contains(repo / "pyproject.toml", ["[tool.pytest", "pytest"])
        or file_contains(repo / "setup.cfg", ["[tool:pytest", "[pytest"])
        or file_contains(repo / "tox.ini", ["[pytest", "pytest"])
    )
    if has_python:
        unittest_command = "python3 -m unittest discover -s tests" if (repo / "tests").is_dir() else "python3 -m unittest discover"
        commands.append("python3 -m pytest" if has_pytest_config else unittest_command)
        if (repo / "ruff.toml").exists() or file_contains(repo / "pyproject.toml", ["[tool.ruff"]):
            commands.append("python3 -m ruff check .")
        if (repo / "mypy.ini").exists() or file_contains(repo / "pyproject.toml", ["[tool.mypy", "[mypy"]):
            commands.append("python3 -m mypy .")
    if (repo / "go.mod").exists():
        commands.append("go test ./...")
    if (repo / "Cargo.toml").exists():
        commands.append("cargo test")
        commands.append("cargo clippy --all-targets --all-features")
    if (repo / "pom.xml").exists():
        commands.append("mvn test")
    if (repo / "build.gradle").exists() or (repo / "build.gradle.kts").exists():
        commands.append("./gradlew test")
    if list(repo.glob("*.csproj")) or list(repo.glob("**/*.csproj")):
        commands.append("dotnet test")
    if not commands:
        commands.append("Run the nearest project-specific tests for the changed files.")
    return dedupe(commands)


def rich_risk_cues(files: list[str]) -> list[dict[str, object]]:
    cues: list[dict[str, object]] = []
    for rule in RISK_RULES:
        pattern = rule["pattern"]
        assert isinstance(pattern, re.Pattern)
        matched = [path for path in files if pattern.search(path)]
        if rule["label"] == "Executable source changed":
            matched = [path for path in matched if is_production_file(path)]
        if matched:
            cues.append(
                {
                    "label": rule["label"],
                    "level": rule["level"],
                    "score": rule["score"],
                    "matched_files": matched[:12],
                    "contracts": rule["contracts"],
                    "actions": rule["actions"],
                    "manual": rule["manual"],
                }
            )
    return cues


def content_risk_cues(diff_lines: list[str | dict[str, str]]) -> list[dict[str, object]]:
    secret_pattern = re.compile(r"(?i)((api[_-]?key|secret|token|password|private[_-]?key)\s*[:=]\s*['\"])[^'\"]{12,}(['\"]|$)|(sk_live_)[A-Za-z0-9_]{12,}")  # change-radar: ignore-risk

    def redact_secret(line: str) -> str:
        return secret_pattern.sub(lambda match: f"{match.group(1) or match.group(4)}[REDACTED]{match.group(3) or ''}", line)

    rules = [
        {
            "label": "Possible secret added",
            "pattern": secret_pattern,
            "level": "P0",
            "score": 55,
            "contracts": ["Secret handling", "Credential boundary"],
            "actions": ["Remove the possible secret, rotate it if real, or document why the match is a safe test fixture."],
            "manual": ["Confirm no live credential or private key is being committed."],
        },
        {
            "label": "Focused test left enabled",
            "pattern": re.compile(r"\b(describe|it|test)\.only\s*\(|\b(fdescribe|fit)\s*\("),
            "level": "P1",
            "score": 35,
            "contracts": ["Verification surface"],
            "actions": ["Remove focused test markers before merging."],
            "manual": [],
        },
        {
            "label": "Skipped test added",
            "pattern": re.compile(r"\b(describe|it|test)\.skip\s*\(|\b(xdescribe|xit)\s*\("),  # change-radar: ignore-risk
            "level": "P1",
            "score": 25,
            "contracts": ["Verification surface"],
            "actions": ["Justify the skipped test or restore active coverage before merging."],
            "manual": [],
        },
        {
            "label": "TODO marker added",  # change-radar: ignore-risk
            "pattern": re.compile(r"\b(TODO|FIXME|HACK)\b"),  # change-radar: ignore-risk
            "level": "P3",
            "score": 0,
            "contracts": ["Implementation completeness"],
            "actions": ["Resolve the TODO or explicitly track it outside the patch."],  # change-radar: ignore-risk
            "manual": [],
        },
    ]
    cues: list[dict[str, object]] = []
    added = [
        normalize_diff_entry(entry)
        for entry in diff_lines
        if "change-radar: ignore-risk" not in (entry.get("line", "") if isinstance(entry, dict) else entry)
    ]
    for rule in rules:
        pattern = rule["pattern"]
        assert isinstance(pattern, re.Pattern)
        evidence: list[str] = []
        paths: list[str] = []
        for entry in added:
            path = entry["path"]
            line = entry["line"]
            if is_doc_file(path):
                continue
            if pattern.search(line):
                evidence.append(line[:160])
                paths.append(path or "diff content")
        if evidence:
            if rule["label"] == "Possible secret added":
                evidence = [redact_secret(line) for line in evidence]
            cues.append(
                {
                    "label": rule["label"],
                    "level": rule["level"],
                    "score": rule["score"],
                    "matched_files": dedupe(paths)[:12],
                    "evidence": evidence[:5],
                    "contracts": rule["contracts"],
                    "actions": rule["actions"],
                    "manual": rule["manual"],
                }
            )
    return cues


def risk_cues(files: list[str]) -> list[tuple[str, list[str]]]:
    return [(str(cue["label"]), list(cue["matched_files"])) for cue in rich_risk_cues(files)]


def extension_summary(files: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for path in files:
        suffix = Path(path).suffix or "[no extension]"
        counts[suffix] = counts.get(suffix, 0) + 1
    return [f"{suffix}: {count}" for suffix, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def top_level_summary(files: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for path in files:
        top = path.split("/", 1)[0]
        counts[top] = counts.get(top, 0) + 1
    return [f"{name}: {count}" for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:12]]


def is_test_file(path: str) -> bool:
    return bool(re.search(r"(^|/)(tests?|spec|__tests__)(/|$)|(\.test|\.spec|_test|test_).*", path))


def is_doc_file(path: str) -> bool:
    return bool(re.search(r"\.(md|mdx|rst|adoc)$|(^|/)(docs?|examples)(/|$)", path))


def is_generated_file(path: str) -> bool:
    return bool(re.search(r"(^|/)(generated|gen|vendor)(/|$)|(\.min\.js|\.snap)$", path))


def is_production_file(path: str) -> bool:
    return not is_test_file(path) and not is_doc_file(path) and not is_generated_file(path)


def nearest_tests(files: list[str], universe: list[str]) -> list[str]:
    universe_set = set(universe)
    candidates: list[str] = []
    for changed in files:
        path = Path(changed)
        stem = path.stem
        if is_test_file(changed):
            continue
        possible = [
            f"tests/{path.with_suffix('').as_posix()}_test{path.suffix}",
            f"tests/test_{stem}{path.suffix}",
            f"{path.parent.as_posix()}/test_{stem}{path.suffix}",
            f"{path.parent.as_posix()}/{stem}_test{path.suffix}",
            f"{path.parent.as_posix()}/{stem}.test{path.suffix}",
            f"{path.parent.as_posix()}/{stem}.spec{path.suffix}",
            f"{path.parent.as_posix()}/__tests__/{stem}.test{path.suffix}",
        ]
        for candidate in possible:
            normalized = candidate.replace("./", "")
            if normalized in universe_set:
                candidates.append(normalized)
    return dedupe(candidates)[:20]


def risk_level_at_least(actual: str, threshold: str) -> bool:
    return RISK_LEVEL_RANK[actual] <= RISK_LEVEL_RANK[threshold]


def overall_risk(risk_score: int, cues: list[dict[str, object]]) -> str:
    levels = [str(cue["level"]) for cue in cues]
    if "P0" in levels or risk_score >= 80:
        return "P0"
    if "P1" in levels or risk_score >= 45:
        return "P1"
    if "P2" in levels or risk_score > 0:
        return "P2"
    return "P3"


def verification_plan(commands: list[str], cues: list[dict[str, object]]) -> dict[str, list[str]]:
    plan = {"focused": [], "static": [], "broad": [], "manual": []}
    for command in commands:
        lower = command.lower()
        if any(token in lower for token in ["typecheck", "lint", "ruff", "mypy", "clippy"]):
            plan["static"].append(command)
        elif "build" in lower or "test:e2e" in lower:
            plan["broad"].append(command)
        elif any(token in lower for token in ["test", "pytest", "unittest"]):
            plan["focused"].append(command)
        else:
            plan["broad"].append(command)
    for cue in cues:
        plan["manual"].extend(str(item) for item in cue.get("manual", []))
    return {key: dedupe(value) for key, value in plan.items()}


def build_report_data(
    repo: Path,
    base: str,
    include_untracked: bool,
    files_override: list[str] | None = None,
) -> dict[str, object]:
    root = git_root(repo)
    effective_repo = root or repo.resolve()
    files = dedupe(files_override) if files_override is not None else (changed_files(effective_repo, base, include_untracked) if root else [])
    all_files = tracked_files(effective_repo)
    tests = nearest_tests(files, all_files)
    cues = rich_risk_cues(files)
    if root and files_override is None:
        cues.extend(content_risk_cues(git_added_lines(effective_repo, base)))
    labels = [str(cue["label"]) for cue in cues]
    commands = suggest_commands(effective_repo, files)
    production_files = [path for path in files if is_production_file(path)]
    score = sum(int(cue["score"]) for cue in cues)
    blocking_gaps: list[str] = []
    recommended_actions: list[str] = []

    if production_files and not tests and not any(is_test_file(path) for path in files):
        blocking_gaps.append("No nearby tests found for changed production files.")
        recommended_actions.append("Add or identify tests for changed production files.")
        score += 15
    if any(cue["label"] == "Possible secret added" for cue in cues):
        blocking_gaps.append("Possible secret detected in added diff lines.")

    large_files = [item for item in diff_numstat(effective_repo, base) if int(item["total"]) >= 400] if root else []
    if large_files:
        recommended_actions.append("Split or explicitly justify large diffs before review.")
        score += 10

    for cue in cues:
        recommended_actions.extend(str(item) for item in cue["actions"])

    risk = overall_risk(score, cues)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "generated_at": now,
        "repository": str(effective_repo),
        "git": {
            "detected": bool(root),
            "branch": current_branch(effective_repo) if root else None,
            "base": base if root else None,
        },
        "project_signals": project_indicators(effective_repo),
        "changed_files": files,
        "blast_radius": {
            "top_level": top_level_summary(files),
            "file_types": extension_summary(files),
            "production_files": production_files,
            "diff_stats": large_files,
        },
        "risk_score": min(score, 100),
        "overall_risk": risk,
        "risk_labels": labels,
        "risk_cues": cues,
        "nearby_tests": tests,
        "blocking_gaps": dedupe(blocking_gaps),
        "recommended_actions": dedupe(recommended_actions),
        "suggested_commands": commands,
        "verification_plan": verification_plan(commands, cues),
    }


def render_report_from_data(data: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append("# Change Radar Report")
    lines.append("")
    lines.append(f"- Generated: {data['generated_at']}")
    lines.append(f"- Repository: `{data['repository']}`")
    git = data["git"]
    assert isinstance(git, dict)
    lines.append(f"- Git detected: {'yes' if git['detected'] else 'no'}")
    if git["detected"]:
        lines.append(f"- Branch: `{git['branch']}`")
        lines.append(f"- Diff base: `{git['base']}`")
    lines.append(f"- Overall risk: **{data['overall_risk']}**")
    lines.append(f"- Risk score: **{data['risk_score']}/100**")
    lines.append("")

    lines.append("## Project Signals")
    project_signals = data["project_signals"]
    assert isinstance(project_signals, list)
    if project_signals:
        for item in project_signals:
            lines.append(f"- {item}")
    else:
        lines.append("- No common project manifest detected.")
    lines.append("")

    lines.append("## Changed Files")
    changed = data["changed_files"]
    assert isinstance(changed, list)
    if changed:
        for path in changed[:80]:
            lines.append(f"- `{path}`")
        if len(changed) > 80:
            lines.append(f"- ... {len(changed) - 80} more")
    else:
        lines.append("- No changed files detected from git diff. Use `--base <ref>` or make changes first.")
    lines.append("")

    lines.append("## Blast Radius Snapshot")
    blast = data["blast_radius"]
    assert isinstance(blast, dict)
    if changed:
        lines.append("Top-level areas:")
        for item in blast["top_level"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("File types:")
        for item in blast["file_types"]:
            lines.append(f"- {item}")
    else:
        lines.append("- No file-based blast radius available.")
    lines.append("")

    lines.append("## Risk Cues")
    cues = data["risk_cues"]
    assert isinstance(cues, list)
    if cues:
        for cue in cues:
            assert isinstance(cue, dict)
            matched = ", ".join(f"`{path}`" for path in cue["matched_files"])
            lines.append(f"- {cue['level']} {cue['label']}: {matched}")
    else:
        lines.append("- No high-signal risk cues matched changed file paths. Still inspect behavior and contracts manually.")
    lines.append("")

    lines.append("## Contract Map")
    contracts = dedupe(str(contract) for cue in cues for contract in cue.get("contracts", []))
    if contracts:
        for contract in contracts:
            lines.append(f"- {contract}")
    else:
        lines.append("- No specific contracts inferred from file paths.")
    lines.append("")

    lines.append("## Blocking Gaps")
    gaps = data["blocking_gaps"]
    assert isinstance(gaps, list)
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- No blocking evidence gaps detected by heuristics.")
    lines.append("")

    lines.append("## Nearby Tests")
    tests = data["nearby_tests"]
    assert isinstance(tests, list)
    if tests:
        for path in tests:
            lines.append(f"- `{path}`")
    else:
        lines.append("- No nearby tests found by filename heuristics.")
    lines.append("")

    lines.append("## Verification Plan")
    plan = data["verification_plan"]
    assert isinstance(plan, dict)
    for group in ["static", "focused", "broad", "manual"]:
        values = plan[group]
        if values:
            lines.append(f"{group.title()}:")
            for value in values:
                prefix = "`" if group != "manual" else ""
                suffix = "`" if group != "manual" else ""
                lines.append(f"- {prefix}{value}{suffix}")
            lines.append("")
    if not any(plan.values()):
        lines.append("- No project-specific verification commands detected.")
        lines.append("")

    lines.append("## Recommended Actions")
    actions = data["recommended_actions"]
    assert isinstance(actions, list)
    if actions:
        for action in actions:
            lines.append(f"- {action}")
    else:
        lines.append("- No extra actions detected.")
    lines.append("")

    lines.append("## Agent Checklist")
    lines.append("- Confirm the user-visible goal and out-of-scope work.")
    lines.append("- Identify touched contracts and label inferred contracts.")
    lines.append("- Run or justify every verification item above.")
    lines.append("- After edits, compare actual changed files against the intended blast radius.")
    lines.append("- Do not claim completion without direct evidence for every explicit requirement.")
    lines.append("")
    return "\n".join(lines)


def render_report(repo: Path, base: str, include_untracked: bool) -> str:
    data = build_report_data(repo, base, include_untracked)
    return render_report_from_data(data)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Change Radar report for a repository.")
    parser.add_argument("--repo", default=".", help="Repository path to inspect. Defaults to the current directory.")
    parser.add_argument("--base", default="HEAD", help="Git ref to diff against. Defaults to HEAD.")
    parser.add_argument("--output", help="Optional path to write the report.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Report format. Defaults to markdown.")
    parser.add_argument("--fail-on-risk", choices=["P0", "P1", "P2", "P3"], help="Exit with code 3 when overall risk is at or above this threshold.")
    parser.add_argument("--no-untracked", action="store_true", help="Exclude untracked files from the changed-file list.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"Repository path does not exist: {repo}", file=sys.stderr)
        return 2
    data = build_report_data(repo, args.base, not args.no_untracked)
    report = json.dumps(data, indent=2, sort_keys=True) + "\n" if args.format == "json" else render_report_from_data(data)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    else:
        print(report, end="" if report.endswith("\n") else "\n")
    if args.fail_on_risk and risk_level_at_least(str(data["overall_risk"]), args.fail_on_risk):
        print(
            f"Risk gate failed: overall risk {data['overall_risk']} meets threshold {args.fail_on_risk}.",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
