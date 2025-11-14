import re
from typing import Any, Optional

from pydantic import BaseModel

from check_datapackage.internals import (
    JsonPath,
    _filter,
    _get_direct_jsonpaths,
    _map,
)
from check_datapackage.issue import Issue


class Exclusion(BaseModel, frozen=True):
    r"""A check to be excluded when checking properties.

    When you use both `jsonpath` and `type` in the same `Exclusion` object, only issues
    that match *both* will be excluded, meaning it is an `AND` logic. If you want `OR`
    logic, use multiple `Exclusion` objects in the `Config`.

    Attributes:
        jsonpath (Optional[str]): [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            to the field or fields in the input object where issues should be ignored.
            Uses JSON path syntax for queries, e.g., `$.resources[0].name`, to ignore
            issues related to that path.
        type (Optional[str]): The type of check to exclude (e.g., a JSON schema type
            such as "required", "type", "pattern", or "format", or a custom type).

    Examples:
        ```{python}
        import check_datapackage as cdp

        exclusion_required = cdp.Exclusion(type="required")
        exclusion_name = cdp.Exclusion(jsonpath="$.name")
        exclusion_desc_required = cdp.Exclusion(
            type="required",
            jsonpath="$.resources[*].description"
        )
        config = cdp.Config(
            exclusions=[
                exclusion_required,
                exclusion_name,
                exclusion_desc_required
            ]
        )
        ```
    """

    jsonpath: Optional[JsonPath] = None
    type: Optional[str] = None


def exclude(
    issues: list[Issue], exclusions: list[Exclusion], descriptor: dict[str, Any]
) -> list[Issue]:
    """Exclude issues defined by Exclusion objects."""
    return _filter(
        issues,
        lambda issue: not _get_any_matches(issue, exclusions, descriptor),
    )


def _get_any_matches(
    issue: Issue, exclusions: list[Exclusion], descriptor: dict[str, Any]
) -> bool:
    matches: list[bool] = _map(
        exclusions, lambda exclusion: _get_matches(issue, exclusion, descriptor)
    )
    return any(matches)


def _get_matches(
    issue: Issue, exclusion: Exclusion, descriptor: dict[str, Any]
) -> bool:
    matches: list[bool] = []

    both_none = exclusion.jsonpath is None and exclusion.type is None
    if both_none:
        return False

    if exclusion.jsonpath:
        matches.append(_jsonpaths_match(issue, exclusion.jsonpath))

    if exclusion.type:
        matches.append(_same_type(issue, exclusion.type))

    return all(matches)


def _jsonpaths_match(issue: Issue, jsonpath: str) -> bool:
    json_object: dict[str, Any] = _get_json_object_from_jsonpath(issue.jsonpath)
    jsonpaths = _get_direct_jsonpaths(jsonpath, json_object)
    return issue.jsonpath in jsonpaths


def _same_type(issue: Issue, type: str) -> bool:
    return type == issue.type


def _get_json_object_from_jsonpath(jsonpath: str) -> dict[str, Any]:
    """Builds an object with a property at the given JSON Path location."""
    path_parts = jsonpath.removeprefix("$.").split(".")
    return _get_object_from_path_parts(path_parts)


def _get_object_from_path_parts(path_parts: list[str]) -> dict[str, Any]:
    current_part = path_parts[0]
    next_value = {}
    if len(path_parts) > 1:
        next_value = _get_object_from_path_parts(path_parts[1:])

    array_parts = _get_array_parts(current_part)
    if array_parts:
        # If the current field is an array, insert the next value as the last item
        # in the array
        name, index = array_parts.groups()
        value: list[dict[str, Any]] = _map(range(int(index)), lambda _: {})
        return {name: value + [next_value]}

    # If the current field is a dict, insert the next value as a property
    return {current_part: next_value}


def _get_array_parts(path_part: str) -> Optional[re.Match[str]]:
    """Extract the name and index from a JSON path part representing an array."""
    return re.search(r"(\w+)\[(\d+)\]$", path_part)
