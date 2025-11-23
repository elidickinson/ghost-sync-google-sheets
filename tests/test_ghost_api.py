#!/usr/bin/env python3
"""
Critical path tests for Ghost API authentication and requests
"""

import pytest
import time
import hmac
import hashlib
import base64
import json
from unittest.mock import patch, MagicMock

import members_to_sqlite


class TestJWTGeneration:
    """Test JWT token generation - critical for API authentication"""

    def test_generate_token_valid_key(self):
        """Test JWT generation with valid admin API key"""
        test_key = (
            "abc123:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        token = members_to_sqlite.generate_token(test_key)

        parts = token.split(".")
        assert len(parts) == 3
        assert all(part for part in parts)

    def test_generate_token_invalid_format(self):
        """Test JWT generation fails with invalid key format"""
        with pytest.raises(ValueError, match="Invalid Admin API Key format"):
            members_to_sqlite.generate_token("invalid-key-no-colon")

    def test_generate_token_non_hex_secret(self):
        """Test JWT generation fails with non-hexadecimal secret"""
        with pytest.raises(ValueError, match="secret must be hexadecimal"):
            members_to_sqlite.generate_token("abc123:not-a-hex-string!")


class TestGhostAPIRequests:
    """Test Ghost API request functionality"""

    @patch("members_to_sqlite.requests.request")
    def test_make_ghost_request_success(self, mock_request):
        """Test successful API request with proper headers"""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"members": []}
        mock_request.return_value = mock_response

        with patch("members_to_sqlite.generate_token", return_value="test-token"):
            result = members_to_sqlite.make_ghost_request("/test")

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["headers"]["Authorization"] == "Ghost test-token"
        assert call_args[1]["headers"]["Accept-Version"] == "v5.0"

    @patch("members_to_sqlite.requests.request")
    def test_make_ghost_request_failure(self, mock_request):
        """Test API request failure raises exception"""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response

        with patch("members_to_sqlite.generate_token", return_value="test-token"):
            with pytest.raises(Exception, match="API returned status 401"):
                members_to_sqlite.make_ghost_request("/test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
