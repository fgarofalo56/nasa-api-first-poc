<!-- Thanks for contributing! Keep the loop green and the docs polished. -->

## What & why

<!-- One or two sentences: what does this change do, and why? Link any issue (Closes #123). -->

## Type of change

- [ ] `feat` — new capability
- [ ] `fix` — bug fix
- [ ] `docs` — documentation only
- [ ] `chore` / `ci` — tooling, deps, pipeline
- [ ] `refactor` / `test` — no behaviour change

## Verification

- [ ] `ruff format --check .` and `ruff check .` pass
- [ ] `pytest -q` passes (and `pytest -q -m integration` if the stack is up)
- [ ] `docker compose --profile core up` still comes up healthy (if touched)

## Security & assurance checklist

- [ ] **No secrets** committed — config stays in the gitignored `.env`; no keys/tokens/passwords in the diff
- [ ] **Synthetic data only** — no real/controlled data or real-data ingestion paths introduced
- [ ] **Zero-move preserved** — Postgres/DAB stay on the `internal` network; the only path to data is still Kong
- [ ] **New dependencies** are justified and licence-compatible (Dependency Review will gate the PR)
- [ ] **New/changed workflows** keep least-privilege `permissions:` (zizmor will check)
- [ ] **Docs updated** to match behaviour, and any Markdown I touched is polished/consistent

## Notes for reviewers

<!-- Anything reviewers (human or Copilot) should focus on. -->
