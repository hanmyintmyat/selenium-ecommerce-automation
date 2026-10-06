"""Explicitly synchronized Selenium actions shared by page objects."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from config.config import Settings
from utils.logger import get_logger
from utils.screenshots import take_screenshot

Locator = tuple[str, str]


class PageWaitError(TimeoutException):
    """A page condition timed out; includes the action and current URL."""


class BasePage:
    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        self.driver = driver
        self.settings = settings
        self.wait = WebDriverWait(driver, settings.timeout)
        self.logger = get_logger(type(self).__name__)

    def wait_until(
        self, condition: Callable[[WebDriver], Any], description: str
    ) -> Any:
        try:
            return self.wait.until(condition, message=description)
        except TimeoutException as exc:
            message = (
                f"{type(self).__name__}: {description} after {self.settings.timeout}s "
                f"at {self.driver.current_url}"
            )
            self.logger.error(message)
            raise PageWaitError(message) from exc

    def open_path(self, path: str = "") -> None:
        url = urljoin(self.settings.base_url, path)
        self.logger.info("Navigate to %s", url)
        self.driver.get(url)

    def wait_for_element_visible(self, locator: Locator) -> WebElement:
        return self.wait_until(
            EC.visibility_of_element_located(locator), f"visible {locator}"
        )

    def wait_for_element_clickable(self, locator: Locator) -> WebElement:
        return self.wait_until(
            EC.element_to_be_clickable(locator), f"clickable {locator}"
        )

    def wait_for_url(self, path: str) -> None:
        url = urljoin(self.settings.base_url, path)
        self.wait_until(EC.url_to_be(url), f"URL equals {url}")

    def click(self, locator: Locator, *, js_fallback: bool = False) -> None:
        self.logger.info("Click %s", locator)
        element = self.wait_for_element_clickable(locator)
        try:
            element.click()
        except ElementClickInterceptedException:
            if not js_fallback:
                raise
            self.logger.warning(
                "Intercepted click; explicit JavaScript fallback %s", locator
            )
            self.javascript_click(locator)

    def type_text(
        self, locator: Locator, text: str, *, sensitive: bool = False
    ) -> None:
        self.logger.info(
            "Type into %s: %s", locator, "[REDACTED]" if sensitive else text
        )
        element = self.wait_for_element_visible(locator)
        element.clear()
        element.send_keys(text)

    def clear_field(self, locator: Locator) -> None:
        self.logger.info("Clear %s", locator)
        self.wait_for_element_visible(locator).clear()

    def get_text(self, locator: Locator) -> str:
        return self.wait_for_element_visible(locator).text.strip()

    def select_dropdown(self, locator: Locator, value: str) -> None:
        self.logger.info("Select %s from %s", value, locator)
        Select(self.wait_for_element_visible(locator)).select_by_value(value)

    def scroll_to_element(self, locator: Locator) -> None:
        element = self.wait_for_element_visible(locator)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )

    def javascript_click(self, locator: Locator) -> None:
        self.logger.warning("JavaScript click %s", locator)
        self.driver.execute_script(
            "arguments[0].click();", self.wait_for_element_visible(locator)
        )

    def take_screenshot(self, name: str) -> Path | None:
        return take_screenshot(self.driver, self.settings.screenshots_dir, name)

    def get_page_title(self) -> str:
        return self.driver.title
