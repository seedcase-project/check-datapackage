from typing import Any

from check_datapackage.check import check
from check_datapackage.config import Config
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
