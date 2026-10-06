# Selenium E-commerce Automation

[![Selenium CI](https://github.com/hanmyintmyat/selenium-ecommerce-automation/actions/workflows/selenium-tests.yml/badge.svg?branch=main&event=push)](https://github.com/hanmyintmyat/selenium-ecommerce-automation/actions/workflows/selenium-tests.yml)

A Python UI automation framework for [Sauce Demo](https://www.saucedemo.com/),
designed as a mid-level QA Automation / Test Engineer portfolio project. It
covers authentication, catalogue sorting, shopping carts, and a complete purchase
journey with independently verified order totals.

The suite contains **28 independent UI tests** and **14 framework regression
checks**, including four UI smoke tests. Each UI test uses a fresh browser
profile. There are no ordered tests, shared carts,
implicit waits, or fixed sleeps. Failures retain diagnostics and fail the build;
retries are opt-in.

## Architecture

```text
Pytest tests (business assertions)
    -> fixtures (configuration, browser lifetime, generated/JSON data)
    -> page objects (locators, actions, explicit waits)
    -> Selenium WebDriver (local browsers or Selenium Grid)

Failure hook -> screenshots + Allure attachments + HTML report
All activity -> automation logs
```

- `BasePage` provides synchronized actions and contextual timeout errors.
- Page objects own locators and return domain values; tests own assertions.
- `DriverFactory` supports Chrome, Firefox, Edge, and remote WebDriver.
- WebDriver Manager installs/caches local drivers. A file lock protects driver
  installation when parallel workers start together. Explicit driver paths are
  supported for CI and pre-provisioned/offline environments.
- Currency values use `Decimal` to avoid floating-point rounding errors.
- JSON supplies users, expected products, sorting scenarios, error messages, and
  checkout expectations. Faker creates synthetic customer information.

## Stack

Python 3.12, Selenium WebDriver, Pytest, Page Object Model, WebDriver Manager,
Allure Pytest, pytest-html, Faker, python-dotenv, pytest-xdist,
pytest-rerunfailures, filelock, Ruff, GitHub Actions, and Docker Compose.
Direct dependencies are pinned in `requirements.txt`.

## Prerequisites

- Python **3.12** and `python3-venv` on Linux.
- Chrome or Firefox installed locally; Edge is optional and must be installed to
  use `--browser edge`. WebDriver Manager installs drivers, not browsers.
- Internet access to Sauce Demo and driver download endpoints.
- Optional: Java 17+, Node.js/npm, and the Allure CLI for rendered Allure reports.
- Optional: Docker Engine running with Docker Compose v2 or newer.

## Installation (Linux)

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and replace `SAUCE_PASSWORD=replace-with-demo-password` with the
**public demo password displayed on Sauce Demo's login page**. Public demo
usernames in JSON are test identities. CI uses Sauce Demo's published password
so pull requests can run without repository secrets.
Do not use personal or production credentials. `.env`, logs, screenshots,
reports, browser caches, and the virtual environment are ignored by Git.

## Running tests

```bash
pytest
pytest -m smoke
pytest -m regression
pytest --browser chrome --headless -m smoke -v
pytest --browser chrome --headless -m regression -v
pytest --browser chrome --headless
pytest --browser firefox --headless
pytest --browser edge --headless
pytest --browser chrome --headless --env qa
pytest -m "login or checkout" --headless
pytest tests/test_login.py --headless
pytest 'tests/test_login.py::test_login_validation[invalid_password]' --headless
```

`pytest` defaults to headed Chrome, with environment `qa`. Use headless mode on
servers without a graphical display. `--headed` overrides `HEADLESS=true`.
CLI browser/environment/headless options override `.env` defaults.

| Marker | Scope |
| --- | --- |
| `smoke` | Login, catalogue, cart, and complete purchase |
| `regression` | All 28 UI tests and 14 framework regression checks |
| `login` | Positive authentication and negative validation |
| `cart` | Cart contents, quantities, badge, removal, navigation |
| `checkout` | Required customer fields, order review, purchase |
| `framework` | Browser lifetime, screenshot/report failures, and original-error preservation |

Markers are registered in `pytest.ini`; misspelled markers fail collection.
The four smoke tests are also regression tests. `-m regression` includes all
42 tests, including the 14 browser-free framework checks. Each CI suite starts
with fresh test sessions, so the smoke subset can safely run in both jobs.

## Coverage

| Area | Tests | Assertions |
| --- | ---: | --- |
| Login | 8 | Successful login; invalid password/username; locked user; empty fields; exact errors; dismiss error |
| Products | 9 | Heading; all six names and prices; single/multiple additions; removal; all four sorting modes without losing products |
| Cart | 6 | Names, prices, quantities, badge; multiple items; remove one/last item; continued shopping; initial empty cart |
| Checkout | 5 | Full purchase; item/subtotal/tax/total; success text; cleared cart; three required fields; correction of invalid data |
| Framework | 14 | Closed sessions; screenshot transport errors; capture/attachment ordering; configuration cleanup; original failure preservation; retry state; reporting errors |

## Configuration

Settings are loaded centrally from `config/config.py`. Shell and CI variables
take precedence over `.env`.

| Variable | Default / purpose |
| --- | --- |
| `SAUCE_USERNAME` | `standard_user`, positive login identity |
| `SAUCE_PASSWORD` | Required for valid-password scenarios; never logged |
| `TEST_ENV` | `qa`; supports `local`, `qa`, `staging` |
| `BROWSER` | `chrome`; also `firefox`, `edge` |
| `HEADLESS` | `false` |
| `BASE_URL` | Global base URL override |
| `LOCAL_BASE_URL`, `QA_BASE_URL`, `STAGING_BASE_URL` | Environment-specific override, taking priority over `BASE_URL` |
| `EXPLICIT_WAIT` | `10` seconds |
| `PAGE_LOAD_TIMEOUT` | `30` seconds |
| `SELENIUM_REMOTE_URL` | Unset; set to a Grid URL to use remote sessions |
| `BROWSER_BINARY` | Optional path to the selected browser binary |
| `CHROME_BINARY`, `FIREFOX_BINARY`, `EDGE_BINARY` | Per-browser paths; take priority over `BROWSER_BINARY` |
| `WEBDRIVER_PATH` | Optional path to a compatible driver; bypasses WebDriver Manager |
| `CHROME_NO_SANDBOX` | `false`; opt-in for containers that require it |

All three environment aliases target the same public demo by default. They are
configuration examples, not separate deployed environments. Point overrides at
an application with the same UI contract; this suite is specifically for Sauce
Demo. URLs and credentials are not scattered throughout tests.

If a Linux Snap Firefox wrapper exits during session startup, point
`FIREFOX_BINARY` at the actual Firefox executable, or install a native Firefox
distribution. `FIREFOX_BINARY` affects only Firefox runs; Chrome continues to use
its default binary.

## Parallel execution

```bash
pytest -n auto --headless
pytest -n 2 --browser chrome --headless
```

Each worker creates independent sessions and test data. Screenshots include the
worker ID, UTC timestamp with microseconds, and a unique suffix. Serial runs log
to `logs/automation.log`; parallel workers log to `logs/automation-gw0.log`,
`logs/automation-gw1.log`, etc. Use two workers on a modest laptop or public demo
to limit resource use. A remote Grid must have enough session capacity for the
chosen worker count.

`-n auto` uses at most four workers by default to limit load on the public demo.
Set `PYTEST_XDIST_AUTO_NUM_WORKERS` to a positive integer to override this cap;
explicit `-n 2` also bypasses auto selection.

## Retries

```bash
pytest --headless --reruns 2
pytest --headless --reruns 2 --only-rerun PageWaitError
```

Retries are disabled by default and in CI. The first command retries every
failure, including assertions, so use it only while investigating intermittent
behavior. Preserve the first failure's artifacts, inspect the report and logs,
and fix the cause. A pass after rerun does not establish that a test is stable.

## Reports

Generate HTML, Allure results, and JUnit together:

```bash
pytest --headless \
  --html=reports/report.html --self-contained-html \
  --alluredir=reports/allure-results \
  --junitxml=reports/junit.xml
```

Or generate reports separately:

```bash
pytest --headless --html=reports/report.html --self-contained-html
pytest --headless --alluredir=reports/allure-results
```

Open `reports/report.html` in a browser. Failure screenshots are embedded so the
HTML file can be shared by itself.

The Python Allure adapter writes results; the **Allure CLI** renders them. With
Java 17+ and Node.js/npm installed:

```bash
npm install -g allure-commandline@2.46.1
allure --version
allure serve reports/allure-results
```

To generate a persistent report:

```bash
allure generate reports/allure-results --clean -o reports/allure-report
allure open reports/allure-report
```

Use a new Allure results directory for each run, or add `--clean-alluredir` to a
serial pytest run. Avoid mixing old results with new ones. CI starts from a fresh
checkout and uploads raw results and the generated Allure HTML.

## Screenshots and logging

When a test fails in setup, call, or teardown, `pytest_runtest_makereport`
uses only that test's registered browser session. Setup/test failures capture a
PNG and attach it to enabled Allure/HTML reports **before fixture teardown**.
The yield-based browser fixture owns configuration and the only explicit
`driver.quit()` call. It captures a final PNG before quitting, unregisters the
active driver, and clears its session ID. Teardown reports use these retained
bytes and never send screenshot commands to WebDriver.

Screenshot capture checks the driver and session ID, plus local driver service
liveness. A crashed remote session can still race with capture; transport errors
(including urllib3 `MaxRetryError`), file writes, and report attachment errors
are logged as warnings without replacing the original assertion/Selenium error.
Cleanup errors also preserve an existing setup/test failure; a standalone
`quit()` failure remains a failing teardown. Reruns clear prior session/report
state and screenshots. A browser that cannot start may have no screenshot.

Run the framework regression checks without opening browsers:

```bash
pytest -m framework -v
```

Example filename:

```text
screenshots/test_login_validation_invalid_password_call_2026-10-06_120000_123456_main_a1b2c3d4.png
```

`logs/automation.log` records timestamps, levels, test IDs, navigation, actions,
validation results, and errors. Username/password entry is redacted. Generated
customer data is synthetic. `PageWaitError` preserves the original timeout as
its cause and identifies the page, condition, timeout, and URL. JavaScript click
fallback is available only when explicitly requested by the calling page object;
normal clicks expose intercepted-click errors.

## Docker

The Python runner connects to a versioned Selenium standalone Chrome container.
The browser service healthcheck gates test startup. Reports, screenshots, and
logs are mounted back to the host. Configure `.env` first.

```bash
docker compose build tests
docker compose run --rm tests
docker compose run --rm tests pytest -m smoke --browser chrome --headless \
  --html=reports/report.html --self-contained-html \
  --alluredir=reports/allure-results
docker compose run --rm tests pytest -n 2 --browser chrome --headless
docker compose down
```

`docker compose run tests` also works and retains the stopped runner container.
The Dockerfile contains the test runner; it requires the Compose browser service
or another Grid through `SELENIUM_REMOTE_URL`. It does not install a local
browser. Do not select Firefox/Edge against the Chrome-only Compose service.
For other remote browsers, provision matching Selenium images.

Validate configuration without starting containers:

```bash
docker compose config --quiet
```

## CI/CD with GitHub Actions

The [Selenium workflow](.github/workflows/selenium-tests.yml) runs automatically
on **pushes to `main`** and **pull requests targeting `main`**. It also supports
manual execution through **Actions → Selenium CI → Run workflow**.

The project directory is the Git repository root, with
`.github/workflows/selenium-tests.yml` directly under that root so GitHub can
discover the workflow. CI uses `standard_user` and Sauce Demo's
**published demo password**, `secret_sauce`, by default. No repository secret is
required, so fork pull requests also run the UI suite. An optional `SAUCE_PASSWORD`
repository Actions secret overrides that demo default; it must match the demo
site's password. A placeholder override fails the configuration check.
The workflow uses `pull_request` with read-only repository permissions.

The status badge shows the latest `main` push workflow status for
[`hanmyintmyat/selenium-ecommerce-automation`](https://github.com/hanmyintmyat/selenium-ecommerce-automation)
and links to the workflow's run history.

### Pipeline and test organization

The workflow uses **Ubuntu 24.04 GitHub-hosted runners** and Python 3.12. Code
quality runs once in a separate job; two independent matrix jobs run the suites:

| Job | Test selection | Local equivalent |
| --- | --- | --- |
| `Code quality` | Dependencies, lint, formatting, test collection/markers | `python -m pip check`, `ruff check .`, `ruff format --check .`, `pytest --collect-only -q` |
| `Chrome / smoke` | 4 critical UI journeys | `pytest --browser chrome --headless -m smoke -v` |
| `Chrome / regression` | All 42 UI/framework tests | `pytest --browser chrome --headless -m regression -v` |

Each job installs dependencies and runs `pip check`. Ruff lint and formatting
checks and strict test collection run in `Code quality`; browser jobs can still
produce diagnostics if that job fails. `actions/setup-python` caches pip downloads
using `requirements.txt` as
the dependency key. Changes to pinned dependencies update the cache key; each
job still installs and validates its own environment.

The Chrome setup action installs **stable Chrome for Testing**, its **matching
ChromeDriver**, and required Ubuntu system libraries. The workflow checks that
both binaries are executable and prints their versions before testing. It passes
the exact paths through `CHROME_BINARY` and `WEBDRIVER_PATH`, so tests use the
provisioned pair. Chrome runs with `--headless` and the existing shared-memory
options. CI sets `CHROME_NO_SANDBOX=true` for compatibility with ephemeral Linux
runners; local execution defaults to the browser sandbox enabled.

All actions are pinned to immutable commit SHAs with release-line comments.
`--reruns 0` makes retries explicitly disabled in CI. The test command keeps
Pytest's exit code: assertions, Selenium errors, setup/teardown errors, and
collection errors fail the job. There is no `continue-on-error` or ignored test
exit status. Console output is saved to `logs/pytest.log` through `tee`, with
`pipefail` enabled so a failing pytest process still fails the step.
Matrix `fail-fast: false` lets the other suite finish its diagnostics
if one job fails. A newer run cancels an obsolete run for the same branch/PR.

### Reports and artifacts

Each test job generates a self-contained pytest-html report, Allure results,
and JUnit XML. Java 17 and the pinned Allure CLI then render a browsable Allure
report. HTML, raw Allure results, JUnit, screenshots, and logs are uploaded
**before** Java/Node setup and Allure rendering, so a rendering failure cannot
prevent their upload. Allure rendering has a three-minute step timeout.
Upload steps run after test failures as well as successes, and artifacts
are retained for **14 days**. Names include `smoke` or `regression` so the two
jobs' files stay separate.

| Artifact name (`<suite>` = `smoke` or `regression`) | Contents |
| --- | --- |
| `selenium-<suite>-html-report` | `report.html`, including embedded failure images |
| `selenium-<suite>-allure-results` | Raw Allure JSON results and attachments |
| `selenium-<suite>-allure-report` | Rendered Allure website |
| `selenium-<suite>-junit-results` | `junit.xml` for test-result tooling |
| `selenium-<suite>-screenshots` | Failure PNGs, when capture was possible |
| `selenium-<suite>-logs` | `pytest.log` console output, `automation.log`, and any worker logs |

Screenshot artifacts are created only when PNG files exist. If a job fails
before test execution, reports may be unavailable; inspect that job's setup-step
logs in Actions. The run summary records the test step outcome and directs you
to the suite-specific artifacts.

### Inspecting a failed run

1. While signed into GitHub, open **Actions → Selenium CI** and select the failed run.
2. Open the failing `Chrome / smoke` or `Chrome / regression` job and inspect
   **Run … tests in headless Chrome** for the original error and test ID.
3. Return to the run summary and download `selenium-<suite>-html-report` from
   **Artifacts**. Extract the ZIP, open `report.html`, and expand the failed row.
   Screenshots are embedded in that file.
4. Download `selenium-<suite>-screenshots` to view PNGs directly. Filenames identify
   the test, failure phase, UTC timestamp, and worker. Use the matching log
   artifact to inspect navigation, actions, and diagnostic warnings.
5. To inspect Allure locally, extract the raw-results artifact into
   `reports/allure-results` and run `allure serve reports/allure-results`. Or
   extract the rendered artifact and use `allure open <extracted-directory>`.

Local reproduction with the same browser mode and report options:

```bash
pytest --browser chrome --headless -m regression -v --env qa --reruns 0 \
  --html=reports/report.html --self-contained-html \
  --alluredir=reports/allure-results --clean-alluredir \
  --junitxml=reports/junit.xml
```

Generated reports, screenshots, logs, `.pytest_cache`, `__pycache__`, `.venv`,
and local `.env` files are ignored by Git. Default `allure-results/` and
`allure-report/` directories, driver caches, and generated HTML/XML reports are
ignored as well. The entire artifact directories, including local `.gitkeep`
files, stay out of commits. Pytest creates the output directories when needed.

## Code quality

```bash
ruff check .
ruff format --check .
python -m pip check
pytest --collect-only -q
```

Add locators and page interactions to `pages/`, expected scenarios to JSON, and
business assertions to `tests/`. Use explicit waits for observable state changes.
Avoid test-order dependencies, production data, catch-all exception suppression,
and automatic retries that mask failures.

## Verification record

Validated against the live Sauce Demo site on **2026-10-06**, with Python 3.12.3,
Chrome 154, and Firefox 157 on Linux:

| Check | Result |
| --- | --- |
| CI/CD upgrade: headless `-m smoke -v` | 4 passed |
| CI/CD upgrade: headless `-m regression -v` | 42 passed |
| Complete suite after CI/CD changes | 42 passed with explicit Chrome/driver paths and CI browser options |
| Workflow failure path through `tee` | Exact CI shell pipeline returned exit code 1 for an intentional assertion; embedded HTML screenshot, Allure PNG attachment, JUnit failure, standalone PNG, and console log verified |
| Marker and ignore-rule audit | Smoke is a 4-test subset of all 42 regression tests; generated output ignored recursively |
| Chrome headless `-v` after lifecycle fix | 42 passed (28 UI tests + 14 framework checks) |
| Chrome headless `-v --tb=short` after lifecycle fix | 42 passed; HTML, Allure results, and JUnit regenerated |
| Closed-driver and screenshot-transport failure probes | Original assertion/fixture failures preserved without reporting/internal errors; 3 live-session PNG attachments checked |
| Chrome headless regression, two xdist workers | 28 passed |
| Chrome headless with CI test selection and explicit browser/driver paths | 28 passed |
| Firefox headless regression, serial | 28 passed |
| Smoke tests with `-n auto` | 4 passed, four workers |
| Intentional setup/call/teardown failures | PNG files plus Allure attachments and embedded HTML images verified |
| Intentional transient failure with `-n 2 --reruns 2` | 1 passed, 1 visible rerun; first failure screenshot retained |
| Allure CLI rendering | Generated HTML with 42 passing results |
| HTML and JUnit reports | Generated and checked |
| Settings and source review | CLI precedence, URL/timeout validation, password redaction, imports, syntax, locator ownership, and required structure checked |
| Ruff and installed dependencies | Lint, formatting, and `pip check` passed |
| GitHub Actions workflow | `actionlint` passed; action inputs checked against upstream definitions |
| Docker Compose | `docker compose config --quiet` passed; pinned image release and healthcheck script verified |

Edge is implemented but was not run because it is not installed in the validation
environment. Docker containers were not executed because the Docker daemon was
unavailable. The GitHub workflow was validated locally; a hosted run requires
pushing to a GitHub repository. No Actions secret is required for Sauce Demo.
Intentional diagnostic probes were kept outside `tests/` and removed after
verification; the normal suite contains no deliberately failing tests.

## Project structure

```text
selenium-ecommerce-automation/
├── config/
│   ├── config.py
│   └── environments.py
├── pages/
│   ├── base_page.py
│   ├── login_page.py
│   ├── inventory_page.py
│   ├── cart_page.py
│   └── checkout_page.py
├── tests/
│   ├── test_login.py
│   ├── test_products.py
│   ├── test_cart.py
│   ├── test_checkout.py
│   └── framework/test_driver_lifecycle.py
├── utils/
│   ├── driver_factory.py
│   ├── logger.py
│   ├── screenshots.py
│   └── test_data.py
├── test_data/users.json
├── reports/
├── screenshots/
├── logs/
├── conftest.py
├── pytest.ini
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── README.md
└── .github/workflows/selenium-tests.yml
```

Python package directories also include `__init__.py`. Artifact directories are
created at runtime and ignored along with the local `.venv` and `.env`.

## References

- [Selenium explicit waits](https://www.selenium.dev/documentation/webdriver/waits/)
- [WebDriver Manager for Python](https://github.com/SergeyPirogov/webdriver_manager)
- [pytest-html user guide](https://pytest-html.readthedocs.io/en/latest/user_guide.html)
- [Allure Pytest documentation](https://allurereport.org/docs/pytest/)
- [Selenium Docker images](https://github.com/SeleniumHQ/docker-selenium)
- [Chrome setup action](https://github.com/browser-actions/setup-chrome)
- [Python setup and dependency caching](https://github.com/actions/setup-python)
- [GitHub Actions status badges](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge)
- [Downloading workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)
