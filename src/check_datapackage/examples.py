from textwrap import dedent
from typing import Any


def example_field_properties() -> dict[str, Any]:
    """Create a set of example field properties.

    Returns:
        A set of example field properties.

    Examples:
        ```{python}
        import check_datapackage as cdp

        cdp.example_field_properties()
        ```
    """
    return {
        "name": "eye-colour",
        "type": "string",
        "title": "Woolly dormouse eye colour",
    }


def example_resource_properties() -> dict[str, Any]:
    """Create a set of example resource properties.

    Returns:
        A set of example resource properties.

    Examples:
        ```{python}
        import check_datapackage as cdp

        cdp.example_resource_properties()
        ```
    """
    return {
        "name": "woolly-dormice-2015",
        "title": "Body fat percentage in the hibernating woolly dormouse",
        "path": "resources/woolly-dormice-2015/data.parquet",
        "schema": {"fields": [example_field_properties()]},
    }


def example_package_properties() -> dict[str, Any]:
    """Create a set of example package properties.

    Returns:
        A set of example package properties.

    Examples:
        ```{python}
        import check_datapackage as cdp

        cdp.example_package_properties()
        ```
    """
    return {
        "name": "woolly-dormice",
        "title": "Hibernation Physiology of the Woolly Dormouse: A Scoping Review.",
        "description": dedent("""
            This scoping review explores the hibernation physiology of the
            woolly dormouse, drawing on data collected over a 10-year period
            along the Taurus Mountain range in Turkey.
            """),
        "id": "123-abc-123",
        "created": "2014-05-14T05:00:01+00:00",
        "version": "1.0.0",
        "licenses": [{"name": "odc-pddl"}],
        "resources": [example_resource_properties()],
    }
