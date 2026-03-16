"""Tests for traceback suppression functionality."""

import builtins
import sys
from unittest.mock import ANY, MagicMock, patch

import pytest

from check_datapackage import setup_suppressed_tracebacks


@pytest.fixture(autouse=True)
def reset_excepthook():
    """Reset sys.excepthook to its default before each test.

    Without this, hooks accumulate across tests because setup_suppressed_tracebacks
    composes on top of whatever is currently in sys.excepthook. A test that relies on
    asserting specific output or delegation counts would otherwise be affected by
    registrations from prior tests.
    """
    sys.excepthook = sys.__excepthook__
    yield


# Input Validation ====


def test_rejects_non_exception_class():
    """Non-exception classes should raise TypeError."""
    with pytest.raises(TypeError, match="is not an exception class"):
        setup_suppressed_tracebacks(str)  # type: ignore[arg-type]


def test_rejects_exception_instance():
    """Exception instances should raise TypeError."""
    with pytest.raises(TypeError, match="is not an exception class"):
        setup_suppressed_tracebacks(ValueError("test"))  # type: ignore[arg-type]


def test_rejects_mixed_types():
    """Mixed valid and invalid types should raise TypeError."""
    with pytest.raises(TypeError, match="is not an exception class"):
        setup_suppressed_tracebacks(ValueError, int)  # type: ignore[arg-type]


def test_accepts_single_and_multiple_exceptions(capsys):
    """Single and multiple valid exceptions should be accepted and suppressed."""
    setup_suppressed_tracebacks(ValueError)
    sys.excepthook(ValueError, ValueError("a"), None)
    assert "ValueError" in capsys.readouterr().out

    setup_suppressed_tracebacks(TypeError, RuntimeError)
    sys.excepthook(TypeError, TypeError("b"), None)
    assert "TypeError" in capsys.readouterr().out
    sys.excepthook(RuntimeError, RuntimeError("c"), None)
    assert "RuntimeError" in capsys.readouterr().out


# Hook Behavior ====


def test_registered_exception_calls_pretty_print(capsys):
    """Registered exception should use pretty print, not traceback."""
    setup_suppressed_tracebacks(ValueError)

    sys.excepthook(ValueError, ValueError("test error message"), None)

    captured = capsys.readouterr()
    assert "ValueError" in captured.out
    assert "test error message" in captured.out


def test_unregistered_exception_not_suppressed():
    """Unregistered exception should delegate to original hook."""
    mock_original = MagicMock()
    sys.excepthook = mock_original
    setup_suppressed_tracebacks(ValueError)

    sys.excepthook(TypeError, TypeError("unregistered error"), None)

    mock_original.assert_called_once_with(TypeError, ANY, None)


def test_exception_subclass_is_suppressed(capsys):
    """Subclass of registered exception should also be suppressed."""

    class SubclassError(Exception):
        pass

    setup_suppressed_tracebacks(Exception)

    sys.excepthook(SubclassError, SubclassError("error from subclass"), None)

    captured = capsys.readouterr()
    assert "SubclassError" in captured.out
    assert "error from subclass" in captured.out


def test_parent_not_suppressed_when_only_subclass_registered():
    """Parent exception should not be suppressed when only child is registered."""

    class SubclassError(Exception):
        pass

    mock_original = MagicMock()
    sys.excepthook = mock_original
    setup_suppressed_tracebacks(SubclassError)

    sys.excepthook(Exception, Exception("parent error"), None)

    mock_original.assert_called_once_with(Exception, ANY, None)


# Exception omposition ====


def test_multiple_registrations_compose(capsys):
    """Multiple calls should compose - all registered exceptions suppressed."""

    class ErrorA(Exception):
        pass

    class ErrorB(Exception):
        pass

    class ErrorC(Exception):
        pass

    setup_suppressed_tracebacks(ErrorA)
    setup_suppressed_tracebacks(ErrorB)
    setup_suppressed_tracebacks(ErrorC)

    # When a traceback is suppressed, the exception is pretty printed to stdout
    # leaving stderr empty. If the traceback is not suppressed, the exception
    # is delegated to the original hook which outputs to stderr leaving stdout
    # empty instead.
    sys.excepthook(ErrorA, ErrorA("a"), None)
    captured = capsys.readouterr()
    assert "ErrorA" in captured.out
    assert captured.err == ""

    sys.excepthook(ErrorB, ErrorB("b"), None)
    captured = capsys.readouterr()
    assert "ErrorB" in captured.out
    assert captured.err == ""

    sys.excepthook(ErrorC, ErrorC("c"), None)
    captured = capsys.readouterr()
    assert "ErrorC" in captured.out
    assert captured.err == ""


def test_re_registering_same_exception(capsys):
    """Re-registering same exception type should work correctly."""
    setup_suppressed_tracebacks(ValueError)
    setup_suppressed_tracebacks(ValueError)

    sys.excepthook(ValueError, ValueError("test"), None)

    captured = capsys.readouterr()
    assert "ValueError" in captured.out


# IPython exception handling ====


def test_ipython_hook_suppresses_registered():
    """IPython hook should suppress registered exceptions."""

    class CustomError(Exception):
        pass

    mock_shell = MagicMock()
    mock_shell.CustomTB = None

    with patch("check_datapackage.check._is_running_from_ipython", return_value=True):
        with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
            setup_suppressed_tracebacks(CustomError)

    mock_shell.set_custom_exc.assert_called_once()
    ipython_hook = mock_shell.set_custom_exc.call_args[0][1]

    result = ipython_hook(mock_shell, CustomError, CustomError("test"), None)

    assert result == []


def test_ipython_hook_delegates_unregistered():
    """IPython hook should delegate unregistered exceptions."""

    class RegisteredError(Exception):
        pass

    mock_shell = MagicMock()
    mock_shell.CustomTB = None

    with patch("check_datapackage.check._is_running_from_ipython", return_value=True):
        with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
            setup_suppressed_tracebacks(RegisteredError)

    ipython_hook = mock_shell.set_custom_exc.call_args[0][1]

    result = ipython_hook(mock_shell, ValueError, ValueError("unregistered"), None)

    assert result is None


def test_ipython_hook_composes_with_existing():
    """IPython hook should compose with existing custom handlers."""

    class ErrorA(Exception):
        pass

    class ErrorB(Exception):
        pass

    class ErrorC(Exception):
        pass

    old_handler = MagicMock(return_value=["old output"])
    mock_shell = MagicMock()
    mock_shell.CustomTB = old_handler

    with patch("check_datapackage.check._is_running_from_ipython", return_value=True):
        with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
            setup_suppressed_tracebacks(ErrorA)

    first_hook = mock_shell.set_custom_exc.call_args[0][1]
    mock_shell.CustomTB = first_hook

    with patch("check_datapackage.check._is_running_from_ipython", return_value=True):
        with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
            setup_suppressed_tracebacks(ErrorB)

    second_hook = mock_shell.set_custom_exc.call_args[0][1]
    mock_shell.CustomTB = second_hook

    with patch("check_datapackage.check._is_running_from_ipython", return_value=True):
        with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
            setup_suppressed_tracebacks(ErrorC)

    third_hook = mock_shell.set_custom_exc.call_args[0][1]

    assert third_hook(mock_shell, ErrorA, ErrorA("a"), None) == []
    assert third_hook(mock_shell, ErrorB, ErrorB("b"), None) == []
    assert third_hook(mock_shell, ErrorC, ErrorC("c"), None) == []
    assert third_hook(mock_shell, ValueError, ValueError("other"), None) == [
        "old output"
    ]
