# fixtures/bad

This branch holds deliberate problems for the `security-scan` self-test in `platform-workflows`. It is never merged. Each file below must be detected, or the self-test fails:

| File | Planted problem | Scanner |
|---|---|---|
| `config/example.env` | A high-entropy value assigned to an API key variable. It is random and grants access to nothing. | gitleaks |
| `vulnerable/package-lock.json` | `lodash` 4.17.20, affected by CVE-2021-23337 (high) | dependency review, trivy |
| `.github/workflows/unsafe.yml` | Template injection from an issue title, an unpinned action and an invalid runner label | zizmor, actionlint |

The workflow file cannot run. It triggers only on issue events, which run workflows from the default branch alone. The organisation also blocks unpinned actions.
