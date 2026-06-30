# CI Usage

Use this reference when Change Radar should participate in pull request review, CI, or automated agent workflows.

## Machine-Readable Report

Emit JSON when another tool will consume the report:

```bash
python3 change-radar/scripts/change_radar.py --repo . --format json --output change-radar-report.json
```

Important fields:

- `overall_risk`: `P0`, `P1`, `P2`, or `P3`.
- `risk_score`: normalized score from 0 to 100.
- `risk_cues`: matched risk rules with files, contracts, and actions.
- `blocking_gaps`: evidence gaps that should be resolved or acknowledged.
- `verification_plan`: grouped `static`, `focused`, `broad`, and `manual` checks.
- `recommended_actions`: concrete follow-up work for the agent or reviewer.

## Risk Gates

Use a risk gate to stop unattended automation from silently merging high-risk changes:

```bash
python3 change-radar/scripts/change_radar.py --repo . --fail-on-risk P0
```

Recommended thresholds:

- `P0`: fail only production hazards such as auth, payments, persistence, or data integrity.
- `P1`: fail cross-contract changes such as public APIs, CI, dependencies, deployment, or runtime config.
- `P2`: fail local runtime changes; useful for strict review queues but noisy for normal CI.
- `P3`: fail almost every detected change; use only for experiments.

Exit code `3` means the risk gate failed. Exit code `2` means tool usage or repository access failed.

## Safe Fixtures

When tests or documentation intentionally include strings that look like secrets or focused tests, add an inline marker on the same added line:

```text
API_KEY = "fake_secret_fixture_value"  # change-radar: ignore-risk
```

Use the marker only for fixtures that are intentionally safe. It is a review signal, not a way to hide unresolved risk.

## GitHub Actions Example

```yaml
name: change-radar

on:
  pull_request:

jobs:
  radar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Generate report
        run: |
          python3 change-radar/scripts/change_radar.py \
            --repo . \
            --base origin/${{ github.base_ref }} \
            --format json \
            --output change-radar-report.json
      - name: Fail on production hazards
        run: |
          python3 change-radar/scripts/change_radar.py \
            --repo . \
            --base origin/${{ github.base_ref }} \
            --fail-on-risk P0
      - uses: actions/upload-artifact@v4
        with:
          name: change-radar-report
          path: change-radar-report.json
```

Use `P0` as a default because it catches serious hazards without blocking ordinary code changes. Raise to `P1` when the team wants stricter human review for public contracts and deployment paths.
