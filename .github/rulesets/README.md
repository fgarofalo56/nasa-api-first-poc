# Branch ruleset

[`main-protection.json`](main-protection.json) is an importable **GitHub repository
ruleset** — the cloud equivalent of this repo's local pre-push hook, but enforced
server-side for everyone. It protects the default branch with:

| Rule | Effect |
|---|---|
| Pull request required | No direct pushes to `main`; changes land via PR. |
| 1 approval + **Code Owner** review | Security-sensitive paths need an owner's sign-off ([`../CODEOWNERS`](../CODEOWNERS)). |
| Required status checks (strict) | CI, CodeQL, dependency review, and the supply-chain scan must pass and be up to date. |
| Required signatures | Every commit on `main` must be **signed** (verified provenance of authorship). |
| Linear history + no force-push + no deletion | `main` history can't be rewritten or destroyed. |

> [!NOTE]
> Rulesets are a **repository setting**, not active just by living in the repo. Import once:
>
> ```bash
> gh api repos/fgarofalo56/nasa-api-first-poc/rulesets \
>   --method POST --input .github/rulesets/main-protection.json
> ```
>
> Adjust the `required_status_checks` contexts if you rename jobs, and review
> `required_signatures` for your contributors' commit-signing setup before enforcing.
