from dataclasses import dataclass
from itertools import chain
from typing import Any, Callable

from jsonpath import JSONPathMatch, finditer

from check_datapackage.issue import Issue


@dataclass
class Exclude:
    """Exclude issues when checking a Data Package descriptor.

    When both `target` and `type` are provided, an issue has to match both to be
    excluded.

    Attributes:
        target (str | None): [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            to the field or fields in the input object where issues should be ignored,
            e.g., `$.resources[*].name`. Needs to point to the location in the
            descriptor of the issue to ignore. If not provided, issues of the given
            `type` will be excluded for all fields.
        type (str | None): The type of the issue to ignore (e.g., "required",
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

    target: str | None = None
    type: str | None = None


def exclude(
    issues: list[Issue], excludes: list[Exclude], descriptor: dict[str, Any]
) -> list[Issue]:
    """Keep only issues that don't match an exclusion rule.

    Args:
        issues: The issues to filter.
        excludes: The exclusion rules to apply to the issues.
        descriptor: The descriptor to check.

    Returns:
        The issues that are kept after applying the exclusion rules.
    """
    excluded_location_groups = [
        _resolve_target_to_location(exclude.target, descriptor)
        for exclude in excludes
        if exclude.target
    ]
    excluded_locations = list(chain.from_iterable(excluded_location_groups))
    kept_issues = _filter(
        issues, lambda issue: issue.location not in excluded_locations
    )

    # kept_issues = _filter(
    #     issues,
    #     lambda issue: _drop_any_target(issue, excludes)
    # )
    # kept_issues: list[Issue] = _drop_any_matching_types(issues, excludes)
    return kept_issues


def _drop_any_matching_types(
    issues: list[Issue], excludes: list[Exclude]
) -> list[Issue]:
    return _filter(issues, lambda issue: not _any_matching_types(issue, excludes))


def _any_matching_types(issue: Issue, excludes: list[Exclude]) -> bool:
    has_matching_types: list[bool] = _map(
        excludes, lambda exclude: _same_type(issue, exclude)
    )
    return any(has_matching_types)


def _same_type(issue: Issue, exclude: Exclude) -> bool:
    return exclude.type == issue.type


def _filter(x: Any, fn: Callable[[Any], bool]) -> list[Any]:
    return list(filter(fn, x))


def _map(x: Any, fn: Callable[[Any], Any]) -> list[Any]:
    return list(map(fn, x))


def _resolve_target(target: str, descriptor: dict[str, Any]) -> list[tuple[str, Any]]:
    """Returns all direct paths that match the target and their values.

    E.g., [("$.resources[0].name", "abc"), ("$.resources[1].name", "def")]
    """
    matches = finditer(target, descriptor)
    return [(_make_path(match), match.obj) for match in matches]


def _resolve_target_to_location(target: str, descriptor: dict[str, Any]) -> list[str]:
    """Returns all direct paths that match the target.

    E.g., ["$.resources[0].name", "$.resources[1].name"]
    """
    matches = _resolve_target(target, descriptor)
    return [match[0] for match in matches]


def _make_path(match: JSONPathMatch) -> str:
    """Assembles a JSON path string from its parts."""
    path = []
    for part in match.parts:
        if isinstance(part, int):
            path.append(f"[{part}]")
        else:
            path.append(f".{part}")
    return "$" + "".join(path)
