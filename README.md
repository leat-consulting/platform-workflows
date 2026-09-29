# platform-workflows

Reusable GitHub Actions workflows from Leat Consulting: CI, security scanning, attested container builds, verified static site deploys and, later, AI-assisted review.

This repository is built in the open. Every change arrives through a reviewed pull request, and the rules that enforce this are defined in [`governance/`](governance/).

## Workflows

| Workflow | What it does |
|---|---|
| [`node-ci.yml`](.github/workflows/node-ci.yml) | Installs from the lockfile with lifecycle scripts off, then runs lint, test and build |
| [`security-scan.yml`](.github/workflows/security-scan.yml) | Secret scanning, dependency review, vulnerability and misconfiguration scanning, workflow linting and a workflow security audit |
| [`container-build.yml`](.github/workflows/container-build.yml) | Native amd64 and arm64 builds, one multi-arch image, build provenance attested and verified, digest as output |
| [`pages-deploy.yml`](.github/workflows/pages-deploy.yml) | Packages a static site, attests and verifies it, then deploys exactly that package to GitHub Pages |

See [`docs/usage.md`](docs/usage.md) for inputs, outputs, required permissions and caller examples.

## How they are kept honest

- Every action is pinned to a full commit SHA, and the organisation refuses to run anything that is not.
- Every job declares minimal permissions and a timeout.
- Scanners are downloaded as release binaries and checked against recorded SHA-256 checksums, so no third-party action wrapper is trusted.
- [`self-test.yml`](.github/workflows/self-test.yml) runs every workflow against fixtures on each pull request. It also scans the [`fixtures/bad`](https://github.com/leat-consulting/platform-workflows/tree/fixtures/bad) branch, which holds a planted secret, a vulnerable dependency and an unsafe workflow, and fails unless every scanner detects them.
- Releases are immutable `vX.Y.Z` tags published by the owner. Callers pin a release by commit SHA and receive updates as Dependabot pull requests.
