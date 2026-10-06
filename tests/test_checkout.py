"""Full purchase journey with monetary checks and required-field validation."""

from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

import allure
import pytest

from config.config import Settings
from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage
from utils.test_data import Customer, Product

pytestmark = [pytest.mark.checkout, pytest.mark.regression, allure.feature("Checkout")]


@pytest.mark.smoke
@allure.story("Complete purchase")
def test_complete_purchase(
    login_page: LoginPage,
    environment_config: Settings,
    expected_products: list[Product],
    customer: Customer,
    test_data: dict,
) -> None:
    with allure.step("Login and select a product"):
        login_page.login(
            environment_config.username, environment_config.require_password()
        )
        inventory = InventoryPage(login_page.driver, environment_config).wait_loaded()
        product = expected_products[0]
        inventory.add_product(product.name)
        inventory.wait_for_cart_count(1)
    with allure.step("Check the cart and begin checkout"):
        inventory.open_cart()
        cart = CartPage(login_page.driver, environment_config).wait_loaded()
        assert cart.products() == [product]
        cart.checkout()
    with allure.step("Enter a generated customer and review the order"):
        checkout = CheckoutPage(
            login_page.driver, environment_config
        ).wait_information_loaded()
        checkout.enter_customer(customer)
        checkout.continue_to_review()
        checkout.wait_review_loaded()
        assert checkout.products() == [product]
        assert checkout.subtotal() == product.price
        expected_tax = (
            product.price * Decimal(test_data["checkout"]["tax_rate"])
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert checkout.tax() == expected_tax
        assert checkout.total() == product.price + expected_tax
    with allure.step("Complete purchase and verify confirmation and empty cart"):
        checkout.finish()
        assert checkout.success_message() == test_data["checkout"]["success_message"]
        assert (
            checkout.completion_details() == test_data["checkout"]["completion_details"]
        )
        assert checkout.cart_is_empty()
        checkout.back_to_products()
        inventory.wait_loaded()
        assert inventory.cart_count() == 0


@allure.story("Required customer fields")
def test_checkout_required_fields(
    checkout_page: CheckoutPage, checkout_case: dict, customer: Customer
) -> None:
    incomplete_customer = replace(customer, **{checkout_case["field"]: ""})
    checkout_page.enter_customer(incomplete_customer)
    checkout_page.continue_to_review()
    assert checkout_page.error_message() == checkout_case["error"]
    checkout_page.wait_for_url("checkout-step-one.html")


def test_customer_can_correct_validation_error(
    checkout_page: CheckoutPage, customer: Customer, expected_products: list[Product]
) -> None:
    checkout_page.enter_customer(replace(customer, postal_code=""))
    checkout_page.continue_to_review()
    assert checkout_page.error_message() == "Error: Postal Code is required"
    checkout_page.enter_customer(customer)
    checkout_page.continue_to_review()
    checkout_page.wait_review_loaded()
    assert checkout_page.products() == [expected_products[0]]
