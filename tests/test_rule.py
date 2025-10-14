from pytest import mark, raises

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.examples import (
    example_package_descriptor,
    example_resource_descriptor,
)
from check_datapackage.issue import Issue
from check_datapackage.rule import RequiredRule, Rule

lowercase_rule = Rule(
    jsonpath="$.name",
    message="Name must be lowercase.",
    check=lambda name: name.islower(),
    type="lowercase",
)
resource_name_rule = Rule(
    jsonpath="$.resources[*].name",
    message="Resource name must start with 'woolly'.",
    check=lambda name: name.startswith("woolly"),
    type="resource-name",
)


def test_direct_jsonpath():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    config = Config(rules=[lowercase_rule])
    issues = check(descriptor, config=config)

    assert issues == [
        Issue(
            jsonpath=lowercase_rule.jsonpath,
            type=lowercase_rule.type,
            message=lowercase_rule.message,
        )
    ]


def test_indirect_jsonpath():
    descriptor = example_package_descriptor()
    descriptor["resources"].append(example_resource_descriptor())
    descriptor["resources"][1]["name"] = "not starting with woolly"

    config = Config(rules=[resource_name_rule])
    issues = check(descriptor, config=config)

    assert issues == [
        Issue(
            jsonpath="$.resources[1].name",
            type=resource_name_rule.type,
            message=resource_name_rule.message,
        ),
    ]


def test_multiple_rules():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    descriptor["resources"][0]["name"] = "not starting with woolly"
    del descriptor["version"]

    version_rule = RequiredRule(
        jsonpath="$.version",
        message="Version is required.",
    )

    config = Config(
        rules=[
            lowercase_rule,
            resource_name_rule,
            version_rule,
        ]
    )
    issues = check(descriptor, config=config)

    assert issues == [
        Issue(
            jsonpath=lowercase_rule.jsonpath,
            type=lowercase_rule.type,
            message=lowercase_rule.message,
        ),
        Issue(
            jsonpath="$.resources[0].name",
            type=resource_name_rule.type,
            message=resource_name_rule.message,
        ),
        Issue(
            jsonpath=version_rule.jsonpath,
            type="required",
            message=version_rule.message,
        ),
    ]


def test_rules_and_default_checks():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    del descriptor["resources"]
    config = Config(rules=[lowercase_rule])
    issues = check(descriptor, config=config)

    assert [issue.type for issue in issues] == ["lowercase", "required"]


def test_no_matching_jsonpath():
    descriptor = example_package_descriptor()
    rule = Rule(
        jsonpath="$.missing",
        message="This check always fails.",
        check=lambda value: False,
        type="always-fail",
    )
    config = Config(rules=[rule])
    issues = check(descriptor, config=config)

    assert issues == []


def test_required_rule_wildcard():
    descriptor = example_package_descriptor()
    rule = RequiredRule(
        jsonpath="$.*.id",
        message="All fields must have an id.",
    )
    config = Config(rules=[rule])

    issues = check(descriptor, config=config)

    assert len(issues) == 8


def test_required_rule_array_wildcard():
    descriptor = example_package_descriptor()
    descriptor["contributors"] = [
        {"path": "a/path"},
        {"path": "a/path"},
        {"path": "a/path", "name": "a name"},
    ]
    rule = RequiredRule(
        jsonpath="$.contributors[*].name",
        message="Contributor name is required.",
    )
    config = Config(rules=[rule])
    issues = check(descriptor, config=config)

    assert issues == [
        Issue(
            jsonpath="$.contributors[0].name",
            type=rule.type,
            message=rule.message,
        ),
        Issue(
            jsonpath="$.contributors[1].name",
            type=rule.type,
            message=rule.message,
        ),
    ]


@mark.parametrize(
    "jsonpath",
    [
        "$",
        "..*",
        "created",
        "$..path",
        "..resources",
        "$.resources[0].*",
        "$.resources[*]",
    ],
)
def test_required_rule_cannot_apply_to_ambiguous_path(jsonpath):
    with raises(ValueError):
        RequiredRule(
            jsonpath=jsonpath,
            message="This should fail.",
        )
