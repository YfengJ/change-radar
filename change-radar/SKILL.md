---
name: change-radar
description: Risk-aware coding workflow for AI-assisted software changes. Use when Codex is asked to write, modify, refactor, debug, review, or ship code and should map blast radius, affected contracts, hidden risks, test selection, and verification evidence before or after edits.
---

# Change Radar

Use Change Radar to make a code change earn confidence before it is merged or declared done. The workflow turns a request into a compact evidence trail: intent, affected surfaces, risk cues, verification commands, and completion proof.

## Quick Start

1. State the requested change in one sentence.
2. Inspect the current repository state before editing.
3. Run the bundled scanner when a filesystem repository is available:

```bash
python3 /path/to/change-radar/scripts/change_radar.py --repo /path/to/repo
```

4. Use the report to choose the implementation path and verification commands.
5. Re-run the scanner after edits if the changed-file set or test plan might have shifted.

If the scanner cannot run, perform the same analysis manually and say which evidence is unavailable.

## Workflow

### 1. Build A Change Brief

Before modifying code, write a terse brief for yourself:

- User-visible goal.
- Files or subsystems likely to change.
- Existing behavior that must be preserved.
- Assumptions that need evidence.
- Out-of-scope tempting work.

Keep it short. The brief exists to prevent accidental scope drift.

### 2. Sweep The Radar

Run `scripts/change_radar.py` from this skill against the target repository. Treat its output as a starting point, not an oracle.

Use the report to identify:

- Changed or likely changed files.
- Project type and available validation commands.
- Risk cues such as migrations, lockfiles, auth, public APIs, CI, config, generated files, or UI surfaces.
- Nearby tests and missing-test signals.

For high-risk changes, read `references/risk-taxonomy.md`. For choosing tests, read `references/test-selection.md`.

### 3. Map Contracts

List the contracts the change touches. Include only contracts that can plausibly break:

- Public APIs, CLI flags, config keys, environment variables.
- Database schemas, migrations, serialized data, queues, events.
- Type signatures, function preconditions, error shapes.
- UI states, accessibility affordances, user flows.
- Build, deploy, CI, package, and runtime assumptions.

If a contract is inferred rather than proven, label it as inferred.

### 4. Select Verification

Choose the smallest high-signal verification set first, then broaden based on risk.

Always include:

- A focused check for the changed behavior.
- A regression check for the nearest affected contract.
- A static check when types, lint rules, config, or generated artifacts are involved.

Do not treat "tests pass" as sufficient unless the chosen tests actually cover the changed contract.

### 5. Implement With Evidence

Edit only after the brief, radar sweep, and verification plan are clear enough to guide the work. Keep changes close to the request and existing project patterns.

While editing:

- Prefer small, explainable changes.
- Update tests next to behavior when risk is meaningful.
- Add or update docs only when public usage changes.
- Preserve unrelated user work in the git tree.

### 6. Completion Audit

Before claiming completion, compare the final state to the original request:

- Each explicit requirement has direct evidence.
- The changed files match the intended blast radius.
- Verification commands were run, or their absence is explained.
- Known residual risks are named honestly.
- No unrelated refactor is being presented as required work.

If evidence is indirect or missing, keep working or report the gap.

## Response Pattern

When this skill affects the user-facing answer, keep the final response compact:

- What changed.
- What was verified.
- Any residual risk or command that could not be run.
- Where the user can inspect the work.

Do not paste the full radar report unless the user asks for it; summarize the high-signal findings.
