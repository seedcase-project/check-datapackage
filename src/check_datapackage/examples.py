from textwrap import dedent
from typing import Any


def example_resource_properties() -> dict[str, Any]:
    """Create a set of example resource properties.

    Returns:
        A set of example resource properties.
    """
    return {
        "name": "woolly-dormice-2015",
        "title": "Body fat percentage in the hibernating woolly dormouse",
        "path": "resources/woolly-dormice-2015/data.parquet",
    }


def example_package_properties() -> dict[str, Any]:
    """Create a set of example package properties.

    Returns:
        A set of example package properties.
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
