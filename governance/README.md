# Governance

The settings that make every `leat-consulting` repository readable by anyone and changeable only through reviewed pull requests, kept as code.

## Why this exists

The organisation is on GitHub Free. Organisation-level rulesets need GitHub Team, but repository rulesets are free on public repositories. So each ruleset is defined once here and applied to every repository by script, and a drift check makes sure nothing has been changed by hand.

## Files

| File | Purpose |
|---|---|
| `org-settings.json` | Organisation settings: 2FA, member privileges, workflow token defaults, fork PR approval, code security configuration |
| `actions-policy.json` | Which actions may run, and that every reference is pinned to a full commit SHA |
| `rulesets/default-branch.json` | Protection for `main` on every repository |
| `rulesets/release-tags.json` | Protection for `v*` tags where releases are published |
| `rulesets/assignments.json` | Which rulesets apply to which repositories |
| `rulesets/required-checks/<repo>.json` | Status checks required on a repository's `main`, merged into `default-branch` at apply time |
| `governance.py` | Implements `apply` (Actions policy and rulesets) and `check` (everything) |
| `apply.sh`, `check.sh` | Entry points |

## What the rules enforce

On `main` in every repository:

- Changes arrive only through a pull request. Direct pushes, force pushes and deletion are blocked.
- One approving review from a code owner is required. `.github/CODEOWNERS` makes the organisation owner the code owner for every path.
- Approvals are dismissed when new commits are pushed, and the most recent push must be approved by someone other than the person who pushed it.
- Review threads must be resolved, history stays linear, and merges are squash only.
- The only bypass is the organisation owner role, in pull-request-only mode. It exists because a pull request written by the only human member could otherwise never be merged. It cannot be used to push directly, and each use is recorded on the pull request and reported by `check.sh`.

On `v*` tags in `platform-workflows` and `demo-app`: only the owner may create, move or delete them.

Organisation-wide:

- Only GitHub-owned actions and actions in this organisation may run, plus any listed in `actions-policy.json`, and every reference must be pinned to a full commit SHA.
- The default workflow token is read-only, and workflows cannot approve pull requests.
- Workflows on pull requests from outside contributors need approval before they run.
- The `leat-baseline` code security configuration (dependency graph, Dependabot alerts and security updates, secret scanning, push protection, private vulnerability reporting) is enforced on every repository and applied to new ones automatically.

## Usage

Both scripts need `gh` and a token in `GH_TOKEN` with organisation administration permissions. Use a short-lived token created for the purpose (see below), never a day-to-day credential.

```sh
./check.sh   # prints each difference as DRIFT and exits 1 if there are any
./apply.sh   # updates the Actions policy and rulesets to match; a second run makes no changes
```

Settings the API does not change: the REST API accepts but ignores `members_can_delete_repositories` and `members_can_change_repo_visibility`. They are listed under `ui_only` in `org-settings.json`. `check.sh` still reports them, but they must be set by hand under Settings, Member privileges.

Settings the plan does not allow: only GitHub Enterprise Cloud can restrict outside collaborator invites to owners. This is listed under `plan_limited` in `org-settings.json`, and `check.sh` reports it as INFO rather than drift. It matters little while the owner is the only member, since the Claude Apps are not members. Revisit it before adding a member.

## Admin tokens for settings changes

No admin credential is kept on the workstation between settings changes. When one is needed:

1. In GitHub, go to Settings, Developer settings, Personal access tokens, Fine-grained tokens, and generate a new token.
2. Resource owner: `leat-consulting`. Expiration: 7 days or less.
3. Repository access: all repositories. Repository permissions: Administration read and write (Metadata read is added automatically).
4. Organisation permissions: Administration read and write.
5. Save it to a file readable only by you, run the change, then run `check.sh` to confirm there is no drift.
6. Delete the token in GitHub and remove the file.

For `check.sh` alone, read-only Administration permissions are enough.

## Evidence

### The rules bind the organisation owner's admin token

A direct push to `demo-app` `main` using an organisation-admin token, on 2026-09-29:

```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Changes must be made through a pull request.
 ! [remote rejected] main -> main (push declined due to repository rule violations)
```

### Drift is detected

With `demo-app`'s required approvals lowered to zero in the ruleset:

```
DRIFT demo-app: ruleset default-branch rules[pull_request].parameters.required_approving_review_count: expected 1, found 0
```

Running `apply.sh` restored it.

### The Claude App cannot administer

Claude Code works through the `leat-claude` GitHub App, with contents, pull requests and workflows write, and checks and actions read. It has no administration, secrets, environments or members permission. With an App installation token, on 2026-09-29:

| Attempt | Result |
|---|---|
| Update the `demo-app` default-branch ruleset | 403 Resource not accessible by integration |
| Delete that ruleset | 403 Resource not accessible by integration |
| Change repository settings | 403 Resource not accessible by integration |
| List Actions secrets | 403 Resource not accessible by integration |
| Change the organisation Actions policy | 403 Resource not accessible by integration |

The App is not a code owner and is not a bypass actor, so its reviews cannot satisfy the ruleset. See `bin/` for how its short-lived tokens are minted.
