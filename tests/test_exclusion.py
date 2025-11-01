from typing import Any

from pytest import mark

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.examples import (
    example_package_properties,
    example_resource_properties,
)
from check_datapackage.exclusion import Exclusion


def test_exclusion_none_type_and_jsonpath():
    """Default Exclusion (without type and jsonpath) doesn't exclude default checks."""
    properties: dict[str, Any] = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "contributors": [{"path": "/a/bad/path"}],
    }

    exclusion = [Exclusion()]
    config = Config(exclusions=exclusion)
    issues = check(properties, config=config)

    assert len(issues) == 1


def test_exclusion_required_type():
    """Exclusion by required type."""
    properties = {"name": "a name with spaces"}

    exclusion = [Exclusion(type="required")]
    config = Config(exclusions=exclusion)
    issues = check(properties, config=config)

    assert len(issues) == 0


def test_exclusion_format_type():
    """Exclusion by format type."""
    # created must match a date format
    properties = {"created": "20240614"}

    exclusion = [Exclusion(type="format")]
    config = Config(exclusions=exclusion)
    issues = check(properties, config=config)

    # One issue: missing resources
    assert len(issues) == 1


def test_exclusion_pattern_type():
    """Exclusion by pattern type."""
    properties: dict[str, Any] = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "contributors": [{"path": "/a/bad/path"}],
    }

    exclusion = [Exclusion(type="pattern")]
    config = Config(exclusions=exclusion)
    issues = check(properties, config=config)

    assert len(issues) == 0


def test_exclusions_multiple_types():
    """Exclusions by multiple types."""
    properties: dict[str, Any] = {
        "name": "a name",
        "created": "20240614",
        "contributors": [{"path": "/a/bad/path"}],
    }

    exclusions = [
        Exclusion(type="required"),
        Exclusion(type="pattern"),
        Exclusion(type="format"),
    ]
    config = Config(exclusions=exclusions)
    issues = check(properties, config=config)

    assert len(issues) == 0


@mark.parametrize(
    "jsonpath, num_issues",
    [
        ("$", 3),
        ("..*", 0),
        ("$.created", 2),
        ("created", 2),
        ("$.contributors[*].path", 2),
        ("$.contributors[0].path", 2),
        ("$..path", 1),
        ("contributors[0].path", 2),
        ("contributors[*].path", 2),
        ("..resources[*]", 3),
        ("..resources", 3),
        ("$.resources[*]", 3),
        ("$.resources[0]", 3),
        ("$.resources[*].path", 2),
        ("$.resources[0].*", 2),
        ("$.resources[0].path", 2),
    ],
)
def test_exclusion_jsonpaths(jsonpath: str, num_issues: int) -> None:
    """Exclusion by various jsonpaths."""
    properties = example_package_properties()
    # Total 3 issues
    properties["created"] = "20240614"
    # Two issues for resources: type and pattern
    properties["resources"][0]["path"] = "/a/bad/path"
    properties.update({"contributors": [{"path": "/a/bad/path"}]})

    exclusion = [Exclusion(jsonpath=jsonpath)]
    config = Config(exclusions=exclusion)
    issues = check(properties, config=config)

    assert len(issues) == num_issues


def test_exclusion_multiple_jsonpaths():
    """Exclusion by multiple jsonpaths."""
    properties = example_package_properties()
    properties["created"] = "20240614"
    properties.update({"contributors": [{"path": "/a/bad/path"}]})

    exclusions = [
        Exclusion(jsonpath="$.contributors[0].path"),
        Exclusion(jsonpath="$.created"),
    ]
    config = Config(exclusions=exclusions)
    issues = check(properties, config=config)

    assert len(issues) == 0


def test_exclusion_jsonpath_and_type():
    """Exclusion by jsonpath and type."""
    properties = example_package_properties()
    properties["contributors"] = [{"path": "/a/bad/path"}, {"path": "/a/bad/path"}]

    exclusions = [
        Exclusion(jsonpath="$.contributors[0].path", type="pattern"),
    ]
    config = Config(exclusions=exclusions)
    issues = check(properties, config=config)

    assert len(issues) == 1


def test_exclusion_jsonpath_and_type_non_overlapping():
    """Exclusion by jsonpath and type where no overlap occurs."""
    properties = example_package_properties()
    # There should be two issues
    properties["created"] = "20240614"
    properties.update({"contributors": [{"path": "/a/bad/path"}]})

    exclusions = [
        Exclusion(jsonpath="$.contributors[0].path"),
        Exclusion(type="pattern"),
    ]
    config = Config(exclusions=exclusions)
    issues = check(properties, config=config)

    # For the created field
    assert len(issues) == 1


def test_exclusion_jsonpath_resources():
    """Exclusion by jsonpath for resources."""
    properties: dict[str, Any] = {
        "name": "woolly-dormice",
        "title": "Hibernation Physiology of the Woolly Dormouse: A Scoping Review.",
        "description": "",
        "id": "123-abc-123",
        "created": "2014-05-14T05:00:01+00:00",
        "version": "1.0.0",
        "licenses": [{"name": "odc-pddl"}],
        "resources": "this is a string",  # should be an array
    }
    issues = check(
        properties, config=Config(exclusions=[Exclusion(jsonpath="$.resources")])
    )
    assert len(issues) == 0


def test_exclude_issue_on_array_item():
    properties = example_package_properties()
    properties["resources"].append("not a resource")
    exclusions = [Exclusion(jsonpath="$.resources[*]")]
    config = Config(exclusions=exclusions)

    issues = check(properties, config=config)

    assert issues == []


@mark.parametrize(
    "jsonpath",
    ["$.resources[*].name", "$.resources[1].*"],
)
def test_exclude_required_at_jsonpath_array(jsonpath):
    properties = example_package_properties()
    properties["resources"].append(example_resource_properties())
    del properties["resources"][1]["name"]
    exclusions = [
        Exclusion(jsonpath=jsonpath, type="required"),
    ]
    config = Config(exclusions=exclusions)

    issues = check(properties, config=config)

    assert issues == []


@mark.parametrize(
    "jsonpath", ["$.*", "$..resources", "..resources", "resources", "..*"]
)
def test_exclude_required_at_jsonpath_dict_field(jsonpath):
    properties = example_package_properties()
    del properties["resources"]
    exclusions = [
        Exclusion(jsonpath=jsonpath, type="required"),
    ]
    config = Config(exclusions=exclusions)

    issues = check(properties, config=config)

    assert issues == []
