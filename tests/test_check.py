from typing import Any

from pytest import mark, raises

from check_datapackage.check import DataPackageError, check
from check_datapackage.config import Config
from check_datapackage.constants import FIELD_TYPES
from check_datapackage.examples import (
    example_package_properties,
    example_resource_properties,
)
from check_datapackage.exclusion import Exclusion
from check_datapackage.extensions import Extensions, RequiredCheck
from check_datapackage.internals import _map
from tests.test_extensions import lowercase_check

# "MUST" checks


def test_passes_matching_properties_with_resources():
    """Should pass properties matching the schema."""
    properties = example_package_properties()

    assert check(properties) == []


def test_fails_properties_without_resources():
    """Should fail properties without resources."""
    properties = {"name": "a name with spaces"}

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "required"
    assert issues[0].jsonpath == "$.resources"


def test_fails_properties_with_empty_resources():
    """Should fail properties with an empty resources array."""
    properties: dict[str, Any] = {
        "name": "a name with spaces",
        "resources": [],
    }

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].jsonpath == "$.resources"


def test_fails_properties_with_bad_type():
    """Should fail properties with a field of the wrong type."""
    properties: dict[str, Any] = {
        "name": 123,
        "resources": [{"name": "a name", "path": "data.csv"}],
    }
    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.name"


def test_fails_properties_with_bad_format():
    """Should fail properties with a field of the wrong format."""
    properties: dict[str, Any] = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "homepage": "not a URL",
    }

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "format"
    assert issues[0].jsonpath == "$.homepage"


def test_fails_properties_with_pattern_mismatch():
    """Should fail properties with a field that does not match the pattern."""
    properties: dict[str, Any] = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "contributors": [{"path": "/a/bad/path"}],
    }

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "pattern"
    assert issues[0].jsonpath == "$.contributors[0].path"


@mark.parametrize("primary_key", ["id", ["id", "name"]])
def test_pass_good_primary_key(primary_key):
    properties = example_package_properties()
    properties["resources"][0]["schema"]["primaryKey"] = primary_key
    properties["resources"][0]["schema"]["fields"].extend(
        [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "string"},
        ]
    )

    issues = check(properties)

    assert issues == []


@mark.parametrize("primary_key", ["", "last_name", ["first_name", "last_name"]])
def test_fail_primary_key_with_unknown_fields(primary_key):
    properties = example_package_properties()
    properties["resources"][0]["schema"]["primaryKey"] = primary_key

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].jsonpath == "$.resources[0].schema.primaryKey"
    assert issues[0].type == "primary-key"
    assert issues[0].instance == primary_key


@mark.parametrize("primary_key", [None, 123, [], [123, "a_field"]])
def test_do_not_check_bad_primary_key_against_fields(primary_key):
    properties = example_package_properties()
    properties["resources"][0]["schema"]["primaryKey"] = primary_key

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type != "primary-key"


def test_do_not_check_primary_key_against_bad_field():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["primaryKey"] = "eye-colour"
    properties["resources"][0]["schema"]["fields"].append(
        # Bad name
        {"name": 123, "type": "integer"},
    )

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type != "primary-key"


# "SHOULD" checks


def test_passes_matching_properties_with_should():
    """Should pass properties matching "SHOULD" specifications."""
    properties: dict[str, Any] = {
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

    assert check(properties, config=Config(strict=True)) == []


def test_fails_properties_with_missing_required_fields_in_should():
    """Should fail properties with missing required properties in strict mode."""
    properties: dict[str, Any] = {
        "resources": [{"name": "a-name-with-no-spaces", "path": "data.csv"}],
    }

    issues = check(properties, config=Config(strict=True))

    assert len(issues) == 3
    assert all(issue.type == "required" for issue in issues)


def test_fails_properties_violating_should():
    """Should fail properties that do not meet "SHOULD" specifications."""
    properties: dict[str, Any] = {
        "name": "a name with spaces",
        "id": "123",
        "version": "not semver",
        "contributors": [{"email": "jane@doe.com"}],
        "sources": [{"email": "jane@doe.com"}],
        "licenses": [{"name": "a-license"}],
        "resources": [{"name": "a name with spaces", "path": "data.csv"}],
    }

    issues = check(properties, config=Config(strict=True))

    assert len(issues) == 5
    assert {issue.jsonpath for issue in issues} == {
        "$.name",
        "$.version",
        "$.contributors[0].title",
        "$.sources[0].title",
        "$.resources[0].name",
    }


def test_exclusion_does_not_exclude_custom_check():
    """Exclusion should not exclude custom check if types do not match."""
    properties = example_package_properties()
    properties["name"] = "ALLCAPS"
    del properties["resources"]
    exclusion_required = Exclusion(type="required")
    config = Config(
        extensions=Extensions(custom_checks=[lowercase_check]),
        exclusions=[exclusion_required],
    )

    issues = check(properties, config=config)

    assert len(issues) == 1
    assert issues[0].type == "lowercase"


def test_exclusion_does_exclude_custom_check():
    """Exclusion should exclude custom check if types match."""
    properties = example_package_properties()
    properties["name"] = "ALLCAPS"
    exclusion_lowercase = Exclusion(type=lowercase_check.type)
    config = Config(
        extensions=Extensions(custom_checks=[lowercase_check]),
        exclusions=[exclusion_lowercase],
    )

    issues = check(properties, config=config)

    assert issues == []


# Issues at $.resources[x]


def test_pass_with_resource_path_missing():
    properties = example_package_properties()
    properties["resources"][0]["data"] = [1, 2, 3]
    del properties["resources"][0]["path"]

    assert check(properties) == []


def test_fail_with_resource_name_path_and_data_missing():
    properties = example_package_properties()
    del properties["resources"][0]["name"]
    del properties["resources"][0]["path"]

    issues = check(properties)

    assert len(issues) == 2
    assert issues[0].jsonpath == "$.resources[0]"
    assert issues[0].type == "required"
    assert issues[1].jsonpath == "$.resources[0].name"
    assert issues[1].type == "required"


def test_fail_with_only_resource_name_missing():
    properties = example_package_properties()
    del properties["resources"][0]["name"]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].jsonpath == "$.resources[0].name"
    assert issues[0].type == "required"


def test_fail_with_multiple_resources():
    properties = example_package_properties()
    properties["resources"].append(example_resource_properties())
    del properties["resources"][0]["path"]
    del properties["resources"][1]["path"]

    issues = check(properties)

    assert len(issues) == 2
    assert issues[0].jsonpath == "$.resources[0]"
    assert issues[0].type == "required"
    assert issues[1].jsonpath == "$.resources[1]"
    assert issues[1].type == "required"


def test_fail_with_both_resource_path_and_data_present():
    properties = example_package_properties()
    properties["resources"][0]["data"] = [1, 2, 3]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "oneOf"


def test_fail_one_resource_pass_another():
    properties = example_package_properties()
    resource2 = example_resource_properties()
    properties["resources"].append(resource2)
    del properties["resources"][0]["path"]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "required"


# Issues at $.resources[x].path


@mark.parametrize(
    "path, location, type",
    [
        (123, "$.resources[0].path", "type"),
        ("/bad/path", "$.resources[0].path", "pattern"),
        ([], "$.resources[0].path", "minItems"),
        ([123], "$.resources[0].path[0]", "type"),
        (["/bad/path"], "$.resources[0].path[0]", "pattern"),
    ],
)
def test_fail_with_bad_resource_path(path, location, type):
    properties = example_package_properties()
    properties["resources"][0]["path"] = path

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == type
    assert issues[0].jsonpath == location


def test_fail_empty_field():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0] = {}

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "required"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].name"


def test_fail_field_of_bad_type():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0] = 123

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0]"


def test_fail_unknown_field():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0]["type"] = "unknown"

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "enum"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].type"


@mark.parametrize("type", FIELD_TYPES)
def test_fail_field_with_bad_property(type):
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0]["type"] = type
    properties["resources"][0]["schema"]["fields"][0]["title"] = 4

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].title"


def test_fail_field_with_bad_format():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0]["format"] = 4

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "enum"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].format"


def test_fail_unknown_field_with_bad_property():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0]["title"] = 4
    properties["resources"][0]["schema"]["fields"][0]["type"] = "unknown"

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "enum"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].type"


def test_fail_package_license_with_no_name_or_path():
    properties = example_package_properties()
    del properties["licenses"][0]["name"]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "required"
    assert issues[0].jsonpath == "$.licenses[0]"


def test_fail_resource_license_with_no_name_or_path():
    properties = example_package_properties()
    properties["resources"][0]["licenses"] = [{}]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "required"
    assert issues[0].jsonpath == "$.resources[0].licenses[0]"


def test_fail_field_with_non_unique_enum_values():
    """Fail a field whose enum array contains duplicate values."""
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0]["type"] = "number"
    properties["resources"][0]["schema"]["fields"][0]["constraints"] = {"enum": [1, 1]}

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "uniqueItems"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].constraints.enum"


def test_fail_unknown_field_with_bad_enum_constraint():
    """Fail a field whose enum constraint is the wrong type when the field's
    type is unknown."""
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0]["type"] = "unknown"
    properties["resources"][0]["schema"]["fields"][0]["constraints"] = {"enum": {}}

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "enum"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].type"


def test_fail_simple_field_with_bad_enum_constraint():
    """Fail a field whose enum values are the wrong type when enum values can
    have only one type."""
    properties = example_package_properties()
    # Expecting enum array to contain strings
    properties["resources"][0]["schema"]["fields"][0]["constraints"] = {"enum": [1]}

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].constraints.enum[0]"


def test_fail_complex_field_with_bad_enum_constraint():
    """Fail a field whose enum values are the wrong type when enum values can
    have multiple types."""
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0]["type"] = "number"
    # Expecting enum array to contain numbers or strings
    properties["resources"][0]["schema"]["fields"][0]["constraints"] = {
        "enum": [{}],
    }

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].constraints.enum"


def test_fail_field_with_mixed_type_enum_constraint():
    """Fail a field whose enum values are not all the same type."""
    properties = example_package_properties()
    properties["resources"][0]["schema"]["fields"][0]["type"] = "geopoint"
    properties["resources"][0]["schema"]["fields"][0]["constraints"] = {
        "enum": [{}, [], "string", 1],
    }

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.fields[0].constraints.enum"


def test_pass_good_foreign_keys():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["foreignKeys"] = [
        {
            "fields": "purchase",
            "reference": {
                "resource": "purchases",
                "fields": "purchase_id",
            },
        },
        {
            "fields": ["first_name", "last_name"],
            "reference": {
                "resource": "customers",
                "fields": ["first_name", "last_name"],
            },
        },
    ]

    issues = check(properties)

    assert issues == []


def test_fail_foreign_keys_of_bad_type():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["foreignKeys"] = 123

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.foreignKeys"


@mark.parametrize("ref_fields", ["purchase_id", ["purchase_id"], 123, []])
def test_fail_foreign_keys_with_missing_fields(ref_fields):
    properties = example_package_properties()
    properties["resources"][0]["schema"]["foreignKeys"] = [
        {
            # fields missing
            "reference": {
                "resource": "purchases",
                "fields": ref_fields,
            },
        },
    ]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "required"
    assert issues[0].jsonpath == "$.resources[0].schema.foreignKeys[0].fields"


@mark.parametrize("fields", [None, 123])
def test_fail_foreign_keys_with_bad_fields(fields):
    properties = example_package_properties()
    properties["resources"][0]["schema"]["foreignKeys"] = [
        {
            "fields": fields,
            "reference": {
                "fields": ["purchase_id"],
            },
        },
    ]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.foreignKeys[0].fields"


def test_fail_foreign_keys_with_bad_fields_while_keeping_other_issues():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["foreignKeys"] = [
        {
            "fields": 123,
            # reference.fields missing
            "reference": {"resource": 123},
        },
    ]

    issues = check(properties)

    assert len(issues) == 3
    assert _map(issues, lambda issue: issue.type) == ["type", "required", "type"]


@mark.parametrize(
    "fields, ref_fields",
    [
        ("purchase", ["purchase_id"]),
        (["purchase"], "purchase_id"),
    ],
)
def test_fail_foreign_keys_with_mismatched_types(fields, ref_fields):
    properties = example_package_properties()
    properties["resources"][0]["schema"]["foreignKeys"] = [
        {
            "fields": fields,
            "reference": {
                "fields": ref_fields,
            },
        },
    ]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.foreignKeys[0].reference.fields"


def test_fail_foreign_keys_with_bad_array():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["foreignKeys"] = [
        {
            "fields": ["first_name", "last_name"],
            "reference": {
                "resource": "customers",
                "fields": [],
            },
        }
    ]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "minItems"
    assert issues[0].jsonpath == "$.resources[0].schema.foreignKeys[0].reference.fields"


def test_fail_foreign_keys_with_bad_array_item():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["foreignKeys"] = [
        {
            "fields": ["first_name", 1],
            "reference": {
                "resource": "customers",
                "fields": ["first_name", 1],
            },
        }
    ]

    issues = check(properties)

    assert len(issues) == 2
    assert issues[0].type == "type"
    assert issues[1].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.foreignKeys[0].fields[1]"
    assert issues[1].jsonpath == (
        "$.resources[0].schema.foreignKeys[0].reference.fields[1]"
    )


def test_fail_primary_key_of_bad_type():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["primaryKey"] = 123

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.primaryKey"


def test_fail_primary_key_with_bad_array():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["primaryKey"] = []

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "minItems"
    assert issues[0].jsonpath == "$.resources[0].schema.primaryKey"


def test_fail_primary_key_with_bad_array_item():
    properties = example_package_properties()
    properties["resources"][0]["schema"]["primaryKey"] = [123, "name"]

    issues = check(properties)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.resources[0].schema.primaryKey[0]"


def test_error_as_true():
    properties = {
        "name": 123,
    }

    with raises(DataPackageError):
        check(properties, error=True)


def test_error_true_no_duplicate_issues():
    resources_required = RequiredCheck(
        jsonpath="$.resources",
        message="'resources' is a required property",
    )

    with raises(DataPackageError) as error:
        check(
            {},
            error=True,
            config=Config(extensions=Extensions(required_checks=[resources_required])),
        )

    assert str(error).count(resources_required.message) == 1
