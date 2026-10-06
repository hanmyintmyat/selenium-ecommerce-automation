"""Cart identity, prices, quantities, removal, and continued shopping."""

from collections import Counter

import allure
import pytest

from config.config import Settings
from pages.cart_page import CartPage
from pages.inventory_page import InventoryPage
from utils.test_data import Product

pytestmark = [pytest.mark.cart, pytest.mark.regression, allure.feature("Shopping cart")]


@pytest.mark.smoke
def test_cart_product_name_price_and_badge(
    inventory_page: InventoryPage,
    environment_config: Settings,
    expected_products: list[Product],
) -> None:
    product = expected_products[0]
    inventory_page.add_product(product.name)
    inventory_page.wait_for_cart_count(1)
    inventory_page.open_cart()
    cart = CartPage(inventory_page.driver, environment_config).wait_loaded()
    assert cart.heading() == "Your Cart"
    assert cart.cart_count() == 1
    assert cart.products() == [product]


def test_multiple_products_in_cart(
    inventory_page: InventoryPage,
    environment_config: Settings,
    expected_products: list[Product],
) -> None:
    products = expected_products[:3]
    for product in products:
        inventory_page.add_product(product.name)
    inventory_page.wait_for_cart_count(len(products))
    inventory_page.open_cart()
    cart = CartPage(inventory_page.driver, environment_config).wait_loaded()
    assert Counter(cart.products()) == Counter(products)
    assert cart.cart_count() == len(products)


def test_remove_product_from_cart(
    inventory_page: InventoryPage,
    environment_config: Settings,
    expected_products: list[Product],
) -> None:
    for product in expected_products[:2]:
        inventory_page.add_product(product.name)
    inventory_page.open_cart()
    cart = CartPage(inventory_page.driver, environment_config).wait_loaded()
    cart.remove_product(expected_products[0].name)
    assert cart.products() == [expected_products[1]]
    assert cart.cart_count() == 1


def test_remove_last_product_from_cart(
    inventory_page: InventoryPage,
    environment_config: Settings,
    expected_products: list[Product],
) -> None:
    product = expected_products[0]
    inventory_page.add_product(product.name)
    inventory_page.open_cart()
    cart = CartPage(inventory_page.driver, environment_config).wait_loaded()
    cart.remove_product(product.name)
    assert cart.products() == []
    assert cart.cart_count() == 0


def test_continue_shopping_preserves_cart(
    inventory_page: InventoryPage,
    environment_config: Settings,
    expected_products: list[Product],
) -> None:
    inventory_page.add_product(expected_products[0].name)
    inventory_page.open_cart()
    cart = CartPage(inventory_page.driver, environment_config).wait_loaded()
    cart.continue_shopping()
    inventory_page.wait_loaded()
    assert inventory_page.heading() == "Products"
    assert inventory_page.cart_count() == 1
    inventory_page.open_cart()
    assert cart.wait_loaded().products() == [expected_products[0]]


def test_initial_cart_is_empty(cart_page: CartPage) -> None:
    assert cart_page.products() == []
    assert cart_page.cart_count() == 0
