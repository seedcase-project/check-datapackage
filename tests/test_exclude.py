from typing import Any

from pytest import mark

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.examples import example_package_descriptor
from check_datapackage.exclude import Exclude


def test_exclude_none_type():
    descriptor: dict[str, Any] = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "contributors": [{"path": "/a/bad/path"}],
    }

    exclude = [Exclude()]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 1


def test_exclude_required_type():
    """Exclude type with the required value."""
    descriptor = {"name": "a name with spaces"}

    exclude = [Exclude(type="required")]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0


def test_exclude_format_type():
    """Exclude type with the format value."""
    # created must match a date format
    descriptor = {"created": "20240614"}

    exclude = [Exclude(type="format")]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    # One issue: missing resources
    assert len(issues) == 1


def test_exclude_pattern_type():
    """Exclude types with the pattern value."""
    descriptor: dict[str, Any] = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "contributors": [{"path": "/a/bad/path"}],
    }

    exclude = [Exclude(type="pattern")]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0


def test_exclude_multiple_types():
    """Exclude by many types."""
    descriptor: dict[str, Any] = {
        "name": "a name",
        "created": "20240614",
        "contributors": [{"path": "/a/bad/path"}],
    }

    exclude = [
        Exclude(type="required"),
        Exclude(type="pattern"),
        Exclude(type="format"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

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
def test_exclude_jsonpath(jsonpath: str, num_issues: int) -> None:
    descriptor = example_package_descriptor()
    # Total 3 issues
    descriptor["created"] = "20240614"
    # Two issues for resources: type and pattern
    descriptor["resources"][0]["path"] = "/a/bad/path"
    descriptor.update({"contributors": [{"path": "/a/bad/path"}]})

    exclude = [Exclude(jsonpath=jsonpath)]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == num_issues


def test_exclude_jsonpath_multiple():
    descriptor = example_package_descriptor()
    descriptor["created"] = "20240614"
    descriptor.update({"contributors": [{"path": "/a/bad/path"}]})

    exclude = [
        Exclude(jsonpath="$.contributors[0].path"),
        Exclude(jsonpath="$.created"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0


def test_exclude_jsonpath_and_type():
    descriptor = example_package_descriptor()
    descriptor["created"] = "20240614"
    descriptor.update({"contributors": [{"path": "/a/bad/path"}]})

    exclude = [
        Exclude(jsonpath="$.contributors[0].path", type="pattern"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 1


def test_exclude_jsonpath_and_type_non_overlapping():
    descriptor = example_package_descriptor()
    # There should be two issues
    descriptor["created"] = "20240614"
    descriptor.update({"contributors": [{"path": "/a/bad/path"}]})

    exclude = [
        Exclude(jsonpath="$.contributors[0].path"),
        Exclude(type="pattern"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    # For the created field
    assert len(issues) == 1


def test_exclude_jsonpath_resources():
    """Exclude by jsonpath for resources."""
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
    issues = check(properties, config=Config(exclude=[Exclude(jsonpath="$.resources")]))
    assert len(issues) == 0
