from dataclasses import dataclass
from typing import Annotated, Any

from jsonpath import (
    CompoundJSONPath,
    JSONPathMatch,
    JSONPathSyntaxError,
    compile,
    finditer,
)
from pydantic import AfterValidator
from seedcase_soil import fmap, keep


@dataclass
class PropertyField:
    """The field of a Data Package property.

    Attributes:
        jsonpath (str): The direct JSON path to the field.
        value (str): The value contained in the field.
    """

    jsonpath: str
    value: Any


def _get_fields_at_jsonpath(
    jsonpath: str, json_object: dict[str, Any]
) -> list[PropertyField]:
    """Returns all fields that match the JSON path."""
    matches = finditer(jsonpath, json_object)
    return fmap(matches, _create_property_field)


def _get_direct_jsonpaths(jsonpath: str, json_object: dict[str, Any]) -> list[str]:
    """Returns all direct JSON paths that match a direct or indirect JSON path."""
    fields = _get_fields_at_jsonpath(jsonpath, json_object)
    return fmap(fields, lambda field: field.jsonpath)


def _create_property_field(match: JSONPathMatch) -> PropertyField:
    return PropertyField(
        jsonpath=match.path.replace("['", ".").replace("']", ""),
        value=match.obj,
    )


def _is_jsonpath(value: str) -> str:
    try:
        jsonpath = compile(value)
    except JSONPathSyntaxError:
        raise ValueError(
            f"'{value}' is not a correct JSON path. See "
            "https://jg-rp.github.io/python-jsonpath/syntax/ for the expected syntax."
        )

    # Doesn't allow intersection paths (e.g. `$.resources & $.name`).
    intersection_token = jsonpath.env.intersection_token
    if isinstance(jsonpath, CompoundJSONPath) and keep(
        jsonpath.paths, lambda path: path[0] == intersection_token
    ):
        raise ValueError(
            f"The intersection operator (`{intersection_token}`) in the JSON path "
            f"'{value}' is not supported."
        )
    return value


type JsonPath = Annotated[str, AfterValidator(_is_jsonpath)]
