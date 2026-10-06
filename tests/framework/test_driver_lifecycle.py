"""Exercise failure paths without relying on an unreachable real browser."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from selenium.common.exceptions import TimeoutException
from urllib3.exceptions import MaxRetryError

import conftest as framework
from utils import screenshots

pytestmark = [pytest.mark.framework, pytest.mark.regression]
PNG = b"\x89PNG\r\n\x1a\nframework-regression-test"


def make_driver() -> Mock:
    driver = Mock()
    driver.session_id = "current-test-session"
    driver.service = SimpleNamespace(process=SimpleNamespace(poll=lambda: None))
    driver.get_screenshot_as_png.return_value = PNG
    return driver


def refused_connection() -> MaxRetryError:
    return MaxRetryError(
        None,
        "/session/current-test-session/screenshot",
        ConnectionRefusedError(111, "Connection refused"),
    )


@pytest.fixture
def item(tmp_path, environment_config):
    config = Mock()
    config.stash = pytest.Stash()
    config.stash[framework.SETTINGS] = replace(
        environment_config, screenshots_dir=tmp_path
    )
    config.getoption.side_effect = lambda name, default=None: {
        "allure_report_dir": "allure-results",
        "htmlpath": "report.html",
    }.get(name, default)
    return SimpleNamespace(
        stash=pytest.Stash(),
        funcargs={},
        config=config,
        name="test_primary_failure",
        nodeid="test_primary_failure",
    )


@pytest.fixture
def allure_attachment(monkeypatch):
    attachment = Mock()
    monkeypatch.setattr(framework.allure, "attach", attachment)
    return attachment


def make_report(when="call", failed=True):
    return SimpleNamespace(
        when=when,
        failed=failed,
        passed=not failed,
        outcome="failed" if failed else "passed",
        longrepr="AssertionError: ORIGINAL TEST FAILURE",
    )


def run_report_hook(item, report):
    hook = framework.pytest_runtest_makereport(item, None)
    next(hook)
    with pytest.raises(StopIteration):
        hook.send(SimpleNamespace(get_result=lambda: report))


def start_browser(monkeypatch, item, driver):
    monkeypatch.setattr(framework.DriverFactory, "create", Mock(return_value=driver))
    return framework.browser.__wrapped__(
        SimpleNamespace(node=item), item.config.stash[framework.SETTINGS]
    )


@pytest.mark.parametrize("state", ["missing", "no_session", "stopped", "no_process"])
def test_screenshot_skips_closed_sessions(state):
    driver = make_driver()
    if state == "missing":
        assert screenshots.capture_screenshot_png(None) is None
        return
    if state == "no_session":
        driver.session_id = None
    elif state == "stopped":
        # Selenium may leave session_id set after quitting a local driver.
        driver.service.process.poll = lambda: 0
    else:
        driver.service.process = None
    assert screenshots.capture_screenshot_png(driver) is None
    driver.get_screenshot_as_png.assert_not_called()


def test_screenshot_transport_failure_is_only_a_warning(caplog):
    driver = make_driver()
    driver.get_screenshot_as_png.side_effect = refused_connection()
    assert screenshots.capture_screenshot_png(driver) is None
    assert "Could not capture failure screenshot" in caplog.text
    assert "Connection refused" in caplog.text


def test_screenshot_write_failure_is_only_a_warning(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(
        screenshots,
        "save_screenshot_bytes",
        Mock(side_effect=PermissionError("read-only directory")),
    )
    assert screenshots.take_screenshot(make_driver(), tmp_path, "failure") is None
    assert "Could not save failure screenshot" in caplog.text


def test_failure_capture_and_attachments_precede_quit(
    monkeypatch, item, allure_attachment
):
    driver = make_driver()
    events = []
    driver.get_screenshot_as_png.side_effect = lambda: (
        events.append("screenshot") or PNG
    )
    driver.quit.side_effect = lambda: events.append("quit")
    allure_attachment.side_effect = lambda *args, **kwargs: events.append("allure")
    original_html_image = framework.pytest_html.extras.png

    def html_image(*args, **kwargs):
        events.append("html")
        return original_html_image(*args, **kwargs)

    monkeypatch.setattr(framework.pytest_html.extras, "png", html_image)
    fixture = start_browser(monkeypatch, item, driver)
    assert next(fixture) is driver
    item.funcargs["browser"] = driver
    report = make_report()
    run_report_hook(item, report)
    assert events == ["screenshot", "allure", "html"]
    with pytest.raises(StopIteration):
        next(fixture)
    assert events == ["screenshot", "allure", "html", "screenshot", "quit"]
    assert driver.session_id is None
    assert framework.DRIVER not in item.stash
    assert report.longrepr == "AssertionError: ORIGINAL TEST FAILURE"
    # Even if funcargs still contains the closed object, teardown uses bytes.
    run_report_hook(item, make_report(when="teardown"))
    assert events[-2:] == ["allure", "html"]
    assert driver.get_screenshot_as_png.call_count == 2
    assert report.extras[0]["content"]


def test_configuration_failure_is_cleaned_up_without_masking_it(monkeypatch, item):
    driver = make_driver()
    driver.set_page_load_timeout.side_effect = TimeoutException(
        "original configuration error"
    )
    driver.quit.side_effect = refused_connection()
    fixture = start_browser(monkeypatch, item, driver)
    with pytest.raises(TimeoutException, match="original configuration error"):
        next(fixture)
    driver.quit.assert_called_once()
    assert driver.session_id is None
    assert framework.DRIVER not in item.stash


def test_capture_and_cleanup_errors_preserve_original_test_failure(
    monkeypatch, item, allure_attachment, caplog
):
    driver = make_driver()
    driver.get_screenshot_as_png.side_effect = refused_connection()
    driver.quit.side_effect = refused_connection()
    fixture = start_browser(monkeypatch, item, driver)
    next(fixture)
    item.funcargs["browser"] = driver
    report = make_report()
    run_report_hook(item, report)
    with pytest.raises(StopIteration):
        next(fixture)
    assert report.longrepr == "AssertionError: ORIGINAL TEST FAILURE"
    assert framework.LAST_PNG not in item.stash
    allure_attachment.assert_not_called()
    driver.quit.assert_called_once()
    assert "Could not capture failure screenshot" in caplog.text
    assert "Browser teardown failed" in caplog.text


def test_standalone_cleanup_failure_is_not_suppressed(monkeypatch, item):
    driver = make_driver()
    driver.quit.side_effect = refused_connection()
    fixture = start_browser(monkeypatch, item, driver)
    next(fixture)
    run_report_hook(item, make_report(failed=False))
    with pytest.raises(MaxRetryError):
        next(fixture)
    assert driver.session_id is None


def test_retry_uses_current_driver_and_clears_old_image(
    monkeypatch, item, allure_attachment
):
    old_driver = make_driver()
    item.funcargs["browser"] = old_driver
    item.stash[framework.LAST_PNG] = b"previous attempt"
    item.stash[framework.TEST_REPORTS] = {"call": make_report()}
    driver = make_driver()
    fixture = start_browser(monkeypatch, item, driver)
    next(fixture)
    assert framework.LAST_PNG not in item.stash
    assert item.stash[framework.TEST_REPORTS] == {}
    run_report_hook(item, make_report())
    driver.get_screenshot_as_png.assert_called_once()
    old_driver.get_screenshot_as_png.assert_not_called()
    with pytest.raises(StopIteration):
        next(fixture)


@pytest.mark.parametrize("destination", ["disk", "allure", "html"])
def test_report_attachment_errors_preserve_original_failure(
    destination, monkeypatch, item, allure_attachment, caplog
):
    driver = make_driver()
    item.stash[framework.DRIVER] = driver
    item.funcargs["browser"] = driver
    error = RuntimeError("intentional reporting error")
    if destination == "disk":
        monkeypatch.setattr(framework, "save_screenshot_bytes", Mock(side_effect=error))
    elif destination == "allure":
        allure_attachment.side_effect = error
    else:
        monkeypatch.setattr(
            framework.pytest_html.extras, "png", Mock(side_effect=error)
        )
    report = make_report()
    run_report_hook(item, report)
    assert report.longrepr == "AssertionError: ORIGINAL TEST FAILURE"
    assert report.failed
    assert "intentional reporting error" in caplog.text
    if destination == "disk":
        allure_attachment.assert_called_once()
        assert len(report.extras) == 1
