from dataclasses import dataclass
from typing import Any, Optional

from check_datapackage.internals import (
    DescriptorField,
    _filter,
    _get_fields_at_jsonpath,
    _map,
)
from check_datapackage.issue import Issue


@dataclass
class Exclude:
    r"""Exclude issues when checking a Data Package descriptor.

    When you use both `jsonpath` and `type`, any issue that matches either of them
    will be excluded. Mean it isn't an `AND` logic, it's an `OR` logic.

    Attributes:
        jsonpath (Optional[str]): [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            to the field or fields in the input object where issues should be ignored.
            Uses JSON path syntax for queries, e.g., `$.resources[0].name`, to ignore
            issues related to that path.
        type (Optional[str]): The type of the issue to ignore (e.g., "required",
            "pattern", or "format").

    Examples:
        ```{python}
        import check_datapackage as cdp

        exclude_required = cdp.Exclude(type="required")
        exclude_name = cdp.Exclude(jsonpath="$.name")
        exclude_desc_required = cdp.Exclude(
            type="required", jsonpath="$.resources[*].description"
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
        matches.append(False)

    if exclude.jsonpath is not None:
        matches.append(_same_jsonpath(issue, exclude, descriptor))

    if exclude.type is not None:
        matches.append(_same_type(issue, exclude))

    return all(matches)


def _same_jsonpath(issue: Issue, exclude: Exclude, descriptor: dict[Any, str]) -> bool:
    if exclude.jsonpath is None:
        return False
    fields: list[DescriptorField] = _get_fields_at_jsonpath(
        exclude.jsonpath, descriptor
    )
    jsonpaths: list[str] = _map(fields, lambda field: field.jsonpath)
    return issue.jsonpath in jsonpaths


def _same_type(issue: Issue, exclude: Exclude) -> bool:
    if exclude.type is None:
        return False
    return exclude.type in issue.type
