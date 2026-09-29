#!/usr/bin/env bash
# Report drift between the governance definitions and live GitHub settings. Exits 1 on drift.
set -euo pipefail
exec python3 "$(dirname "$0")/governance.py" check
