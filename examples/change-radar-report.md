# Change Radar Report

- Generated: 2026-06-30 00:00:00 UTC
- Repository: `/workspace/example-app`
- Git detected: yes
- Branch: `feature/checkout-session`
- Diff base: `HEAD`

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

- Dependencies changed: `package.json`
- Public API or integration changed: `src/api/checkout.ts`, `src/api/checkout.test.ts`
- Auth, security, or money path changed: `src/auth/session.ts`, `src/api/checkout.ts`, `src/api/checkout.test.ts`
- Tests changed: `src/api/checkout.test.ts`

## Nearby Tests

- `src/api/checkout.test.ts`

## Suggested Verification Commands

- `pnpm run typecheck`
- `pnpm run lint`
- `pnpm run test`
- `pnpm run build`

## Agent Checklist

- Confirm the user-visible goal and out-of-scope work.
- Identify touched contracts and label inferred contracts.
- Choose focused verification before broad verification.
- After edits, compare actual changed files against the intended blast radius.
- Do not claim completion without direct evidence for every explicit requirement.
