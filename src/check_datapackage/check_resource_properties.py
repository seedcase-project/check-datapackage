from typing import Any

from check_datapackage.check_error import CheckError
from check_datapackage.constants import DATA_PACKAGE_SCHEMA_PATH
from check_datapackage.internals import (
    _add_resource_recommendations,
    _check_object_against_json_schema,
    _read_json,
)


def check_resource_properties(
    properties: dict[str, Any], check_recommendations: bool = True
) -> list[CheckError]:
    """Checks that the resource `properties` matches the Data Resource standard (v2.0).

    This function expects an individual set of resource properties as input. Structural,
    type and format constraints are all checked. All schema violations are collected
    before errors are returned.

    The schema loaded or constructed in this function overrides any values specified
    in the `$schema` attribute of `properties`, including the default value.

    Args:
        properties: The resource properties to check.
        check_recommendations: Whether `properties` should be checked against
            recommendations in the Data Resource standard in addition to requirements.
            Defaults to True.

    Returns:
        A list of errors. An empty list, if no errors are found.
    """
    schema = _read_json(DATA_PACKAGE_SCHEMA_PATH)

    # Recommendations from the Data Package standard
    if check_recommendations:
        _add_resource_recommendations(schema)

    # Consider only Data Resource schema
    schema = schema["properties"]["resources"]["items"]
    return _check_object_against_json_schema(properties, schema)
