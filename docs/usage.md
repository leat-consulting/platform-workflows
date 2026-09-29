# Using the workflows

Each workflow is called with `uses:` from a job in your own workflow. Pin the reference to a full commit SHA of a published release, with the version in a comment. The organisation refuses unpinned references, and Dependabot proposes updates as pull requests.

```yaml
uses: leat-consulting/platform-workflows/.github/workflows/node-ci.yml@<commit-sha> # v1.0.0
```

Replace `<commit-sha>` with the commit of the release you want, from the [releases page](https://github.com/leat-consulting/platform-workflows/releases). Each calling job must grant the permissions listed for the workflow. A reusable workflow can never receive more than its caller grants.

## node-ci

Installs dependencies from `package-lock.json` with lifecycle scripts turned off, then runs the `lint`, `test` and `build` scripts in that order, skipping any that are not defined. There is no dependency cache, because a cache written by one run could be read by a later release build.

**Caller permissions:** `contents: read`.

| Input | Type | Default | Description |
|---|---|---|---|
| `node-version` | string | `24` | Node.js version to install. |
| `working-directory` | string | `.` | Directory containing package.json and package-lock.json. |
| `ignore-scripts` | boolean | `true` | Skip dependency lifecycle scripts during install. Turn off only if a dependency genuinely needs them. |
| `artifact-path` | string | empty | Path, relative to working-directory, to upload after the build. Leave empty to upload nothing. |
| `artifact-name` | string | `build` | Name of the uploaded artifact. |

| Output | Description |
|---|---|
| `artifact-name` | Name of the uploaded artifact, or empty if nothing was uploaded. |

```yaml
jobs:
  ci:
    uses: leat-consulting/platform-workflows/.github/workflows/node-ci.yml@<commit-sha> # v1.0.0
    permissions:
      contents: read
    with:
      artifact-path: dist
```

## security-scan

Runs five scanners and fails in `enforce` mode if any of them reports a finding. `report` mode records the same findings without failing, which helps when adopting the scan on an existing repository.

| Scanner | What it checks | Scope |
|---|---|---|
| gitleaks | Secrets in commits | Commits in the pull request or push only |
| Dependency review | Newly added dependencies with known vulnerabilities | Pull requests, or `base-ref`..`head-ref` |
| trivy | Known vulnerabilities in lockfiles, and misconfiguration in files such as Dockerfiles | `working-directory` |
| actionlint | Errors in workflow files | `.github/workflows` |
| zizmor | Security problems in workflows and actions, such as template injection and excessive permissions | Whole repository, using `zizmor.yml` if present |

The scanners are downloaded as release binaries and checked against SHA-256 checksums recorded in the workflow. Findings, without secret values, are written to the job summary.

**Caller permissions:** `contents: read`.

| Input | Type | Default | Description |
|---|---|---|---|
| `mode` | string | `enforce` | enforce: fail on any finding. report: record findings without failing. |
| `ref` | string | empty | Git ref to check out and scan. Defaults to the ref that triggered the caller. |
| `base-ref` | string | empty | Base ref for secret scanning and dependency review. Defaults to the pull request base or the previous push. |
| `head-ref` | string | empty | Head ref for secret scanning and dependency review. Used only with base-ref. |
| `working-directory` | string | `.` | Directory for the filesystem vulnerability and misconfiguration scan. |
| `trivy-severity` | string | `HIGH,CRITICAL` | Comma-separated severities that count as findings in the filesystem scan. |
| `dependency-review-fail-on` | string | `high` | Lowest advisory severity that counts as a finding in dependency review (low, moderate, high, critical). |
| `zizmor-min-severity` | string | `low` | Lowest zizmor severity that counts as a finding (informational, low, medium, high). |

| Output | Description |
|---|---|
| `gitleaks-findings` | Number of secrets found in the commits scanned. |
| `dependency-findings` | Number of vulnerable dependency changes, or 0 when dependency review did not run. |
| `trivy-findings` | Number of vulnerabilities and failed misconfiguration checks at the configured severities. |
| `actionlint-findings` | Number of actionlint errors in workflow files. |
| `zizmor-findings` | Number of zizmor findings at or above the configured severity. |

```yaml
jobs:
  scan:
    uses: leat-consulting/platform-workflows/.github/workflows/security-scan.yml@<commit-sha> # v1.0.0
    permissions:
      contents: read
```

To accept a gitleaks finding that is not a secret, add a `.gitleaks.toml` allowlist or a `.gitleaksignore` entry. To accept a zizmor finding, add an inline `# zizmor: ignore[<audit>]` comment with a reason.

## container-build

Builds on native `ubuntu-24.04` (amd64) and `ubuntu-24.04-arm` (arm64) runners, without emulation.

- With `push: true`, each architecture is pushed by digest, combined into one multi-arch index tagged with the commit SHA and branch, and build provenance is attested for the index digest and verified before the job ends. Deploy by the `digest` output, not by tag.
- With `push: false`, both architectures are built and nothing is pushed. Use this on pull requests.

**Caller permissions:** `contents: read` when `push` is false. With `push: true`, also `packages: write`, `id-token: write` and `attestations: write`.

| Input | Type | Default | Description |
|---|---|---|---|
| `image` | string | required | Image name without tag, for example ghcr.io/leat-consulting/demo-app. Must be lower case. |
| `context` | string | `.` | Build context directory. |
| `dockerfile` | string | empty | Path to the Dockerfile. Defaults to Dockerfile in the context. |
| `push` | boolean | `false` | Push, attest and verify the image. Leave false for pull request builds. |

| Output | Description |
|---|---|
| `image` | Image name, without tag or digest. |
| `digest` | The sha256 digest of the multi-arch index. Empty when push is false. |

```yaml
jobs:
  image-check:
    if: github.event_name == 'pull_request'
    uses: leat-consulting/platform-workflows/.github/workflows/container-build.yml@<commit-sha> # v1.0.0
    permissions:
      contents: read
    with:
      image: ghcr.io/leat-consulting/demo-app

  image:
    if: github.event_name == 'push'
    uses: leat-consulting/platform-workflows/.github/workflows/container-build.yml@<commit-sha> # v1.0.0
    permissions:
      contents: read
      packages: write # push images to GHCR
      id-token: write # OIDC token for Sigstore signing
      attestations: write # store the provenance attestation
    with:
      image: ghcr.io/leat-consulting/demo-app
      push: true
```

Anyone can check an image the same way the workflow does:

```sh
gh attestation verify oci://ghcr.io/leat-consulting/demo-app@sha256:<digest> \
  --repo leat-consulting/demo-app \
  --signer-workflow leat-consulting/platform-workflows/.github/workflows/container-build.yml
```

## pages-deploy

Downloads a built site from an artifact in the same run, packages it, attests the package, verifies the attestation, then deploys exactly that package to GitHub Pages. The deploy job runs only on the default branch, and only through the caller's `github-pages` environment.

Set up the calling repository first: enable Pages with source "GitHub Actions", and limit the `github-pages` environment to the default branch.

**Caller permissions:** `contents: read`, `id-token: write`, `attestations: write`, `pages: write`.

| Input | Type | Default | Description |
|---|---|---|---|
| `artifact-name` | string | required | Name of an artifact from the same run that contains the built site (for example from node-ci). |
| `deploy` | boolean | `true` | Deploy after verification. Set false to package, attest and verify only. |

| Output | Description |
|---|---|
| `page-url` | URL of the deployed site, or empty if nothing was deployed. |

```yaml
jobs:
  build:
    uses: leat-consulting/platform-workflows/.github/workflows/node-ci.yml@<commit-sha> # v1.0.0
    permissions:
      contents: read
    with:
      artifact-path: dist
      artifact-name: site

  deploy:
    needs: build
    uses: leat-consulting/platform-workflows/.github/workflows/pages-deploy.yml@<commit-sha> # v1.0.0
    permissions:
      contents: read
      id-token: write # OIDC token for signing and deployment
      attestations: write # store the provenance attestation
      pages: write # deploy to GitHub Pages
    with:
      artifact-name: site
```

## Releases

1. Dispatch the `release` workflow on `main` with the next version, for example `v1.1.0`. It checks the version is new and creates a draft release with generated notes. Drafts do not create tags.
2. The owner reviews the draft and publishes it, which creates the tag. Only the owner can create `v*` tags, and published releases are immutable.
3. Dependabot proposes the new commit SHA to each calling repository as a pull request.
