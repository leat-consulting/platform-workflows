#!/usr/bin/env bash
# Apply rulesets from rulesets/*.json to the repos in rulesets/assignments.json.
set -euo pipefail
exec python3 "$(dirname "$0")/governance.py" apply
