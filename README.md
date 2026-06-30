# Change Radar

Change Radar is a Codex skill for safer AI-assisted coding. It makes an agent map the blast radius, touched contracts, hidden risk, and verification evidence before it changes code or claims that work is done.

AI coding is fast. Change Radar is the seatbelt.

## Why This Matters

Modern coding agents are very good at producing patches, but the expensive failures usually happen around the patch: missed contracts, weak test selection, accidental scope drift, migrations, auth paths, deployment files, generated artifacts, and vague final answers.

Change Radar gives the agent a repeatable engineering ritual:

- Build a concise change brief.
- Sweep the repository for changed files, project signals, and risk cues.
- Map affected contracts.
- Select tests that actually prove the change.
- Audit completion requirement by requirement.

## Install

Clone the repository and copy the skill folder into your Codex skills directory:

```bash
git clone https://github.com/YfengJ/change-radar.git
cp -R change-radar/change-radar ~/.codex/skills/
```

Restart Codex if your environment does not hot-load new skills.

## Use

Invoke the skill explicitly when starting non-trivial code work:

```text
Use $change-radar to implement this API change safely.
```

Or:

```text
Use $change-radar to review this diff and tell me what tests actually matter.
```

## What Is Inside

```text
change-radar/
├── SKILL.md
├── agents/openai.yaml
├── scripts/change_radar.py
└── references/
    ├── risk-taxonomy.md
    └── test-selection.md
```

The bundled scanner is dependency-free Python:

```bash
python3 change-radar/scripts/change_radar.py --repo /path/to/project
```

It reports:

- Changed files from git diff, staged changes, and untracked files.
- Common project manifests.
- Risk cues for dependencies, CI, migrations, auth, APIs, UI, generated files, and docs.
- Nearby test files by naming convention.
- Suggested verification commands from project manifests.

See [examples/change-radar-report.md](examples/change-radar-report.md) for sample output.

## Good Fit

Use Change Radar for:

- Feature implementation.
- Bug fixes.
- Refactors.
- Pull request review.
- CI failure fixes.
- Migration, auth, payment, API, or deployment changes.
- Any moment where "tests passed" is too vague to be trustworthy.

## Not A Replacement For Judgment

The scanner is deliberately heuristic. Its job is to wake the agent up, not to decide for it. The skill tells the agent to label inferred contracts, choose verification based on actual risk, and be honest when evidence is missing.

## License

MIT
