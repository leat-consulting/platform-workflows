#!/usr/bin/env python3
"""Apply and check the leat-consulting GitHub governance baseline.

GitHub Free has no organisation rulesets, so rulesets are defined once in
rulesets/*.json and applied to each repo listed in rulesets/assignments.json.
Organisation settings live in org-settings.json and actions-policy.json.

Usage:
  governance.py check   report every difference from the definitions; exit 1 if any
  governance.py apply   update the Actions policy and rulesets so they match the definitions

Requires `gh` authenticated (GH_TOKEN) with organisation administration read
for check, and repository administration write for apply.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULESET_KEYS = ("name", "target", "enforcement", "conditions", "bypass_actors", "rules")


def load(name):
    return json.loads((HERE / name).read_text())


def api(path, method="GET", body=None):
    cmd = ["gh", "api", "-X", method, path]
    if body is not None:
        cmd += ["--input", "-"]
    result = subprocess.run(
        cmd,
        input=json.dumps(body) if body is not None else None,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{method} {path} failed: {result.stdout.strip() or result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def desired_ruleset(name, repo):
    ruleset = load(f"rulesets/{name}.json")
    checks_file = HERE / "rulesets" / "required-checks" / f"{repo}.json"
    if ruleset["target"] == "branch" and checks_file.exists():
        checks = json.loads(checks_file.read_text())
        ruleset["rules"].append({
            "type": "required_status_checks",
            "parameters": {
                "strict_required_status_checks_policy": checks.get("strict", True),
                "do_not_enforce_on_create": False,
                "required_status_checks": checks["required_status_checks"],
            },
        })
    return ruleset


def subset_diff(want, have, path=""):
    """Return differences where `have` does not contain `want`.

    Extra keys GitHub adds with default values are ignored, but rules are
    matched by type in both directions so an extra live rule is reported.
    """
    diffs = []
    if isinstance(want, dict):
        if not isinstance(have, dict):
            return [f"{path}: expected object, found {have!r}"]
        for key, value in want.items():
            diffs += subset_diff(value, have.get(key), f"{path}.{key}" if path else key)
    elif isinstance(want, list) and path.endswith("rules"):
        have = have or []
        want_by_type = {r["type"]: r for r in want}
        have_by_type = {r["type"]: r for r in have}
        for rtype in sorted(set(want_by_type) | set(have_by_type)):
            if rtype not in have_by_type:
                diffs.append(f"{path}: missing rule {rtype}")
            elif rtype not in want_by_type:
                diffs.append(f"{path}: unexpected rule {rtype}")
            else:
                diffs += subset_diff(want_by_type[rtype], have_by_type[rtype], f"{path}[{rtype}]")
    elif isinstance(want, list):
        if not isinstance(have, list) or len(want) != len(have):
            return [f"{path}: expected {want!r}, found {have!r}"]
        if all(not isinstance(item, (dict, list)) for item in want):
            if sorted(want) != sorted(have):
                diffs.append(f"{path}: expected {want!r}, found {have!r}")
        else:
            for i, (w, h) in enumerate(zip(want, have)):
                diffs += subset_diff(w, h, f"{path}[{i}]")
    elif want != have:
        diffs.append(f"{path}: expected {want!r}, found {have!r}")
    return diffs


def live_rulesets(org, repo):
    summaries = api(f"repos/{org}/{repo}/rulesets?includes_parents=false&per_page=100") or []
    return {s["name"]: api(f"repos/{org}/{repo}/rulesets/{s['id']}") for s in summaries}


def check_org(org):
    diffs = []
    settings = load("org-settings.json")
    for endpoint, expected in settings["settings"].items():
        live = api(endpoint.replace("{org}", org))
        for key, value in expected.items():
            if live.get(key) != value:
                diffs.append(f"org {endpoint}.{key}: expected {value!r}, found {live.get(key)!r}")

    policy = load("actions-policy.json")
    live = api(f"orgs/{org}/actions/permissions")
    diffs += [f"actions permissions {d}" for d in subset_diff(policy["permissions"], live)]
    live = api(f"orgs/{org}/actions/permissions/selected-actions")
    diffs += [f"actions selected {d}" for d in subset_diff(policy["selected_actions"], live)]

    cs = settings["code_security"]
    defaults = api(f"orgs/{org}/code-security/configurations/defaults") or []
    match = [d for d in defaults if d["configuration"]["name"] == cs["configuration_name"]]
    if not match:
        diffs.append(f"code security: {cs['configuration_name']} is not a default configuration")
    else:
        config = match[0]["configuration"]
        if match[0]["default_for_new_repos"] != cs["default_for_new_repos"]:
            diffs.append(f"code security: default_for_new_repos is {match[0]['default_for_new_repos']!r}")
        if config["enforcement"] != cs["enforcement"]:
            diffs.append(f"code security: enforcement is {config['enforcement']!r}")
        for key, value in cs["features"].items():
            if config.get(key) != value:
                diffs.append(f"code security: {key} expected {value!r}, found {config.get(key)!r}")
    return diffs


def check_repos(org):
    diffs = []
    assignments = load("rulesets/assignments.json")
    cs_name = load("org-settings.json")["code_security"]["configuration_name"]
    repos = sorted(r["name"] for r in api(f"orgs/{org}/repos?per_page=100&type=all"))
    for repo in repos:
        attached = api(f"repos/{org}/{repo}/code-security-configuration")
        if not attached or attached["configuration"]["name"] != cs_name:
            diffs.append(f"{repo}: code security configuration {cs_name} not attached")
        expected = [name for name, targets in assignments.items() if repo in targets]
        if not expected:
            diffs.append(f"{repo}: not listed in rulesets/assignments.json")
        live = live_rulesets(org, repo)
        for name in expected:
            if name not in live:
                diffs.append(f"{repo}: ruleset {name} missing")
                continue
            want = {k: desired_ruleset(name, repo)[k] for k in RULESET_KEYS}
            diffs += [f"{repo}: ruleset {name} {d}" for d in subset_diff(want, live[name])]
        for name in sorted(set(live) - set(expected)):
            diffs.append(f"{repo}: unexpected ruleset {name}")
    return diffs


def plan_limited_report(org):
    lines = []
    for endpoint, fields in load("org-settings.json").get("plan_limited", {}).items():
        live = api(endpoint.replace("{org}", org))
        for key, spec in fields.items():
            if live.get(key) != spec["wanted"]:
                lines.append(f"{endpoint}.{key} is {live.get(key)!r}; not enforceable on this plan. {spec['reason']}")
    return lines


def bypass_report(org):
    lines = []
    for repo in sorted(set(sum(load("rulesets/assignments.json").values(), []))):
        suites = api(f"repos/{org}/{repo}/rulesets/rule-suites?rule_suite_result=bypass&time_period=month&per_page=100") or []
        if suites:
            lines.append(f"{repo}: {len(suites)} ruleset bypass(es) in the last month")
    return lines


def apply_actions_policy(org):
    policy = load("actions-policy.json")
    changed = 0
    if subset_diff(policy["permissions"], api(f"orgs/{org}/actions/permissions")):
        api(f"orgs/{org}/actions/permissions", "PUT", policy["permissions"])
        print("org: updated Actions permissions")
        changed += 1
    if subset_diff(policy["selected_actions"], api(f"orgs/{org}/actions/permissions/selected-actions")):
        api(f"orgs/{org}/actions/permissions/selected-actions", "PUT", policy["selected_actions"])
        print("org: updated allowed actions")
        changed += 1
    if not changed:
        print("org: Actions policy unchanged")
    return changed


def apply(org):
    assignments = load("rulesets/assignments.json")
    changed = apply_actions_policy(org)
    for name, repos in assignments.items():
        for repo in repos:
            want = desired_ruleset(name, repo)
            live = live_rulesets(org, repo)
            if name not in live:
                api(f"repos/{org}/{repo}/rulesets", "POST", want)
                print(f"{repo}: created ruleset {name}")
                changed += 1
            elif subset_diff({k: want[k] for k in RULESET_KEYS}, live[name]):
                api(f"repos/{org}/{repo}/rulesets/{live[name]['id']}", "PUT", want)
                print(f"{repo}: updated ruleset {name}")
                changed += 1
            else:
                print(f"{repo}: ruleset {name} unchanged")
    print(f"{changed} change(s) applied")


def main():
    org = load("org-settings.json")["org"]
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    if command == "apply":
        apply(org)
        return 0
    if command == "check":
        diffs = check_org(org) + check_repos(org)
        for line in diffs:
            print(f"DRIFT {line}")
        for line in plan_limited_report(org) + bypass_report(org):
            print(f"INFO  {line}")
        print("no drift" if not diffs else f"{len(diffs)} difference(s)")
        return 1 if diffs else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
