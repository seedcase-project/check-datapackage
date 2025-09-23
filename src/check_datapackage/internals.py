import re
from json import loads
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft7Validator, FormatChecker, ValidationError

from check_datapackage.constants import (
    NAME_PATTERN,
    PACKAGE_RECOMMENDED_FIELDS,
    SEMVER_PATTERN,
)
from check_datapackage.issue import Issue


def _read_json(path: Path) -> dict[str, Any]:
    """Reads the contents of a JSON file into an object.

    Args:
        path: The path to the file to load.

    Returns:
        The contents of the file as an object.

    Raises:
        JSONDecodeError: If the contents of the file cannot be de-serialised as JSON.
        TypeError: If the object in the file is not a dictionary.
    """
    loaded_object = loads(path.read_text())
    if not isinstance(loaded_object, dict):
        raise TypeError(
            f"Expected {path} to contain a JSON dictionary object "
            f"but found {type(loaded_object)}."
        )
    return loaded_object


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
        {
            issue
            for error in validation_errors
            for issue in _validation_error_to_issues(error)
        }
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

    return [_create_issue(sub_error) for sub_error in sub_errors]


def _handle_S_resources_x(sub_errors: list[ValidationError]) -> list[Issue]:
    """Do not flag missing `path` and `data` separately."""
    issues: list[Issue] = []
    path_or_data_required_error: ValidationError | None = None

    for error in sub_errors:
        path = _get_full_json_path_from_error(error)

        if str(error.validator) == "required" and path.endswith(("path", "data")):
            path_or_data_required_error = error
        else:
            issues.append(_create_issue(error))

    if path_or_data_required_error:
        issues.append(
            Issue(
                message=(
                    "This resource has no `path` or `data` field. "
                    "One of them must be provided."
                ),
                location=path_or_data_required_error.json_path,
                type="required",
            )
        )

    return issues


def _handle_S_resources_x_path(sub_errors: list[ValidationError]) -> list[Issue]:
    """Only flag errors for the relevant type.

    If `path` is a string, flag errors for the string-based schema.
    If `path` is an array, flag errors for the array-based schema.
    """
    non_type_errors = [
        error
        for error in sub_errors
        if not (str(error.validator) == "type" and error.absolute_path[-1] == "path")
    ]
    if non_type_errors:
        return [_create_issue(err) for err in non_type_errors]

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
