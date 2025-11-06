import re
import sys
from dataclasses import dataclass, field
from functools import reduce
from types import TracebackType
from typing import Any, Callable, Iterator, Optional

from jsonschema import Draft7Validator, FormatChecker, ValidationError

from check_datapackage.config import Config
from check_datapackage.constants import (
    DATA_PACKAGE_SCHEMA_PATH,
    FIELD_TYPES,
    GROUP_ERRORS,
)
from check_datapackage.exclusion import exclude
from check_datapackage.extensions import apply_extensions
from check_datapackage.internals import (
    _filter,
    _flat_map,
    _map,
)
from check_datapackage.issue import Issue
from check_datapackage.read_json import read_json


def no_traceback_hook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Exception hook to hide tracebacks for DataPackageError."""
    if issubclass(exc_type, DataPackageError):
        # Only print the message, without traceback
        print("{0}".format(exc_value))
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


# Need to use a custom exception hook to hide tracebacks for our custom exceptions
sys.excepthook = no_traceback_hook


class DataPackageError(Exception):
    """Convert Data Package issues to an error and hide the traceback."""

    def __init__(
        self,
        issues: list[Issue],
    ) -> None:
        """Create the DataPackageError attributes from issues."""
        # TODO: Switch to using `explain()` once implemented
        errors: list[str] = _map(
            issues,
            lambda issue: f"- Property `{issue.jsonpath}`: {issue.message}\n",
        )
        message: str = (
            "There were some issues found in your `datapackage.json`:\n\n"
            + "\n".join(errors)
        )
        super().__init__(message)


def check(
    properties: dict[str, Any], config: Config = Config(), error: bool = False
) -> list[Issue]:
    """Checks a Data Package's properties against the Data Package standard.

    Args:
        properties: A Data Package's metadata from `datapackage.json` as a Python
            dictionary.
        config: Configuration for the checks to be done. See the `Config`
            class for more details, especially about the default values.
        error: Whether to treat any issues found as errors. Defaults
            to `False`, meaning that issues will be returned as a list of `Issue`
            objects. Will internally run `explain()` on the Issues
            if set to `True`.

    Returns:
        A list of `Issue` objects representing any issues found
            while checking the properties. If no issues are found, an empty list
            is returned.
    """
    schema = read_json(DATA_PACKAGE_SCHEMA_PATH)

    if config.strict:
        _set_should_fields_to_required(schema)

    issues = _check_object_against_json_schema(properties, schema)
    issues += apply_extensions(properties, config.extensions)
    issues = exclude(issues, config.exclusions, properties)

    if error and issues:
        raise DataPackageError(issues)

    return sorted(set(issues))


def _set_should_fields_to_required(schema: dict[str, Any]) -> dict[str, Any]:
    """Set 'SHOULD' fields to 'REQUIRED' in the schema."""
    should_fields = ("name", "id", "licenses")
    name_pattern = r"^[a-z0-9._-]+$"

    # From https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
    semver_pattern = (
        r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0"
        r"|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>"
        r"[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    # Convert to required
    schema["required"].extend(should_fields)
    schema["properties"]["name"]["pattern"] = name_pattern
    schema["properties"]["version"]["pattern"] = semver_pattern
    schema["properties"]["contributors"]["items"]["required"] = ["title"]
    schema["properties"]["sources"]["items"]["required"] = ["title"]
    schema["properties"]["resources"]["items"]["properties"]["name"]["pattern"] = (
        name_pattern
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


@dataclass(frozen=True)
class SchemaError:
    """A simpler representation of `ValidationError` for easier processing.

    Attributes:
        message (str): The error message generated by `jsonschema`.
        type (str): The type of the error (e.g., a JSON schema type such as "required",
            "type", "pattern", or "format", or a custom type).
        schema_path (str): The path to the violated check in the JSON schema.
            Path components are separated by '/'.
        jsonpath (str): The JSON path to the field that violates the check.
        instance (Any): The part of the object that failed the check.
        schema_value (Optional[Any]): The part of the schema violated by this error.
        parent (Optional[SchemaError]): The error group the error belongs to, if any.
    """

    message: str
    type: str
    schema_path: str
    jsonpath: str
    instance: Any
    schema_value: Optional[Any] = None
    parent: Optional["SchemaError"] = None


def _validation_errors_to_issues(
    validation_errors: Iterator[ValidationError],
) -> list[Issue]:
    """Transforms `jsonschema.ValidationError`s to more compact `Issue`s.

    Args:
        validation_errors: The `jsonschema.ValidationError`s to transform.

    Returns:
        A list of `Issue`s.
    """
    schema_errors = _flat_map(validation_errors, _validation_error_to_schema_errors)
    grouped_errors = _filter(schema_errors, lambda error: error.type in GROUP_ERRORS)
    schema_errors = reduce(_handle_grouped_error, grouped_errors, schema_errors)

    return _map(schema_errors, _create_issue)


@dataclass(frozen=True)
class SchemaErrorEdits:
    """Expresses which errors to add to or remove from schema errors."""

    add: list[SchemaError] = field(default_factory=list)
    remove: list[SchemaError] = field(default_factory=list)


def _handle_S_resources_x(
    parent_error: SchemaError,
    schema_errors: list[SchemaError],
) -> SchemaErrorEdits:
    """Do not flag missing `path` and `data` separately."""
    edits = SchemaErrorEdits()
    errors_in_group = _get_errors_in_group(schema_errors, parent_error)
    # If the parent error is caused by other errors, remove it
    if errors_in_group:
        edits.remove.append(parent_error)

    path_or_data_required_errors = _filter(
        errors_in_group, _path_or_data_required_error
    )
    # If path and data are both missing, add a more informative error
    if len(path_or_data_required_errors) > 1:
        edits.add.append(
            SchemaError(
                message=(
                    "This resource has no `path` or `data` field. "
                    "One of them must be provided."
                ),
                type="required",
                jsonpath=parent_error.jsonpath,
                schema_path=parent_error.schema_path,
                instance=parent_error.instance,
            )
        )

    # Remove all required errors on path and data
    edits.remove.extend(path_or_data_required_errors)
    return edits


def _handle_S_resources_x_path(
    parent_error: SchemaError,
    schema_errors: list[SchemaError],
) -> SchemaErrorEdits:
    """Only flag errors for the relevant type.

    If `path` is a string, flag errors for the string-based schema.
    If `path` is an array, flag errors for the array-based schema.
    """
    edits = SchemaErrorEdits()
    errors_in_group = _get_errors_in_group(schema_errors, parent_error)
    type_errors = _filter(errors_in_group, _is_path_type_error)
    only_type_errors = len(errors_in_group) == len(type_errors)

    if type_errors:
        edits.remove.append(parent_error)

    # If the only error is that $.resources[x].path is of the wrong type,
    # add a more informative error
    if only_type_errors:
        edits.add.append(
            SchemaError(
                message="The `path` property must be either a string or an array.",
                type="type",
                jsonpath=type_errors[0].jsonpath,
                schema_path=type_errors[0].schema_path,
                instance=parent_error.instance,
            )
        )

    # Remove all original type errors on $.resources[x].path
    edits.remove.extend(type_errors)
    return edits


def _handle_S_resources_x_schema_fields_x(
    parent_error: SchemaError,
    schema_errors: list[SchemaError],
) -> SchemaErrorEdits:
    """Only flag errors for the relevant field type.

    E.g., if the field type is `string`, flag errors for the string-based schema only.
    """
    edits = SchemaErrorEdits()
    errors_in_group = _get_errors_in_group(schema_errors, parent_error)
    edits.remove.append(parent_error)

    field_type: str = parent_error.instance.get("type", "string")

    # The field's type is unknown
    if field_type not in FIELD_TYPES:
        unknown_field_error = SchemaError(
            message=(
                "The type property in this resource schema field is incorrect. "
                f"The value can only be one of these types: {', '.join(FIELD_TYPES)}."
            ),
            type="enum",
            jsonpath=f"{parent_error.jsonpath}.type",
            schema_path=parent_error.schema_path,
            instance=parent_error.instance,
        )
        # Replace all errors with an unknown field error
        edits.add.append(unknown_field_error)
        edits.remove.extend(errors_in_group)
        return edits

    # The field's type is known; keep only errors for this field type
    schema_index = FIELD_TYPES.index(field_type)

    errors_for_other_types = _filter(
        errors_in_group,
        lambda error: f"fields/items/oneOf/{schema_index}/" not in error.schema_path,
    )
    edits.remove.extend(errors_for_other_types)
    return edits


def _handle_S_resources_x_schema_fields_x_constraints_enum(
    parent_error: SchemaError,
    schema_errors: list[SchemaError],
) -> SchemaErrorEdits:
    """Only flag errors for the relevant field type.

    E.g., if the field type is `string`, flag enum errors for the string-based
    schema only.
    """
    edits = SchemaErrorEdits()
    if not parent_error.parent:
        return edits

    errors_in_group = _get_errors_in_group(schema_errors, parent_error)
    field_type: str = parent_error.parent.instance.get("type", "string")
    edits.remove.append(parent_error)

    # The field's type is unknown; this is already flagged, so remove all errors
    if field_type not in FIELD_TYPES:
        edits.remove.extend(errors_in_group)
        return edits

    # The field's type is known; keep only errors for this field type
    schema_index = FIELD_TYPES.index(field_type)
    path_for_type = f"fields/items/oneOf/{schema_index}/"

    errors_for_this_type = _filter(
        errors_in_group,
        lambda error: path_for_type in error.schema_path and error.type == "type",
    )
    errors_for_other_types = _filter(
        errors_in_group, lambda error: path_for_type not in error.schema_path
    )

    edits.remove.extend(errors_for_other_types)
    if not errors_for_this_type:
        return edits

    # Unify multiple enum errors
    an_error = errors_for_this_type[0]
    same_type = all(
        _map(
            errors_for_this_type,
            lambda error: type(error.instance) is type(an_error.instance),
        )
    )
    message = "All enum values must be the same type."
    if same_type:
        allowed_types = set(
            _map(errors_for_this_type, lambda error: str(error.schema_value))
        )
        message = (
            "Incorrect enum value type. Enum values should be "
            f"one of {', '.join(allowed_types)}."
        )

    unified_error = SchemaError(
        message=message,
        type="type",
        schema_path=an_error.schema_path,
        jsonpath=_strip_index(an_error.jsonpath),
        instance=an_error.instance,
    )
    edits.add.append(unified_error)
    edits.remove.extend(errors_for_this_type)

    return edits


_schema_path_to_handler: list[
    tuple[str, Callable[[SchemaError, list[SchemaError]], SchemaErrorEdits]]
] = [
    ("resources/items/oneOf", _handle_S_resources_x),
    ("resources/items/properties/path/oneOf", _handle_S_resources_x_path),
    ("fields/items/oneOf", _handle_S_resources_x_schema_fields_x),
    (
        "constraints/properties/enum/oneOf",
        _handle_S_resources_x_schema_fields_x_constraints_enum,
    ),
]


def _handle_grouped_error(
    schema_errors: list[SchemaError], parent_error: SchemaError
) -> list[SchemaError]:
    """Handle grouped schema errors that need special treatment.

    Args:
        schema_errors: All remaining schema errors.
        parent_error: The parent error of a group.

    Returns:
        The schema errors after processing.
    """

    def _get_edits(
        handlers: list[
            tuple[str, Callable[[SchemaError, list[SchemaError]], SchemaErrorEdits]]
        ],
    ) -> SchemaErrorEdits:
        schema_path, handler = handlers[0]
        edits = SchemaErrorEdits()
        if parent_error.schema_path.endswith(schema_path):
            edits = handler(parent_error, schema_errors)

        if len(handlers) == 1:
            return edits

        next_edits = _get_edits(handlers[1:])
        return SchemaErrorEdits(
            add=edits.add + next_edits.add,
            remove=edits.remove + next_edits.remove,
        )

    edits = _get_edits(_schema_path_to_handler)
    return _filter(schema_errors, lambda error: error not in edits.remove) + edits.add


def _validation_error_to_schema_errors(error: ValidationError) -> list[SchemaError]:
    current = [_create_schema_error(error)]
    if not error.context:
        return current

    return current + _flat_map(error.context, _validation_error_to_schema_errors)


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


def _create_schema_error(error: ValidationError) -> SchemaError:
    return SchemaError(
        message=error.message,
        type=str(error.validator),
        jsonpath=_get_full_json_path_from_error(error),
        schema_path="/".join(_map(error.absolute_schema_path, str)),
        instance=error.instance,
        schema_value=error.validator_value,
        parent=_create_schema_error(error.parent) if error.parent else None,  # type: ignore[arg-type]
    )


def _path_or_data_required_error(error: SchemaError) -> bool:
    return error.jsonpath.endswith(("path", "data")) and error.type == "required"


def _is_path_type_error(error: SchemaError) -> bool:
    return error.type == "type" and error.jsonpath.endswith("path")


def _create_issue(error: SchemaError) -> Issue:
    return Issue(
        message=error.message,
        jsonpath=error.jsonpath,
        type=error.type,
    )


def _get_errors_in_group(
    schema_errors: list[SchemaError], parent_error: SchemaError
) -> list[SchemaError]:
    return _filter(schema_errors, lambda error: error.parent == parent_error)


def _strip_index(jsonpath: str) -> str:
    return re.sub(r"\[\d+\]$", "", jsonpath)
