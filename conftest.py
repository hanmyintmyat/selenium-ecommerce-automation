"""CLI configuration, independent fixtures, and report diagnostics."""

import base64
import os
from collections.abc import Iterator
from copy import deepcopy
from decimal import Decimal
from typing import Any

import allure
import pytest
import pytest_html
from faker import Faker
from selenium.webdriver.remote.webdriver import WebDriver

from config.config import ConfigurationError, Settings
from config.environments import ENVIRONMENTS
from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage
from utils.driver_factory import DriverFactory
from utils.logger import configure_logging, get_logger
from utils.screenshots import capture_screenshot_png, save_screenshot_bytes
from utils.test_data import Customer, Product, load_test_data, make_customer

SETTINGS = pytest.StashKey[Settings]()
DRIVER = pytest.StashKey[WebDriver]()
LAST_PNG = pytest.StashKey[bytes]()
TEST_REPORTS = pytest.StashKey[dict[str, pytest.TestReport]]()
logger = get_logger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("selenium", "Selenium browser configuration")
    group.addoption("--browser", choices=["chrome", "firefox", "edge"], default=None)
    group.addoption("--headless", action="store_true", default=None)
    group.addoption(
        "--headed", action="store_true", default=False, help="Override HEADLESS=true"
    )
    group.addoption("--env", choices=list(ENVIRONMENTS), default=None)


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("headless") and config.getoption("headed"):
        raise pytest.UsageError("Choose --headless or --headed, not both")
    headless = False if config.getoption("headed") else config.getoption("headless")
    try:
        settings = Settings.load(
            environment=config.getoption("env"),
            browser=config.getoption("browser"),
            headless=headless,
        )
    except ConfigurationError as exc:
        raise pytest.UsageError(str(exc)) from exc
    config.stash[SETTINGS] = settings
    for directory in (
        settings.reports_dir,
        settings.screenshots_dir,
        settings.logs_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.logs_dir)


def pytest_report_header(config: pytest.Config) -> str:
    settings = config.stash[SETTINGS]
    return (
        f"Selenium: browser={settings.browser}, headless={settings.headless}, "
        f"environment={settings.environment}, base_url={settings.base_url}"
    )


def pytest_xdist_auto_num_workers(config: pytest.Config) -> int:
    """Keep auto execution modest for a public demo; allow explicit overrides."""
    override = os.getenv("PYTEST_XDIST_AUTO_NUM_WORKERS")
    if override:
        try:
            workers = int(override)
        except ValueError as exc:
            raise pytest.UsageError(
                "PYTEST_XDIST_AUTO_NUM_WORKERS must be positive"
            ) from exc
        if workers < 1:
            raise pytest.UsageError("PYTEST_XDIST_AUTO_NUM_WORKERS must be positive")
        return workers
    return min(4, os.cpu_count() or 1)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    data = load_test_data()
    for name, key in (
        ("login_case", "login_cases"),
        ("sorting_case", "sorting_cases"),
        ("checkout_case", "checkout_cases"),
    ):
        if name in metafunc.fixturenames:
            metafunc.parametrize(
                name, data[key], ids=[case["id"] for case in data[key]]
            )


@pytest.fixture(scope="session")
def environment_config(pytestconfig: pytest.Config) -> Settings:
    return pytestconfig.stash[SETTINGS]


@pytest.fixture(scope="session")
def _test_data() -> dict[str, Any]:
    return load_test_data()


@pytest.fixture
def test_data(_test_data: dict[str, Any]) -> dict[str, Any]:
    # Each test receives its own copy, including during parallel execution.
    return deepcopy(_test_data)


@pytest.fixture
def fake() -> Faker:
    return Faker("en_US")


@pytest.fixture
def customer(fake: Faker) -> Customer:
    return make_customer(fake)


@pytest.fixture
def expected_products(test_data: dict[str, Any]) -> list[Product]:
    return [
        Product(item["name"], Decimal(item["price"])) for item in test_data["products"]
    ]


@pytest.fixture
def browser(
    request: pytest.FixtureRequest, environment_config: Settings
) -> Iterator[WebDriver]:
    # Reset attempt-specific state so reruns never reuse a previous session/image.
    request.node.stash[TEST_REPORTS] = {}
    if LAST_PNG in request.node.stash:
        del request.node.stash[LAST_PNG]
    driver = DriverFactory.create(environment_config)
    request.node.stash[DRIVER] = driver
    configured = False
    try:
        driver.implicitly_wait(0)
        driver.set_page_load_timeout(environment_config.page_load_timeout)
        driver.set_window_size(1440, 1000)
        configured = True
        yield driver
    finally:
        # Teardown reports arrive after all finalizers. Retain pixels BEFORE
        # quitting; the teardown report hook must never talk to this driver.
        png = capture_screenshot_png(driver)
        if png is not None:
            request.node.stash[LAST_PNG] = png
        del request.node.stash[DRIVER]
        try:
            if driver.session_id is not None:
                driver.quit()
                logger.info("Browser session closed")
        except Exception as exc:
            logger.warning("Browser teardown failed: %s", exc)
            reports = request.node.stash[TEST_REPORTS]
            # Preserve an existing setup/test failure, including configuration
            # errors raised before yield. A standalone cleanup failure still fails.
            if configured and not any(report.failed for report in reports.values()):
                raise
        finally:
            driver.session_id = None


@pytest.fixture
def login_page(browser: WebDriver, environment_config: Settings) -> LoginPage:
    return LoginPage(browser, environment_config).open()


@pytest.fixture
def inventory_page(
    login_page: LoginPage, environment_config: Settings
) -> InventoryPage:
    login_page.login(environment_config.username, environment_config.require_password())
    return InventoryPage(login_page.driver, environment_config).wait_loaded()


@pytest.fixture
def cart_page(inventory_page: InventoryPage, environment_config: Settings) -> CartPage:
    inventory_page.open_cart()
    return CartPage(inventory_page.driver, environment_config).wait_loaded()


@pytest.fixture
def checkout_page(
    inventory_page: InventoryPage,
    expected_products: list[Product],
    environment_config: Settings,
) -> CheckoutPage:
    inventory_page.add_product(expected_products[0].name)
    inventory_page.open_cart()
    CartPage(inventory_page.driver, environment_config).wait_loaded().checkout()
    return CheckoutPage(
        inventory_page.driver, environment_config
    ).wait_information_loaded()


@pytest.fixture(autouse=True)
def log_test_lifecycle(request: pytest.FixtureRequest) -> Iterator[None]:
    logger.info("TEST START %s", request.node.nodeid)
    yield


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    reports = item.stash.get(TEST_REPORTS, {})
    reports[report.when] = report
    item.stash[TEST_REPORTS] = reports
    if report.when == "call" and report.passed:
        logger.info("VALIDATION PASSED %s", item.nodeid)
    if report.when == "teardown":
        logger.info("TEST COMPLETE %s teardown=%s", item.nodeid, report.outcome)
    if not report.failed:
        return
    logger.error(
        "TEST FAILED %s phase=%s\n%s", item.nodeid, report.when, report.longrepr
    )
    png = None
    if report.when in {"setup", "call"} and DRIVER in item.stash:
        # Use this test's fixture, with its per-item registration as a fallback
        # if browser configuration failed before the fixture reached yield.
        registered_driver = item.stash[DRIVER]
        fixture_driver = item.funcargs.get("browser")
        driver = (
            fixture_driver if fixture_driver is registered_driver else registered_driver
        )
        png = capture_screenshot_png(driver)
        if png is not None:
            item.stash[LAST_PNG] = png
    else:
        # Never call screenshot APIs during/after browser teardown.
        png = item.stash.get(LAST_PNG, None)
    if png is None:
        logger.warning(
            "No browser screenshot available for %s (%s)", item.nodeid, report.when
        )
        return
    settings = item.config.stash[SETTINGS]
    try:
        path = save_screenshot_bytes(
            png, settings.screenshots_dir, f"{item.name}_{report.when}"
        )
        logger.info("Failure screenshot: %s", path)
    except Exception as exc:
        logger.warning("Could not save failure screenshot: %s", exc)
    if item.config.getoption("allure_report_dir", default=None):
        try:
            allure.attach(
                png,
                name=f"{item.name} ({report.when})",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception as exc:
            logger.warning("Could not attach Allure failure screenshot: %s", exc)
    if item.config.getoption("htmlpath", default=None):
        try:
            extras = getattr(report, "extras", [])
            extras.append(
                pytest_html.extras.png(
                    base64.b64encode(png).decode("ascii"), name="Failure screenshot"
                )
            )
            report.extras = extras
        except Exception as exc:
            logger.warning("Could not attach HTML failure screenshot: %s", exc)
