import re
from dataclasses import dataclass
from itertools import chain
from typing import Any, Callable, Iterable, Iterator, TypeVar

from jsonpath import JSONPathMatch, finditer
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
    return [
        Issue(
            message=error.message,
            jsonpath=_get_full_json_path_from_error(error),
            type=str(error.validator),
        )
        for error in _unwrap_errors(list(validation_errors))
        if str(error.validator) not in COMPLEX_VALIDATORS
    ]


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


@dataclass
class DescriptorField:
    """A field in the Data Package descriptor.

    Attributes:
        jsonpath (str): The direct JSON path to the field.
        value (str): The value contained in the field.
    """

    jsonpath: str
    value: Any


def _get_fields_at_jsonpath(
    jsonpath: str, descriptor: dict[str, Any]
) -> list[DescriptorField]:
    """Returns all fields that match the JSON path."""
    matches = finditer(jsonpath, descriptor)
    return _map(matches, _create_descriptor_field)


def _create_descriptor_field(match: JSONPathMatch) -> DescriptorField:
    return DescriptorField(
        jsonpath=match.path.replace("['", ".").replace("']", ""),
        value=match.obj,
    )


In = TypeVar("In")
Out = TypeVar("Out")


def _map(x: Iterable[In], fn: Callable[[In], Out]) -> list[Out]:
    return list(map(fn, x))


def _filter(x: Iterable[In], fn: Callable[[In], bool]) -> list[In]:
    return list(filter(fn, x))


def _flat_map(items: Iterable[In], fn: Callable[[In], Iterable[Out]]) -> list[Out]:
    """Maps and flattens the items by one level."""
    return list(chain.from_iterable(map(fn, items)))
