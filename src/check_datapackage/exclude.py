import re
from dataclasses import dataclass
from functools import reduce
from typing import Any, Optional

from check_datapackage.internals import (
    _filter,
    _get_direct_jsonpaths,
    _map,
)
from check_datapackage.issue import Issue


@dataclass
class Exclude:
    r"""Exclude issues when checking a Data Package descriptor.

    When you use both `jsonpath` and `type` in the same `Exclude`, only issues that
    match *both* will be excluded, meaning it is an `AND` logic. If you want `OR` logic,
    use multiple `Exclude` objects in the `Config`.

    Attributes:
        jsonpath (Optional[str]): [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            to the field or fields in the input object where issues should be ignored.
            Uses JSON path syntax for queries, e.g., `$.resources[0].name`, to ignore
            issues related to that path.
        type (Optional[str]): The type of the issue to ignore (e.g., "required", "type",
            "pattern", or "format").

    Examples:
        ```{python}
        import check_datapackage as cdp

        exclude_required = cdp.Exclude(type="required")
        exclude_name = cdp.Exclude(jsonpath="$.name")
        exclude_desc_required = cdp.Exclude(
            type="required",
            jsonpath="$.resources[*].description"
        )
        ```
    """

    jsonpath: Optional[str] = None
    type: Optional[str] = None


def exclude(
    issues: list[Issue], excludes: list[Exclude], descriptor: dict[str, Any]
) -> list[Issue]:
    """Exclude issues based on the provided configuration settings."""
    return _filter(
        issues,
        lambda issue: not _get_any_matches(issue, excludes, descriptor),
    )


def _get_any_matches(
    issue: Issue, excludes: list[Exclude], descriptor: dict[str, Any]
) -> bool:
    matches: list[bool] = _map(
        excludes, lambda exclude: _get_matches(issue, exclude, descriptor)
    )
    return any(matches)


def _get_matches(issue: Issue, exclude: Exclude, descriptor: dict[str, Any]) -> bool:
    matches: list[bool] = []

    both_none = exclude.jsonpath is None and exclude.type is None
    if both_none:
        return False

    if exclude.jsonpath:
        test_object = _get_test_object_for_exclude(issue, exclude, descriptor)
        matches.append(_same_jsonpath(issue, exclude.jsonpath, test_object))

    if exclude.type:
        matches.append(_same_type(issue, exclude.type))

    return all(matches)


def _same_jsonpath(issue: Issue, jsonpath: str, descriptor: dict[Any, str]) -> bool:
    jsonpaths = _get_direct_jsonpaths(jsonpath, descriptor)
    return issue.jsonpath in jsonpaths


def _same_type(issue: Issue, type: str) -> bool:
    return type == issue.type


def _get_test_object_for_exclude(
    issue: Issue, exclude: Exclude, descriptor: dict[str, Any]
) -> dict[str, Any]:
    """Gets object for testing JSON path exclusion based on exclude type."""
    if exclude.type and exclude.type == "required":
        return _get_test_object_from_jsonpath(issue.jsonpath)
    return descriptor


def _get_test_object_from_jsonpath(jsonpath: str) -> dict[str, Any]:
    """Builds an object with a property at the given JSON Path location."""
    fields = jsonpath.removeprefix("$.").split(".")
    test_object: dict[str, Any] = {}
    reduce(_set_object_field, fields, test_object)
    return test_object


def _set_object_field(obj: dict[str, Any], field: str) -> dict[str, Any]:
    """Sets a field on the object to a placeholder value.

    Array fields are set to an array with the necessary number of items.
    E.g., `resources[1]` creates `'resources': [{}, {}]`.

    Other fields are set to an empty object.

    Returns:
        The object most recently set. For arrays, this is the item at the given index.
    """
    array_match = re.search(r"(\w+)\[(\d+)\]$", field)
    if array_match:
        array_name, index = array_match.groups()
        index = int(index)
        array_value: list[dict[str, Any]] = _map(range(index + 1), lambda _: {})
        obj[array_name] = array_value
        return array_value[index]

    dict_value: dict[str, Any] = {}
    obj[field] = dict_value
    return dict_value
