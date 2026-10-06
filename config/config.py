"""Load .env without overriding shell/CI variables and validate settings."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from config.environments import ENVIRONMENTS

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(ValueError):
    """A framework setting is missing or invalid."""


def _positive_number(name: str, default: str) -> float:
    try:
        value = float(os.getenv(name, default))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a positive number") from exc
    if not 0 < value < float("inf"):
        raise ConfigurationError(f"{name} must be a finite positive number")
    return value


def _boolean(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default).strip().lower()
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise ConfigurationError(f"{name} must be true or false")
    return value in {"true", "1", "yes"}


def _url(value: str, name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError(f"{name} must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ConfigurationError(f"{name} must not contain credentials")
    return value


@dataclass(frozen=True)
class Settings:
    environment: str
    base_url: str
    browser: str
    headless: bool
    timeout: float
    page_load_timeout: float
    remote_url: str | None
    browser_binary: str | None
    driver_path: str | None
    chrome_no_sandbox: bool
    username: str
    password: str = field(repr=False)
    reports_dir: Path = PROJECT_ROOT / "reports"
    screenshots_dir: Path = PROJECT_ROOT / "screenshots"
    logs_dir: Path = PROJECT_ROOT / "logs"

    @classmethod
    def load(
        cls,
        environment: str | None = None,
        browser: str | None = None,
        headless: bool | None = None,
    ) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        environment = environment or os.getenv("TEST_ENV", "qa")
        if environment not in ENVIRONMENTS:
            raise ConfigurationError(f"Unknown environment: {environment}")
        browser = (browser or os.getenv("BROWSER", "chrome")).lower()
        if browser not in {"chrome", "firefox", "edge"}:
            raise ConfigurationError(f"Unsupported browser: {browser}")
        base_url = os.getenv(
            f"{environment.upper()}_BASE_URL",
            os.getenv("BASE_URL", ENVIRONMENTS[environment]),
        )
        remote_url = os.getenv("SELENIUM_REMOTE_URL") or None
        return cls(
            environment=environment,
            base_url=_url(base_url, "BASE_URL").rstrip("/") + "/",
            browser=browser,
            headless=_boolean("HEADLESS") if headless is None else headless,
            timeout=_positive_number("EXPLICIT_WAIT", "10"),
            page_load_timeout=_positive_number("PAGE_LOAD_TIMEOUT", "30"),
            remote_url=_url(remote_url, "SELENIUM_REMOTE_URL") if remote_url else None,
            browser_binary=(
                os.getenv(f"{browser.upper()}_BINARY")
                or os.getenv("BROWSER_BINARY")
                or None
            ),
            driver_path=os.getenv("WEBDRIVER_PATH") or None,
            chrome_no_sandbox=_boolean("CHROME_NO_SANDBOX"),
            username=os.getenv("SAUCE_USERNAME", "standard_user"),
            password=os.getenv("SAUCE_PASSWORD", ""),
        )

    def require_password(self) -> str:
        if not self.password or self.password == "replace-with-demo-password":
            raise ConfigurationError(
                "Set SAUCE_PASSWORD in .env or the process environment. "
                "The public demo password is displayed on Sauce Demo's login page."
            )
        return self.password
