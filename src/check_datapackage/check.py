import re
import sys
from dataclasses import dataclass, field
from functools import reduce
from types import TracebackType
from typing import Any, Callable, Iterator, Optional, cast

from jsonpath import findall, resolve
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
    PropertyField,
    _filter,
    _flat_map,
    _get_fields_at_jsonpath,
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
        """Create the DataPackageError from issues."""
        super().__init__(explain(issues))


def explain(issues: list[Issue]) -> str:
    """Explain the issues in a human-readable format.

    Args:
        issues: A list of `Issue` objects to explain.

    Returns:
        A human-readable explanation of the issues.

    Examples:
        ```{python}
        import check_datapackage as cdp

        issue = cdp.Issue(
            jsonpath="$.resources[2].title",
            type="required",
            message="The `title` field is required but missing at the given JSON path.",
        )

        cdp.explain([issue])
        ```
    """
    issue_explanations: list[str] = _map(
        issues,
        _create_explanation,
    )
    num_issues = len(issue_explanations)
    singular_or_plural = " was" if num_issues == 1 else "s were"
    return (
        f"{num_issues} issue{singular_or_plural} found in your `datapackage.json`:\n\n"
        + "\n".join(issue_explanations)
    )


def _create_explanation(issue: Issue) -> str:
    """Create an informative explanation of what went wrong in each issue."""
    # Remove suffix '$' to account for root path when `[]` is passed to `check()`
    property_name = issue.jsonpath.removesuffix("$").split(".")[-1]
    number_of_carets = len(str(issue.instance))
    return (  # noqa: F401
        f"At package{issue.jsonpath.removeprefix('$')}:\n"
        "|\n"
        f"| {property_name}{': ' if property_name else '  '}{issue.instance}\n"
        f"| {' ' * len(property_name)}  {'^' * number_of_carets}\n"
        f"{issue.message}\n"
    )


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
    issues += _check_keys(properties, issues)
    issues += apply_extensions(properties, config.extensions)
    issues = exclude(issues, config.exclusions, properties)
    issues = sorted(set(issues))

    if error and issues:
        raise DataPackageError(issues)

    return issues


def _check_keys(properties: dict[str, Any], issues: list[Issue]) -> list[Issue]:
    """Check that primary and foreign keys exist."""
    # Primary keys
    resources_with_pk = _get_fields_at_jsonpath(
        "$.resources[?(length(@.schema.primaryKey) > 0 || @.schema.primaryKey == '')]",
        properties,
    )
    resources_with_pk = _keep_resources_with_no_issue_at_property(
        resources_with_pk, issues, "schema.primaryKey"
    )
    key_issues = _flat_map(resources_with_pk, _check_primary_key)

    # Foreign keys
    resources_with_fk = _get_fields_at_jsonpath(
        "$.resources[?(length(@.schema.foreignKeys) > 0)]",
        properties,
    )
    resources_with_fk = _keep_resources_with_no_issue_at_property(
        resources_with_fk, issues, "schema.foreignKeys"
    )
    key_issues += _flat_map(
        resources_with_fk,
        lambda resource: _check_foreign_keys(resource, properties),
    )
    return key_issues


def _issues_at_property(
    resource: PropertyField, issues: list[Issue], jsonpath: str
) -> list[Issue]:
    return _filter(
        issues,
        lambda issue: f"{resource.jsonpath}.{jsonpath}" in issue.jsonpath,
    )


def _keep_resources_with_no_issue_at_property(
    resources: list[PropertyField], issues: list[Issue], jsonpath: str
) -> list[PropertyField]:
    """Filter out resources that have an issue at or under the given `jsonpath`."""
    return _filter(
        resources,
        lambda resource: not _issues_at_property(resource, issues, jsonpath),
    )


def _check_primary_key(resource: PropertyField) -> list[Issue]:
    """Check that primary key fields exist in the resource."""
    pk_fields = resolve("/schema/primaryKey", resource.value)
    pk_fields_list = _key_fields_as_str_list(pk_fields)
    unknown_fields = _get_unknown_key_fields(pk_fields_list, resource.value)

    if not unknown_fields:
        return []

    return [
        Issue(
            jsonpath=f"{resource.jsonpath}.schema.primaryKey",
            type="primary-key",
            message=(
                f"No fields found in resource for primary key fields: {unknown_fields}."
            ),
            instance=pk_fields,
        )
    ]


def _check_foreign_keys(
    resource: PropertyField, properties: dict[str, Any]
) -> list[Issue]:
    """Check that foreign key source and destination fields exist."""
    # Safe, as only FKs of the correct type here
    foreign_keys = cast(
        list[dict[str, Any]], resolve("/schema/foreignKeys", resource.value)
    )
    foreign_keys_diff_resource = _filter(
        foreign_keys,
        lambda fk: "resource" in fk["reference"] and fk["reference"]["resource"] != "",
    )
    foreign_keys_same_resource = _filter(
        foreign_keys, lambda fk: fk not in foreign_keys_diff_resource
    )

    issues = _flat_map(foreign_keys, lambda fk: _check_fk_source_fields(fk, resource))
    issues += _flat_map(
        foreign_keys_same_resource,
        lambda fk: _check_fk_dest_fields_same_resource(fk, resource),
    )
    issues += _flat_map(
        foreign_keys_diff_resource,
        lambda fk: _check_fk_dest_fields_diff_resource(fk, resource, properties),
    )

    return issues


def _key_fields_as_str_list(key_fields: Any) -> list[str]:
    """Returns the list representation of primary and foreign key fields.

    Key fields can be represented either as a string (containing one field name)
    or a list of strings.

    The input should contain a correctly typed `key_fields` object.
    """
    if not isinstance(key_fields, list):
        key_fields = [key_fields]
    return cast(list[str], key_fields)


def _get_unknown_key_fields(
    key_fields: list[str], properties: dict[str, Any], resource_path: str = ""
) -> str:
    """Return the key fields that don't exist on the specified resource."""
    known_fields = findall(f"{resource_path}schema.fields[*].name", properties)
    unknown_fields = _filter(key_fields, lambda field: field not in known_fields)
    unknown_fields = _map(unknown_fields, lambda field: f"{field!r}")
    return ", ".join(unknown_fields)


def _check_fk_source_fields(
    foreign_key: dict[str, Any], resource: PropertyField
) -> list[Issue]:
    """Check that foreign key source fields exist and have the correct number."""
    issues = []
    source_fields = resolve("/fields", foreign_key)
    source_field_list = _key_fields_as_str_list(source_fields)
    unknown_fields = _get_unknown_key_fields(source_field_list, resource.value)
    if unknown_fields:
        issues.append(
            Issue(
                jsonpath=f"{resource.jsonpath}.schema.foreignKeys.fields",
                type="foreign-key-source-fields",
                message=(
                    "No fields found in resource for foreign key source fields: "
                    f"{unknown_fields}."
                ),
                instance=source_fields,
            )
        )

    dest_fields = _key_fields_as_str_list(resolve("/reference/fields", foreign_key))
    if len(source_field_list) != len(dest_fields):
        issues.append(
            Issue(
                jsonpath=f"{resource.jsonpath}.schema.foreignKeys.fields",
                type="foreign-key-source-fields",
                message=(
                    "The number of foreign key source fields must be the same as "
                    "the number of foreign key destination fields."
                ),
                instance=source_fields,
            )
        )
    return issues


def _check_fk_dest_fields_same_resource(
    foreign_key: dict[str, Any],
    resource: PropertyField,
) -> list[Issue]:
    """Check that foreign key destination fields exist on the same resource."""
    dest_fields = resolve("/reference/fields", foreign_key)
    dest_field_list = _key_fields_as_str_list(dest_fields)
    unknown_fields = _get_unknown_key_fields(dest_field_list, resource.value)
    if not unknown_fields:
        return []

    return [
        Issue(
            jsonpath=f"{resource.jsonpath}.schema.foreignKeys.reference.fields",
            type="foreign-key-destination-fields",
            message=(
                "No fields found in resource for foreign key "
                f"destination fields: {unknown_fields}."
            ),
            instance=dest_fields,
        )
    ]


def _check_fk_dest_fields_diff_resource(
    foreign_key: dict[str, Any], resource: PropertyField, properties: dict[str, Any]
) -> list[Issue]:
    """Check that foreign key destination fields exist on the destination resource."""
    dest_fields = resolve("/reference/fields", foreign_key)
    dest_field_list = _key_fields_as_str_list(dest_fields)
    # Safe, as only keys of the correct type here
    dest_resource_name = cast(str, resolve("/reference/resource", foreign_key))

    dest_resource_path = f"resources[?(@.name == '{dest_resource_name}')]"
    if not findall(dest_resource_path, properties):
        return [
            Issue(
                jsonpath=f"{resource.jsonpath}.schema.foreignKeys.reference.resource",
                type="foreign-key-destination-resource",
                message=(
                    f"The destination resource {dest_resource_name!r} of this foreign "
                    "key doesn't exist in the package."
                ),
                instance=dest_resource_name,
            )
        ]

    unknown_fields = _get_unknown_key_fields(
        dest_field_list, properties, f"{dest_resource_path}."
    )
    if not unknown_fields:
        return []

    return [
        Issue(
            jsonpath=f"{resource.jsonpath}.schema.foreignKeys.reference.fields",
            type="foreign-key-destination-fields",
            message=(
                f"No fields found in destination resource {dest_resource_name!r} "
                f"for foreign key destination fields: {unknown_fields}."
            ),
            instance=dest_fields,
        )
    ]


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
        schema_value (Optional[Any]): The expected value that is checked against,
            which is part of the schema violated by this error.
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
    edits = SchemaErrorEdits(remove=[parent_error])
    errors_in_group = _get_errors_in_group(schema_errors, parent_error)

    parent_instance = parent_error.instance
    if not isinstance(parent_instance, dict):
        return edits

    field_type: str = parent_instance.get("type", "string")

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
            instance=parent_instance,
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
    """Only flag errors for the relevant field type and simplify errors."""
    edits = SchemaErrorEdits(remove=[parent_error])
    errors_in_group = _get_errors_in_group(schema_errors, parent_error)

    # Remove errors for other field types
    if _not_field_type_error(parent_error):
        edits.remove.extend(errors_in_group)
        return edits

    value_errors = _filter(
        errors_in_group,
        lambda error: not error.jsonpath.endswith("enum"),
    )

    # If there are only value errors, simplify them
    if value_errors == errors_in_group:
        edits.add.append(_get_enum_values_error(parent_error, value_errors))

    # Otherwise, keep only top-level enum errors
    edits.remove.extend(value_errors)
    return edits


def _get_enum_values_error(
    parent_error: SchemaError,
    value_errors: list[SchemaError],
) -> SchemaError:
    message = "All enum values must be the same type."
    same_type = len(set(_map(parent_error.instance, lambda value: type(value)))) == 1
    if same_type:
        allowed_types = set(_map(value_errors, lambda error: str(error.schema_value)))
        message = (
            "The enum value type is not correct. Enum values should be "
            f"one of {', '.join(allowed_types)}."
        )
    return SchemaError(
        message=message,
        type="type",
        schema_path=value_errors[0].schema_path,
        jsonpath=_strip_index(value_errors[0].jsonpath),
        instance=value_errors[0].instance,
    )


def _not_field_type_error(parent_error: SchemaError) -> bool:
    if not parent_error.parent:
        return True
    field_type: str = parent_error.parent.instance.get("type", "string")
    if field_type not in FIELD_TYPES:
        return True
    schema_index = FIELD_TYPES.index(field_type)
    return f"fields/items/oneOf/{schema_index}/" not in parent_error.schema_path


def _handle_S_resources_x_schema_primary_key(
    parent_error: SchemaError,
    schema_errors: list[SchemaError],
) -> SchemaErrorEdits:
    """Only flag errors for the relevant type and simplify errors."""
    PRIMARY_KEY_TYPES: tuple[type[Any], ...] = (list, str)
    edits = SchemaErrorEdits(remove=[parent_error])
    errors_in_group = _get_errors_in_group(schema_errors, parent_error)

    key_type = type(parent_error.instance)
    if key_type in PRIMARY_KEY_TYPES:
        schema_for_type = f"primaryKey/oneOf/{PRIMARY_KEY_TYPES.index(key_type)}/"
        edits.remove.extend(
            _filter(
                errors_in_group,
                lambda error: schema_for_type not in error.schema_path,
            )
        )
        return edits

    edits.remove.extend(errors_in_group)
    edits.add.append(
        SchemaError(
            message="The `primaryKey` property must be a string or an array.",
            type="type",
            jsonpath=parent_error.jsonpath,
            schema_path=parent_error.schema_path,
            instance=parent_error.instance,
        )
    )

    return edits


def _handle_S_resources_x_schema_foreign_keys(
    parent_error: SchemaError,
    schema_errors: list[SchemaError],
) -> SchemaErrorEdits:
    """Only flag errors for the relevant type and simplify errors.

    The sub-schema to use is determined based on the type of the top-level foreign
    key fields property.
    """
    FOREIGN_KEY_TYPES: tuple[type[Any], ...] = (list, str)
    edits = SchemaErrorEdits(remove=[parent_error])
    errors_in_group = _get_errors_in_group(schema_errors, parent_error)

    parent_instance = parent_error.instance
    key_exists = isinstance(parent_instance, dict) and "fields" in parent_instance

    # If the key type is correct, use that schema
    if (
        key_exists
        and (key_type := type(parent_instance["fields"])) in FOREIGN_KEY_TYPES
    ):
        schema_part = f"foreignKeys/items/oneOf/{FOREIGN_KEY_TYPES.index(key_type)}/"
        edits.remove.extend(
            _filter(
                errors_in_group,
                lambda error: schema_part not in error.schema_path,
            )
        )
        return edits

    # If the key type is incorrect, remove all errors that depend on it
    key_type_errors = _filter(
        errors_in_group,
        lambda error: error.schema_path.endswith("fields/type")
        or "reference/properties/fields" in error.schema_path,
    )
    edits.remove.extend(key_type_errors)

    # If the key exists, flag incorrect type
    if key_exists:
        edits.add.append(
            SchemaError(
                message=(
                    "The `fields` property of a foreign key must be a string or "
                    "an array."
                ),
                type="type",
                jsonpath=f"{parent_error.jsonpath}.fields",
                schema_path=parent_error.schema_path,
                instance=parent_error.instance,
            )
        )

    return edits


def _handle_licenses(
    parent_error: SchemaError,
    schema_errors: list[SchemaError],
) -> SchemaErrorEdits:
    """Only include one error if both `name` and `path` are missing."""
    errors_in_group = _get_errors_in_group(schema_errors, parent_error)
    return SchemaErrorEdits(
        remove=errors_in_group + [parent_error],
        add=[
            SchemaError(
                message=(
                    "Licenses must have at least one of the following properties: "
                    "`name`, `path`."
                ),
                type="required",
                schema_path=parent_error.schema_path,
                jsonpath=parent_error.jsonpath,
                instance=parent_error.instance,
            )
        ],
    )


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
    ("primaryKey/oneOf", _handle_S_resources_x_schema_primary_key),
    ("foreignKeys/items/oneOf", _handle_S_resources_x_schema_foreign_keys),
    ("licenses/items/anyOf", _handle_licenses),
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
        instance=error.instance,
    )


def _get_errors_in_group(
    schema_errors: list[SchemaError], parent_error: SchemaError
) -> list[SchemaError]:
    return _filter(schema_errors, lambda error: error.parent == parent_error)


def _strip_index(jsonpath: str) -> str:
    return re.sub(r"\[\d+\]$", "", jsonpath)
