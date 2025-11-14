# tests/test_telemetry.py
import os
import unittest
from unittest.mock import AsyncMock, patch

import aiohttp

from minitrino.telemetry import Telemetry


# A test that checks if the Telemetry class is enabled by default.
def test_telemetry_is_enabled(self):
    os.environ["MINITRINO_TELEMETRY"] = "true"
    telemetry = Telemetry()
    self.assertTrue(telemetry.is_telemetry_enabled())


# A test that checks if the send_telemetry function is making a network request.
@patch("aiohttp.ClientSession.post", new_callable=AsyncMock)
async def test_send_telemetry_makes_network_request(self, mock_post):
    # We need to mock the environment variable to enable telemetry.
    os.environ["MINITRINO_TELEMETRY"] = "true"
    telemetry = Telemetry()

    # The mock will return a successful response.
    mock_post.return_value.__aenter__.return_value.status = 200

    # Now, we call the send_telemetry function.
    await telemetry.send_telemetry("start-cluster")

    # We assert that the mock was called with the correct arguments.
    self.assertTrue(mock_post.called)



# A test that checks if the send_telemetry function is resilient to network errors.
@patch("aiohttp.ClientSession.post", new_callable=AsyncMock)
async def test_send_telemetry_handles_network_error(self, mock_post):
    # The mock will raise a ClientError.
    mock_post.side_effect = aiohttp.ClientError

    # We need to mock the environment variable to enable telemetry.
    os.environ["MINITRINO_TELEMETRY"] = "true"
    telemetry = Telemetry()

    # Now, we call the send_telemetry function.
    await telemetry.send_telemetry("start-cluster")

    # The test will pass if no exception is raised.
    self.assertFalse(mock_post.called)
