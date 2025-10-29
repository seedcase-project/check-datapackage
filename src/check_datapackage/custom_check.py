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
    """A custom check to be done on Data Package metadata.

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

    def apply(self, properties: dict[str, Any]) -> list[Issue]:
        """Checks the properties against this check and creates issues on failure.

        Args:
            properties: The properties to check.

        Returns:
            A list of `Issue`s.
        """
        matching_fields = _get_fields_at_jsonpath(self.jsonpath, properties)
        failed_fields = _filter(
            matching_fields, lambda field: not self.check(field.value)
        )
        return _map(
            failed_fields,
            lambda field: Issue(
                jsonpath=field.jsonpath, type=self.type, message=self.message
            ),
        )


@dataclass(frozen=True)
class RequiredCheck:
    """A check that checks if a field is present (i.e. not None).

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

    jsonpath: str
    message: str

    def apply(self, properties: dict[str, Any]) -> list[Issue]:
        """Checks the properties against this check and creates issues on failure.

        Args:
            properties: The properties to check.

        Returns:
            A list of `Issue`s.
        """
        # TODO: check jsonpath when checking other user input
        field_name_match = re.search(r"(?<!\.)(\.\w+)$", self.jsonpath)
        if not field_name_match:
            return []
        field_name = field_name_match.group(1)

        matching_paths = _get_direct_jsonpaths(self.jsonpath, properties)
        indirect_parent_path = self.jsonpath.removesuffix(field_name)
        direct_parent_paths = _get_direct_jsonpaths(indirect_parent_path, properties)
        missing_paths = _filter(
            direct_parent_paths,
            lambda path: f"{path}{field_name}" not in matching_paths,
        )
        return _map(
            missing_paths,
            lambda path: Issue(
                jsonpath=path + field_name,
                type="required",
                message=self.message,
            ),
        )


def apply_checks(
    checks: list[CustomCheck | RequiredCheck], properties: dict[str, Any]
) -> list[Issue]:
    """Checks the properties for all user-defined checks and creates issues if any fail.

    Args:
        checks: The user-defined checks to apply to the properties.
        properties: The properties to check.

    Returns:
        A list of `Issue`s.
    """
    return _flat_map(
        checks,
        lambda check: check.apply(properties),
    )
