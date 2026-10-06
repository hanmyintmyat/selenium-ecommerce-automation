"""Sauce Demo authentication page."""

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class LoginPage(BasePage):
    USERNAME = (By.CSS_SELECTOR, '[data-test="username"]')
    PASSWORD = (By.CSS_SELECTOR, '[data-test="password"]')
    LOGIN = (By.CSS_SELECTOR, '[data-test="login-button"]')
    ERROR = (By.CSS_SELECTOR, '[data-test="error"]')
    ERROR_CLOSE = (By.CSS_SELECTOR, '[data-test="error-button"]')

    def open(self) -> "LoginPage":
        self.open_path()
        self.wait_for_element_visible(self.LOGIN)
        return self

    def login(self, username: str, password: str) -> None:
        self.type_text(self.USERNAME, username, sensitive=True)
        self.type_text(self.PASSWORD, password, sensitive=True)
        self.click(self.LOGIN)

    def error_message(self) -> str:
        return self.get_text(self.ERROR)

    def dismiss_error(self) -> None:
        self.click(self.ERROR_CLOSE)

    def has_error(self) -> bool:
        return any(
            element.is_displayed() for element in self.driver.find_elements(*self.ERROR)
        )
