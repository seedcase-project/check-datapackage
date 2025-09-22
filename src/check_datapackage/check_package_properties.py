from typing import Any

from check_datapackage.check_error import CheckError
from check_datapackage.constants import (
    DATA_PACKAGE_SCHEMA_PATH,
)
from check_datapackage.internals import (
    _add_package_recommendations,
    _check_object_against_json_schema,
)
from check_datapackage.read_json import read_json


def check_package_properties(
    properties: dict[str, Any], check_recommendations: bool = True
) -> list[CheckError]:
    """Checks that `properties` matches the Data Package standard (v2.0).

    Only package properties are checked. Schema constraints for resource properties are
    removed, so the internal structure of resource properties is not checked.
    Structural, type and format constraints are all checked. All schema violations are
    collected before errors are returned.

    The schema loaded or constructed in this function overrides any values specified
    in the `$schema` attribute of `properties`, including the default value.

    Args:
        properties: The package properties to check.
        check_recommendations: Whether `properties` should be checked against
            recommendations in the Data Package standard in addition to requirements.
            Defaults to True.

    Returns:
        A list of errors. An empty list, if no errors are found.
    """
    schema = read_json(DATA_PACKAGE_SCHEMA_PATH)

    # Recommendations from the Data Package standard
    if check_recommendations:
        _add_package_recommendations(schema)

    # Remove schema constraints for resource properties
    schema["required"].remove("resources")
    del schema["properties"]["resources"]["minItems"]
    del schema["properties"]["resources"]["items"]

    return _check_object_against_json_schema(properties, schema)
