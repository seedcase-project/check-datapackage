import re
from dataclasses import dataclass
from typing import Any, Optional

from check_datapackage.internals import (
    _filter,
    _get_direct_jsonpaths,
    _map,
)
from check_datapackage.issue import Issue


@dataclass
class Exclusion:
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
        ```
    """

    jsonpath: Optional[str] = None
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
    test_object = _get_test_object_from_jsonpath(issue.jsonpath)
    jsonpaths = _get_direct_jsonpaths(jsonpath, test_object)
    return issue.jsonpath in jsonpaths


def _same_type(issue: Issue, type: str) -> bool:
    return type == issue.type


def _get_test_object_from_jsonpath(jsonpath: str) -> dict[str, Any]:
    """Builds an object with a property at the given JSON Path location."""
    path_parts = jsonpath.removeprefix("$.").split(".")
    return _get_object_from_path_parts(path_parts)


def _get_object_from_path_parts(remaining: list[str]) -> dict[str, Any]:
    current_path = remaining[0]
    # The innermost field is always an empty object
    if len(remaining) == 1:
        return {current_path: {}}
    
    next_field = _get_object_from_path_parts(remaining[1:])

    array_match = re.search(r"(\w+)\[(\d+)\]$", current_path)
    if array_match:
        # If the current field is an array, insert the next field as the last item
        # in the array
        array_name, index = array_match.groups()
        array_value: list[dict[str, Any]] = _map(range(int(index)), lambda _: {})
        return {array_name: array_value + [next_field]}

    # If the current field is a dict, insert the next field as a property
    return {current_path: next_field}
