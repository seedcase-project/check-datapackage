from dataclasses import dataclass

from check_datapackage.internals import _filter, _map
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


def exclude(issues: list[Issue], excludes: list[Exclude]) -> list[Issue]:
    """Keep only issues that don't match an exclusion rule.

    Args:
        issues: The issues to filter.
        excludes: The exclusion rules to apply to the issues.

    Returns:
        The issues that are kept after applying the exclusion rules.
    """
    # kept_issues = _filter(
    #     issues,
    #     lambda issue: _drop_any_target(issue, excludes)
    # )
    kept_issues: list[Issue] = _drop_any_matching_types(issues, excludes)
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
