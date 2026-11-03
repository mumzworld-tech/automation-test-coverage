#!/usr/bin/env python3
"""Build tenure.json -- the suite before 1 April 2026 against the suite since.

mapping.json only measures coverage from 6 Sep 2026, when the case-by-case map
was first written. This reaches further back by reading automation_web_2.0 at
the start of every month since 1 April and applying TODAY's mapping to the suite
as it stood then:

  * a case's mapped tests that did not exist yet, or were hard-skipped then,
    do not count;
  * every mapped test present  -> the case keeps today's status;
    only some present          -> at best "partial";
    none present               -> "none".

That makes the early points an estimate -- today's evidence applied to an older
suite, never more generous than today -- and the report labels them so. Scope
is today's TestMO scope throughout, so every point shares one denominator.

Needs the full git history, so it runs locally, not in CI:

    python3 build_tenure.py ~/automation_web_2.0
"""
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import extract_tests as ex

HERE = Path(__file__).parent
START = "2026-04-01"
TZ = "+04:00"   # the team works to Dubai time; "before 1 April" means before midnight there
MONTHS = ["2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01"]

# Functional area of a test file, by name. Ordered: first match wins.
AREAS = [
    ("Now / super app", r"super_?app"),
    ("Gift registry", r"gift_registry"),
    ("Coupons & promotions", r"coupon"),
    ("Checkout & payments", r"checkout"),
    ("Cart", r"cart"),
    ("Wishlist", r"wishlist"),
    ("Filters & sort", r"filter|sort"),
    ("Categories", r"categor"),
    ("Account & sign-in", r"account|user|login|register|profile"),
    ("Home & search", r"home|search"),
]


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def area(path):
    stem = path.rsplit("/", 1)[-1]
    return next((name for name, rx in AREAS if re.search(rx, stem)), "Other")


def inventory_at(repo, sha):
    """The extractor's own parse of the suite at one commit."""
    ex.REF = sha
    ar_files = ex.arabic_ticket_files(repo)
    tests = []
    for platform, rel_dir in ex.PLATFORMS.items():
        try:
            files = ex.list_test_files(repo, rel_dir)
        except SystemExit:
            continue
        found = []
        for path in files:
            src = ex.git(repo, "show", f"{sha}:{path}")
            ar = path in ar_files or path in ex.LOCALE_AGNOSTIC or bool(ex.LOCALE_MARKER.search(src))
            found += ex.parse_file(src, path, platform, ar)
        ex.disambiguate(found)
        tests += found
    return tests


def snapshot(repo, day, mapping, cutoff=None):
    """The suite as it stood at `cutoff` (default: the start of `day`)."""
    cutoff = cutoff or f"{day}T00:00:00{TZ}"
    sha = git(repo, "rev-list", "-1", f"--before={cutoff}", "origin/main").strip()
    tests = inventory_at(repo, sha)
    by_ref = {t["ref"]: t for t in tests}
    # A ref can gain an "@file" suffix later, when a second file reuses the name.
    by_name = {(t["platform"], t["name"]): t for t in tests}

    def live(ref):
        t = by_ref.get(ref)
        if not t:
            platform, name = ref.split("::", 1)
            t = by_name.get((platform, name.split("@", 1)[0]))
        return t and (t["skip"] or {}).get("type") != "hard"

    share = {}
    for platform, key in (("web", "testmo_tests"), ("app", "app_testmo_tests")):
        covered = full = scope = 0
        for c in mapping[key]:
            if not c["in_scope"]:
                continue
            scope += 1
            refs, status = c["automated_tests"], c["coverage_status"]
            present = [r for r in refs if live(r)]
            if status == "none" or not present:
                continue
            covered += 1
            full += status == "full" and len(present) == len(refs)
        share[platform] = [covered, full, scope]

    hard = sum(1 for t in tests if (t["skip"] or {}).get("type") == "hard")
    return {
        "date": day, "sha": git(repo, "rev-parse", "--short", sha).strip(),
        "commit_date": git(repo, "log", "-1", "--format=%cs", sha).strip(),
        "web": share["web"], "app": share["app"],
        "tests": len(tests), "hard_skipped": hard,
        "ar_safe": sum(1 for t in tests if "ar" in t["locales"]),
        "platforms": dict(Counter(t["platform"] for t in tests)),
        "areas": dict(Counter(area(t["path"]) for t in tests)),
        "files": len({t["path"] for t in tests}),
        "reconstructed": True,
    }


def delivered(repo):
    """Merged pull requests on main since START, newest first, with their tickets."""
    out = []
    log = git(repo, "log", "origin/main", f"--since={START}T00:00:00{TZ}", "--first-parent",
              "--format=%H|%cs|%an|%s")
    for line in log.splitlines():
        sha, day, author, subject = line.split("|", 3)
        pr = re.search(r"\(#(\d+)\)\s*$", subject) or re.match(r"Merge pull request #(\d+)", subject)
        if not pr:
            continue
        if subject.startswith("Merge pull request"):
            body = git(repo, "log", "-1", "--format=%b", sha).strip().splitlines()
            subject = body[0] if body else subject
        title = re.sub(r"\s*\(#\d+\)\s*$", "", subject).strip()
        # Against the first parent: a merge commit lists no files of its own.
        changed = git(repo, "diff", "--name-only", f"{sha}^1", sha).split()
        test_files = [f for f in changed if re.search(r"^tests/.+/test_[^/]*\.py$", f)]
        out.append({
            "date": day, "pr": int(pr.group(1)), "title": title[:140],
            "tickets": sorted(set(re.findall(r"FALCONS-\d+", title))),
            "author": author,
            "areas": sorted({area(f) for f in test_files}),
            "app": any(f.startswith("tests/app/") for f in test_files),
            "web": any(f.startswith("tests/web/") for f in test_files),
        })
    return out


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "automation_web_2.0"
    mapping = json.loads((HERE / "mapping.json").read_text())

    # Month starts, then the end of every day the measured history recorded,
    # then main as it is now -- all by one method, so the line has no seam
    # where the estimate meets the record. The last point must equal today's
    # headline, which checks the method.
    recorded = sorted({h["date"] for h in mapping["metadata"].get("history", [])} - set(MONTHS))
    stops = [(d, None) for d in MONTHS] + [(d, f"{d}T23:59:59{TZ}") for d in recorded]
    points = []
    for day, cutoff in stops:
        p = snapshot(repo, day, mapping, cutoff)
        points.append(p)
        pct = lambda s: round(s[0] / s[2] * 100)
        print(f"  {day} @ {p['sha']}: {p['tests']:3d} tests, app {pct(p['app'])}%, mWeb {pct(p['web'])}%")

    cov = mapping["metadata"]["coverage"]
    last = points[-1]
    if (last["web"][0], last["app"][0]) != (cov["web"]["covered"], cov["app"]["covered"]):
        raise SystemExit(f"latest estimate {last['web']}/{last['app']} disagrees with mapping.json -- method broken")

    prs = delivered(repo)
    authors = Counter(git(repo, "log", "origin/main", f"--since={START}T00:00:00{TZ}",
                          "--format=%an").splitlines())
    before_authors = Counter(git(repo, "log", "origin/main", f"--before={START}T00:00:00{TZ}",
                                 "--format=%an").splitlines())
    out = {
        "start": START,
        "generated": date.today().isoformat(),
        "method": "Reconstructed: today's case mapping applied to automation_web_2.0 as it stood on each date. "
                  "A mapped test that did not exist yet, or was hard-skipped then, does not count; a case "
                  "with only some of its tests present counts as partial at best.",
        "points": points,
        "prs": prs,
        "tickets": len({t for p in prs for t in p["tickets"]}),
        "commits_since": sum(authors.values()),
        "commits_before": sum(before_authors.values()),
        "commit_authors_since": authors.most_common(),
        "first_commit": git(repo, "log", "origin/main", "--reverse", "--format=%cs").split()[0],
    }
    (HERE / "tenure.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(prs)} PRs merged since {START}, {out['tickets']} FALCONS tickets -> tenure.json")


if __name__ == "__main__":
    main()
