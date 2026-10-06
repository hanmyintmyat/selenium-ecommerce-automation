"""Cart line items and navigation."""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage, Locator
from utils.test_data import Product, parse_price


class CartPage(BasePage):
    TITLE = (By.CSS_SELECTOR, '[data-test="title"]')
    CART_LIST = (By.CSS_SELECTOR, '[data-test="cart-list"]')
    ITEMS = (By.CSS_SELECTOR, '[data-test="inventory-item"]')
    ITEM_NAME = (By.CSS_SELECTOR, '[data-test="inventory-item-name"]')
    ITEM_PRICE = (By.CSS_SELECTOR, '[data-test="inventory-item-price"]')
    QUANTITY = (By.CSS_SELECTOR, '[data-test="item-quantity"]')
    BADGE = (By.CSS_SELECTOR, '[data-test="shopping-cart-badge"]')
    CONTINUE = (By.CSS_SELECTOR, '[data-test="continue-shopping"]')
    CHECKOUT = (By.CSS_SELECTOR, '[data-test="checkout"]')

    def wait_loaded(self) -> "CartPage":
        self.wait_for_url("cart.html")
        self.wait_for_element_visible(self.CART_LIST)
        return self

    def heading(self) -> str:
        return self.get_text(self.TITLE)

    def products(self) -> list[Product]:
        self.wait_for_element_visible(self.CART_LIST)
        return [
            Product(
                row.find_element(*self.ITEM_NAME).text,
                parse_price(row.find_element(*self.ITEM_PRICE).text),
                int(row.find_element(*self.QUANTITY).text),
            )
            for row in self.driver.find_elements(*self.ITEMS)
        ]

    @staticmethod
    def _remove_button(product_name: str) -> Locator:
        slug = product_name.lower().replace(" ", "-")
        return By.CSS_SELECTOR, f'[data-test="remove-{slug}"]'

    def remove_product(self, product_name: str) -> None:
        locator = self._remove_button(product_name)
        self.click(locator)
        self.wait_until(
            EC.invisibility_of_element_located(locator), f"removed {product_name}"
        )

    def cart_count(self) -> int:
        badges = self.driver.find_elements(*self.BADGE)
        return int(badges[0].text) if badges else 0

    def continue_shopping(self) -> None:
        self.click(self.CONTINUE)
        self.wait_for_url("inventory.html")

    def checkout(self) -> None:
        self.click(self.CHECKOUT)
        self.wait_for_url("checkout-step-one.html")
