"""Local WebDriver Manager drivers and optional Selenium Grid sessions."""

from functools import lru_cache

from filelock import FileLock
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from config.config import PROJECT_ROOT, Settings
from utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=3)
def _managed_driver_path(browser: str) -> str:
    # Serialize cache writes when xdist workers start together.
    cache_dir = PROJECT_ROOT / ".driver-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    with FileLock(str(cache_dir / f"{browser}.lock"), timeout=180):
        if browser == "chrome":
            return ChromeDriverManager().install()
        if browser == "firefox":
            return GeckoDriverManager().install()
        return EdgeChromiumDriverManager().install()


class DriverFactory:
    """Create a browser with a fresh profile for every test."""

    @staticmethod
    def create(settings: Settings) -> WebDriver:
        if settings.browser == "firefox":
            options = webdriver.FirefoxOptions()
            if settings.headless:
                options.add_argument("-headless")
        else:
            options = (
                webdriver.ChromeOptions()
                if settings.browser == "chrome"
                else webdriver.EdgeOptions()
            )
            if settings.headless:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1440,1000")
            options.add_argument("--disable-dev-shm-usage")
            if settings.chrome_no_sandbox:
                options.add_argument("--no-sandbox")
            options.add_argument("--disable-search-engine-choice-screen")
            options.add_argument(
                "--disable-features=PasswordLeakDetection,PasswordManagerOnboarding"
            )
            options.add_experimental_option(
                "prefs",
                {
                    "credentials_enable_service": False,
                    "profile.password_manager_enabled": False,
                    "profile.password_manager_leak_detection": False,
                },
            )
        if settings.browser_binary:
            options.binary_location = settings.browser_binary
        logger.info(
            "Starting browser=%s headless=%s remote=%s",
            settings.browser,
            settings.headless,
            bool(settings.remote_url),
        )
        if settings.remote_url:
            driver = webdriver.Remote(settings.remote_url, options=options)
        else:
            driver_path = settings.driver_path or _managed_driver_path(settings.browser)
            if settings.browser == "chrome":
                driver = webdriver.Chrome(
                    service=ChromeService(driver_path), options=options
                )
            elif settings.browser == "firefox":
                driver = webdriver.Firefox(
                    service=FirefoxService(driver_path), options=options
                )
            else:
                driver = webdriver.Edge(
                    service=EdgeService(driver_path), options=options
                )
        # Configuration and cleanup belong to the browser fixture, which can
        # release a successfully created session even if configuration fails.
        return driver
