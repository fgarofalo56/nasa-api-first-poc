# Branch ruleset

[`main-protection.json`](main-protection.json) is an importable **GitHub repository
ruleset** — the cloud equivalent of this repo's local pre-push hook, but enforced
server-side for everyone. It is tuned for a **solo maintainer with automated merges**:
`main` is protected from rewrite and destruction, every change still lands through a PR
that must pass CI, and the [`automerge`](../workflows/automerge.yml) workflow can land
green PRs without a human gate.

| Rule | Effect |
|---|---|
| Pull request required | No direct pushes to `main`; changes land via PR. |
| 0 required approvals | Auto-merge can land a green PR; you can still review/approve any PR voluntarily. |
| Required status checks | `lint-test` and `compose-smoke` (the CI jobs) must pass before a PR merges. |
| Linear history + no force-push + no deletion | `main` history can't be rewritten or destroyed. |
| Squash-only merges | Keeps `main` linear and matches the auto-merge workflow. |
| Admin bypass | The repository admin (you) can push directly in a break-glass situation. |

> [!NOTE]
> Rulesets are a **repository setting**, not active just by living in the repo. They
> require a **public** repository or a **GitHub Pro/Team** plan. Import once:
>
> ```bash
> gh api repos/fgarofalo56/nasa-api-first-poc/rulesets \
>   --method POST --input .github/rulesets/main-protection.json
> ```

> [!TIP]
> **Why these settings (vs. a stricter team policy).** A solo maintainer can't approve
> their own PR, so requiring an approval or a Code Owner review would deadlock both you
> and the auto-merge workflow. Likewise, *required signatures* would block every commit
> unless you've set up verified commit signing. When this repo gains other maintainers,
> tighten it back up:
>
> - bump `required_approving_review_count` to `1` and set `require_code_owner_review: true`,
> - add the security checks (`Analyze (python)`, `Analyze (javascript-typescript)`,
>   `dependency-review`, `Trivy scan + SBOM`) to `required_status_checks` — and switch
>   `automerge` to wait on **all** checks, not just CI,
> - add `{ "type": "required_signatures" }` once contributors sign their commits,
> - drop the admin entry from `bypass_actors` for no-exceptions enforcement.
>
> Adjust the `required_status_checks` contexts if you rename CI jobs.
