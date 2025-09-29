import re
from itertools import chain
from typing import Any, Callable, Iterable, Iterator, TypeVar

from jsonschema import Draft7Validator, FormatChecker, ValidationError

from check_datapackage.constants import (
    NAME_PATTERN,
    PACKAGE_RECOMMENDED_FIELDS,
    SEMVER_PATTERN,
)
from check_datapackage.issue import Issue


def _add_package_recommendations(schema: dict[str, Any]) -> dict[str, Any]:
    """Add recommendations from the Data Package standard to the schema.

    Modifies the schema in place.

    Args:
        schema: The full Data Package schema.

    Returns:
        The updated Data Package schema.
    """
    schema["required"].extend(PACKAGE_RECOMMENDED_FIELDS.keys())
    schema["properties"]["name"]["pattern"] = NAME_PATTERN
    schema["properties"]["version"]["pattern"] = SEMVER_PATTERN
    schema["properties"]["contributors"]["items"]["required"] = ["title"]
    schema["properties"]["sources"]["items"]["required"] = ["title"]
    return schema


def _add_resource_recommendations(schema: dict[str, Any]) -> dict[str, Any]:
    """Add recommendations from the Data Resource standard to the schema.

    Modifies the schema in place.

    Args:
        schema: The full Data Package schema.

    Returns:
        The updated Data Package schema.
    """
    schema["properties"]["resources"]["items"]["properties"]["name"]["pattern"] = (
        NAME_PATTERN
    )
    return schema


def _check_object_against_json_schema(
    json_object: dict[str, Any], schema: dict[str, Any]
) -> list[Issue]:
    """Checks that `json_object` matches the given JSON schema.

    Structural, type and format constraints are all checked. All schema violations are
    collected before issues are returned.

    Args:
        json_object: The JSON object to check.
        schema: The JSON schema to check against.

    Returns:
        A list of issues. An empty list, if no issues are found.

    Raises:
        jsonschema.exceptions.SchemaError: If the given schema is invalid.
    """
    Draft7Validator.check_schema(schema)
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    return _validation_errors_to_issues(validator.iter_errors(json_object))


def _validation_errors_to_issues(
    validation_errors: Iterator[ValidationError],
) -> list[Issue]:
    """Transforms `jsonschema.ValidationError`s to more compact `Issue`s.

    Args:
        validation_errors: The `jsonschema.ValidationError`s to transform.

    Returns:
        A list of `Issue`s.
    """
    return sorted(
        set(chain.from_iterable(map(_validation_error_to_issues, validation_errors)))
    )


def _validation_error_to_issues(error: ValidationError) -> list[Issue]:
    """Maps a `ValidationError` to one or more `Issue`s."""
    if not error.context:
        return [_create_issue(error)]
    sub_errors = error.context

    # Handle issues at $.resources[x]
    if _schema_path_ends_in(error, ["resources", "items", "oneOf"]):
        return _handle_S_resources_x(sub_errors)

    # Handle issues at $.resources[x].path
    if _schema_path_ends_in(
        error,
        [
            "resources",
            "items",
            "properties",
            "path",
            "oneOf",
        ],
    ):
        return _handle_S_resources_x_path(sub_errors)

    return _map(sub_errors, _create_issue)


def _handle_S_resources_x(sub_errors: list[ValidationError]) -> list[Issue]:
    """Do not flag missing `path` and `data` separately."""
    path_or_data_required_errors, other_errors = _partition(
        sub_errors,
        lambda error: str(error.validator) == "required"
        and _get_full_json_path_from_error(error).endswith(("path", "data")),
    )

    issues = _map(other_errors, _create_issue)

    if path_or_data_required_errors:
        issues.append(
            Issue(
                message=(
                    "This resource has no `path` or `data` field. "
                    "One of them must be provided."
                ),
                location=path_or_data_required_errors[0].json_path,
                type="required",
            )
        )

    return issues


def _handle_S_resources_x_path(sub_errors: list[ValidationError]) -> list[Issue]:
    """Only flag errors for the relevant type.

    If `path` is a string, flag errors for the string-based schema.
    If `path` is an array, flag errors for the array-based schema.
    """
    non_type_errors = _filter(
        sub_errors,
        lambda error: str(error.validator) != "type"
        or error.absolute_path[-1] != "path",
    )
    if non_type_errors:
        return _map(non_type_errors, _create_issue)

    return [
        Issue(
            message="The `path` property must be either a string or an array.",
            location=sub_errors[0].json_path,
            type="type",
        )
    ]


def _schema_path_ends_in(error: ValidationError, target: list[str]) -> bool:
    """Check if the schema path of a validation error ends in the given sequence."""
    return list(error.schema_path)[-len(target) :] == target


def _create_issue(error: ValidationError) -> Issue:
    """Create an `Issue` from a `ValidationError`."""
    return Issue(
        message=error.message,
        location=_get_full_json_path_from_error(error),
        type=str(error.validator),
    )


def _get_full_json_path_from_error(error: ValidationError) -> str:
    """Returns the full `json_path` to the error.

    For 'required' errors, the field name is extracted from the error message.

    Args:
        error: The error to get the full `json_path` for.

    Returns:
        The full `json_path` of the error.
    """
    if str(error.validator) == "required":
        match = re.search("'(.*)' is a required property", error.message)
        if match:
            return f"{error.json_path}.{match.group(1)}"
    return error.json_path


In = TypeVar("In")
Out = TypeVar("Out")


def _filter(x: Iterable[In], fn: Callable[[In], bool]) -> list[In]:
    return list(filter(fn, x))


def _map(x: Iterable[In], fn: Callable[[In], Out]) -> list[Out]:
    return list(map(fn, x))


def _partition(
    items: Iterable[In], condition: Callable[[In], bool]
) -> tuple[list[In], list[In]]:
    """Split items into two lists based on a condition."""
    return (
        _filter(items, condition),
        _filter(items, lambda item: not condition(item)),
    )
