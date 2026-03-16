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


class TestValidation:
    """Tests for input validation."""

    def test_rejects_non_exception_class(self):
        """Non-exception classes should raise TypeError."""
        with pytest.raises(TypeError, match="is not an exception class"):
            setup_suppressed_tracebacks(str)  # type: ignore[arg-type]

    def test_rejects_exception_instance(self):
        """Exception instances should raise TypeError."""
        with pytest.raises(TypeError, match="is not an exception class"):
            setup_suppressed_tracebacks(ValueError("test"))  # type: ignore[arg-type]

    def test_rejects_mixed_types(self):
        """Mixed valid and invalid types should raise TypeError."""
        with pytest.raises(TypeError, match="is not an exception class"):
            setup_suppressed_tracebacks(ValueError, int)  # type: ignore[arg-type]

    def test_accepts_single_and_multiple_exceptions(self):
        """Single and multiple valid exceptions should be accepted."""
        original = sys.excepthook
        setup_suppressed_tracebacks(ValueError)
        first_hook = sys.excepthook
        assert first_hook is not original

        setup_suppressed_tracebacks(TypeError, RuntimeError)
        assert sys.excepthook is not first_hook


class TestHookBehavior:
    """Tests for the actual hook behavior."""

    def test_registered_exception_calls_pretty_print(self, capsys):
        """Registered exception should use pretty print, not traceback."""
        setup_suppressed_tracebacks(ValueError)

        sys.excepthook(ValueError, ValueError("test error message"), None)

        captured = capsys.readouterr()
        assert "ValueError" in captured.out
        assert "test error message" in captured.out

    def test_unregistered_exception_calls_original_hook(self):
        """Unregistered exception should delegate to original hook."""
        mock_original = MagicMock()
        sys.excepthook = mock_original
        setup_suppressed_tracebacks(ValueError)

        sys.excepthook(TypeError, TypeError("unregistered error"), None)

        mock_original.assert_called_once_with(TypeError, ANY, None)

    def test_exception_subclass_is_suppressed(self, capsys):
        """Subclass of registered exception should also be suppressed."""

        class MyValueError(ValueError):
            pass

        setup_suppressed_tracebacks(ValueError)

        sys.excepthook(MyValueError, MyValueError("subclass error"), None)

        captured = capsys.readouterr()
        assert "MyValueError" in captured.out
        assert "subclass error" in captured.out

    def test_parent_not_suppressed_when_only_child_registered(self):
        """Parent exception should not be suppressed when only child is registered."""

        class ChildError(Exception):
            pass

        mock_original = MagicMock()
        sys.excepthook = mock_original
        setup_suppressed_tracebacks(ChildError)

        sys.excepthook(Exception, Exception("parent error"), None)

        mock_original.assert_called_once_with(Exception, ANY, None)


class TestComposition:
    """Tests for hook composability."""

    def test_multiple_registrations_compose(self):
        """Multiple calls should compose - all registered exceptions handled."""

        class ErrorA(Exception):
            pass

        class ErrorB(Exception):
            pass

        class ErrorC(Exception):
            pass

        mock_original = MagicMock()
        sys.excepthook = mock_original
        setup_suppressed_tracebacks(ErrorA)
        setup_suppressed_tracebacks(ErrorB)
        setup_suppressed_tracebacks(ErrorC)

        sys.excepthook(ErrorA, ErrorA("a"), None)
        sys.excepthook(ErrorB, ErrorB("b"), None)
        sys.excepthook(ErrorC, ErrorC("c"), None)
        sys.excepthook(ValueError, ValueError("other"), None)

        assert mock_original.call_count == 1
        args = mock_original.call_args[0]
        assert args[0] is ValueError

    def test_re_registering_same_exception(self, capsys):
        """Re-registering same exception type should work correctly."""
        setup_suppressed_tracebacks(ValueError)
        setup_suppressed_tracebacks(ValueError)

        sys.excepthook(ValueError, ValueError("test"), None)

        captured = capsys.readouterr()
        assert "ValueError" in captured.out


class TestIPythonHooks:
    """Tests for IPython exception hooks."""

    def test_ipython_hook_suppresses_registered(self):
        """IPython hook should suppress registered exceptions."""

        class CustomError(Exception):
            pass

        mock_shell = MagicMock()
        mock_shell.CustomTB = None

        with patch(
            "check_datapackage.check._is_running_from_ipython", return_value=True
        ):
            with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
                setup_suppressed_tracebacks(CustomError)

        mock_shell.set_custom_exc.assert_called_once()
        ipython_hook = mock_shell.set_custom_exc.call_args[0][1]

        result = ipython_hook(mock_shell, CustomError, CustomError("test"), None)

        assert result == []

    def test_ipython_hook_delegates_unregistered(self):
        """IPython hook should delegate unregistered exceptions."""

        class RegisteredError(Exception):
            pass

        mock_shell = MagicMock()
        mock_shell.CustomTB = None

        with patch(
            "check_datapackage.check._is_running_from_ipython", return_value=True
        ):
            with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
                setup_suppressed_tracebacks(RegisteredError)

        ipython_hook = mock_shell.set_custom_exc.call_args[0][1]

        result = ipython_hook(mock_shell, ValueError, ValueError("unregistered"), None)

        assert result is None

    def test_ipython_hook_composes_with_existing(self):
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

        with patch(
            "check_datapackage.check._is_running_from_ipython", return_value=True
        ):
            with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
                setup_suppressed_tracebacks(ErrorA)

        first_hook = mock_shell.set_custom_exc.call_args[0][1]
        mock_shell.CustomTB = first_hook

        with patch(
            "check_datapackage.check._is_running_from_ipython", return_value=True
        ):
            with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
                setup_suppressed_tracebacks(ErrorB)

        second_hook = mock_shell.set_custom_exc.call_args[0][1]
        mock_shell.CustomTB = second_hook

        with patch(
            "check_datapackage.check._is_running_from_ipython", return_value=True
        ):
            with patch.dict(builtins.__dict__, {"get_ipython": lambda: mock_shell}):
                setup_suppressed_tracebacks(ErrorC)

        third_hook = mock_shell.set_custom_exc.call_args[0][1]

        assert third_hook(mock_shell, ErrorA, ErrorA("a"), None) == []
        assert third_hook(mock_shell, ErrorB, ErrorB("b"), None) == []
        assert third_hook(mock_shell, ErrorC, ErrorC("c"), None) == []
        assert third_hook(mock_shell, ValueError, ValueError("other"), None) == [
            "old output"
        ]


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_none_traceback(self, capsys):
        """Hook should handle None traceback gracefully."""
        setup_suppressed_tracebacks(ValueError)

        sys.excepthook(ValueError, ValueError("test"), None)

        captured = capsys.readouterr()
        assert "ValueError" in captured.out

    def test_exception_with_complex_message(self, capsys):
        """Hook should handle exceptions with complex messages."""
        setup_suppressed_tracebacks(ValueError)

        complex_msg = "Error with 'quotes' and \"double quotes\" and\nnewlines"
        sys.excepthook(ValueError, ValueError(complex_msg), None)

        captured = capsys.readouterr()
        assert "ValueError" in captured.out
        assert "quotes" in captured.out

    def test_base_exception_not_suppressed_by_default(self):
        """BaseException should not be suppressed unless explicitly registered."""
        mock_original = MagicMock()
        sys.excepthook = mock_original
        setup_suppressed_tracebacks(ValueError)

        sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)

        mock_original.assert_called_once()

    def test_can_suppress_base_exception_if_registered(self, capsys):
        """BaseException can be suppressed if explicitly registered."""
        setup_suppressed_tracebacks(KeyboardInterrupt)

        sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)

        captured = capsys.readouterr()
        assert "KeyboardInterrupt" in captured.out
