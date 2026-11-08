"""Validated, immutable snapshots. No optimizer, persistence, or Streamlit imports."""
from dataclasses import dataclass
import json
from types import MappingProxyType
from collections.abc import Mapping


class ValidationError(ValueError):
    """Input does not satisfy the transportation data contract."""


def _integer(value, path):
    # bool is an int subclass in Python, but True is not a valid unit count.
    if type(value) is not int or value < 0:
        raise ValidationError(f"{path}: expected a nonnegative integer")


def _catalog(value, path):
    if not isinstance(value, Mapping) or not value:
        raise ValidationError(f"{path}: expected a nonempty ID-to-name mapping")
    for key, name in value.items():
        for text in (key, name):
            if not isinstance(text, str) or not text.strip() or text != text.strip():
                raise ValidationError(f"{path}: IDs and names must be nonblank, trimmed strings")
    return MappingProxyType(dict(value))


def _matrix(value, rows, columns, path):
    if not isinstance(value, Mapping) or set(value) != set(rows):
        raise ValidationError(f"{path}: rows must exactly match the location IDs")
    result = {}
    for row_id, row in value.items():
        if not isinstance(row, Mapping) or set(row) != set(columns):
            raise ValidationError(f"{path}.{row_id}: missing or unknown column IDs")
        for column_id, number in row.items():
            _integer(number, f"{path}.{row_id}.{column_id}")
        result[row_id] = MappingProxyType(dict(row))
    return MappingProxyType(result)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class State:
    items: Mapping[str, str]
    warehouses: Mapping[str, str]
    stores: Mapping[str, str]
    inventory: Mapping[str, Mapping[str, int]]
    demand: Mapping[str, Mapping[str, int]]
    shipping_costs_cents: Mapping[str, Mapping[str, int]]
    revision: int = 0
    schema_version: int = 1

    def __post_init__(self):
        _integer(self.revision, "revision")
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValidationError("schema_version: only integer version 1 is supported")
        for name in ("items", "warehouses", "stores"):
            object.__setattr__(self, name, _catalog(getattr(self, name), name))
        for name, rows, columns in (
            ("inventory", self.warehouses, self.items),
            ("demand", self.stores, self.items),
            ("shipping_costs_cents", self.warehouses, self.stores),
        ):
            object.__setattr__(self, name, _matrix(getattr(self, name), rows, columns, name))

    @classmethod
    def from_dict(cls, data):
        expected = set(cls.__dataclass_fields__)
        if not isinstance(data, Mapping) or set(data) != expected:
            raise ValidationError("state: missing or unknown top-level fields")
        return cls(**data)

    @classmethod
    def from_json(cls, text):
        """Decode a string only; file I/O and atomic saving belong to Stage 8."""
        try:
            data = json.loads(text, object_pairs_hook=_unique_object)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValidationError(f"Invalid JSON: {error}") from error
        return cls.from_dict(data)

    def to_dict(self):
        """Return an independent, JSON-compatible copy, never mutable internals."""
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            **{name: dict(getattr(self, name))
               for name in ("items", "warehouses", "stores")},
            **{name: {key: dict(row) for key, row in getattr(self, name).items()}
               for name in ("inventory", "demand", "shipping_costs_cents")},
        }

    def with_quantity(self, table, location_id, item_id, quantity, operation="set"):
        """Return a validated edit; failures leave this snapshot untouched."""
        if table not in ("inventory", "demand"):
            raise ValidationError("table must be inventory or demand")
        _integer(quantity, "quantity")
        matrix = getattr(self, table)
        if location_id not in matrix or item_id not in self.items:
            raise ValidationError("Unknown location or item ID")
        old = matrix[location_id][item_id]
        if operation == "set":
            new = quantity
        elif operation == "add":
            new = old + quantity
        elif operation == "remove":
            new = old - quantity
        else:
            raise ValidationError("operation must be set, add, or remove")
        _integer(new, "resulting quantity")
        return self._with_cell(table, location_id, item_id, new)

    def with_shipping_cost(self, warehouse_id, store_id, cents):
        _integer(cents, "shipping cost in cents")
        if warehouse_id not in self.warehouses or store_id not in self.stores:
            raise ValidationError("Unknown warehouse or store ID")
        return self._with_cell("shipping_costs_cents", warehouse_id, store_id, cents)

    def _with_cell(self, table, row, column, value):
        if getattr(self, table)[row][column] == value:
            return self
        data = self.to_dict()
        data[table][row][column] = value
        data["revision"] += 1
        return State.from_dict(data)
