from dataclasses import dataclass

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
    """Exclude issues by rule type.

    Args:
        issues: The issues to filter.
        excludes: The exclusions to the issues.

    Returns:
        The filtered issues.
    """
    # excluded_targets = filter(
    #     lambda issue: _exclude_any_target(issue, excludes), issues
    # )
    filtered_by_type = filter(lambda issue: _exclude_any_type(issue, excludes), issues)
    return list(excluded_types)


def _exclude_any_type(issue: Issue, excludes: list[Exclude]) -> bool:
    """List any issue that has no exclusions as True."""
    any_types = list(map(lambda exclude: _has_type(issue, exclude), excludes))
    return not any(any_types)


def _has_type(issue: Issue, exclude: Exclude) -> bool:
    """Logic for when an issue matches an exclude by type."""
    return exclude.type == issue.type
