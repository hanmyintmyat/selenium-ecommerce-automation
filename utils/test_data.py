"""JSON scenarios, Decimal currency values, and per-test Faker customers."""

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from faker import Faker

from config.config import PROJECT_ROOT


@dataclass(frozen=True)
class Product:
    name: str
    price: Decimal
    quantity: int = 1


@dataclass(frozen=True)
class Customer:
    first_name: str
    last_name: str
    postal_code: str


def load_test_data(
    path: Path = PROJECT_ROOT / "test_data" / "users.json",
) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def make_customer(fake: Faker) -> Customer:
    return Customer(fake.first_name(), fake.last_name(), fake.postcode())


def parse_price(text: str) -> Decimal:
    return Decimal(text.rsplit("$", 1)[-1].strip())
