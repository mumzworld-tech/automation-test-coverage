# Regenerates mapping.json -- the source of truth behind index.html.
#
# WEB_CSV must be the run-2154 export that includes the "Automated" column
# (the plain testmo-export-run-2154.csv does not). That column decides which
# cases count towards coverage, so the wrong export silently changes every
# percentage in the report.
WEB_CSV ?= $(HOME)/Downloads/testmo-export-run-2154 (1).csv
APP_CSV ?= $(HOME)/Downloads/testmo-export-repository-241 (2).csv
# The mWEB regression repository itself (repository 3 / group 73697). WEB_CSV is
# a run OF this repository and supplies the case names; this export supplies the
# full group, including cases no run has covered. Optional -- if absent the
# report shows only what run 2154 contained.
REG_CSV ?= $(HOME)/Downloads/testmo-export-repository-3 (1).csv
REPO    ?= $(HOME)/automation_web_2.0

.PHONY: generate clean open verify tenure runs

generate: testmo_tests.json app_testmo_tests.json web_regression_tests.json automated_tests.json mapping.json
	@$(MAKE) --no-print-directory verify
	@echo "Report ready -- open index.html"

testmo_tests.json: parse_testmo_csv.py
	python3 parse_testmo_csv.py "$(WEB_CSV)" testmo_tests.json

app_testmo_tests.json: parse_testmo_csv.py
	python3 parse_testmo_csv.py "$(APP_CSV)" app_testmo_tests.json

# Optional. This export has no case-name column, so --allow-unnamed labels each
# case with TestMO's own Summary; cases already named by the run export keep
# that name. Absent file -> skipped, no failure.
web_regression_tests.json: parse_testmo_csv.py
	@if [ -f "$(REG_CSV)" ]; then \
		python3 parse_testmo_csv.py "$(REG_CSV)" web_regression_tests.json --allow-unnamed; \
	else \
		echo "REG_CSV not found, skipping the mWEB regression repository: $(REG_CSV)"; \
		rm -f web_regression_tests.json; \
	fi

# Reads origin/main via `git show`; never checks out or pulls in $(REPO).
automated_tests.json: extract_tests.py
	python3 extract_tests.py "$(REPO)"

mapping.json: build_mapping.py testmo_tests.json app_testmo_tests.json web_regression_tests.json automated_tests.json testmo_case_links.json
	python3 build_mapping.py


# The before/after-1-April section and the trend line. Needs the full git
# history of $(REPO), so it runs locally rather than in CI; re-run it when you
# want the latest month reflected, after `make generate`.
tenure: mapping.json
	python3 build_tenure.py "$(REPO)"

# Every FALCON run published to Allure -> runs.json. Only full regressions
# (>= 85% of the suite as it stood) count towards the pass rates.
runs:
	python3 build_runs.py

verify:
	@python3 verify_mapping.py

clean:
	rm -f testmo_tests.json app_testmo_tests.json web_regression_tests.json automated_tests.json mapping.json

open: generate
	open index.html
