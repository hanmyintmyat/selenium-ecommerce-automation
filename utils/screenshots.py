"""Unique screenshot artifacts across workers, parameters, and retries."""

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from selenium.webdriver.remote.webdriver import WebDriver

from utils.logger import get_logger

logger = get_logger(__name__)


def capture_screenshot_png(driver: WebDriver | None) -> bytes | None:
    """Capture only a known live session; diagnostics must not fail a test.

    Local drivers can retain session_id after quit(), so also check their
    service process without issuing another HTTP command. A remote session or
    process may disappear between this check and capture; protect that race too.
    """
    try:
        if driver is None or not driver.session_id:
            return None
        service = getattr(driver, "service", None)
        if service is not None:
            process = service.process
            if process is None or process.poll() is not None:
                logger.warning(
                    "Could not capture failure screenshot: driver service is closed"
                )
                return None
        return driver.get_screenshot_as_png()
    except Exception as exc:
        # Includes urllib3 transport failures, not just Selenium exceptions.
        logger.warning("Could not capture failure screenshot: %s", exc)
        return None


def save_screenshot_bytes(png: bytes, directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w.-]+", "_", name).strip("_")[:140]
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S_%f")
    worker = os.getenv("PYTEST_XDIST_WORKER", "main")
    path = directory / f"{safe_name}_{timestamp}_{worker}_{uuid4().hex[:8]}.png"
    path.write_bytes(png)
    return path


def take_screenshot(
    driver: WebDriver | None, directory: Path, name: str
) -> Path | None:
    png = capture_screenshot_png(driver)
    if png is None:
        return None
    try:
        return save_screenshot_bytes(png, directory, name)
    except Exception as exc:
        logger.warning("Could not save failure screenshot: %s", exc)
        return None
