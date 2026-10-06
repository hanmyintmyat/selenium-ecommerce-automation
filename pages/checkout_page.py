"""Customer information, order review, and purchase confirmation."""

from decimal import Decimal

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage
from utils.test_data import Customer, Product, parse_price


class CheckoutPage(BasePage):
    FIRST_NAME = (By.CSS_SELECTOR, '[data-test="firstName"]')
    LAST_NAME = (By.CSS_SELECTOR, '[data-test="lastName"]')
    POSTAL_CODE = (By.CSS_SELECTOR, '[data-test="postalCode"]')
    CONTINUE = (By.CSS_SELECTOR, '[data-test="continue"]')
    ERROR = (By.CSS_SELECTOR, '[data-test="error"]')
    ITEMS = (By.CSS_SELECTOR, '[data-test="inventory-item"]')
    ITEM_NAME = (By.CSS_SELECTOR, '[data-test="inventory-item-name"]')
    ITEM_PRICE = (By.CSS_SELECTOR, '[data-test="inventory-item-price"]')
    QUANTITY = (By.CSS_SELECTOR, '[data-test="item-quantity"]')
    SUBTOTAL = (By.CSS_SELECTOR, '[data-test="subtotal-label"]')
    TAX = (By.CSS_SELECTOR, '[data-test="tax-label"]')
    TOTAL = (By.CSS_SELECTOR, '[data-test="total-label"]')
    FINISH = (By.CSS_SELECTOR, '[data-test="finish"]')
    SUCCESS = (By.CSS_SELECTOR, '[data-test="complete-header"]')
    COMPLETE_TEXT = (By.CSS_SELECTOR, '[data-test="complete-text"]')
    BACK_HOME = (By.CSS_SELECTOR, '[data-test="back-to-products"]')
    BADGE = (By.CSS_SELECTOR, '[data-test="shopping-cart-badge"]')

    def wait_information_loaded(self) -> "CheckoutPage":
        self.wait_for_url("checkout-step-one.html")
        self.wait_for_element_visible(self.FIRST_NAME)
        return self

    def enter_customer(self, customer: Customer) -> None:
        self.type_text(self.FIRST_NAME, customer.first_name)
        self.type_text(self.LAST_NAME, customer.last_name)
        self.type_text(self.POSTAL_CODE, customer.postal_code)

    def continue_to_review(self) -> None:
        self.click(self.CONTINUE)

    def error_message(self) -> str:
        return self.get_text(self.ERROR)

    def wait_review_loaded(self) -> "CheckoutPage":
        self.wait_for_url("checkout-step-two.html")
        self.wait_for_element_visible(self.TOTAL)
        return self

    def products(self) -> list[Product]:
        rows = self.wait_until(
            EC.visibility_of_all_elements_located(self.ITEMS), "review items"
        )
        return [
            Product(
                row.find_element(*self.ITEM_NAME).text,
                parse_price(row.find_element(*self.ITEM_PRICE).text),
                int(row.find_element(*self.QUANTITY).text),
            )
            for row in rows
        ]

    def subtotal(self) -> Decimal:
        return parse_price(self.get_text(self.SUBTOTAL))

    def tax(self) -> Decimal:
        return parse_price(self.get_text(self.TAX))

    def total(self) -> Decimal:
        return parse_price(self.get_text(self.TOTAL))

    def finish(self) -> None:
        self.click(self.FINISH)
        self.wait_for_url("checkout-complete.html")
        self.wait_for_element_visible(self.SUCCESS)

    def success_message(self) -> str:
        return self.get_text(self.SUCCESS)

    def completion_details(self) -> str:
        return self.get_text(self.COMPLETE_TEXT)

    def cart_is_empty(self) -> bool:
        return not self.driver.find_elements(*self.BADGE)

    def back_to_products(self) -> None:
        self.click(self.BACK_HOME)
        self.wait_for_url("inventory.html")
