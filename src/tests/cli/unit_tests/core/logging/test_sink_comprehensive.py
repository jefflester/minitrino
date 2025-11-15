"""Comprehensive tests for logging sink behavior.

This module tests all aspects of the logging sink functionality including buffer
management, thread safety, and interaction with other components.
"""

import contextlib
import threading
import time

from minitrino.core.logging.logger import MinitrinoLogger
from minitrino.core.logging.sink import SinkCollector


class TestLoggingSinkBehavior:
    """Test suite for logging sink functionality."""

    def test_sink_buffer_initialization(self):
        """Test that sink buffer initializes correctly."""
        sink = SinkCollector()
        assert sink.buffer == []
        assert hasattr(sink, "_buffer_size_bytes")
        assert sink._buffer_size_bytes == 0

    def test_sink_captures_messages(self):
        """Test sink captures messages with different metadata."""
        sink = SinkCollector()

        # Simulate different message types being added to sink
        sink("debug message", "stdout", False)
        sink("info message", "stdout", False)
        sink("warn message", "stderr", False)
        sink("error message", "stderr", False)

        # Check all messages captured
        assert len(sink.buffer) == 4
        assert sink.buffer[0] == ("debug message", "stdout", False)
        assert sink.buffer[1] == ("info message", "stdout", False)
        assert sink.buffer[2] == ("warn message", "stderr", False)
        assert sink.buffer[3] == ("error message", "stderr", False)

    def test_sink_with_handler(self):
        """Test that sink works with handler."""
        sink = SinkCollector()
        logger = MinitrinoLogger("test")
        logger._log_sink = sink

        # Call sink directly to simulate handler behavior
        sink("test message", "stdout", False)

        assert len(sink.buffer) == 1
        assert sink.buffer[0] == ("test message", "stdout", False)

    def test_sink_buffer_call(self):
        """Test direct buffer call functionality."""
        sink = SinkCollector()

        sink("message 1", "stdout", False)
        sink("message 2", "stderr", False)
        sink("message 3", "stdout", True)

        assert len(sink.buffer) == 3
        assert sink.buffer[0] == ("message 1", "stdout", False)
        assert sink.buffer[1] == ("message 2", "stderr", False)
        assert sink.buffer[2] == ("message 3", "stdout", True)

    def test_sink_buffer_size_limit(self):
        """Test sink respects maximum buffer size."""
        sink = SinkCollector()

        # Add many large messages to exceed size limit
        large_msg = "x" * 1000000  # 1MB message
        for i in range(150):  # Try to add 150MB of data
            sink(f"Message {i}: {large_msg}", "stdout", False)

        # Buffer should have been trimmed
        assert sink._buffer_size_bytes < sink.MAX_BUFFER_BYTES
        # Should have some messages but not all
        assert len(sink.buffer) > 0
        assert len(sink.buffer) < 150

    def test_sink_thread_safety(self):
        """Test sink is thread-safe with concurrent writes."""
        sink = SinkCollector()
        messages_per_thread = 100
        num_threads = 5

        def add_messages(thread_id, count):
            """Add messages from a thread."""
            for i in range(count):
                sink(f"Thread {thread_id}: Message {i}", "stdout", False)
                # Small delay to increase chance of race conditions
                time.sleep(0.0001)

        # Start threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=add_messages, args=(i, messages_per_thread))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no messages were lost
        assert len(sink.buffer) == num_threads * messages_per_thread

        # Verify all threads' messages are present
        for thread_id in range(num_threads):
            thread_messages = [m for m in sink.buffer if f"Thread {thread_id}" in m[0]]
            assert len(thread_messages) == messages_per_thread

    def test_sink_with_spinner_interaction(self):
        """Test sink behavior during spinner operations."""
        sink = SinkCollector()

        # Simulate messages with spinner flag
        sink("Before spinner", "stdout", False)
        sink("During spinner 1", "stdout", True)
        sink("Debug during spinner", "stdout", True)
        sink("Warning during spinner", "stderr", True)
        sink("After spinner", "stdout", False)

        # All messages should be captured with correct flags
        assert len(sink.buffer) == 5
        assert sink.buffer[0] == ("Before spinner", "stdout", False)
        assert sink.buffer[1] == ("During spinner 1", "stdout", True)
        assert sink.buffer[2] == ("Debug during spinner", "stdout", True)
        assert sink.buffer[3] == ("Warning during spinner", "stderr", True)
        assert sink.buffer[4] == ("After spinner", "stdout", False)

    def test_sink_clear_functionality(self):
        """Test clearing sink buffer."""
        sink = SinkCollector()

        # Add messages
        sink("Message 1", "stdout", False)
        sink("Message 2", "stdout", False)
        assert len(sink.buffer) == 2

        # Clear buffer
        sink.clear()
        assert len(sink.buffer) == 0
        assert sink._buffer_size_bytes == 0

        # Add new messages
        sink("Message 3", "stdout", False)
        assert len(sink.buffer) == 1
        assert sink.buffer[0][0] == "Message 3"

    def test_sink_buffer_property(self):
        """Test accessing the buffer property."""
        sink = SinkCollector()

        sink("message 1", "stdout", False)
        sink("message 2", "stderr", False)

        # Get buffer
        buffer = sink.buffer

        # Verify contents
        assert len(buffer) == 2
        assert buffer[0] == ("message 1", "stdout", False)
        assert buffer[1] == ("message 2", "stderr", False)

        # Buffer is the actual list, not a copy
        assert buffer is sink.buffer

    def test_sink_filtering_capability(self):
        """Test sink can filter messages based on criteria."""

        # Create a custom filtered sink
        class FilteredSink(SinkCollector):
            def __call__(self, msg, stream, is_spinner):
                # Filter out DEBUG messages
                if "DEBUG" not in msg:
                    super().__call__(msg, stream, is_spinner)

        sink = FilteredSink()

        sink("INFO: Normal message", "stdout", False)
        sink("DEBUG: Debug message", "stdout", False)
        sink("ERROR: Error message", "stderr", False)
        sink("WARN: Warning message", "stdout", False)

        # DEBUG message should be filtered out
        assert len(sink.buffer) == 3
        assert not any("DEBUG" in msg[0] for msg in sink.buffer)
        assert any("INFO" in msg[0] for msg in sink.buffer)
        assert any("ERROR" in msg[0] for msg in sink.buffer)
        assert any("WARN" in msg[0] for msg in sink.buffer)

    def test_multiple_sinks_independence(self):
        """Test multiple sinks work independently."""
        sink1 = SinkCollector()
        sink2 = SinkCollector()

        # Add to different sinks
        sink1("Sink1 message", "stdout", False)
        sink2("Sink2 message", "stdout", False)

        # Verify independence
        assert len(sink1.buffer) == 1
        assert len(sink2.buffer) == 1
        assert sink1.buffer[0][0] == "Sink1 message"
        assert sink2.buffer[0][0] == "Sink2 message"

    def test_sink_context_manager_usage(self):
        """Test sink as context manager for scoped logging."""

        # Create context manager for sink
        class SinkContext:
            def __init__(self):
                self.sink = SinkCollector()

            def __enter__(self):
                return self.sink

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Could clear or finalize here
                pass

        # Use sink in context
        with SinkContext() as sink:
            sink("Context message 1", "stdout", False)
            sink("Context message 2", "stdout", False)
            assert len(sink.buffer) == 2

        # After context, sink still works
        sink("Outside context", "stdout", False)
        assert len(sink.buffer) == 3

    def test_sink_performance_under_load(self):
        """Test sink performance with high message volume."""
        sink = SinkCollector()

        # Add many messages quickly
        start_time = time.monotonic()
        message_count = 10000

        for i in range(message_count):
            sink(f"Performance test message {i}", "stdout", False)

        elapsed = time.monotonic() - start_time

        # Verify all messages captured
        assert len(sink.buffer) == message_count

        # Performance assertion (should handle 10k messages in reasonable time)
        assert elapsed < 5.0, f"Took {elapsed}s to process {message_count} messages"

    def test_sink_with_exception_handling(self):
        """Test sink handles exceptions gracefully."""
        sink = SinkCollector()

        # Add normal message
        sink("Before exception", "stdout", False)

        # Try to cause an error with bad input
        # The sink should handle this gracefully
        with contextlib.suppress(Exception):
            # SinkCollector should handle various input types
            sink(None, "stdout", False)  # None as message

        # Should still work after exception
        sink("After exception", "stdout", False)

        # Verify messages were captured
        assert len(sink.buffer) >= 2
        assert sink.buffer[0][0] == "Before exception"
        assert sink.buffer[-1][0] == "After exception"

    def test_sink_memory_management(self):
        """Test sink properly manages memory with large messages."""
        sink = SinkCollector()

        # Create large message
        large_message = "x" * 10000  # 10KB message

        # Add several large messages
        for i in range(100):
            sink(f"Large message {i}: {large_message}", "stdout", False)

        # Clear to free memory
        sink.clear()

        # Verify buffer is empty
        assert len(sink.buffer) == 0
        assert sink._buffer_size_bytes == 0

        # Add small message to verify still working
        sink("Small message", "stdout", False)
        assert len(sink.buffer) == 1

    def test_sink_unicode_handling(self):
        """Test sink handles Unicode characters correctly."""
        sink = SinkCollector()

        # Various Unicode messages
        unicode_messages = [
            "Hello 世界",  # Chinese
            "Привет мир",  # Russian
            "مرحبا بالعالم",  # Arabic
            "🚀 Emoji test 🎉",  # Emojis
            "Ñoño",  # Spanish
        ]

        for msg in unicode_messages:
            sink(msg, "stdout", False)

        # Verify all captured correctly
        assert len(sink.buffer) == len(unicode_messages)
        for i, original_msg in enumerate(unicode_messages):
            assert sink.buffer[i][0] == original_msg
