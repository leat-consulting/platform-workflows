#!/usr/bin/env bash
# Apply the Actions policy, and rulesets from rulesets/*.json to the repos in rulesets/assignments.json.
set -euo pipefail
exec python3 "$(dirname "$0")/governance.py" apply
