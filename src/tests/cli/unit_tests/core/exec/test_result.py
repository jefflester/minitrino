"""Unit tests for command execution result module.

Tests the CommandResult dataclass.
"""

from minitrino.core.exec.result import CommandResult


class TestCommandResult:
    """Test suite for CommandResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful command result."""
        result = CommandResult(exit_code=0, output="Command succeeded", error="")

        assert result.exit_code == 0
        assert result.output == "Command succeeded"
        assert result.error == ""

    def test_failed_result(self):
        """Test creating a failed command result."""
        result = CommandResult(exit_code=1, output="", error="Command failed")

        assert result.exit_code == 1
        assert result.output == ""
        assert result.error == "Command failed"

    def test_result_with_both_output_and_error(self):
        """Test result with both output and error."""
        result = CommandResult(exit_code=0, output="Some output", error="Some warnings")

        assert result.exit_code == 0
        assert result.output == "Some output"
        assert result.error == "Some warnings"

    def test_result_with_non_zero_exit_codes(self):
        """Test various non-zero exit codes."""
        test_codes = [1, 2, 127, 255, -1]

        for code in test_codes:
            result = CommandResult(exit_code=code, output="", error="")
            assert result.exit_code == code

    def test_result_with_multiline_output(self):
        """Test result with multiline output."""
        output = "Line 1\nLine 2\nLine 3"
        error = "Error line 1\nError line 2"

        result = CommandResult(exit_code=0, output=output, error=error)

        assert result.output == output
        assert result.error == error
        assert "\n" in result.output
        assert "\n" in result.error

    def test_result_with_empty_strings(self):
        """Test result with empty strings."""
        result = CommandResult(exit_code=0, output="", error="")

        assert result.exit_code == 0
        assert result.output == ""
        assert result.error == ""

    def test_result_immutability(self):
        """Test that CommandResult fields can be modified (not frozen)."""
        result = CommandResult(exit_code=0, output="original", error="")

        # Should be able to modify fields (dataclass not frozen)
        result.exit_code = 1
        result.output = "modified"

        assert result.exit_code == 1
        assert result.output == "modified"

    def test_result_equality(self):
        """Test equality comparison between CommandResult instances."""
        result1 = CommandResult(exit_code=0, output="test", error="")
        result2 = CommandResult(exit_code=0, output="test", error="")
        result3 = CommandResult(exit_code=1, output="test", error="")

        assert result1 == result2
        assert result1 != result3

    def test_result_string_representation(self):
        """Test string representation of CommandResult."""
        result = CommandResult(exit_code=0, output="output", error="error")

        str_repr = str(result)
        assert "CommandResult" in str_repr
        assert "exit_code=0" in str_repr
        assert "output=" in str_repr
        assert "error=" in str_repr

    def test_result_with_none_values(self):
        """Test handling of None values (if allowed)."""
        # This might raise an error depending on the implementation
        try:
            result = CommandResult(exit_code=0, output=None, error=None)
            # If it doesn't raise, check the values
            assert result.exit_code == 0
            assert result.output is None
            assert result.error is None
        except TypeError:
            # If None is not allowed, that's also valid
            pass
