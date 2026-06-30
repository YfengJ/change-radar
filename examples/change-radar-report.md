# Change Radar Report

- Generated: 2026-06-30 00:00:00 UTC
- Repository: `/workspace/example-app`
- Git detected: yes
- Branch: `feature/checkout-session`
- Diff base: `HEAD`
- Overall risk: **P0**
- Risk score: **100/100**

## Project Signals

- Node package
- Python project

## Changed Files

- `package.json`
- `src/auth/session.ts`
- `src/api/checkout.ts`
- `src/api/checkout.test.ts`

## Blast Radius Snapshot

Top-level areas:

- src: 3
- package.json: 1

File types:

- .ts: 3
- .json: 1

## Risk Cues

- P1 Dependencies changed: `package.json`
- P1 Public API or integration changed: `src/api/checkout.ts`, `src/api/checkout.test.ts`
- P0 Auth, security, or money path changed: `src/auth/session.ts`, `src/api/checkout.ts`, `src/api/checkout.test.ts`
- P2 Executable source changed: `src/auth/session.ts`, `src/api/checkout.ts`
- P3 Tests changed: `src/api/checkout.test.ts`

## Contract Map

- Dependency graph
- Install and runtime compatibility
- Public API shape
- Integration boundary
- Authorization boundary
- Security or payment invariant
- Local runtime behavior
- Verification surface

## Blocking Gaps

- No blocking evidence gaps detected by heuristics.

## Nearby Tests

- `src/api/checkout.test.ts`

## Verification Plan

Static:

- `pnpm run typecheck`
- `pnpm run lint`

Focused:

- `pnpm run test`

Broad:

- `pnpm run build`

Manual:

- Review abuse cases, least privilege, duplicate submission, and failure safety.

## Recommended Actions

- Verify dependency install, lockfile consistency, build, and runtime compatibility.
- Verify request/response shape, status codes, error bodies, clients, and docs.
- Verify negative cases, privilege boundaries, token lifetime, idempotency, and replay behavior.
- Verify changed behavior with focused tests or a direct executable check.
- Review whether tests assert behavior rather than implementation details.

## Agent Checklist

- Confirm the user-visible goal and out-of-scope work.
- Identify touched contracts and label inferred contracts.
- Run or justify every verification item above.
- After edits, compare actual changed files against the intended blast radius.
- Do not claim completion without direct evidence for every explicit requirement.
