#!/usr/bin/env python3
"""Extract the automated test inventory from automation_web_2.0 @ origin/main.

Reads the tree with `git show origin/main:<path>` so the working copy is never
touched -- the repo is usually parked on a feature branch and the report must
always reflect main.

Each test is emitted with a platform-qualified `ref` ("app::test_foo"). That
matters: 10 test names exist in two files at once (the app cart/checkout suites
were ported from the web ones and kept their names), so a bare name cannot say
which test covers a TestMO case.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# platform -> directory in the repo
PLATFORMS = {
    "app": "tests/app",
    "web_uae": "tests/web/UAE",
    "web_ksa": "tests/web/KSA",
    "web_commons": "tests/web/commons",
}

# Preferred ref, with fallbacks. A CI checkout is a detached HEAD and may not
# carry refs/remotes/origin/*, so falling back to a local `main` and finally to
# HEAD keeps the workflow working instead of silently reading the wrong tree.
REF_CANDIDATES = ("origin/main", "main", "HEAD")
REF = "origin/main"

# Tickets that delivered / hardened Arabic locale support. Files they touched
# are treated as AR-verified, as are files that carry locale-aware code.
ARABIC_TICKETS = ["FALCONS-321", "FALCONS-330", "FALCONS-335", "FALCONS-336",
                  "FALCONS-394"]   # Arabic locators and RTL for the KSA app suites
# FALCONS-393 (mWeb KSA in Arabic) is deliberately NOT a ticket here: in its
# Arabic regression most of test_coupon_ksa.py failed, so crediting every file
# it touched would overclaim. Its passing tests are credited one by one below.

# Tests that PASSED on both Android and iOS in the full Arabic (sa-ar) mWeb KSA
# regressions of 13 Nov 2026 -- Allure projects
# falcons-393-{android,ios}-preprod-sa-ar-regression, 92 tests each. Evidence
# from a run, per test, for tests no file-level rule above already credits.
ARABIC_RUN_DATE = "2026-11-13"
ARABIC_RUN_VERIFIED = {
    "web_ksa::test_ksa_user_register_from_account_page",
    "web_ksa::test_ksa_user_register_from_cart_page",
    "web_ksa::test_ksa_user_logs_in_from_account_page",
    "web_ksa::test_ksa_user_logs_in_from_cart_page",
    "web_ksa::test_ksa_wishlist_add_all_product_types_existing_user",
    "web_ksa::test_ksa_wishlist_add_all_product_types_new_user",
    "web_commons::test_categories_levels_load",
    "web_commons::test_web_filters_one_filter_at_a_time",
    "web_commons::test_web_filters_multiple_filters",
    "web_commons::test_web_filters_yalla_from_listing",
    "web_commons::test_web_filters_price_range",
    "web_commons::test_web_filters_color_and_diaper_size",
    "web_commons::test_web_filters_discounts",
    "web_commons::test_web_sort_by_price_from_both_entry_points",
    "web_commons::test_wishlist_delete_all_product_types",
    "web_commons::test_wishlist_add_products_from_plps_new_user",
    "web_commons::test_wishlist_add_products_from_plps_existing_user",
    "web_commons::test_wishlist_move_all_product_types_to_cart_existing_user",
    "web_commons::test_wishlist_move_all_product_types_to_cart_new_user",
}


def mark_run_verified(tests):
    """Credit Arabic to the tests that passed in the Arabic regression."""
    for t in tests:
        if t["ref"] in ARABIC_RUN_VERIFIED:
            t["locales"] = ["en", "ar"]

# A suite is AR-safe by one of two designs, and only the first was detected:
#
#   locale-aware     — carries LOCALE / LANGUAGE_DATA / locale-nested locators
#   locale-agnostic  — asserts against whatever the UI rendered rather than a
#                      hardcoded English string, so it needs no per-locale data
#
# The second is arguably the stronger design and was being marked EN-only,
# because looking for locale *code* finds nothing in a suite that needs none.
LOCALE_MARKER = re.compile(
    r"LOCALE|locale_|\.locale|lang=|locale-agnostic|no locale-specific|no per-locale")

# Locale-agnostic files, verified by reading them. Kept explicit rather than
# regexed: "asserts the rendered label" is a design, not a token.
LOCALE_AGNOSTIC = {
    # reads back the label the chip actually rendered; free-text registry names
    "tests/web/commons/test_gift_registry.py",
    # asserts the category name the suggestion returned, not an English constant
    "tests/web/commons/test_home.py",
}

DEF_RE = re.compile(r"^def (test_\w+)\(", re.M)


def git(repo, *args):
    out = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def resolve_ref(repo):
    """First candidate ref that exists in this clone."""
    for ref in REF_CANDIDATES:
        out = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref],
                             cwd=repo, capture_output=True, text=True)
        if out.returncode == 0:
            return ref
    raise SystemExit(f"none of {REF_CANDIDATES} exist in {repo}")


def list_test_files(repo, rel_dir):
    names = git(repo, "ls-tree", "-r", "--name-only", REF, "--", rel_dir).split()
    return [n for n in names if re.search(r"/test_[^/]*\.py$", n)]


def arabic_ticket_files(repo):
    """Test files touched by any of the Arabic tickets."""
    touched = set()
    for ticket in ARABIC_TICKETS:
        for sha in git(repo, "log", REF, "--format=%H", f"--grep={ticket}").split():
            for line in git(repo, "show", "--name-only", "--format=", sha).splitlines():
                if line.startswith("tests/"):
                    touched.add(line.strip())
    return touched


def decorator_block(lines, def_idx):
    """Lines directly above a def, back to the previous blank line."""
    block, i = [], def_idx - 1
    while i >= 0 and lines[i].strip():
        block.insert(0, lines[i])
        i -= 1
    return "\n".join(block)


def docstring_after(lines, def_idx):
    i = def_idx
    while i < len(lines) and not lines[i].rstrip().endswith("):"):
        i += 1
    i += 1
    if i >= len(lines) or not lines[i].strip().startswith('"""'):
        return ""
    first = lines[i].strip().lstrip('"')
    parts = [first] if first.strip() else []
    if first.rstrip().endswith('"""'):
        return re.sub(r"\s+", " ", first.rstrip('"')).strip()
    i += 1
    while i < len(lines) and '"""' not in lines[i]:
        parts.append(lines[i].strip())
        i += 1
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def parse_skip(block):
    m = re.search(r"@pytest\.mark\.skip\(\s*(?:reason\s*=\s*)?[\"'](.*?)[\"']", block, re.S)
    if m:
        return {"type": "hard", "reason": re.sub(r"\s+", " ", m.group(1)).strip()}
    if "@pytest.mark.skip(" in block:
        return {"type": "hard", "reason": ""}
    if "@pytest.mark.skipif" in block:
        m = re.search(r"@pytest\.mark\.skipif\(\s*(.+?)(?:,\s*reason|\n)", block, re.S)
        cond = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        # Prefer the human reason over the condition. Storing only `OS.lower() ==
        # "ios"` told a reader what was skipped but never why -- and the why is
        # the part that decides whether it is a gap or a platform limitation.
        rm = re.search(r'reason\s*=\s*((?:"[^"]*"\s*)+)', block, re.S)
        why = " ".join(re.findall(r'"([^"]*)"', rm.group(1))).strip() if rm else ""
        return {"type": "conditional",
                "reason": (f"{why} [{cond}]" if why else cond)[:220],
                "condition": cond}
    return None


def _mark_from_call(kind, args, scope):
    """Turn a captured pytest.mark.skip/skipif call into a skip record."""
    cond = re.sub(r"\s+", " ", args.split(",")[0]).strip()
    rm = re.search(r'reason\s*=\s*((?:"[^"]*"\s*)+)', args, re.S)
    why = " ".join(re.findall(r'"([^"]*)"', rm.group(1))).strip() if rm else ""
    return {"type": "conditional" if kind == "skipif" else "hard",
            "reason": (f"{why} [{cond}]" if why else cond)[:220],
            "condition": cond, "scope": scope}


def marker_aliases(source):
    """Module-level `NAME = pytest.mark.skipif(...)` applied later as `@NAME`.

    tests/app/test_app_gift_registry.py moved from a blanket `pytestmark` to
    `GIFT_REGISTRY_AE_ONLY = pytest.mark.skipif(COUNTRY == "SA", ...)` decorated
    onto four of its five tests -- deliberately leaving the newest one ungated.
    Looking only for `pytestmark` lost that entirely and showed the suite as
    running on SA.
    """
    out = {}
    for m in re.finditer(r"^([A-Z_][A-Z0-9_]*)\s*=\s*pytest\.mark\.(skipif|skip)\((.*?)\n\)",
                         source, re.M | re.S):
        out[m.group(1)] = _mark_from_call(m.group(2), m.group(3), "alias")
    return out


def module_skip(source):
    """A module-level `pytestmark` applies to every test in the file.

    Handles both shapes: a bare `pytestmark = pytest.mark.skipif(...)` and the
    list form `pytestmark = [pytest.mark.skipif(...), ...]` the superApp suites
    use. Only the first was recognised, so the Now-vertical suites read as
    running everywhere when they are UAE-only.
    """
    m = re.search(r"^pytestmark\s*=\s*(.*?)\n(?:\]|\))\n", source, re.M | re.S)
    if not m:
        return None
    call = re.search(r"pytest\.mark\.(skipif|skip)\((.*)", m.group(1), re.S)
    if not call:
        return None
    return _mark_from_call(call.group(1), call.group(2), "module")


def parse_file(source, path, platform, ar_verified):
    lines = source.split("\n")
    mod_skip = module_skip(source)
    aliases = marker_aliases(source)
    tests = []
    for i, line in enumerate(lines):
        m = DEF_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        block = decorator_block(lines, i)

        title = re.search(r"@allure\.title\([\"'](.+?)[\"']\)", block)
        feature = re.search(r"@allure\.feature\([\"'](.+?)[\"']\)", block)
        story = re.search(r"@allure\.story\([\"'](.+?)[\"']\)", block)
        severity = re.search(r"severity_level\.(\w+)", block)

        tags = []
        for tm in re.finditer(r"@allure\.tag\((.+?)\)", block, re.S):
            tags += [t.strip().strip("\"'") for t in tm.group(1).split(",") if t.strip()]

        tests.append({
            "ref": f"{platform}::{name}",
            "name": name,
            "platform": platform,
            "path": path,
            "file": path.rsplit("/", 1)[-1],
            "title": title.group(1) if title else "",
            "feature": feature.group(1) if feature else "",
            "story": story.group(1) if story else "",
            "severity": severity.group(1).lower() if severity else "",
            "tags": tags,
            "docstring": docstring_after(lines, i)[:400],
            "parametrized": "@pytest.mark.parametrize" in block,
            # Precedence: a marker on the test, then an alias marker decorated
            # onto it, then a module-wide pytestmark.
            "skip": (parse_skip(block)
                     or next((aliases[a] for a in aliases if f"@{a}" in block), None)
                     or mod_skip),
            "locales": ["en", "ar"] if ar_verified else ["en"],
        })
    return tests


def disambiguate(tests):
    """Make every ref unique.

    "platform::name" is enough for almost everything, but a name can repeat
    inside one platform too -- test_uae_cart_apply_gift_wrap_and_place_order
    lives in both tests/web/UAE/test_cart.py (hard-skipped duplicate) and
    tests/web/UAE/test_checkout.py (the live copy). Those get the file stem
    appended so the two can never be confused for one another.
    """
    seen = {}
    for t in tests:
        seen.setdefault(t["name"], []).append(t)
    for name, group in seen.items():
        if len(group) > 1:
            for t in group:
                stem = t["file"].removesuffix(".py")
                t["ref"] = f"{t['platform']}::{name}@{stem}"


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "automation_web_2.0"
    globals()["REF"] = resolve_ref(repo)
    head = git(repo, "rev-parse", "--short", REF).strip()
    print(f"Reading {repo} @ {REF} ({head}) -- working copy untouched")
    if REF != REF_CANDIDATES[0]:
        print(f"  note: {REF_CANDIDATES[0]} not present; used {REF}")

    ar_files = arabic_ticket_files(repo)
    ar_reasons = []
    result = {}
    for platform, rel_dir in PLATFORMS.items():
        files = list_test_files(repo, rel_dir)
        tests = []
        for path in files:
            src = git(repo, "show", f"{REF}:{path}")
            why = ("AR ticket" if path in ar_files else
                   "locale-agnostic" if path in LOCALE_AGNOSTIC else
                   "locale-aware" if LOCALE_MARKER.search(src) else None)
            tests += parse_file(src, path, platform, bool(why))
            if why:
                ar_reasons.append((path, why))
        disambiguate(tests)
        mark_run_verified(tests)
        result[platform] = tests
        print(f"  {platform:12s} {len(files)} files, {len(tests):3d} tests")

    result["_meta"] = {"ref": REF, "sha": head, "repo": str(repo)}
    out = Path(__file__).parent / "automated_tests.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    flat = [t for k, v in result.items() if k != "_meta" for t in v]
    hard = sum(1 for t in flat if t["skip"] and t["skip"]["type"] == "hard")
    cond = sum(1 for t in flat if t["skip"] and t["skip"]["type"] == "conditional")
    ar = sum(1 for t in flat if "ar" in t["locales"])
    print(f"Total {len(flat)} tests -- {len(flat) - hard - cond} active, "
          f"{hard} hard-skipped, {cond} OS-gated, {ar} AR-safe -> {out}")
    for path, why in sorted(ar_reasons):
        print(f"    AR-safe ({why}): {path}")
    print(f"    AR-safe (passed the {ARABIC_RUN_DATE} Arabic regression): "
          f"{sum(1 for t in flat if t['ref'] in ARABIC_RUN_VERIFIED)} tests")


if __name__ == "__main__":
    main()
