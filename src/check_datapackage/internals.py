from dataclasses import dataclass
from itertools import chain
from typing import Annotated, Any, Callable, Iterable, TypeVar

from jsonpath import JSONPathMatch, JSONPathSyntaxError, compile, finditer
from pydantic import AfterValidator


@dataclass
class DescriptorField:
    """A field in the Data Package descriptor.

    Attributes:
        jsonpath (str): The direct JSON path to the field.
        value (str): The value contained in the field.
    """

    jsonpath: str
    value: Any


def _get_fields_at_jsonpath(
    jsonpath: str, json_object: dict[str, Any]
) -> list[DescriptorField]:
    """Returns all fields that match the JSON path."""
    matches = finditer(jsonpath, json_object)
    return _map(matches, _create_descriptor_field)


def _get_direct_jsonpaths(jsonpath: str, json_object: dict[str, Any]) -> list[str]:
    """Returns all direct JSON paths that match a direct or indirect JSON path."""
    fields = _get_fields_at_jsonpath(jsonpath, json_object)
    return _map(fields, lambda field: field.jsonpath)


def _create_descriptor_field(match: JSONPathMatch) -> DescriptorField:
    return DescriptorField(
        jsonpath=match.path.replace("['", ".").replace("']", ""),
        value=match.obj,
    )


In = TypeVar("In")
Out = TypeVar("Out")


def _map(x: Iterable[In], fn: Callable[[In], Out]) -> list[Out]:
    return list(map(fn, x))


def _filter(x: Iterable[In], fn: Callable[[In], bool]) -> list[In]:
    return list(filter(fn, x))


def _flat_map(items: Iterable[In], fn: Callable[[In], Iterable[Out]]) -> list[Out]:
    """Maps and flattens the items by one level."""
    return list(chain.from_iterable(map(fn, items)))


def _is_jsonpath(value: str) -> str:
    try:
        compile(value)
    except JSONPathSyntaxError:
        raise ValueError(
            f"'{value}' is not a correct JSON path. See "
            "https://jg-rp.github.io/python-jsonpath/syntax/ for the expected syntax."
        )
    return value


type JsonPath = Annotated[str, AfterValidator(_is_jsonpath)]
