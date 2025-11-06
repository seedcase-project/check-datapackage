import re
from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel, PrivateAttr, field_validator, model_validator

from check_datapackage.internals import (
    DescriptorField,
    JsonPath,
    _filter,
    _flat_map,
    _get_direct_jsonpaths,
    _get_fields_at_jsonpath,
    _map,
)
from check_datapackage.issue import Issue


class CustomCheck(BaseModel, frozen=True):
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
        config = cdp.Config(
            extensions=cdp.Extensions(
                custom_checks=[license_check]
            )
        )
        # check(descriptor, config=config)
        ```
    """

    jsonpath: JsonPath
    message: str
    check: Callable[[Any], bool]
    type: str = "custom"

    @field_validator("type", mode="after")
    @classmethod
    def _check_not_required(cls, value: str) -> str:
        if value == "required":
            raise ValueError(
                "Cannot use `CustomCheck` with `type='required'`."
                " Use `RequiredCheck` to set properties as required instead."
            )
        return value

    def apply(self, properties: dict[str, Any]) -> list[Issue]:
        """Applies the custom check to the properties.

        Args:
            properties: The properties to check.

        Returns:
            A list of `Issue`s.
        """
        fields: list[DescriptorField] = _get_fields_at_jsonpath(
            self.jsonpath,
            properties,
        )
        matches: list[DescriptorField] = _filter(
            fields,
            lambda field: not self.check(field.value),
        )
        return _map(
            matches,
            lambda field: Issue(
                jsonpath=field.jsonpath, type=self.type, message=self.message
            ),
        )


class RequiredCheck(BaseModel, frozen=True):
    """Set a specific property as required.

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

    jsonpath: JsonPath
    message: str
    _field_name: str = PrivateAttr()

    @model_validator(mode="after")
    def _check_field_name_in_jsonpath(self) -> Self:
        field_name_match = re.search(r"(?<!\.)(\.\w+)$", self.jsonpath)
        if not field_name_match:
            raise ValueError(
                f"Cannot use `RequiredCheck` for this JSON path `{self.jsonpath}`."
                " A `RequiredCheck` must target a concrete object field (e.g.,"
                " `$.title`) or set of properties/JSON paths (e.g.,"
                " `$.resources[*].title`). Ambiguous paths (e.g., `$..title`)"
                " or paths pointing to array items (e.g., `$.resources[0]`) are"
                " not allowed."
            )

        object.__setattr__(self, "_field_name", field_name_match.group(1))
        return self

    def apply(self, properties: dict[str, Any]) -> list[Issue]:
        """Applies the required check to the properties.

        Args:
            properties: The properties to check.

        Returns:
            A list of `Issue`s.
        """
        matching_paths = _get_direct_jsonpaths(self.jsonpath, properties)
        indirect_parent_path = self.jsonpath.removesuffix(self._field_name)
        direct_parent_paths = _get_direct_jsonpaths(indirect_parent_path, properties)
        missing_paths = _filter(
            direct_parent_paths,
            lambda path: f"{path}{self._field_name}" not in matching_paths,
        )
        return _map(
            missing_paths,
            lambda path: Issue(
                jsonpath=path + self._field_name,
                type="required",
                message=self.message,
            ),
        )


class Extensions(BaseModel, frozen=True):
    """Extensions to the standard checks.

    This sub-item of `Config` defines extensions, i.e., additional checks
    that supplement those specified by the Data Package standard. It
    contains sub-items that store additional checks. This `Extensions` class
    can be expanded to include more types of extensions.

    Each extension class must implement its own `apply()` method that takes
    the `datapackage.json` properties `dict` as input and outputs an `Issue`
    list that contains the issues found by that extension.

    Attributes:
        required_checks: A list of `RequiredCheck` objects defining properties
            to set as required.
        custom_checks: A list of `CustomCheck` objects defining extra, custom
            checks to run alongside the standard checks.

    Examples:
        ```{python}
        import check_datapackage as cdp

        extensions = cdp.Extensions(
            required_checks=[
                cdp.RequiredCheck(
                    jsonpath="$.description",
                    message="Data Packages must include a description.",
                ),
                cdp.RequiredCheck(
                    jsonpath="$.contributors[*].email",
                    message="All contributors must have an email address.",
                ),
            ],
            custom_checks=[
                cdp.CustomCheck(
                    type="only-mit",
                    jsonpath="$.licenses[*].name",
                    message="Data Packages may only be licensed under MIT.",
                    check=lambda license_name: license_name == "mit",
                )
            ],
        )
        # check(properties, config=cdp.Config(extensions=extensions))
        ```
    """

    required_checks: list[RequiredCheck] = []
    custom_checks: list[CustomCheck] = []


def apply_extensions(
    properties: dict[str, Any],
    extensions: Extensions,
) -> list[Issue]:
    """Applies the extension checks to the properties.

    Args:
        properties: The properties to check.
        extensions: The user-defined extensions to apply to the properties.

    Returns:
        A list of `Issue`s.
    """
    extensions_as_one: list[CustomCheck | RequiredCheck] = (
        extensions.required_checks + extensions.custom_checks
    )
    return _flat_map(
        extensions_as_one,
        lambda extension: extension.apply(properties),
    )
