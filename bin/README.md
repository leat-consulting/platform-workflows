# bin

How Claude Code authenticates to GitHub on the workstation.

Claude Code acts as the `leat-claude` GitHub App, never as the owner's account. Its commits and pull requests are attributed to `leat-claude[bot]`, so the owner can review and approve them.

| Script | Purpose |
|---|---|
| `gh-app-token` | Signs a JWT with the App's private key and exchanges it for an installation token, which expires after one hour. Refuses to run unless the key file is mode 600 or 400. Writes nothing to disk. |
| `gh-as-app` | Runs `gh` with a freshly minted token. |
| `git-credential-leat-app` | Git credential helper that supplies a fresh token for HTTPS pushes. |

The private key lives at `~/.config/leat/leat-claude.pem`, outside any repository. It is never stored as an Actions secret or used in CI.
