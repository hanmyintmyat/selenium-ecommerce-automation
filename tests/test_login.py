"""Positive authentication and JSON-driven negative scenarios."""

import allure
import pytest
from faker import Faker

from config.config import Settings
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage

pytestmark = [pytest.mark.login, pytest.mark.regression, allure.feature("Login")]


@pytest.mark.smoke
@allure.story("Standard user authentication")
def test_successful_login(login_page: LoginPage, environment_config: Settings) -> None:
    login_page.login(environment_config.username, environment_config.require_password())
    inventory = InventoryPage(login_page.driver, environment_config).wait_loaded()
    assert inventory.heading() == "Products"
    assert inventory.get_page_title() == "Swag Labs"


@allure.story("Authentication validation")
def test_login_validation(
    login_page: LoginPage,
    login_case: dict,
    test_data: dict,
    environment_config: Settings,
    fake: Faker,
) -> None:
    username_key = login_case["username"]
    if username_key == "empty":
        username = ""
    elif username_key == "invalid":
        username = f"unknown_{fake.uuid4()}"
    else:
        username = test_data["users"][username_key]
    password_key = login_case["password"]
    if password_key == "empty":
        password = ""
    elif password_key == "invalid":
        password = fake.password(length=20)
    else:
        password = environment_config.require_password()
    login_page.login(username, password)
    assert login_page.error_message() == login_case["error"]
    login_page.wait_for_url("")


def test_dismiss_login_validation(login_page: LoginPage) -> None:
    login_page.login("", "")
    assert login_page.error_message() == "Epic sadface: Username is required"
    login_page.dismiss_error()
    assert not login_page.has_error()
