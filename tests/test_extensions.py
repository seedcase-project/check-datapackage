from pytest import mark, raises

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.examples import (
    example_package_properties,
    example_resource_properties,
)
from check_datapackage.extensions import CustomCheck, Extensions, RequiredCheck
from check_datapackage.internals import _map
from check_datapackage.issue import Issue

lowercase_check = CustomCheck(
    jsonpath="$.name",
    message="Name must be lowercase.",
    check=lambda name: name.islower(),
    type="lowercase",
)
resource_name_check = CustomCheck(
    jsonpath="$.resources[*].name",
    message="Resource name must start with 'woolly'.",
    check=lambda name: name.startswith("woolly"),
    type="resource-name",
)


def test_direct_jsonpath():
    properties = example_package_properties()
    properties["name"] = "ALLCAPS"
    config = Config(extensions=Extensions(custom_checks=[lowercase_check]))
    issues = check(properties, config=config)

    assert issues == [
        Issue(
            jsonpath=lowercase_check.jsonpath,
            type=lowercase_check.type,
            message=lowercase_check.message,
        )
    ]


def test_indirect_jsonpath():
    properties = example_package_properties()
    properties["resources"].append(example_resource_properties())
    properties["resources"][1]["name"] = "not starting with woolly"

    config = Config(extensions=Extensions(custom_checks=[resource_name_check]))
    issues = check(properties, config=config)

    assert issues == [
        Issue(
            jsonpath="$.resources[1].name",
            type=resource_name_check.type,
            message=resource_name_check.message,
        ),
    ]


def test_multiple_custom_checks():
    properties = example_package_properties()
    properties["name"] = "ALLCAPS"
    properties["resources"][0]["name"] = "not starting with woolly"
    del properties["version"]

    version_check = RequiredCheck(
        jsonpath="$.version",
        message="Version is required.",
    )
    config = Config(
        extensions=Extensions(
            required_checks=[version_check],
            custom_checks=[lowercase_check, resource_name_check],
        )
    )
    issues = check(properties, config=config)

    assert issues == [
        Issue(
            jsonpath=lowercase_check.jsonpath,
            type=lowercase_check.type,
            message=lowercase_check.message,
        ),
        Issue(
            jsonpath="$.resources[0].name",
            type=resource_name_check.type,
            message=resource_name_check.message,
        ),
        Issue(
            jsonpath=version_check.jsonpath,
            type="required",
            message=version_check.message,
        ),
    ]


def test_custom_checks_and_default_checks():
    properties = example_package_properties()
    properties["name"] = "ALLCAPS"
    del properties["resources"]
    config = Config(extensions=Extensions(custom_checks=[lowercase_check]))
    issues = check(properties, config=config)

    assert [issue.type for issue in issues] == ["lowercase", "required"]


def test_no_matching_jsonpath():
    properties = example_package_properties()
    custom_check = CustomCheck(
        jsonpath="$.missing",
        message="This check always fails.",
        check=lambda value: False,
        type="always-fail",
    )
    config = Config(extensions=Extensions(custom_checks=[custom_check]))
    issues = check(properties, config=config)

    assert issues == []


def test_required_check_wildcard():
    properties = example_package_properties()
    id_check = RequiredCheck(
        jsonpath="$.*.id",
        message="All fields must have an id.",
    )
    config = Config(extensions=Extensions(required_checks=[id_check]))

    issues = check(properties, config=config)

    assert len(issues) == 8


def test_required_check_array_wildcard():
    properties = example_package_properties()
    properties["contributors"] = [
        {"path": "a/path"},
        {"path": "a/path"},
        {"path": "a/path", "name": "a name"},
    ]
    name_check = RequiredCheck(
        jsonpath="$.contributors[*].name",
        message="Contributor name is required.",
    )
    config = Config(extensions=Extensions(required_checks=[name_check]))
    issues = check(properties, config=config)

    assert issues == [
        Issue(
            jsonpath="$.contributors[0].name",
            type="required",
            message=name_check.message,
        ),
        Issue(
            jsonpath="$.contributors[1].name",
            type="required",
            message=name_check.message,
        ),
    ]


def test_required_check_union():
    properties = example_package_properties()
    del properties["licenses"]
    required_check = RequiredCheck(
        jsonpath="$['licenses', 'sources'] | $.resources[*]['licenses', 'sources']",
        message="Package and resources must have licenses and sources.",
    )
    config = Config(extensions=Extensions(required_checks=[required_check]))

    issues = check(properties, config=config)

    assert all(_map(issues, lambda issue: issue.type == "required"))
    assert _map(issues, lambda issue: issue.jsonpath) == [
        "$.licenses",
        "$.resources[0].licenses",
        "$.resources[0].sources",
        "$.sources",
    ]


def test_required_check_non_final_recursive_descent():
    properties = example_package_properties()
    properties["resources"][0]["licenses"] = [{"name": "odc-pddl"}]
    required_check = RequiredCheck(
        jsonpath="$..licenses[*].title",
        message="Licenses must have a title.",
    )
    config = Config(extensions=Extensions(required_checks=[required_check]))

    issues = check(properties, config=config)

    assert _map(issues, lambda issue: issue.jsonpath) == [
        "$.licenses[0].title",
        "$.resources[0].licenses[0].title",
    ]


def test_required_check_root():
    properties = example_package_properties()
    required_check = RequiredCheck(
        jsonpath="$",
        message="Package must have a root.",
    )
    config = Config(extensions=Extensions(required_checks=[required_check]))

    issues = check(properties, config=config)

    assert issues == []


@mark.parametrize(
    "jsonpath",
    [
        "<><>bad.path",
        "..*",
        "$..path",
        "..resources",
        "$.resources[0].*",
        "$.resources[*]",
        "$.no & $.intersection",
        "$.no & $.intersection | $.operator",
    ],
)
def test_required_check_cannot_apply_to_bad_or_ambiguous_path(jsonpath):
    with raises(ValueError):
        RequiredCheck(
            jsonpath=jsonpath,
            message="This should fail.",
        )


@mark.parametrize(
    "jsonpath",
    [
        "<><>bad.path",
        "$.no & $.intersection",
        "$.no & $.intersection | $.operator",
    ],
)
def test_custom_check_cannot_apply_to_bad_path(jsonpath):
    with raises(ValueError):
        CustomCheck(
            jsonpath=jsonpath,
            message="A message.",
            check=lambda _: True,
        )


def test_custom_check_cannot_be_type_required():
    with raises(ValueError):
        CustomCheck(
            jsonpath="$.name",
            message="A message.",
            check=lambda _: True,
            type="required",
        )
