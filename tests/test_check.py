from pytest import mark

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.examples import example_package_descriptor
from check_datapackage.exclude import Exclude
from tests.test_rule import lowercase_rule

# Without recommendations


def test_passes_matching_descriptor_with_resources():
    """Should pass descriptor matching the schema."""
    descriptor = {
        "name": "a name with spaces",
        "title": "A Title",
        "created": "2024-05-14T05:00:01+00:00",
        "version": "a version",
        "contributors": [{"email": "jane@doe.com"}],
        "sources": [{"email": "jane@doe.com"}],
        "resources": [{"name": "a name", "path": "data.csv"}],
    }

    assert check(descriptor) == []


def test_fails_descriptor_without_resources():
    """Should fail descriptor without resources."""
    descriptor = {"name": "a name with spaces"}

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "required"
    assert issues[0].jsonpath == "$.resources"


@mark.parametrize(
    "resources, jsonpath, num_issues",
    [
        ([], "$.resources", 1),
        ([{}], "$.resources[0].data", 3),
        ([{"name": "a name", "path": "/a/bad/path"}], "$.resources[0].path", 2),
    ],
)
def test_fails_descriptor_with_bad_resources(resources, jsonpath, num_issues):
    """Should fail descriptor with malformed resources."""
    descriptor = {
        "name": "a name with spaces",
        "resources": resources,
    }

    issues = check(descriptor)

    assert len(issues) == num_issues
    assert issues[0].jsonpath == jsonpath


def test_fails_descriptor_with_missing_required_fields():
    """Should fail descriptor with missing required fields."""
    descriptor = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "licenses": [{"title": "my license"}],
    }

    issues = check(descriptor)

    assert len(issues) == 2
    assert all(issue.type == "required" for issue in issues)
    assert {issue.jsonpath for issue in issues} == {
        "$.licenses[0].name",
        "$.licenses[0].path",
    }


def test_fails_descriptor_with_bad_type():
    """Should fail descriptor with a field of the wrong type."""
    descriptor = {
        "name": 123,
        "resources": [{"name": "a name", "path": "data.csv"}],
    }
    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.name"


def test_fails_descriptor_with_bad_format():
    """Should fail descriptor with a field of the wrong format."""
    descriptor = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "homepage": "not a URL",
    }

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "format"
    assert issues[0].jsonpath == "$.homepage"


def test_fails_descriptor_with_pattern_mismatch():
    """Should fail descriptor with a field that does not match the pattern."""
    descriptor = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "contributors": [{"path": "/a/bad/path"}],
    }

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "pattern"
    assert issues[0].jsonpath == "$.contributors[0].path"


# With recommendations


def test_passes_matching_descriptor_with_recommendations():
    """Should pass descriptor matching recommendations."""
    descriptor = {
        "name": "a-name-with-no-spaces",
        "title": "A Title",
        "id": "123",
        "created": "2024-05-14T05:00:01+00:00",
        "version": "3.2.1",
        "contributors": [{"title": "a contributor"}],
        "sources": [{"title": "a source"}],
        "licenses": [{"name": "a-license"}],
        "resources": [{"name": "a-name-with-no-spaces", "path": "data.csv"}],
    }

    assert check(descriptor, config=Config(strict=True)) == []


def test_fails_descriptor_with_missing_required_fields_with_recommendations():
    """Should fail descriptor with missing required fields."""
    descriptor = {
        "resources": [{"name": "a-name-with-no-spaces", "path": "data.csv"}],
    }

    issues = check(descriptor, config=Config(strict=True))

    assert len(issues) == 3
    assert all(issue.type == "required" for issue in issues)


def test_fails_descriptor_violating_recommendations():
    """Should fail descriptor that do not meet the recommendations."""
    descriptor = {
        "name": "a name with spaces",
        "id": "123",
        "version": "not semver",
        "contributors": [{"email": "jane@doe.com"}],
        "sources": [{"email": "jane@doe.com"}],
        "licenses": [{"name": "a-license"}],
        "resources": [{"name": "a name with spaces", "path": "data.csv"}],
    }

    issues = check(descriptor, config=Config(strict=True))

    assert len(issues) == 5
    assert {issue.jsonpath for issue in issues} == {
        "$.name",
        "$.version",
        "$.contributors[0].title",
        "$.sources[0].title",
        "$.resources[0].name",
    }


def test_exclude_not_excluding_rule():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    del descriptor["resources"]
    exclude_required = Exclude(type="required")
    config = Config(rules=[lowercase_rule], exclude=[exclude_required])

    issues = check(descriptor, config=config)

    assert len(issues) == 1
    assert issues[0].type == "lowercase"


def test_exclude_excluding_rule():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    exclude_lowercase = Exclude(type=lowercase_rule.type)
    config = Config(rules=[lowercase_rule], exclude=[exclude_lowercase])

    issues = check(descriptor, config=config)

    assert issues == []
