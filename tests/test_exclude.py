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
        # TODO: This should work but doesn't
        # ("$", 0),
        ("..*", 0),
        ("$.created", 3),
        ("created", 3),
        ("$.contributors[*].path", 3),
        ("$.contributors[0].path", 3),
        ("$..path", 1),
        ("contributors[0].path", 3),
        ("contributors[*].path", 3),
        # TODO: These should work but don't
        # ("..resources[*]", 2),
        # ("..resources", 2),
        # ("$.resources[*]", 2),
        # ("$.resources[0]", 2),
        ("$.resources[*].path", 2),
        ("$.resources[0].*", 2),
        ("$.resources[0].path", 2),
    ],
)
def test_exclude_jsonpath(jsonpath: str, num_issues: int) -> None:
    descriptor = example_package_descriptor()
    # Total 4 issues
    descriptor["created"] = "20240614"
    # Two issues for resources: type and pattern
    descriptor["resources"][0]["path"] = "/a/bad/path"
    descriptor.update({"contributors": [{"path": "/a/bad/path"}]})

    exclude = [Exclude(jsonpath=jsonpath)]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)
    print(issues)

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

    # To confirm that one on it's own works
    exclude = [
        Exclude(type="format"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 1

    exclude = [
        Exclude(jsonpath="$.contributors[0].path", type="format"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0

    exclude = [
        Exclude(jsonpath="$.contributors[0].path"),
        Exclude(type="format"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0
