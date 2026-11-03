#!/usr/bin/env python3
"""Build runs.json -- every FALCON run published to the Allure Docker Service.

The FALCON runner (dashboard -> Lambda -> EC2 -> BrowserStack) uploads each
run's results to Allure, one project per country + OS. That service is the
complete record of what ran, so this reads it directly instead of keeping a
hand-maintained list:

  GET /projects                                   -> every project id
  GET /projects/<id>/reports/latest/widgets/summary.json      -> counts, start, duration
  GET /projects/<id>/reports/latest/widgets/environment.json  -> ENVIRONMENT, COUNTRY,
                                                                 OS, RUN_NATIVE_APP ...

Only full regressions count. A run is one when it ran at least 85% of its
suite as it stood then -- measured per suite and country against the largest
run in the 45 days up to it, because mWeb UAE carries more tests than KSA and
both suites grew from ~30 to ~107 tests. Everything smaller is "partial": a
targeted re-run while a fix is checked, or a run that ended early.

Pass rate is passed / executed, where executed = passed + failed + broken.
Skips are left out because their count drifts between runs and would move the
figure on its own. Broken counts as failed.

    python3 build_runs.py
"""
import json
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).parent
BASE = "https://allure-reports.mumzstage.com/allure-docker-service"
REPORT = "https://allure-reports.mumzstage.com/allure-docker-service/projects/{}/reports/latest/index.html"
DUBAI = timezone(timedelta(hours=4))
FULL_SHARE = 0.85   # of the suite's size at the time
MIN_TESTS = 25      # below this it is never a regression, whatever ran before it


def get(url):
    # curl rather than urllib: the host's certificate chain is not in every
    # Python build's trust store, and curl uses the system one.
    out = subprocess.run(["curl", "-sS", "-m", "30", url], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def project(pid):
    widgets = f"{BASE}/projects/{pid}/reports/latest/widgets"
    return pid, get(f"{widgets}/summary.json"), get(f"{widgets}/environment.json")


def main():
    ids = list((get(f"{BASE}/projects") or {}).get("data", {}).get("projects", {}))
    if not ids:
        raise SystemExit("Allure returned no projects -- is the service reachable?")
    with ThreadPoolExecutor(16) as pool:
        fetched = list(pool.map(project, ids))

    runs = []
    for pid, summary, env in fetched:
        stat, time = (summary or {}).get("statistic") or {}, (summary or {}).get("time") or {}
        if not stat.get("total") or not time.get("start"):
            continue                     # an empty project: created, never uploaded to
        e = {x["name"]: x["values"][0] for x in (env or []) if x.get("values")}
        if not e:
            continue                     # uploaded by hand, outside the runner: no provenance
        start = datetime.fromtimestamp(time["start"] / 1000, DUBAI)
        failed = stat.get("failed", 0) + stat.get("broken", 0)
        runs.append({
            "project": pid,
            "url": REPORT.format(pid),
            "start": start.isoformat(timespec="minutes"),
            "date": start.date().isoformat(),
            "suite": "app" if e.get("RUN_NATIVE_APP") == "true" else "mweb",
            "env": e.get("ENVIRONMENT", ""),
            "country": e.get("COUNTRY", ""),
            "os": e.get("OS", ""),
            "browser": e.get("BROWSER", ""),
            "locale": e.get("LOCALE", "en"),
            "passed": stat.get("passed", 0),
            "failed": failed,
            "skipped": stat.get("skipped", 0),
            "total": stat["total"],
            "minutes": round((time.get("duration") or 0) / 60000),
        })

    # A full regression is one that ran (nearly) the whole suite and finished.
    # The suite's size differs by country (mWeb UAE carries more tests than
    # KSA) and grew over time, so each run is measured against the largest run
    # of the same suite and country in the 45 days up to it. Anything under
    # FULL_SHARE of that is a targeted re-run or a run that ended early, and is
    # left out of every pass rate.
    runs.sort(key=lambda r: r["start"])
    for r in runs:
        day = datetime.fromisoformat(r["start"])
        peers = [o["total"] for o in runs if (o["suite"], o["country"]) == (r["suite"], r["country"])
                 and timedelta(0) <= day - datetime.fromisoformat(o["start"]) <= timedelta(days=45)]
        r["suite_size"] = max(peers)
        full = r["total"] >= MIN_TESTS and r["total"] >= FULL_SHARE * r["suite_size"]
        r["kind"] = "regression" if full else "partial"

    runs.sort(key=lambda r: r["start"])
    out = {
        "generated": datetime.now(DUBAI).isoformat(timespec="minutes"),
        "source": f"{BASE}/projects",
        "pass_rate": "passed / (passed + failed + broken); skips excluded",
        "runs": runs,
    }
    (HERE / "runs.json").write_text(json.dumps(out, indent=1))
    reg = [r for r in runs if r["kind"] == "regression"]
    print(f"{len(runs)} runs ({len(reg)} full regression, {len(runs) - len(reg)} partial), "
          f"{runs[0]['date']} -> {runs[-1]['date']} -> runs.json")


if __name__ == "__main__":
    main()
