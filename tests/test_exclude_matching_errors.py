from check_datapackage.check_error import CheckError
from check_datapackage.check_error_matcher import CheckErrorMatcher
from check_datapackage.exclude_matching_errors import (
    exclude_matching_errors,
)

errors = [
    CheckError("'path' is a required property", "$.path", "required"),
    CheckError("'name' is a required property", "$.name", "required"),
    CheckError("123 is not of type 'string'", "$.resources[0].name", "type"),
    CheckError("pattern 'xyz' doesn't match", "$.created", "pattern"),
    CheckError("pattern 'xyz' doesn't match", "$.version", "pattern"),
]


def test_empty_matchers_have_no_effect():
    """An empty list as a list of matchers should have no effect."""
    assert exclude_matching_errors(errors, []) == errors


def test_not_matching_matchers_have_no_effect():
    """If no matchers match, no errors should be excluded."""
    assert (
        exclude_matching_errors(
            errors,
            [
                CheckErrorMatcher(validator="no-match"),
                CheckErrorMatcher(
                    validator="required", json_path="path", message="no match!"
                ),
                CheckErrorMatcher(
                    validator="type", json_path=r"\$no\.match", message="123 is not"
                ),
            ],
        )
        == errors
    )


def test_matched_errors_are_excluded():
    """If any matchers match, the error should be excluded."""
    assert (
        exclude_matching_errors(
            errors,
            [
                CheckErrorMatcher(json_path="name", validator="required"),
                CheckErrorMatcher(validator="pattern"),
                CheckErrorMatcher(validator="type"),
                CheckErrorMatcher(message="type 'string'"),
            ],
        )
        == errors[:1]
    )
