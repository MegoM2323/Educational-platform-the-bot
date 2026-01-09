import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from django.contrib.auth.models import AnonymousUser
from chat.middleware import TokenAuthMiddleware


class TestTokenAuthMiddlewareExtractToken:
    """Tests for token extraction methods"""

    def test_extract_token_from_authorization_header(self):
        """Test extracting token from Authorization header"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b"Bearer testtoken123"}
        token = middleware._extract_token_from_headers(headers)
        assert token == "testtoken123"

    def test_extract_token_from_authorization_header_with_extra_spaces(self):
        """Test extracting token with extra spaces"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b"Bearer   testtoken123"}
        token = middleware._extract_token_from_headers(headers)
        assert token == "  testtoken123"

    def test_extract_token_no_bearer_prefix(self):
        """Test that token without Bearer prefix is not extracted"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b"testtoken123"}
        token = middleware._extract_token_from_headers(headers)
        assert token is None

    def test_extract_token_empty_authorization_header(self):
        """Test empty Authorization header"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b""}
        token = middleware._extract_token_from_headers(headers)
        assert token is None

    def test_extract_token_no_authorization_header(self):
        """Test missing Authorization header"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {}
        token = middleware._extract_token_from_headers(headers)
        assert token is None

    def test_extract_token_invalid_encoding(self):
        """Test handling of invalid UTF-8 encoding"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b"\x80\x81"}
        token = middleware._extract_token_from_headers(headers)
        assert token is None

    def test_extract_token_bearer_case_sensitive(self):
        """Test that Bearer keyword is case-sensitive"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b"bearer testtoken123"}
        token = middleware._extract_token_from_headers(headers)
        assert token is None

    def test_extract_token_only_bearer_no_token(self):
        """Test Authorization header with just 'Bearer '"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b"Bearer "}
        token = middleware._extract_token_from_headers(headers)
        assert token == ""


class TestTokenAuthMiddlewareCall:
    """Tests for __call__ method"""

    @pytest.mark.asyncio
    async def test_non_websocket_connection(self):
        """Test that middleware only processes WebSocket connections"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)
        scope = {
            "type": "http",
            "path": "/api/chat/",
            "headers": [(b"authorization", b"Bearer testtoken")],
            "query_string": b"",
        }
        receive = None
        send = None

        await middleware(scope, receive, send)

        inner_mock.assert_called_once_with(scope, receive, send)
        assert "user" not in scope

    @pytest.mark.asyncio
    async def test_websocket_with_header_token(self):
        """Test WebSocket connection with Authorization header token"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.role = "student"

        with patch.object(middleware, "get_user_from_token") as mock_get_user:
            mock_get_user.return_value = mock_user

            scope = {
                "type": "websocket",
                "path": "/ws/chat/room1/",
                "headers": [(b"authorization", b"Bearer validtoken123")],
                "query_string": b"",
            }
            receive = None
            send = None

            await middleware(scope, receive, send)

            mock_get_user.assert_called_once_with("validtoken123")
            assert scope["user"].id == 1
            assert scope["user"].email == "test@example.com"

    @pytest.mark.asyncio
    async def test_websocket_with_invalid_header_token(self):
        """Test WebSocket connection with invalid Authorization header token"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        with patch.object(middleware, "get_user_from_token") as mock_get_user:
            mock_get_user.return_value = None

            scope = {
                "type": "websocket",
                "path": "/ws/chat/room1/",
                "headers": [(b"authorization", b"Bearer invalidtoken")],
                "query_string": b"",
            }
            receive = None
            send = None

            await middleware(scope, receive, send)

            assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_with_query_string_token(self):
        """Test WebSocket connection with query string token (legacy)"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        mock_user = Mock()
        mock_user.id = 2
        mock_user.email = "user@example.com"

        with patch.object(middleware, "get_user_from_token") as mock_get_user:
            mock_get_user.return_value = mock_user

            scope = {
                "type": "websocket",
                "path": "/ws/chat/room1/",
                "headers": [],
                "query_string": b"token=validtoken456",
            }
            receive = None
            send = None

            await middleware(scope, receive, send)

            mock_get_user.assert_called_once_with("validtoken456")
            assert scope["user"].id == 2

    @pytest.mark.asyncio
    async def test_websocket_header_has_priority_over_query(self):
        """Test that Authorization header has priority over query string"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        mock_user = Mock()
        mock_user.id = 3
        mock_user.email = "priority@example.com"

        with patch.object(middleware, "get_user_from_token") as mock_get_user:
            mock_get_user.return_value = mock_user

            scope = {
                "type": "websocket",
                "path": "/ws/chat/room1/",
                "headers": [(b"authorization", b"Bearer headertoken")],
                "query_string": b"token=querytoken",
            }
            receive = None
            send = None

            await middleware(scope, receive, send)

            mock_get_user.assert_called_once_with("headertoken")
            assert scope["user"].id == 3

    @pytest.mark.asyncio
    async def test_websocket_no_token_provided(self):
        """Test WebSocket connection without token"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        scope = {
            "type": "websocket",
            "path": "/ws/chat/room1/",
            "headers": [],
            "query_string": b"",
        }
        receive = None
        send = None

        await middleware(scope, receive, send)

        assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_malformed_query_string(self):
        """Test WebSocket with malformed query string"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        scope = {
            "type": "websocket",
            "path": "/ws/chat/room1/",
            "headers": [],
            "query_string": b"invalid&format&",
        }
        receive = None
        send = None

        await middleware(scope, receive, send)

        assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_exception_handling(self):
        """Test that exceptions are caught and AnonymousUser is set"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        with patch.object(middleware, "_extract_token_from_headers") as mock_extract:
            mock_extract.side_effect = Exception("Test error")

            scope = {
                "type": "websocket",
                "path": "/ws/chat/room1/",
                "headers": [(b"authorization", b"Bearer token")],
                "query_string": b"",
            }
            receive = None
            send = None

            await middleware(scope, receive, send)

            assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_empty_headers_list(self):
        """Test WebSocket with empty headers list"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        scope = {
            "type": "websocket",
            "path": "/ws/chat/room1/",
            "headers": [],
            "query_string": b"",
        }
        receive = None
        send = None

        await middleware(scope, receive, send)

        assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_missing_scope_fields(self):
        """Test WebSocket with missing optional scope fields"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        scope = {
            "type": "websocket",
            "path": "/ws/chat/room1/",
        }
        receive = None
        send = None

        await middleware(scope, receive, send)

        assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_token_source_header(self):
        """Test that token_source is properly tracked for headers"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        mock_user = Mock()
        mock_user.id = 4
        mock_user.email = "test@example.com"
        mock_user.role = "student"

        with patch.object(middleware, "get_user_from_token") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("chat.middleware.logger") as mock_logger:
                scope = {
                    "type": "websocket",
                    "path": "/ws/chat/room1/",
                    "headers": [(b"authorization", b"Bearer headertoken")],
                    "query_string": b"",
                }
                receive = None
                send = None

                await middleware(scope, receive, send)

                debug_calls = [
                    call
                    for call in mock_logger.debug.call_args_list
                    if "Authorization header" in str(call)
                ]
                assert len(debug_calls) > 0

    @pytest.mark.asyncio
    async def test_websocket_token_source_query(self):
        """Test that token_source is properly tracked for query string"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        mock_user = Mock()
        mock_user.id = 5
        mock_user.email = "test@example.com"
        mock_user.role = "student"

        with patch.object(middleware, "get_user_from_token") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("chat.middleware.logger") as mock_logger:
                scope = {
                    "type": "websocket",
                    "path": "/ws/chat/room1/",
                    "headers": [],
                    "query_string": b"token=querytoken",
                }
                receive = None
                send = None

                await middleware(scope, receive, send)

                debug_calls = [
                    call
                    for call in mock_logger.debug.call_args_list
                    if "query string" in str(call)
                ]
                assert len(debug_calls) > 0


class TestTokenAuthMiddlewareEdgeCases:
    """Edge case tests"""

    def test_extract_token_with_newlines(self):
        """Test header with newlines"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b"Bearer token\nwith\nnewlines"}
        token = middleware._extract_token_from_headers(headers)
        assert token == "token\nwith\nnewlines"

    def test_extract_token_with_special_characters(self):
        """Test token with special characters"""
        middleware = TokenAuthMiddleware(AsyncMock())
        headers = {b"authorization": b"Bearer token-with_special.chars123"}
        token = middleware._extract_token_from_headers(headers)
        assert token == "token-with_special.chars123"

    def test_extract_token_very_long_token(self):
        """Test with very long token"""
        middleware = TokenAuthMiddleware(AsyncMock())
        long_token = "x" * 10000
        headers = {b"authorization": f"Bearer {long_token}".encode()}
        token = middleware._extract_token_from_headers(headers)
        assert token == long_token

    @pytest.mark.asyncio
    async def test_websocket_query_string_with_multiple_tokens(self):
        """Test query string with multiple token parameters"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        mock_user = Mock()
        mock_user.id = 6
        mock_user.email = "test@example.com"

        with patch.object(middleware, "get_user_from_token") as mock_get_user:
            mock_get_user.return_value = mock_user

            scope = {
                "type": "websocket",
                "path": "/ws/chat/room1/",
                "headers": [],
                "query_string": b"token=first&token=second&other=value",
            }
            receive = None
            send = None

            await middleware(scope, receive, send)

            mock_get_user.assert_called_once_with("first")

    @pytest.mark.asyncio
    async def test_websocket_url_encoded_token(self):
        """Test with URL-encoded token in query string"""
        inner_mock = AsyncMock()
        middleware = TokenAuthMiddleware(inner_mock)

        mock_user = Mock()
        mock_user.id = 7
        mock_user.email = "test@example.com"

        with patch.object(middleware, "get_user_from_token") as mock_get_user:
            mock_get_user.return_value = mock_user

            scope = {
                "type": "websocket",
                "path": "/ws/chat/room1/",
                "headers": [],
                "query_string": b"token=abc%2Bdef%3Dghi",
            }
            receive = None
            send = None

            await middleware(scope, receive, send)

            mock_get_user.assert_called_once_with("abc+def=ghi")
