import re
from dataclasses import dataclass
from typing import Any, Callable

from check_datapackage.internals import (
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

    def apply(self, descriptor: dict[str, Any]) -> list[Issue]:
        """Checks the descriptor against this check and creates issues on failure.

        Args:
            descriptor: The descriptor to check.

        Returns:
            A list of `Issue`s.
        """
        matching_fields = _get_fields_at_jsonpath(self.jsonpath, descriptor)
        failed_fields = _filter(
            matching_fields, lambda field: not self.check(field.value)
        )
        return _map(
            failed_fields,
            lambda field: Issue(
                jsonpath=field.jsonpath, type=self.type, message=self.message
            ),
        )


class RequiredCheck(CustomCheck):
    """A custom check that checks that a field is present (i.e. not None).

    Attributes:
        jsonpath (str): The location of the field or fields, expressed in [JSON
            path](https://jg-rp.github.io/python-jsonpath/syntax/) notation, to which
            the check applies (e.g., `$.resources[*].name`).
        message (str): The message that is shown when the check fails.

    Examples:
        ```{python}
        import check_datapackage as cdp
        required_title_check = cdp.RequiredCheck(
            jsonpath="$.title",
            message="A title is required.",
        )
        ```
    """

    _field_name: str

    def __init__(self, jsonpath: str, message: str):
        """Initializes the `RequiredCheck`."""
        field_name_match = re.search(r"(?<!\.)(\.\w+)$", jsonpath)
        if not field_name_match:
            raise ValueError(
                f"Cannot define `RequiredCheck` for JSON path `{jsonpath}`."
                " A `RequiredCheck` must target a concrete object field (e.g.,"
                " `$.title`) or set of fields (e.g., `$.resources[*].title`)."
                " Ambiguous paths (e.g., `$..title`) or paths pointing to array items"
                " (e.g., `$.resources[0]`) are not allowed."
            )

        self._field_name = field_name_match.group(1)
        super().__init__(
            jsonpath=jsonpath,
            message=message,
            check=lambda value: value is not None,
            type="required",
        )

    def apply(self, descriptor: dict[str, Any]) -> list[Issue]:
        """Checks the descriptor against this check and creates issues on failure.

        Args:
            descriptor: The descriptor to check.

        Returns:
            A list of `Issue`s.
        """
        matching_paths = _get_direct_jsonpaths(self.jsonpath, descriptor)
        indirect_parent_path = self.jsonpath.removesuffix(self._field_name)
        direct_parent_paths = _get_direct_jsonpaths(indirect_parent_path, descriptor)
        missing_paths = _filter(
            direct_parent_paths,
            lambda path: f"{path}{self._field_name}" not in matching_paths,
        )
        return _map(
            missing_paths,
            lambda path: Issue(
                jsonpath=path + self._field_name,
                type=self.type,
                message=self.message,
            ),
        )


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
        lambda check: check.apply(descriptor),
    )
