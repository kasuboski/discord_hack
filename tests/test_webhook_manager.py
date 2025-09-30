"""Tests for webhook manager message splitting."""

import pytest

from discord_hack.webhook_manager import WebhookManager


class TestMessageSplitting:
    """Tests for the message splitting functionality."""

    def test_split_message_under_limit(self):
        """Test that messages under the limit are not split."""
        manager = WebhookManager()
        content = "This is a short message"
        chunks = manager._split_message(content)

        assert len(chunks) == 1
        assert chunks[0] == content

    def test_split_message_at_exact_limit(self):
        """Test that messages at exactly 2000 chars are not split."""
        manager = WebhookManager()
        content = "a" * 2000
        chunks = manager._split_message(content)

        assert len(chunks) == 1
        assert chunks[0] == content

    def test_split_message_over_limit_by_lines(self):
        """Test splitting long messages by line breaks."""
        manager = WebhookManager()
        # Create a message with multiple lines, total >2000 chars
        line = "This is a line of text.\n"
        content = line * 100  # ~2300 chars

        chunks = manager._split_message(content)

        assert len(chunks) == 2
        # Verify no chunk exceeds limit
        for chunk in chunks:
            assert len(chunk) <= 2000
        # Verify all content is preserved
        assert "".join(chunks).replace("\n", "").strip() == content.replace(
            "\n", ""
        ).strip()

    def test_split_message_preserves_line_breaks(self):
        """Test that line breaks are preserved during splitting."""
        manager = WebhookManager()
        content = "Line 1\nLine 2\nLine 3\n" * 50  # ~900 chars
        chunks = manager._split_message(content)

        # Should fit in one chunk
        assert len(chunks) == 1
        assert "Line 1\nLine 2\nLine 3\n" in chunks[0]

    def test_split_message_long_single_line_by_sentences(self):
        """Test splitting a very long single line by sentences."""
        manager = WebhookManager()
        # Create a single line >2000 chars with sentences
        sentence = "This is a sentence. "
        content = sentence * 150  # ~3000 chars, single line

        chunks = manager._split_message(content)

        assert len(chunks) >= 2
        # Verify no chunk exceeds limit
        for chunk in chunks:
            assert len(chunk) <= 2000

    def test_split_message_no_punctuation_force_split(self):
        """Test force-splitting when no sentence boundaries exist."""
        manager = WebhookManager()
        # Single very long word/string without punctuation
        content = "a" * 3000

        chunks = manager._split_message(content)

        assert len(chunks) == 2
        assert len(chunks[0]) == 2000
        assert len(chunks[1]) == 1000

    def test_split_message_mixed_content(self):
        """Test splitting markdown-style content with code blocks."""
        manager = WebhookManager()
        # Simulate a long technical response
        content = """Here's how to do it:

```python
def example():
    pass
```

""" * 40  # ~2400 chars, will need splitting

        chunks = manager._split_message(content)

        # Should be split into multiple chunks
        assert len(chunks) >= 2
        # Verify all chunks contain valid content
        for chunk in chunks:
            assert len(chunk) <= 2000
        # Verify markdown syntax is preserved
        assert any("```python" in chunk for chunk in chunks)

    def test_split_message_very_long_content(self):
        """Test splitting very long content (>4000 chars)."""
        manager = WebhookManager()
        # Create content that will need multiple splits
        paragraph = "This is a paragraph of text. " * 50 + "\n\n"
        content = paragraph * 5  # ~7500 chars

        chunks = manager._split_message(content)

        assert len(chunks) >= 3
        # Verify no chunk exceeds limit
        for chunk in chunks:
            assert len(chunk) <= 2000
        # Verify chunks are not empty
        for chunk in chunks:
            assert len(chunk.strip()) > 0

    def test_split_message_custom_max_length(self):
        """Test splitting with a custom max length."""
        manager = WebhookManager()
        content = "a" * 150

        chunks = manager._split_message(content, max_length=100)

        assert len(chunks) == 2
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 50

    def test_split_message_empty_string(self):
        """Test splitting an empty string."""
        manager = WebhookManager()
        content = ""

        chunks = manager._split_message(content)

        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_split_message_whitespace_only(self):
        """Test splitting whitespace-only content."""
        manager = WebhookManager()
        content = "   \n\n\n   "

        chunks = manager._split_message(content)

        assert len(chunks) == 1

    def test_split_message_maintains_content_integrity(self):
        """Test that splitting doesn't lose or duplicate content."""
        manager = WebhookManager()
        # Create distinctive content
        content = "\n".join([f"Line {i}" for i in range(200)])  # ~1400 chars

        chunks = manager._split_message(content)

        # Rejoin and verify all lines are present
        rejoined = "\n".join(chunk.strip() for chunk in chunks)
        for i in range(200):
            assert f"Line {i}" in rejoined
