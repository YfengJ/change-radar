#!/usr/bin/env python3
"""Generate a compact risk and verification report for a code change."""

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

RISK_RULES = [
    ("Dependencies changed", re.compile(r"(^|/)(package-lock|pnpm-lock|yarn\.lock|bun\.lockb|poetry\.lock|uv\.lock|Pipfile\.lock|go\.sum|Cargo\.lock|Gemfile\.lock)$|(^|/)(package\.json|pyproject\.toml|requirements.*\.txt|go\.mod|Cargo\.toml|Gemfile)$")),
    ("Runtime configuration changed", re.compile(r"(^|/)(\.env|\.env\..*|config|settings|application\.ya?ml|application\.properties|docker-compose\.ya?ml|Dockerfile)(/|$)|(^|/)(vite|webpack|rollup|next|nuxt|tsconfig|eslint|prettier|babel|jest|vitest|pytest|ruff|mypy)\.")),
    ("CI or deployment changed", re.compile(r"(^|/)(\.github/workflows|\.gitlab-ci\.yml|Jenkinsfile|deploy|deployment|k8s|helm|terraform|infra|vercel\.json|netlify\.toml)(/|$)")),
    ("Database or persistence changed", re.compile(r"(^|/)(migrations?|schema|models?|entities|repositories|prisma|drizzle|sequelize|typeorm|alembic)(/|$)|\.(sql)$")),
    ("Public API or integration changed", re.compile(r"(^|/)(api|routes|controllers|handlers|openapi|swagger|proto|graphql|schemas?)(/|$)|\.(proto|graphql|gql)$")),
    ("Auth, security, or money path changed", re.compile(r"auth|oauth|session|jwt|password|permission|acl|security|crypto|secret|token|billing|payment|stripe|checkout", re.IGNORECASE)),
    ("User interface changed", re.compile(r"\.(tsx|jsx|vue|svelte|css|scss|less)$|(^|/)(components|pages|app|views|templates|styles)(/|$)")),
    ("Tests changed", re.compile(r"(^|/)(tests?|spec|__tests__)(/|$)|(\.test|\.spec|_test|test_).*\.")),
    ("Generated or bundled artifact changed", re.compile(r"(^|/)(generated|gen|vendor)(/|$)|(\.min\.js|\.snap)$")),
    ("Documentation changed", re.compile(r"\.(md|mdx|rst|adoc)$|(^|/)(docs?|examples)(/|$)")),
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


def dedupe(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in paths:
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


def risk_cues(files: list[str]) -> list[tuple[str, list[str]]]:
    cues: list[tuple[str, list[str]]] = []
    for label, pattern in RISK_RULES:
        matched = [path for path in files if pattern.search(path)]
        if matched:
            cues.append((label, matched[:8]))
    return cues


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


def nearest_tests(files: list[str], universe: list[str]) -> list[str]:
    universe_set = set(universe)
    candidates: list[str] = []
    for changed in files:
        path = Path(changed)
        stem = path.stem
        if re.search(r"(\.test|\.spec|_test|test_)", changed):
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


def render_report(repo: Path, base: str, include_untracked: bool) -> str:
    root = git_root(repo)
    effective_repo = root or repo.resolve()
    files = changed_files(effective_repo, base, include_untracked) if root else []
    all_files = tracked_files(effective_repo)
    tests = nearest_tests(files, all_files)
    cues = risk_cues(files)
    indicators = project_indicators(effective_repo)
    commands = suggest_commands(effective_repo, files)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = []
    lines.append("# Change Radar Report")
    lines.append("")
    lines.append(f"- Generated: {now}")
    lines.append(f"- Repository: `{effective_repo}`")
    lines.append(f"- Git detected: {'yes' if root else 'no'}")
    if root:
        lines.append(f"- Branch: `{current_branch(effective_repo)}`")
        lines.append(f"- Diff base: `{base}`")
    lines.append("")

    lines.append("## Project Signals")
    if indicators:
        for item in indicators:
            lines.append(f"- {item}")
    else:
        lines.append("- No common project manifest detected.")
    lines.append("")

    lines.append("## Changed Files")
    if files:
        for path in files[:80]:
            lines.append(f"- `{path}`")
        if len(files) > 80:
            lines.append(f"- ... {len(files) - 80} more")
    else:
        lines.append("- No changed files detected from git diff. Use `--base <ref>` or make changes first.")
    lines.append("")

    lines.append("## Blast Radius Snapshot")
    if files:
        lines.append("Top-level areas:")
        for item in top_level_summary(files):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("File types:")
        for item in extension_summary(files):
            lines.append(f"- {item}")
    else:
        lines.append("- No file-based blast radius available.")
    lines.append("")

    lines.append("## Risk Cues")
    if cues:
        for label, matched in cues:
            lines.append(f"- {label}: " + ", ".join(f"`{path}`" for path in matched))
    else:
        lines.append("- No high-signal risk cues matched changed file paths. Still inspect behavior and contracts manually.")
    lines.append("")

    lines.append("## Nearby Tests")
    if tests:
        for path in tests:
            lines.append(f"- `{path}`")
    else:
        lines.append("- No nearby tests found by filename heuristics.")
    lines.append("")

    lines.append("## Suggested Verification Commands")
    for command in commands:
        lines.append(f"- `{command}`")
    lines.append("")

    lines.append("## Agent Checklist")
    lines.append("- Confirm the user-visible goal and out-of-scope work.")
    lines.append("- Identify touched contracts and label inferred contracts.")
    lines.append("- Choose focused verification before broad verification.")
    lines.append("- After edits, compare actual changed files against the intended blast radius.")
    lines.append("- Do not claim completion without direct evidence for every explicit requirement.")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Change Radar report for a repository.")
    parser.add_argument("--repo", default=".", help="Repository path to inspect. Defaults to the current directory.")
    parser.add_argument("--base", default="HEAD", help="Git ref to diff against. Defaults to HEAD.")
    parser.add_argument("--output", help="Optional path to write the Markdown report.")
    parser.add_argument("--no-untracked", action="store_true", help="Exclude untracked files from the changed-file list.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"Repository path does not exist: {repo}", file=sys.stderr)
        return 2
    report = render_report(repo, args.base, not args.no_untracked)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
