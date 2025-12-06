"""
Supabase mocks and fixtures for testing
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    mock_client = MagicMock()

    # Mock auth methods
    mock_client.auth.sign_up.return_value = {
        'user': {
            'id': 'test-user-id-123',
            'email': 'test@example.com',
            'created_at': '2024-01-01T00:00:00Z'
        },
        'session': {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token'
        }
    }

    mock_client.auth.sign_in_with_password.return_value = {
        'user': {
            'id': 'test-user-id-123',
            'email': 'test@example.com'
        },
        'session': {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token'
        }
    }

    mock_client.auth.sign_out.return_value = None

    # Mock database methods
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = {'data': [], 'error': None}

    mock_client.table.return_value = mock_table

    # Mock storage methods
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.upload.return_value = {
        'path': 'test/path/file.jpg',
        'error': None
    }
    mock_storage.download.return_value = b'test file content'
    mock_storage.remove.return_value = {'error': None}
    mock_storage.get_public_url.return_value = 'https://example.com/test/path/file.jpg'

    mock_client.storage = mock_storage

    return mock_client


@pytest.fixture
def mock_supabase_create_client():
    """Mock supabase.create_client() function"""
    with patch('supabase.create_client') as mock:
        mock_client = MagicMock()

        # Setup basic auth responses
        mock_client.auth.sign_up.return_value = {
            'user': {'id': 'test-user-id', 'email': 'test@example.com'},
            'session': {'access_token': 'test-token'}
        }

        mock.return_value = mock_client
        yield mock


@pytest.fixture
def mock_supabase_auth_success():
    """Mock successful Supabase authentication"""
    return {
        'user': {
            'id': 'test-user-id-123',
            'email': 'test@example.com',
            'user_metadata': {
                'first_name': 'Test',
                'last_name': 'User'
            },
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z'
        },
        'session': {
            'access_token': 'test-access-token-abc123',
            'refresh_token': 'test-refresh-token-xyz789',
            'expires_in': 3600,
            'token_type': 'bearer'
        }
    }


@pytest.fixture
def mock_supabase_auth_error():
    """Mock Supabase authentication error"""
    return {
        'user': None,
        'session': None,
        'error': {
            'message': 'Invalid login credentials',
            'status': 400
        }
    }


@pytest.fixture
def mock_supabase_storage_upload_success():
    """Mock successful file upload to Supabase storage"""
    return {
        'data': {
            'path': 'uploads/test-file-123.jpg',
            'id': 'file-id-123',
            'fullPath': 'public/uploads/test-file-123.jpg'
        },
        'error': None
    }


@pytest.fixture
def mock_supabase_storage_upload_error():
    """Mock file upload error to Supabase storage"""
    return {
        'data': None,
        'error': {
            'message': 'File too large',
            'status': 413
        }
    }


@pytest.fixture
def mock_supabase_db_select():
    """Mock Supabase database select query"""
    return {
        'data': [
            {
                'id': 1,
                'name': 'Test Item 1',
                'created_at': '2024-01-01T00:00:00Z'
            },
            {
                'id': 2,
                'name': 'Test Item 2',
                'created_at': '2024-01-02T00:00:00Z'
            }
        ],
        'error': None,
        'count': 2
    }


@pytest.fixture
def mock_supabase_db_insert():
    """Mock Supabase database insert query"""
    return {
        'data': {
            'id': 1,
            'name': 'New Test Item',
            'created_at': '2024-01-01T00:00:00Z'
        },
        'error': None
    }


@pytest.fixture
def mock_supabase_db_error():
    """Mock Supabase database error"""
    return {
        'data': None,
        'error': {
            'message': 'Unique constraint violation',
            'code': '23505',
            'details': 'Key (email) already exists'
        }
    }


@pytest.fixture(autouse=True)
def mock_supabase_service(mocker, settings):
    """
    Automatically mock SupabaseAuthService for all tests.

    This prevents real Supabase client initialization and provides
    consistent mock responses for sign_in, sign_up, etc.

    The mock returns proper structure matching SupabaseAuthService.sign_in():
    - success: False (simulating "not configured" state)
    - error: "Supabase не настроен"

    Tests can override this by patching SupabaseAuthService explicitly.
    """
    # Set test ENV values (prevents any accidental real connections)
    settings.SUPABASE_URL = ''
    settings.SUPABASE_KEY = ''
    settings.SUPABASE_SERVICE_ROLE_KEY = ''

    # Mock the SupabaseAuthService class at its source
    # This will affect all imports including from accounts.views
    mock_service_class = mocker.patch('accounts.supabase_service.SupabaseAuthService')
    mock_instance = MagicMock()

    # Configure sign_in to return "not configured" response
    mock_instance.sign_in.return_value = {
        'success': False,
        'error': 'Supabase не настроен. Используйте стандартную аутентификацию Django.'
    }

    # Configure sign_up to return "not configured" response
    mock_instance.sign_up.return_value = {
        'success': False,
        'error': 'Supabase не настроен. Используйте стандартную аутентификацию Django.'
    }

    # Configure sign_out
    mock_instance.sign_out.return_value = {
        'success': False,
        'error': 'Supabase не настроен. Используйте стандартную аутентификацию Django.'
    }

    # Make SupabaseAuthService() return our mock instance
    mock_service_class.return_value = mock_instance

    # Also make sign_in callable via getattr check in views.py
    mock_instance.is_mock = True

    return mock_instance


@pytest.fixture(autouse=True)
def disable_supabase_in_tests(settings):
    """
    DEPRECATED: Use mock_supabase_service instead.

    Kept for backwards compatibility with existing tests.
    """
    pass  # mock_supabase_service handles everything now
