#!/usr/bin/env python3
"""Check the workflow rules in CLAUDE.md that actionlint and zizmor do not.

For every workflow under .github/workflows:
  - a top-level `permissions:` block exists
  - no `pull_request_target` or `workflow_run` trigger is used
  - every job declares `permissions:`
  - every job that runs steps declares `timeout-minutes:`
  - every actions/checkout step sets `persist-credentials: false`

Exits 1 and lists each violation if any are found.
"""

import json
import subprocess
import sys
from pathlib import Path

FORBIDDEN_TRIGGERS = {"pull_request_target", "workflow_run"}


def load(path):
    try:
        import yaml
    except ImportError:
        # GitHub-hosted runners ship yq; use it when PyYAML is unavailable.
        return json.loads(subprocess.check_output(["yq", "-o=json", ".", str(path)]))
    return yaml.safe_load(path.read_text())


def triggers(doc):
    # PyYAML reads the bare key `on` as boolean True.
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    return set(on or {})


def lint(path):
    problems = []
    doc = load(path) or {}
    if "permissions" not in doc:
        problems.append("no top-level permissions block")
    for trigger in sorted(triggers(doc) & FORBIDDEN_TRIGGERS):
        problems.append(f"uses forbidden trigger {trigger}")
    for job_id, job in (doc.get("jobs") or {}).items():
        if "permissions" not in job:
            problems.append(f"job {job_id}: no permissions block")
        if "steps" in job and "timeout-minutes" not in job:
            problems.append(f"job {job_id}: no timeout-minutes")
        for index, step in enumerate(job.get("steps") or []):
            uses = step.get("uses", "")
            if uses.startswith("actions/checkout@"):
                if (step.get("with") or {}).get("persist-credentials") is not False:
                    problems.append(f"job {job_id} step {index + 1}: checkout without persist-credentials: false")
    return [f"{path}: {p}" for p in problems]


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    files = sorted((root / ".github" / "workflows").glob("*.y*ml"))
    problems = [p for f in files for p in lint(f)]
    for problem in problems:
        print(problem)
    print(f"{len(files)} workflow(s) checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
