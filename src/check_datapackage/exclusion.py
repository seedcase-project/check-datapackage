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
        config = cdp.Config(
            exclusions=[
                exclusion_required,
                exclusion_name,
                exclusion_desc_required
            ]
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
        matches.append(_same_jsonpath(issue, exclusion.jsonpath, descriptor))

    if exclusion.type:
        matches.append(_same_type(issue, exclusion.type))

    return all(matches)


def _same_jsonpath(issue: Issue, jsonpath: str, descriptor: dict[Any, str]) -> bool:
    fields: list[DescriptorField] = _get_fields_at_jsonpath(jsonpath, descriptor)
    jsonpaths: list[str] = _map(fields, lambda field: field.jsonpath)
    return issue.jsonpath in jsonpaths


def _same_type(issue: Issue, type: str) -> bool:
    return type == issue.type
