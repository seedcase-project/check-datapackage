from dataclasses import dataclass
from typing import Any, Callable

from check_datapackage.internals import (
    _filter,
    _flat_map,
    _get_fields_at_jsonpath,
    _map,
)
from check_datapackage.issue import Issue


@dataclass
class CustomCheck:
    """A custom check to be done on a Data Package descriptor.

    Attributes:
        jsonpath (str): The location of the field or fields the custom check applies to,
            expressed in [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            notation (e.g., `$.resources[*].name`).
        message (str): The message shown when the check is violated.
        check (Callable[[Any], bool]): A function that expresses the custom check.
            It takes the value at the `jsonpath` location as input and
            returns true if the check is met, false if it isn't.
        type (str): The type of the custom check (e.g., a JSON schema type such as
            "required", "type", "pattern", or "format", or a custom type). It will be
            shown in error messages and can be used in an `Exclusion` object to exclude
            the check. Each custom check should have a unique `type`.

    Examples:
        ```{python}
        import check_datapackage as cdp

        license_check = cdp.CustomCheck(
            type="only-mit",
            jsonpath="$.licenses[*].name",
            message="Data Packages may only be licensed under MIT.",
            check=lambda license_name: license_name == "mit",
        )
        ```
    """

    jsonpath: str
    message: str
    check: Callable[[Any], bool]
    type: str = "custom"


def apply_custom_checks(
    custom_checks: list[CustomCheck], descriptor: dict[str, Any]
) -> list[Issue]:
    """Checks the descriptor for all custom checks and creates issues if any fail.

    Args:
        custom_checks: The custom checks to apply to the descriptor.
        descriptor: The descriptor to check.

    Returns:
        A list of `Issue`s.
    """
    return _flat_map(
        custom_checks,
        lambda custom_check: _apply_custom_check(custom_check, descriptor),
    )


def _apply_custom_check(
    custom_check: CustomCheck, descriptor: dict[str, Any]
) -> list[Issue]:
    """Applies the custom check to the descriptor.

    If any fields fail the custom check, this function creates a list of issues
    for those fields.

    Args:
        custom_check: The custom check to apply to the descriptor.
        descriptor: The descriptor to check.

    Returns:
        A list of `Issue`s.
    """
    matching_fields = _get_fields_at_jsonpath(custom_check.jsonpath, descriptor)
    failed_fields = _filter(
        matching_fields, lambda field: not custom_check.check(field.value)
    )
    return _map(
        failed_fields,
        lambda field: Issue(
            jsonpath=field.jsonpath,
            type=custom_check.type,
            message=custom_check.message,
        ),
    )
