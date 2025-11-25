from collections.abc import Callable
from dataclasses import dataclass
from operator import itemgetter
from typing import Any, Self, cast

from jsonpath import JSONPath, compile
from jsonpath.segments import JSONPathRecursiveDescentSegment
from jsonpath.selectors import NameSelector
from pydantic import BaseModel, PrivateAttr, field_validator, model_validator

from check_datapackage.internals import (
    JsonPath,
    PropertyField,
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
        fields: list[PropertyField] = _get_fields_at_jsonpath(
            self.jsonpath,
            properties,
        )
        matches: list[PropertyField] = _filter(
            fields,
            lambda field: not self.check(field.value),
        )
        return _map(
            matches,
            lambda field: Issue(
                jsonpath=field.jsonpath, type=self.type, message=self.message
            ),
        )


@dataclass(frozen=True)
class TargetJsonPath:
    """A JSON path targeted by a `RequiredCheck`.

    Attributes:
        parent (str): The JSON path to the parent of the targeted field.
        field (str): The name of the targeted field.
    """

    parent: str
    field: str


def _jsonpath_to_targets(jsonpath: JSONPath) -> list[TargetJsonPath]:
    """Create a list of `TargetJsonPath`s from a `JSONPath`."""
    # Segments are path parts, e.g., `resources`, `*`, `name` for `$.resources[*].name`
    if not jsonpath.segments:
        return []

    full_path = jsonpath.segments[0].token.path
    last_segment = jsonpath.segments[-1]
    if isinstance(last_segment, JSONPathRecursiveDescentSegment):
        raise ValueError(
            f"Cannot use the JSON path `{full_path}` in `RequiredCheck`"
            " because it ends in the recursive descent (`..`) operator."
        )

    # Things like field names, array indices, and/or wildcards.
    selectors = last_segment.selectors
    if _filter(selectors, lambda selector: not isinstance(selector, NameSelector)):
        raise ValueError(
            f"Cannot use `RequiredCheck` for the JSON path `{full_path}`"
            " because it doesn't end in a name selector."
        )

    parent = "".join(_map(jsonpath.segments[:-1], str))
    name_selectors = cast(tuple[NameSelector], selectors)
    return _map(
        name_selectors,
        lambda selector: TargetJsonPath(
            parent=str(compile(parent)), field=selector.name
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
    _targets: list[TargetJsonPath] = PrivateAttr()

    @model_validator(mode="after")
    def _check_field_name_in_jsonpath(self) -> Self:
        jsonpath = compile(self.jsonpath)
        if isinstance(jsonpath, JSONPath):
            paths = [jsonpath]
        else:
            first_path = cast(JSONPath, jsonpath.path)
            paths = [first_path] + _map(jsonpath.paths, itemgetter(1))

        object.__setattr__(self, "_targets", _flat_map(paths, _jsonpath_to_targets))
        return self

    def apply(self, properties: dict[str, Any]) -> list[Issue]:
        """Applies the required check to the properties.

        Args:
            properties: The properties to check.

        Returns:
            A list of `Issue`s.
        """
        matching_paths = _get_direct_jsonpaths(self.jsonpath, properties)
        return _flat_map(
            self._targets,
            lambda target: self._target_to_issues(target, matching_paths, properties),
        )

    def _target_to_issues(
        self,
        target: TargetJsonPath,
        matching_paths: list[str],
        properties: dict[str, Any],
    ) -> list[Issue]:
        """Create a list of `Issue`s from a `TargetJsonPath`."""
        direct_parent_paths = _get_direct_jsonpaths(target.parent, properties)
        missing_paths = _filter(
            direct_parent_paths,
            lambda path: f"{path}.{target.field}" not in matching_paths,
        )
        return _map(
            missing_paths,
            lambda path: Issue(
                jsonpath=f"{path}.{target.field}",
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
