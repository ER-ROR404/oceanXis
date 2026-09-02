# Bugfix Workflow

Repeatable bug-fix workflow for agents.

## Steps

1. **Reproduce**: write a failing test that demonstrates the bug (RED). Use synthetic fixtures.
2. **Root-cause**: trace through the module without unrelated context. Do not guess; inspect.
3. **Fix (GREEN)**: smallest change that resolves the root cause. Respect boundaries/layering.
4. **Refactor (IMPROVE)**: remove any duplicate/incidental code touched.
5. **Regression guard**: keep the failing test (regression test) in the appropriate `tests/` dir.
6. **Update docs/contracts** if behavior changed (RULE 6, RULE 20).
7. **Verify**: module tests + coverage + `make lint` (+ `make test-all` for cross-cutting).

## Special domains

- **Data bug** → verify the dataset/manifest first (RULE 7 provenance), then fix pipeline.
- **Model bug** → checkpoint + manifest lineage; confirm the dataloader/split didn't leak (RULE 10–11).
- **API bug** → confirm response still validates against `contracts/api/*`.

Do not "fix" by weakening a test unless the test itself was wrong — justify in the commit.