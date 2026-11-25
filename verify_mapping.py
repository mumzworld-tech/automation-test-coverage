#!/usr/bin/env python3
"""Fail the build if mapping.json is not internally consistent.

These are the invariants that make the report a source of truth rather than a
guess. Run by `make generate`; run it yourself after hand-editing mapping.json.
"""
import json
import sys
from pathlib import Path

m = json.loads((Path(__file__).parent / "mapping.json").read_text())
inventory = {t["ref"]: t for v in m["automated_tests"].values() for t in v}
problems = []

# Every ref in the inventory is unique and every mapped ref resolves to one.
declared = sum(len(v) for v in m["automated_tests"].values())
if declared != len(inventory):
    problems.append(f"{declared - len(inventory)} duplicate test refs -- disambiguation is broken")

for key, label in (("testmo_tests", "mWEB"), ("app_testmo_tests", "App")):
    for c in m[key]:
        cid = f"{label} C-{c['case_id']}"
        for ref in c["automated_tests"]:
            if ref not in inventory:
                problems.append(f"{cid}: ref '{ref}' does not exist on main")
        # Status and evidence must agree, in both directions.
        # "none" with refs is legitimate for a skipped-only case: scripts exist
        # but none of them run, so the case is not automated.
        if (c["coverage_status"] == "none" and c["automated_tests"]
                and not c.get("skipped_only") and not c.get("gated_only")):
            problems.append(f"{cid}: status 'none' with {len(c['automated_tests'])} live refs")
        if c["coverage_status"] != "none" and not c["automated_tests"]:
            problems.append(f"{cid}: status '{c['coverage_status']}' with no refs")
        if c["coverage_status"] != "none" and not (c.get("notes") or "").strip():
            problems.append(f"{cid}: '{c['coverage_status']}' with no note saying what is covered")
        # Not planned cases the suite automates are counted anyway (build_mapping.main);
        # the override must still carry real evidence.
        overridden = (c.get("scope_override") == "automated_but_not_planned"
                      and c["automated_flag"].upper() == "NOT PLANNED" and c["coverage_status"] != "none")
        if c["in_scope"] != (c["automated_flag"].upper() in ("YES", "NO") or overridden):
            problems.append(f"{cid}: in_scope disagrees with Automated='{c['automated_flag']}'")
        # Locales are derived, never hand-set.
        expected = set()
        for ref in c["automated_tests"]:
            expected.update(inventory[ref]["locales"] if ref in inventory else [])
        if set(c.get("locales") or ["en"]) != (expected or {"en"}):
            problems.append(f"{cid}: locales {c.get('locales')} do not match the mapped tests")

if problems:
    print(f"mapping.json has {len(problems)} problem(s):", file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    sys.exit(1)

cov = m["metadata"]["coverage"]
print(f"mapping.json OK -- {len(inventory)} tests, "
      f"mWEB {cov['web']['covered']}/{cov['web']['in_scope']} ({cov['web']['pct']}%), "
      f"App {cov['app']['covered']}/{cov['app']['in_scope']} ({cov['app']['pct']}%), "
      f"overall {cov['combined']['covered']}/{cov['combined']['in_scope']} ({cov['combined']['pct']}%)")
