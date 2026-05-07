"""Global threading event for handling shutdown signals."""

import threading

shutdown_event = threading.Event()
