import re
from itertools import chain, repeat
from typing import Any, Callable, Iterator

from jsonschema import Draft7Validator, FormatChecker, ValidationError

from check_datapackage.constants import (
    COMPLEX_VALIDATORS,
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

    The list of errors is:

      - flattened
      - filtered for summary-type errors
      - filtered for duplicates
      - sorted by error location

    Args:
        validation_errors: The `jsonschema.ValidationError`s to transform.

    Returns:
        A list of `Issue`s.
    """
    issues = [
        Issue(
            message=error.message,
            jsonpath=_get_full_json_path_from_error(error),
            type=str(error.validator),
        )
        for error in _unwrap_errors(list(validation_errors))
        if str(error.validator) not in COMPLEX_VALIDATORS
    ]
    return sorted(set(issues))


def _unwrap_errors(errors: list[ValidationError]) -> list[ValidationError]:
    """Recursively extracts all errors into a flat list of errors.

    Args:
        errors: A nested list of errors.

    Returns:
        A flat list of errors.
    """
    unwrapped = []
    for error in errors:
        unwrapped.append(error)
        if error.context:
            unwrapped.extend(_unwrap_errors(error.context))
    return unwrapped


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


def _map2(x: list[Any], y: list[Any], fn: Callable[[Any, Any], Any]) -> list[Any]:
    if len(y) == 1:
        y = list(repeat(y[0], len(x)))
    return list(map(fn, x, y))


def _flat_map2(x: list[Any], y: list[Any], fn: Callable[[Any, Any], Any]) -> list[Any]:
    """Uses map and flattens the result by one level."""
    return list(chain.from_iterable(_map2(x, y, fn)))
