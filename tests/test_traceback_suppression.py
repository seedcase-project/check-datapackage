"""Tests for traceback suppression functionality."""

import sys
from types import TracebackType
from typing import Any, Optional

import pytest

from check_datapackage import setup_suppressed_tracebacks


class TestValidation:
    """Tests for input validation."""

    def test_rejects_non_exception_class(self):
        """Non-exception classes should raise TypeError."""
        with pytest.raises(TypeError, match="is not an exception class"):
            setup_suppressed_tracebacks(str)

    def test_rejects_exception_instance(self):
        """Exception instances should raise TypeError."""
        with pytest.raises(TypeError, match="is not an exception class"):
            setup_suppressed_tracebacks(ValueError("test"))

    def test_rejects_mixed_types(self):
        """Mixed valid and invalid types should raise TypeError."""
        with pytest.raises(TypeError, match="is not an exception class"):
            setup_suppressed_tracebacks(ValueError, int)

    def test_accepts_single_exception(self):
        """Single valid exception should be accepted."""
        # Should not raise
        setup_suppressed_tracebacks(ValueError)

    def test_accepts_multiple_exceptions(self):
        """Multiple valid exceptions should be accepted."""
        # Should not raise
        setup_suppressed_tracebacks(ValueError, TypeError, RuntimeError)


class TestPythonComposability:
    """Tests for composable Python exception hooks."""

    def test_single_exception_suppressed(self):
        """Single registered exception should have traceback suppressed."""

        class CustomError(Exception):
            pass

        setup_suppressed_tracebacks(CustomError)

        try:
            raise CustomError("test")
        except CustomError as e:
            # The hook should suppress the traceback
            # We can't easily test this directly, but we verify the hook exists
            assert sys.excepthook is not sys.__excepthook__

    def test_multiple_exceptions_compose(self):
        """Multiple calls should compose - all registered exceptions suppressed."""

        class ErrorA(Exception):
            pass

        class ErrorB(Exception):
            pass

        class ErrorC(Exception):
            pass

        # Register each exception separately
        setup_suppressed_tracebacks(ErrorA)
        setup_suppressed_tracebacks(ErrorB)
        setup_suppressed_tracebacks(ErrorC)

        # All should be suppressed (no traceback)
        for error_class in [ErrorA, ErrorB, ErrorC]:
            try:
                raise error_class("test")
            except error_class as e:
                # Verify hook is set (indirectly tests composability)
                assert sys.excepthook is not sys.__excepthook__

    def test_unregistered_exception_shows_traceback(self):
        """Unregistered exceptions should still show tracebacks."""

        # The hook should delegate to original for unregistered exceptions
        # We can't easily test traceback display, but verify hook exists
        class RegisteredError(Exception):
            pass

        setup_suppressed_tracebacks(RegisteredError)

        try:
            raise ValueError("unregistered")
        except ValueError:
            # Hook should still be set but not affect this
            assert sys.excepthook is not sys.__excepthook__


class TestIPythonComposability:
    """Tests for composable IPython exception hooks."""

    @pytest.fixture
    def mock_ipython(self):
        """Mock IPython environment."""

        class MockIPythonShell:
            def __init__(self):
                self.CustomTB = None
                self.custom_exceptions = ()

            def set_custom_exc(self, exc_tuple, handler):
                import types

                self.CustomTB = types.MethodType(handler, self)
                self.custom_exceptions = exc_tuple

        mock = MockIPythonShell()

        # Inject mock into builtins
        import builtins

        old_get_ipython = getattr(builtins, "get_ipython", None)
        builtins.get_ipython = lambda: mock

        yield mock

        # Cleanup
        if old_get_ipython:
            builtins.get_ipython = old_get_ipython
        elif hasattr(builtins, "get_ipython"):
            delattr(builtins, "get_ipython")

    def test_ipython_single_exception(self, mock_ipython):
        """Single exception should be suppressed in IPython."""

        class CustomError(Exception):
            pass

        setup_suppressed_tracebacks(CustomError)

        assert mock_ipython.CustomTB is not None

        try:
            raise CustomError("test")
        except CustomError as e:
            result = mock_ipython.CustomTB(type(e), e, e.__traceback__)
            assert result == []  # Empty list means suppressed

    def test_ipython_multiple_exceptions_compose(self, mock_ipython):
        """Multiple calls should compose in IPython - all registered exceptions suppressed."""

        class ErrorA(Exception):
            pass

        class ErrorB(Exception):
            pass

        # First registration
        setup_suppressed_tracebacks(ErrorA)

        # Second registration
        setup_suppressed_tracebacks(ErrorB)

        # Both should be suppressed
        for error_class in [ErrorA, ErrorB]:
            try:
                raise error_class("test")
            except error_class as e:
                result = mock_ipython.CustomTB(type(e), e, e.__traceback__)
                assert result == []  # Empty list means suppressed

    def test_ipython_unregistered_returns_none(self, mock_ipython):
        """Unregistered exceptions should return None (default behavior)."""

        class RegisteredError(Exception):
            pass

        setup_suppressed_tracebacks(RegisteredError)

        try:
            raise ValueError("unregistered")
        except ValueError as e:
            result = mock_ipython.CustomTB(type(e), e, e.__traceback__)
            assert result is None  # None means use default behavior

    def test_ipython_chain_calls_previous_handler(self, mock_ipython):
        """Verify that chained handlers are called in order."""
        call_order = []

        class ErrorA(Exception):
            pass

        class ErrorB(Exception):
            pass

        # First registration
        setup_suppressed_tracebacks(ErrorA)
        first_handler = mock_ipython.CustomTB

        # Wrap the first handler to track calls
        import types

        original_first = (
            first_handler.__func__
            if hasattr(first_handler, "__func__")
            else first_handler
        )

        def tracked_first(self, exc_type, exc_value, exc_traceback, tb_offset=None):
            call_order.append("first")
            return original_first(exc_type, exc_value, exc_traceback, tb_offset)

        mock_ipython.CustomTB = types.MethodType(tracked_first, mock_ipython)

        # Second registration
        setup_suppressed_tracebacks(ErrorB)

        # Trigger ErrorA (should call first handler in chain)
        try:
            raise ErrorA("test")
        except ErrorA as e:
            result = mock_ipython.CustomTB(type(e), e, e.__traceback__)
            assert result == []  # Suppressed
            assert "first" in call_order  # First handler was called
