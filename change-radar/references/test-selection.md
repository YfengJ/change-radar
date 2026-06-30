# Test Selection

Use this reference to turn a risk map into a verification plan. Prefer evidence that would actually catch the failure mode, not commands that merely look impressive.

## Selection Order

1. Run the smallest focused test that proves the requested behavior.
2. Run the nearest regression test for the touched contract.
3. Run static checks when signatures, types, lint-sensitive code, config, or generated files changed.
4. Run broader suites when the blast radius crosses modules or public contracts.
5. Add manual verification only for behavior that automated tests cannot observe cheaply.

## Command Heuristics

- Node: prefer project scripts from `package.json`, especially `typecheck`, `lint`, `test`, and `build`.
- Python: prefer `python3 -m pytest` when pytest is configured, or `python3 -m unittest discover -s tests` for standard-library test suites with a `tests/` directory; add `ruff`, `mypy`, or format checks when configured.
- Go: use `go test ./...`; add race tests only when concurrency changed.
- Rust: use `cargo test`; add `cargo clippy --all-targets --all-features` for shared libraries.
- Java/Kotlin: use Maven or Gradle test tasks already present in the repo.
- .NET: use `dotnet test`.
- Frontend UI: combine unit/component tests with a browser or screenshot check when layout, interaction, or accessibility changed.

## Coverage Traps

- A passing broad suite is weak evidence if no test touches the changed contract.
- Snapshot updates are weak evidence unless the semantic change is reviewed.
- Type checks do not prove runtime behavior.
- Unit tests do not prove integration boundaries.
- Manual checks do not prevent regressions unless they are documented or converted into tests.
- Generated clients or schemas need regeneration checks, not just source tests.

## When To Add Tests

Add or update tests when:

- The change fixes a bug that can recur.
- The touched behavior has no direct existing coverage.
- The code crosses a public, persistence, auth, payment, or deployment boundary.
- The implementation has branching logic with meaningful edge cases.
- The user asked for behavior that can be stated as an assertion.

Do not add tests only to increase file count. Add tests that would fail for the bug or regression you are trying to prevent.

## Verification Statement Template

Use this structure in final answers:

```text
Verified:
- <command>: <what it proves>
- <manual check or inspection>: <what it proves>

Not run:
- <command>: <why not, and residual risk>
```
