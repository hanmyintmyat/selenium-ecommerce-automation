"""Product catalogue, sorting controls, and cart badge."""

from decimal import Decimal

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage, Locator
from utils.test_data import Product, parse_price


class InventoryPage(BasePage):
    TITLE = (By.CSS_SELECTOR, '[data-test="title"]')
    ITEMS = (By.CSS_SELECTOR, '[data-test="inventory-item"]')
    ITEM_NAME = (By.CSS_SELECTOR, '[data-test="inventory-item-name"]')
    ITEM_PRICE = (By.CSS_SELECTOR, '[data-test="inventory-item-price"]')
    SORT = (By.CSS_SELECTOR, '[data-test="product-sort-container"]')
    CART = (By.CSS_SELECTOR, '[data-test="shopping-cart-link"]')
    BADGE = (By.CSS_SELECTOR, '[data-test="shopping-cart-badge"]')

    def wait_loaded(self) -> "InventoryPage":
        self.wait_for_url("inventory.html")
        self.wait_for_element_visible(self.ITEMS)
        return self

    def heading(self) -> str:
        return self.get_text(self.TITLE)

    def products(self) -> list[Product]:
        rows = self.wait_until(
            EC.visibility_of_all_elements_located(self.ITEMS), "product rows"
        )
        return [
            Product(
                row.find_element(*self.ITEM_NAME).text,
                parse_price(row.find_element(*self.ITEM_PRICE).text),
            )
            for row in rows
        ]

    def product_names(self) -> list[str]:
        return [product.name for product in self.products()]

    def product_prices(self) -> list[Decimal]:
        return [product.price for product in self.products()]

    @staticmethod
    def _button(product_name: str, action: str) -> Locator:
        slug = product_name.lower().replace(" ", "-")
        return By.CSS_SELECTOR, f'[data-test="{action}-{slug}"]'

    def add_product(self, product_name: str) -> None:
        self.click(self._button(product_name, "add-to-cart"))
        self.wait_for_element_visible(self._button(product_name, "remove"))

    def remove_product(self, product_name: str) -> None:
        self.click(self._button(product_name, "remove"))
        self.wait_for_element_visible(self._button(product_name, "add-to-cart"))

    def cart_count(self) -> int:
        badges = self.driver.find_elements(*self.BADGE)
        return int(badges[0].text) if badges else 0

    def wait_for_cart_count(self, expected: int) -> None:
        self.wait_until(
            lambda _: self.cart_count() == expected, f"cart badge equals {expected}"
        )

    def open_cart(self) -> None:
        self.click(self.CART)
        self.wait_for_url("cart.html")

    def sort_products(self, value: str) -> None:
        self.select_dropdown(self.SORT, value)
        self.wait_until(
            lambda driver: (
                driver.find_element(*self.SORT).get_attribute("value") == value
            ),
            f"sort selection equals {value}",
        )
