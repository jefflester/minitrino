"""Unit tests for ANSI escape sequence stripping.

Tests the strip_ansi function for removing ANSI codes from strings.
"""

from minitrino import ansi


class TestStripAnsi:
    """Test suite for strip_ansi function."""

    def test_strip_ansi_with_no_codes(self):
        """Test stripping plain text without ANSI codes."""
        plain_text = "This is plain text"
        result = ansi.strip_ansi(plain_text)
        assert result == plain_text

    def test_strip_ansi_with_color_codes(self):
        """Test stripping ANSI color codes."""
        # Red text
        colored = "\x1b[31mRed Text\x1b[0m"
        result = ansi.strip_ansi(colored)
        assert result == "Red Text"

        # Bold green text
        colored = "\x1b[1m\x1b[32mBold Green\x1b[0m"
        result = ansi.strip_ansi(colored)
        assert result == "Bold Green"

    def test_strip_ansi_with_cursor_movement(self):
        """Test stripping ANSI cursor movement codes."""
        # Cursor up
        text = "Line 1\x1b[1ALine 2"
        result = ansi.strip_ansi(text)
        assert result == "Line 1Line 2"

        # Cursor down, forward, backward
        text = "Text\x1b[2B\x1b[3C\x1b[4DMore"
        result = ansi.strip_ansi(text)
        assert result == "TextMore"

    def test_strip_ansi_with_clear_codes(self):
        """Test stripping ANSI clear screen/line codes."""
        # Clear screen
        text = "Before\x1b[2JAfter"
        result = ansi.strip_ansi(text)
        assert result == "BeforeAfter"

        # Clear line
        text = "Start\x1b[KEnd"
        result = ansi.strip_ansi(text)
        assert result == "StartEnd"

    def test_strip_ansi_with_multiple_codes(self):
        """Test stripping multiple ANSI codes in one string."""
        complex_text = "\x1b[1m\x1b[31mBold Red\x1b[0m Normal \x1b[32mGreen\x1b[0m"
        result = ansi.strip_ansi(complex_text)
        assert result == "Bold Red Normal Green"

    def test_strip_ansi_with_256_colors(self):
        """Test stripping 256-color ANSI codes."""
        # Foreground 256 color
        text = "\x1b[38;5;196mRed 256\x1b[0m"
        result = ansi.strip_ansi(text)
        assert result == "Red 256"

        # Background 256 color
        text = "\x1b[48;5;21mBlue Background\x1b[0m"
        result = ansi.strip_ansi(text)
        assert result == "Blue Background"

    def test_strip_ansi_with_rgb_colors(self):
        """Test stripping RGB (24-bit) color codes."""
        # RGB foreground
        text = "\x1b[38;2;255;0;0mRGB Red\x1b[0m"
        result = ansi.strip_ansi(text)
        assert result == "RGB Red"

        # RGB background
        text = "\x1b[48;2;0;255;0mRGB Green BG\x1b[0m"
        result = ansi.strip_ansi(text)
        assert result == "RGB Green BG"

    def test_strip_ansi_empty_string(self):
        """Test stripping empty string."""
        result = ansi.strip_ansi("")
        assert result == ""

    def test_strip_ansi_default_parameter(self):
        """Test strip_ansi with no parameter (default empty string)."""
        result = ansi.strip_ansi()
        assert result == ""

    def test_strip_ansi_with_text_attributes(self):
        """Test stripping text attribute codes."""
        # Bold
        text = "\x1b[1mBold\x1b[22m"
        result = ansi.strip_ansi(text)
        assert result == "Bold"

        # Italic
        text = "\x1b[3mItalic\x1b[23m"
        result = ansi.strip_ansi(text)
        assert result == "Italic"

        # Underline
        text = "\x1b[4mUnderline\x1b[24m"
        result = ansi.strip_ansi(text)
        assert result == "Underline"

    def test_strip_ansi_preserves_newlines(self):
        """Test that newlines are preserved."""
        text = "Line 1\n\x1b[31mLine 2\x1b[0m\nLine 3"
        result = ansi.strip_ansi(text)
        assert result == "Line 1\nLine 2\nLine 3"

    def test_strip_ansi_preserves_tabs(self):
        """Test that tabs are preserved."""
        text = "Col1\t\x1b[32mCol2\x1b[0m\tCol3"
        result = ansi.strip_ansi(text)
        assert result == "Col1\tCol2\tCol3"

    def test_strip_ansi_with_save_restore_cursor(self):
        """Test stripping save/restore cursor position codes."""
        text = "Text\x1b[sMore\x1b[uEnd"
        result = ansi.strip_ansi(text)
        assert result == "TextMoreEnd"

    def test_strip_ansi_with_alternate_screen(self):
        """Test stripping alternate screen buffer codes."""
        # Switch to alternate screen
        text = "\x1b[?1049hAlternate Screen\x1b[?1049l"
        result = ansi.strip_ansi(text)
        assert result == "Alternate Screen"

    def test_strip_ansi_with_terminal_title(self):
        """Test stripping terminal title sequences."""
        # OSC sequence for terminal title
        text = "\x1b]0;Terminal Title\x07Rest of text"
        result = ansi.strip_ansi(text)
        assert result == "Rest of text"

    def test_strip_ansi_with_hyperlinks(self):
        """Test stripping hyperlink ANSI sequences."""
        # OSC 8 hyperlink
        text = "\x1b]8;;http://example.com\x1b\\Link Text\x1b]8;;\x1b\\"
        result = ansi.strip_ansi(text)
        assert result == "Link Text"

    def test_strip_ansi_unicode_text(self):
        """Test that Unicode text is preserved."""
        text = "\x1b[31m你好\x1b[0m 世界 🌍"
        result = ansi.strip_ansi(text)
        assert result == "你好 世界 🌍"

    def test_strip_ansi_mixed_escape_formats(self):
        """Test stripping various escape sequence formats."""
        # CSI, OSC, and other formats mixed
        text = "\x1b[31mCSI\x1b[0m\x1b]0;OSC\x07\x1b[?25hDEC"
        result = ansi.strip_ansi(text)
        assert result == "CSIDEC"
