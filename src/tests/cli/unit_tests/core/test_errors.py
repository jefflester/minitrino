"""Unit tests for error handling module.

Tests custom exception classes and error formatting.
"""

import pytest

from minitrino.core.errors import MinitrinoError, UserError


class TestMinitrinoError:
    """Test suite for MinitrinoError base exception."""

    def test_initialization_with_message(self):
        """Test MinitrinoError with a message."""
        error = MinitrinoError("Test error message")

        assert error.msg == "Test error message"
        assert str(error) == "Test error message"
        assert error.exit_code == 1  # Default exit code

    def test_initialization_empty(self):
        """Test MinitrinoError with empty message."""
        error = MinitrinoError()

        assert error.msg == ""
        assert str(error) == ""
        assert error.exit_code == 1

    def test_inheritance_from_exception(self):
        """Test that MinitrinoError is an Exception."""
        error = MinitrinoError("Test")

        assert isinstance(error, Exception)
        assert isinstance(error, MinitrinoError)

    def test_can_be_raised_and_caught(self):
        """Test that MinitrinoError can be raised and caught."""
        with pytest.raises(MinitrinoError) as exc_info:
            raise MinitrinoError("Test error")

        assert str(exc_info.value) == "Test error"
        assert exc_info.value.exit_code == 1

    def test_exit_code_is_class_attribute(self):
        """Test that exit_code is a class attribute."""
        assert MinitrinoError.exit_code == 1

        # Instances have access to it
        error = MinitrinoError("test")
        assert error.exit_code == 1


class TestUserError:
    """Test suite for UserError exception."""

    def test_initialization_with_message_only(self):
        """Test UserError with just a message."""
        error = UserError("User made an error")

        # UserError prepends "User error: " to the message
        assert "User error: User made an error" in str(error)
        assert error.exit_code == 2  # UserError has exit_code 2

    def test_initialization_with_hint(self):
        """Test UserError with a hint."""
        error = UserError("Invalid input", hint_msg="Try using --help")

        error_str = str(error)
        assert "User error: Invalid input" in error_str
        assert "Hint: Try using --help" in error_str
        assert error.exit_code == 2

    def test_initialization_empty_hint(self):
        """Test UserError with empty hint."""
        error = UserError("Error message", hint_msg="")

        # Empty hint should not add "Hint: " line
        error_str = str(error)
        assert "User error: Error message" in error_str
        assert "Hint:" not in error_str

    def test_initialization_empty(self):
        """Test UserError with no parameters."""
        error = UserError()

        assert "User error: " in str(error)
        assert error.exit_code == 2

    def test_inheritance_chain(self):
        """Test that UserError inherits from MinitrinoError."""
        error = UserError("Test")

        assert isinstance(error, Exception)
        assert isinstance(error, MinitrinoError)
        assert isinstance(error, UserError)

    def test_exit_code_is_class_attribute(self):
        """Test that UserError has exit_code 2."""
        assert UserError.exit_code == 2

        # Instances have access to it
        error = UserError("test")
        assert error.exit_code == 2

    def test_can_be_raised_and_caught_as_minitrino_error(self):
        """Test UserError can be caught as MinitrinoError."""
        with pytest.raises(MinitrinoError) as exc_info:
            raise UserError("User error", hint_msg="Fix this")

        error = exc_info.value
        assert isinstance(error, UserError)
        assert "User error: User error" in str(error)
        assert "Hint: Fix this" in str(error)

    def test_different_hints(self):
        """Test various hint formats."""
        test_cases = [
            ("", "User error: Error"),  # Empty hint
            ("Try --help", "Hint: Try --help"),
            (
                "Use 'minitrino provision' instead",
                "Hint: Use 'minitrino provision' instead",
            ),
        ]

        for hint_input, expected_content in test_cases:
            error = UserError("Error", hint_msg=hint_input)
            error_str = str(error)
            assert expected_content in error_str or hint_input == ""


class TestErrorUsagePatterns:
    """Test common usage patterns for error classes."""

    def test_error_chaining(self):
        """Test that errors can be chained with from."""
        original_error = ValueError("Original error")

        try:
            raise MinitrinoError("Wrapped error") from original_error
        except MinitrinoError as e:
            assert e.__cause__ == original_error

    def test_user_error_in_try_except(self):
        """Test typical try-except pattern with UserError."""

        def function_that_fails():
            raise UserError(
                "Invalid module name",
                hint_msg="Use 'minitrino modules' to see available modules",
            )

        try:
            function_that_fails()
            assert False, "Should have raised"
        except UserError as e:
            assert "Invalid module name" in str(e)
            assert "Use 'minitrino modules' to see available modules" in str(e)
            assert e.exit_code == 2

    def test_error_message_formatting(self):
        """Test that error messages handle various formats."""
        test_messages = [
            "Simple message",
            "Message with\nnewlines",
            "Message with 'quotes'",
            'Message with "double quotes"',
            "Message with special chars: @#$%",
            "",  # Empty message
        ]

        for msg in test_messages:
            error = MinitrinoError(msg)
            assert str(error) == msg
            assert error.msg == msg

    def test_user_error_formats_message(self):
        """Test that UserError formats messages correctly."""
        error = UserError("Something went wrong")
        assert str(error) == "User error: Something went wrong"

        error_with_hint = UserError("Bad input", hint_msg="Check the format")
        expected = "User error: Bad input\nHint: Check the format"
        assert str(error_with_hint) == expected

    def test_minitrino_error_str_method(self):
        """Test __str__ method returns msg attribute."""
        error = MinitrinoError("Custom message")
        assert str(error) == "Custom message"
        assert error.msg == "Custom message"
