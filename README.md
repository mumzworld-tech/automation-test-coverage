# Mumzworld Automation Test Coverage

**Live:** https://mumzworld-tech.github.io/automation-test-coverage/

Single source of truth for what the `automation_web_2.0` suite actually guards, mapped
case by case against TestMO.

* **mWeb** — [regression repository 3 / group 73697](https://mumzworld.testmo.net/repositories/3?group_id=73697).
  Read via the **run 2154** export, because that is what carries the case names; the
  repository export has no `Case` column. The build cross-checks the two: same case ids,
  same `Automated` flags, and every in-scope regression case present.
* **Native app** — [repository 241](https://mumzworld.testmo.net/repositories/241) release checklist.

## Coverage

Measured against `automation_web_2.0` **`origin/main`**.

| | Full | Partial | Not covered | In scope | Coverage |
|---|---|---|---|---|---|
| mWeb — regression repo 3 / group 73697 | 34 | 6 | 15 | 55 | **73 %** |
| Native app — repository 241 | 21 | 4 | 4 | 29 | **86 %** |
| **Combined** | **55** | **10** | **19** | **84** | **77 %** |

Automated tests on main (`53d29c8`, 3 Nov 2026): **224** — 200 active, 18 hard-skipped, 6 OS-gated.
114 are verified in Arabic as well as English.

### Scope: only `Automated = YES` or `NO` counts

The `Automated` column in the TestMO export decides whether a case is an automation
candidate. Cases marked **Not planned** — Admin-side product creation, Geo-IP, push
notifications, Maya, GTM, Apple Pay — are kept in the report for reference but are
excluded from every percentage. This is the same filter as
`repositories/3?group_id=73697&filter=…custom_automated:[18,144]`.

79 of the 163 cases are excluded this way (60 mWeb + 19 app). Tick **Show *Not planned***
in the toolbar to see them; the numbers do not move.

The report now mirrors the regression repository exactly: **all 104 cases** of group 73697,
of which **55 are in scope and all 55 are mapped**. The other 49 are `Not planned` — mostly
the Returns / refunds / credit-memo area, which has no automation at all. A further 11 Admin
"Product types" cases sit outside group 73697 and are also `Not planned`, bringing the mWeb
table to 115 rows.

34 of those cases exist only in the repository export, which has no case-name column. They are
labelled with TestMO's own **Summary** text, shown in italic with a `◦` marker, and carry
`name_source: "summary"` — the report never displays a name TestMO did not write. Re-export
with the case-name column and they pick up their real names automatically.

### What "full" and "partial" mean

* **full** — every scenario in the TestMO case is covered end to end.
* **partial** — part of the case is covered, *or* the only script covering it is
  `@pytest.mark.skip`. The Evidence column always says what is and is not covered.
* **none** — nothing covers it. The Evidence column often records why, including why a
  previously-recorded link was removed.

Nothing is mapped by keyword similarity. Every link was checked by reading the test's
docstring and allure title against the TestMO case's summary and steps.

## How it works

```bash
make generate   # parse both exports + read origin/main + build + verify
make open       # generate, then open the report
```

1. `parse_testmo_csv.py` — parses a TestMO export (run layout or repository layout) and
   carries the `Automated` column through as `automated_flag` / `in_scope`. It refuses an
   export with no case-name column rather than producing rows keyed on bare ids.
2. `extract_tests.py` — reads `tests/app`, `tests/web/UAE`, `tests/web/KSA` and
   `tests/web/commons` from `origin/main` via `git show`. It never checks out or pulls,
   so your working branch in `automation_web_2.0` is left alone.
3. `build_mapping.py` — holds the case-by-case mapping and validates it. It also reads
   `REG_CSV` (the regression repository export) to tag each mWeb case with its group and to
   fail the build if the two exports ever disagree on a case's `Automated` flag, or if an
   in-scope regression case is missing from the report.
4. `verify_mapping.py` — fails the build if any invariant breaks.
5. `index.html` — the report; loads `mapping.json`.

### Test references are platform-qualified

Refs look like `app::test_uae_cart_remove_item`, not a bare test name. Ten test names
exist in two files at once — the app cart and checkout suites were ported from the web
ones and kept their names — so `test_uae_cart_remove_item` alone cannot say whether the
app or the mWeb test covers a case. Where a name repeats inside one platform, the file
stem is appended too: `web_uae::test_uae_cart_apply_gift_wrap_and_place_order@test_checkout`.

### Arabic

Arabic is a run dimension, not a second set of cases: the same suites run with `LOCALE=en`
and `LOCALE=ar`, so the case counts are unchanged. Delivered by **FALCONS-321** (app),
**FALCONS-330** (mWeb), **FALCONS-335** and **FALCONS-336** (stabilisation). `conftest.py`
maps `(COUNTRY, LOCALE)` to `/ar`, `/sa-ar`, `/bh-ar`, `/kw-ar` and `/global-ar`;
`locatorsApp.json` carries 233 locale-nested selectors. A test is marked AR-verified when
one of those tickets touched its file or the file carries locale-aware code.

## Editing the report

The report is editable in the browser:

* **+ Add test** on any row, then pick from the real inventory on main.
  A newly added link lands as **partial**, never **full** — promote it by hand once you
  have read the test and written the Evidence note.
* **×** on a tag removes a link.
* **💾 Save for Everyone** persists to the shared Gist (`37aafe3290f5c00dbd0ddb910a19f939`).
  It asks for an edit password and then for a **GitHub PAT with `gist` scope**, kept in your own
  browser's `localStorage` and never committed.

### Credentials

**This repo is public.** Anything in `index.html` is readable by every visitor, so no token is
embedded in it. Reads degrade silently without one — the committed JSON already holds everything
the report renders — and only the two write actions ("Save for Everyone", "Add Regression Run")
and "Update from Main" ask for a token.

The edit password is a speed bump against accidental edits, not access control: it is in the page
source. Treat the whole report as public, and keep anything genuinely sensitive out of it.

### Before and since 1 April 2026

`build_tenure.py` writes `tenure.json`, which drives the trend line and the before/after section.
It reads `automation_web_2.0` at 1 April and at the start of every month since, and applies
**today's** mapping to the suite as it stood then: a mapped test that did not exist yet, or was
hard-skipped, does not count, and a case with only some of its tests present is partial at best.
The early points are therefore an estimate, never more generous than today, and the page says so.
The run must reproduce today's headline exactly or it fails. It needs the full git history, so it
is run locally with `make tenure`, not in CI.

### Regression runs

`build_runs.py` writes `runs.json` from every run the FALCON runner published to the Allure Docker
Service, so the run history needs no hand entry. Only **full regressions** count: a run must cover at
least 85% of its suite as it stood then, measured per suite and country against the largest run in the
45 days before it. Targeted re-runs and runs that ended early are kept as `partial` and never averaged
in. Pass rate is passed ÷ (passed + failed + broken). Refresh with `make runs`.

### Keeping it current

This project stands alone: nothing in `automation_web_2.0` refers to it.
`.github/workflows/refresh-coverage.yml` polls that repo's `main` every 30 minutes in Dubai
working hours (08:00–20:00, Mon–Fri) and once a day at weekends. When `main` has moved past the
commit `mapping.json` was built from (`metadata.source_sha`), it regenerates the inventory and
mapping and commits them here. A merged test therefore shows up within about half an hour;
**Actions → Refresh coverage from main → Run workflow** does it at once.

The schedule is set by cost: the repo is private, so each run bills at least one Actions
minute against the organisation's Free-plan allowance.

It reads `automation_web_2.0` with a classic PAT (`repo` scope). `mumzworld-tech` does not
accept fine-grained PATs. Setting the secret needs admin on this repo:

* `gh secret set AUTOMATION_REPO_TOKEN --repo mumzworld-tech/automation-test-coverage`

Structural changes (new cases, re-mapping a whole area) belong in `build_mapping.py`, not
in the browser — that file is the record of *why* each link exists.

**🔄 Update from Main** refreshes the test inventory and drops links to tests that no
longer exist. It does not create mappings. The keyword matcher that used to run here
produced links such as `Checkout – Apple pay → test_uae_checkout_cod_normal_coupon`;
it has been removed.

## What is not mapped

48 tests on main are not linked to any case. 13 of those are hard-skipped, so they guard
nothing today. The rest are UAE cart-behaviour tests (`test_uae_cart_remove_item`,
`..._increase_and_decrease_quantity`, `..._bundle_multiple_variants`,
`..._order_summary_updates_after_item_removal`, `..._add_all_product_types_and_verify` and
friends) plus `test_app_cart_existing_user_orders_no_coupon_yalla` and
`test_app_gift_registry_create_from_my_registries`.

These are real, running tests with no matching case in either TestMO source — they test cart
behaviour at a finer grain than the UF1–UF12 user flows the regression repository describes.
The fix is TestMO-side: add cases for them, or widen the existing UF cases. The report lists
them in the amber "Automated tests not linked to any case" panel so they stay visible.

## Stack

* Python + Selenium + Appium + Pytest + Allure
* Test management: [TestMO](https://mumzworld.testmo.net/runs/view/2154)
* CI: BrowserStack
