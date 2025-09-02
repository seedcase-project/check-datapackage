from pytest import mark

from check_datapackage.check_error import CheckError
from check_datapackage.check_error_matcher import CheckErrorMatcher


@mark.parametrize(
    "message,matcher,expected",
    [
        ("", "", True),
        ("Match!", None, True),
        ("Match!", "", True),
        ("Complete match", "Complete match", True),
        ("Beginning matches", "Beginning", True),
        ("End matches", "d matches", True),
        ("", "No match", False),
        ("No match", "something else", False),
    ],
)
def test_matches_message(message, matcher, expected):
    """Should match if the matcher's message is a substring of the error's message."""
    assert (
        CheckErrorMatcher(message=matcher).matches(
            CheckError(message=message, json_path="$.name", validator="")
        )
        is expected
    )


@mark.parametrize(
    "json_path,matcher,expected",
    [
        ("$.match", None, True),
        ("$.match", "", True),
        ("", "", True),
        ("$.same", r"\$\.same", True),
        ("$.start.match", r"\$\.start", True),
        ("$.start.match", r"^\$\.start", True),
        ("$.match.end", "end", True),
        ("$.match.end", r"end$", True),
        ("$.match.middle.match", "middle", True),
        ("$.match.list[999].match", r"list\[\d+\]", True),
        ("$.not.last.field", r"\.last$", False),
        ("$.not.first.field", r"^\$\.first", False),
        ("$.no.match", "other", False),
    ],
)
def test_matches_json_path(json_path, matcher, expected):
    """Should match if the regular expression in the matcher's `json_path` matches the
    `json_path` of the error."""
    assert (
        CheckErrorMatcher(json_path=matcher).matches(
            CheckError(message="Hello", json_path=json_path, validator="")
        )
        is expected
    )


@mark.parametrize(
    "validator,matcher,expected",
    [
        ("match", None, True),
        ("match", "match", True),
        ("", "", True),
        ("no-match", "match", False),
        ("no-match", "", False),
        ("", "no-match", False),
    ],
)
def test_matches_validator(validator, matcher, expected):
    """Should match if the matcher's validator is the same as the error's."""
    assert (
        CheckErrorMatcher(validator=matcher).matches(
            CheckError(message="Hello", json_path="", validator=validator)
        )
        is expected
    )


@mark.parametrize(
    "message,json_path,validator,expected",
    [
        ("name' is a", "name", "required", True),
        ("name' is a", "name", "no-match", False),
        ("name' is a", r"no\.match", "required", False),
        ("no match", "name", "required", False),
        ("no match", "name", "no-match", False),
        ("no match", r"no\.match", "no-match", False),
    ],
)
def test_matches_on_all_fields(message, json_path, validator, expected):
    """Should only match if all fields match."""
    assert (
        CheckErrorMatcher(
            message=message, json_path=json_path, validator=validator
        ).matches(
            CheckError(
                message="'name' is a required property",
                json_path="$.name",
                validator="required",
            )
        )
        is expected
    )
