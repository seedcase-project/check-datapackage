from dataclasses import dataclass
from itertools import chain, repeat
from re import sub
from typing import Any, Callable, Optional

from jsonpath import JSONPathMatch, finditer

from check_datapackage.issue import Issue


@dataclass
class Exclude:
    r"""Exclude issues when checking a Data Package descriptor.

    When both `target` and `type` are provided, an issue has to match both to be
    excluded.

    Attributes:
        target (Optional[str]): [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            to the field or fields in the input object where issues should be ignored.
            Must be an explicit path, e.g., `$.resources[0].name`.  Needs to
            point to the location in the descriptor of the issue to ignore. If
            not provided, issues of the given `type` will be excluded for all
            fields.
        type (Optional[str]): The type of the issue to ignore (e.g., "required",
            "pattern", or "format").  If not provided, all types of issues will be
            ignored for the given `target`.

    Examples:
        ```{python}
        import check_datapackage as cdp

        exclude_required = cdp.Exclude(type="required")
        exclude_name = cdp.Exclude(target="$.name")
        exclude_desc_required = cdp.Exclude(
            type="required", target="$.resources[*].description"
        )
        ```
    """

    target: Optional[str] = None
    type: Optional[str] = None


def exclude_types(issues: list[Issue], excludes: list[Exclude]) -> list[Issue]:
    """Keep only issues that don't match an exclusion rule.

    Args:
        issues: The issues to filter.
        excludes: The exclusion rules to apply to the issues.

    Returns:
        The issues that are kept after applying the exclusion rules.
    """
    return _drop_types(issues, excludes)


def exclude_target(
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
        excludes, [descriptor], _get_any_matches_on_target
    )
    return _filter(issues, lambda issue: issue.location not in jsonpaths_to_exclude)


def _drop_types(issues: list[Issue], excludes: list[Exclude]) -> list[Issue]:
    return _drop_any_matches(issues, excludes, _same_type)


# Generic functions to build up the exclusion by either type or target


def _drop_any_matches(
    issues: list[Issue], excludes: list[Exclude], fn: Callable[[Issue, Exclude], bool]
) -> list[Issue]:
    return _filter(issues, lambda issue: not _any_matches_on_issue(issue, excludes, fn))


def _any_matches_on_issue(
    issue: Issue, excludes: list[Exclude], fn: Callable[[Issue, Exclude], bool]
) -> bool:
    has_match: list[bool] = _map(excludes, lambda exclude: fn(issue, exclude))
    return any(has_match)


def _same_type(issue: Issue, exclude: Exclude) -> bool:
    return exclude.type == issue.type


def _filter(x: Any, fn: Callable[[Any], bool]) -> list[Any]:
    return list(filter(fn, x))


def _map(x: Any, fn: Callable[[Any], Any]) -> list[Any]:
    return list(map(fn, x))


def _map2(x: list[Any], y: list[Any], fn: Callable[[Any, Any], Any]) -> list[Any]:
    if len(y) == 1:
        y = list(repeat(y[0], len(x)))
    return list(map(fn, x, y))


def _flat_map2(x: list[Any], y: list[Any], fn: Callable[[Any, Any], Any]) -> list[Any]:
    """Uses map and flattens the result by one level."""
    return list(chain.from_iterable(_map2(x, y, fn)))


def _get_any_matches_on_target(
    exclude: Exclude, descriptor: dict[Any, str]
) -> list[str]:
    if exclude.target is None:
        return []
    matches = finditer(exclude.target, descriptor)
    paths = _map(matches, _get_jsonpath)
    return paths


def _get_jsonpath(match: JSONPathMatch) -> str:
    cleaned: str = sub(r"\['", ".", match.path)
    return sub(r"'\]", "", cleaned)
