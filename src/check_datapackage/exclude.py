from dataclasses import dataclass
from re import sub
from typing import Any, Callable, Optional

from jsonpath import JSONPathMatch, finditer

from check_datapackage.internals import _flat_map2
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


def exclude_types(issues: list[Issue], excludes: list[Exclude]) -> list[Issue]:
    """Keep only issues that don't match an exclusion rule.

    Args:
        issues: The issues to filter.
        excludes: The exclusion rules to apply to the issues.

    Returns:
        The issues that are kept after applying the exclusion rules.
    """
    return _drop_any_matching_types(issues, excludes)


def exclude_jsonpath(
    issues: list[Issue], descriptor: dict[str, Any], excludes: list[Exclude]
) -> list[Issue]:
    """Keep only issues that don't match an exclusion rule.

    Args:
        issues: The issues to filter.
        descriptor: The Data Package descriptor as a dictionary.
        excludes: The exclusion rules to apply to the issues.

    Returns:
        The issues that are kept after applying the exclusion rules.
    """
    jsonpaths_to_exclude = _flat_map2(
        excludes, [descriptor], _get_any_matches_on_jsonpath
    )
    return _filter(issues, lambda issue: issue.jsonpath not in jsonpaths_to_exclude)


# Generic functions to build up the exclusion by either type or jsonpath


def _drop_any_matching_types(
    issues: list[Issue], excludes: list[Exclude]
) -> list[Issue]:
    return _filter(issues, lambda issue: not _get_any_matches_on_type(issue, excludes))


def _get_any_matches_on_type(issue: Issue, excludes: list[Exclude]) -> bool:
    has_match: list[bool] = _map(excludes, lambda exclude: _same_type(issue, exclude))
    return any(has_match)


def _same_type(issue: Issue, exclude: Exclude) -> bool:
    return exclude.type == issue.type


def _filter(x: Any, fn: Callable[[Any], bool]) -> list[Any]:
    return list(filter(fn, x))


def _map(x: Any, fn: Callable[[Any], Any]) -> list[Any]:
    return list(map(fn, x))


def _get_any_matches_on_jsonpath(
    exclude: Exclude, descriptor: dict[Any, str]
) -> list[str]:
    if exclude.jsonpath is None:
        return []
    matches = finditer(exclude.jsonpath, descriptor)
    paths = _map(matches, _get_match_jsonpath)
    return paths


def _get_match_jsonpath(match: JSONPathMatch) -> str:
    cleaned: str = sub(r"\['", ".", match.path)
    return sub(r"'\]", "", cleaned)
