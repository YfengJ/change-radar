# Risk Taxonomy

Use this reference when a requested code change has more than local implementation risk. The goal is to name the risk precisely enough to choose verification.

## Risk Levels

- P0: Can break production, data integrity, authentication, payments, deployment, or a core user journey.
- P1: Can break a public contract, important workflow, migration path, performance budget, or cross-package behavior.
- P2: Local behavior risk that is covered by focused tests or obvious manual checks.
- P3: Low-risk docs, comments, or isolated cleanup with no runtime effect.

Risk level is about blast radius and reversibility, not file count.

## Common Risk Cues

- Dependency or lockfile changes: verify install, build, and runtime compatibility.
- Database migrations or schemas: verify upgrade path, rollback story, seed data, and old/new code compatibility.
- Auth, permission, or session code: verify negative cases, token lifetime, privilege boundaries, and existing users.
- Payment or billing paths: verify idempotency, webhooks, retries, rounding, and duplicate events.
- Public APIs: verify request/response shape, status codes, error body, versioning, generated clients, and docs.
- Serialization or events: verify producers and consumers, backward compatibility, missing fields, and replay behavior.
- Config and environment variables: verify defaults, missing values, local/dev/prod differences, and secret handling.
- Build, CI, or deployment: verify clean checkout behavior, cache assumptions, and release ordering.
- UI or accessibility: verify loading, empty, error, disabled, keyboard, small viewport, and screen reader relevant states.
- Performance-sensitive code: verify algorithmic complexity, query count, payload size, and hot-path allocations.
- Generated artifacts: verify source-of-truth regeneration and avoid hand-edited generated files unless expected.
- Possible secrets in added lines: remove the secret, rotate it if real, or prove it is a safe fixture.
- Focused or skipped tests in added lines: remove `.only` and justify or restore skipped coverage.

## Contract Questions

Ask these before editing high-risk areas:

- Who calls this code, and what do they assume?
- What data created by old code must new code still read?
- What happens when the new code talks to old services or clients?
- Are failures safe, retriable, observable, and reversible?
- Which tests would fail if this contract broke?
- Which required evidence cannot be produced locally?

## Escalation

Escalate the verification plan when any of these are true:

- The change crosses service, package, process, or persistence boundaries.
- The change touches auth, money, deployment, migration, or secrets.
- Existing tests do not exercise the touched contract.
- The implementation relies on undocumented behavior.
- A rollback would require data repair or user communication.
- The diff appears to add credentials, focused tests, or skipped tests.
