from typing import Any

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


def test_exclude_target_explicit():
    """Exclude targets at explicit target."""
    descriptor = example_package_descriptor()
    descriptor["created"] = "20240614"

    exclude = [Exclude(target=r"\$\.created")]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0


def test_exclude_target_pattern():
    """Exclude targets at pattern target."""
    descriptor = example_package_descriptor()
    descriptor["created"] = "20240614"

    exclude = [Exclude(target="created")]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0


def test_exclude_target_nested():
    descriptor = example_package_descriptor()
    descriptor.update({"contributors": [{"path": "/a/bad/path"}]})

    exclude = [
        Exclude(target=r"\$\.contributors\[.*\]\.path"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0

    exclude = [
        Exclude(target=r"path"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0


def test_exclude_target_multiple():
    descriptor = example_package_descriptor()
    descriptor["created"] = "20240614"
    descriptor.update({"contributors": [{"path": "/a/bad/path"}]})

    exclude = [
        Exclude(target=r"\$\.contributors\[.*\]\.path"),
        Exclude(target=r"created"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0


def test_exclude_target_and_type():
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
        Exclude(target=r"path", type="format"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0

    exclude = [
        Exclude(target=r"path"),
        Exclude(type="format"),
    ]
    config = Config(exclude=exclude)
    issues = check(descriptor, config=config)

    assert len(issues) == 0
