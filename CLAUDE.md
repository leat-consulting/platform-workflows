# Leat Consulting: platform-workflows

## Context
Leat Consulting builds secure delivery platforms for scaling engineering teams.
This repository holds the reusable GitHub Actions workflows that every Leat
repository calls, and the governance definitions for the organisation. It is
public and is part of the demo: treat every file as something a prospective
client will read.

## Rules
- Every workflow sets top-level `permissions: {}` or read-only, and every job declares minimal `permissions:` with a comment on each write permission.
- Every job that runs steps declares `timeout-minutes:`.
- Every `uses:` is pinned to a full commit SHA with a version comment. The organisation enforces this.
- Checkout steps set `persist-credentials: false`.
- Never use `pull_request_target` or `workflow_run` for anything that touches pull request code.
- Pass untrusted values (inputs, event fields) to `run:` steps through `env:`, never by `${{ }}` interpolation in the script.
- Prefer GitHub-owned actions. For scanners, download release binaries by version and SHA-256 rather than adding a third-party action. Any new third-party action needs an entry in `governance/actions-policy.json`.
- No secrets in code, logs or fixtures. Planted problems for scanner tests live only on the `fixtures/bad` branch.
- Prose: British English, measured tone, no exclamation marks, no em-dashes.

## Checks to run before committing
```sh
actionlint
zizmor --persona pedantic .
python3 scripts/lint-workflows.py
```

## Workflow
- Plan before implementing. Show the plan and wait for approval.
- Small commits with clear messages. Open a pull request as `leat-claude[bot]`; `main` only changes through reviewed pull requests.
- Update `docs/usage.md` whenever a workflow's inputs, outputs or required permissions change.
- Releases: dispatch `release.yml` to draft, and the owner publishes.
