import re
from dataclasses import dataclass, field
from typing import Any, Callable

from check_datapackage.internals import (
    DescriptorField,
    _filter,
    _flat_map,
    _get_direct_jsonpaths,
    _get_fields_at_jsonpath,
    _map,
)
from check_datapackage.issue import Issue


@dataclass(frozen=True)
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
        type (str): An identifier for the custom check. It will be shown in error
            messages and can be used to exclude the check. Each custom check
            should have a unique `type`.
        check_missing (bool): Whether fields that would match the JSON path but are
            missing from the object should be passed to `check` as `None`.
            Defaults to False.

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
    check_missing: bool = False
    _field_name: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Checks that `CustomCheck`s with `check_missing` have sensible `jsonpath`s."""
        if self.check_missing:
            field_name_match = re.search(r"(?<!\.)(\.\w+)$", self.jsonpath)
            if not field_name_match:
                raise ValueError(
                    f"Cannot define `CustomCheck` for JSON path `{self.jsonpath}`."
                    " A check with `check_missing` set to true must target a concrete "
                    "object field (e.g., `$.title`) or set of fields (e.g., "
                    "`$.resources[*].title`). Ambiguous paths (e.g., `$..title`) or "
                    "paths pointing to array items (e.g., `$.resources[0]`) are not"
                    " allowed."
                )
            super().__setattr__("_field_name", field_name_match.group(1))


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
    if custom_check.check_missing:
        matching_fields += _get_missing_fields(
            custom_check, descriptor, matching_fields
        )

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


def _get_missing_fields(
    check: CustomCheck,
    descriptor: dict[str, Any],
    matching_fields: list[DescriptorField],
) -> list[DescriptorField]:
    """Returns the missing fields that the check would apply to if they were present."""
    parent_jsonpath = check.jsonpath.removesuffix(check._field_name)
    potentially_matching_paths = _map(
        _get_direct_jsonpaths(parent_jsonpath, descriptor),
        lambda path: f"{path}{check._field_name}",
    )
    actually_matching_paths = _map(matching_fields, lambda field: field.jsonpath)
    missing_paths = _filter(
        potentially_matching_paths,
        lambda path: path not in actually_matching_paths,
    )
    return _map(missing_paths, lambda path: DescriptorField(jsonpath=path, value=None))
