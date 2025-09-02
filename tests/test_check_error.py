from pytest import mark, raises

from check_datapackage.check_error import CheckError

check_error = CheckError(
    message="There was an error!", json_path="a.b.field", validator="a-validator"
)


def test_error_stringified_correctly():
    """Should stringify error correctly."""
    assert (
        str(check_error)
        == "Error at `a.b.field` caused by `a-validator`: There was an error!"
    )


def test_error_represented_correctly():
    """Should generate the developer-friendly representation correctly."""
    assert repr(check_error) == (
        "CheckError(message='There was an error!', json_path='a.b.field', "
        "validator='a-validator')"
    )


@mark.parametrize(
    "error, other, expected",
    [
        (CheckError("msg1", "path1", "v1"), CheckError("msg1", "path1", "v1"), True),
        (CheckError("msg1", "path1", "v1"), CheckError("msg2", "path1", "v1"), False),
        (CheckError("msg1", "path1", "v1"), CheckError("msg1", "path2", "v1"), False),
        (CheckError("msg1", "path1", "v1"), CheckError("msg1", "path1", "v2"), False),
        (CheckError("msg1", "path1", "v1"), None, False),
        (CheckError("msg1", "path1", "v1"), "not a CheckError", False),
    ],
)
def test_equality_checked_correctly(error, other, expected):
    """Should compare errors for equality correctly."""
    assert (error == other) is expected
    assert (other == error) is expected


@mark.parametrize(
    "error, other, expected",
    [
        (CheckError("msg A", "path1", "v1"), CheckError("msg A", "path2", "v1"), True),
        (CheckError("msg A", "path1", "v1"), CheckError("msg A", "path1", "v2"), True),
        (CheckError("msg A", "path1", "v1"), CheckError("msg B", "path1", "v1"), True),
        (CheckError("msg A", "path2", "v1"), CheckError("msg A", "path1", "v1"), False),
        (CheckError("msg A", "path1", "v2"), CheckError("msg A", "path1", "v1"), False),
        (CheckError("msg B", "path1", "v1"), CheckError("msg A", "path1", "v1"), False),
    ],
)
def test_lt_checked_correctly_for_different_errors(error, other, expected):
    """Should find the smaller (the one that comes first) of two different errors."""
    assert (error < other) is expected
    assert (other < error) is not expected


def test_lt_checked_correctly_for_same_error():
    """Should not consider an error smaller than itself."""
    assert not (check_error < check_error)


@mark.parametrize(
    "error, other",
    [
        (CheckError("msg", "path", "val"), None),
        (CheckError("msg", "path", "val"), "not a CheckError"),
    ],
)
def test_lt_raises_error_for_wrong_type(error, other):
    """Should raise an error when comparing an error with an object of a different
    type."""
    with raises(TypeError):
        error < other
