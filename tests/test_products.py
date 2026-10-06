"""Catalogue contents, cart mutations, and all sorting modes."""

from collections import Counter

import allure
import pytest

from pages.inventory_page import InventoryPage
from utils.test_data import Product

pytestmark = [pytest.mark.regression, allure.feature("Products")]


@pytest.mark.smoke
def test_products_page_loads(
    inventory_page: InventoryPage, expected_products: list[Product]
) -> None:
    assert inventory_page.heading() == "Products"
    assert len(inventory_page.products()) == len(expected_products)
    assert inventory_page.cart_count() == 0


def test_product_names_and_prices(
    inventory_page: InventoryPage, expected_products: list[Product]
) -> None:
    assert Counter(inventory_page.products()) == Counter(expected_products)


def test_add_one_product(
    inventory_page: InventoryPage, expected_products: list[Product]
) -> None:
    inventory_page.add_product(expected_products[0].name)
    inventory_page.wait_for_cart_count(1)
    assert inventory_page.cart_count() == 1


def test_add_multiple_products(
    inventory_page: InventoryPage, expected_products: list[Product]
) -> None:
    for count, product in enumerate(expected_products[:3], start=1):
        inventory_page.add_product(product.name)
        inventory_page.wait_for_cart_count(count)
    assert inventory_page.cart_count() == 3


def test_remove_product(
    inventory_page: InventoryPage, expected_products: list[Product]
) -> None:
    inventory_page.add_product(expected_products[0].name)
    inventory_page.wait_for_cart_count(1)
    inventory_page.remove_product(expected_products[0].name)
    inventory_page.wait_for_cart_count(0)
    assert inventory_page.cart_count() == 0


@allure.story("Product sorting")
def test_product_sorting(
    inventory_page: InventoryPage, sorting_case: dict, expected_products: list[Product]
) -> None:
    inventory_page.sort_products(sorting_case["value"])
    field = sorting_case["field"]
    expected = sorted(
        [getattr(product, field) for product in expected_products],
        reverse=sorting_case["reverse"],
    )
    inventory_page.wait_until(
        lambda _: (
            [getattr(product, field) for product in inventory_page.products()]
            == expected
        ),
        f"products sorted by {sorting_case['id']}",
    )
    actual = (
        inventory_page.product_names()
        if field == "name"
        else inventory_page.product_prices()
    )
    assert actual == expected
    assert Counter(inventory_page.products()) == Counter(expected_products)
