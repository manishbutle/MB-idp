"""
Property-Based Tests for FTP Upload Path Correctness
Property 23: FTP Upload Path Correctness

For any valid FTP configuration with a remote directory specified,
the file should be uploaded to that exact directory path.
When no remote directory is specified, the file should be uploaded to the default directory.

Validates: Requirements 19.3, 19.4
"""

import json
import base64
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume, HealthCheck
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from handler import handle_ftp


# Strategy for generating valid directory paths
@st.composite
def valid_directory_paths(draw):
    """Generate valid FTP directory paths"""
    # Generate path components (alphanumeric with underscores and hyphens)
    num_components = draw(st.integers(min_value=1, max_value=4))
    components = []
    
    for _ in range(num_components):
        component = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-'),
            min_size=1,
            max_size=20
        ))
        # Ensure component doesn't start with hyphen or underscore
        if component and component[0] not in ['-', '_']:
            components.append(component)
    
    if not components:
        components = ['uploads']
    
    # Join with forward slashes and ensure leading slash
    path = '/' + '/'.join(components)
    return path


@st.composite
def ftp_upload_events(draw):
    """Generate FTP upload events with various directory configurations"""
    # Generate file name
    file_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='._-'),
        min_size=5,
        max_size=50
    ))
    
    # Ensure file has an extension
    if '.' not in file_name:
        file_name += '.csv'
    
    # Generate file content
    content = draw(st.text(min_size=10, max_size=1000))
    encoded_content = base64.b64encode(content.encode()).decode()
    
    # Generate remote directory (or None for default)
    use_remote_dir = draw(st.booleans())
    remote_directory = draw(valid_directory_paths()) if use_remote_dir else ''
    
    event = {
        'path': '/ftp',
        'httpMethod': 'POST',
        'body': json.dumps({
            'file_name': file_name,
            'file_content': encoded_content,
            'remote_directory': remote_directory
        })
    }
    
    return event, file_name, remote_directory


@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = 'test-request-id'
    return context


@pytest.fixture
def mock_logger():
    """Mock logger"""
    with patch('handler.logger') as mock_log:
        mock_log.info = Mock()
        mock_log.error = Mock()
        mock_log.warning = Mock()
        mock_log.log_info = Mock()
        mock_log.log_error = Mock()
        mock_log.log_warning = Mock()
        mock_log.set_context = Mock()
        mock_log.clear_context = Mock()
        mock_log.log_execution_start = Mock()
        mock_log.log_execution_complete = Mock()
        yield mock_log


@pytest.fixture
def mock_secrets_manager():
    """Mock Secrets Manager"""
    with patch('handler.secrets_manager') as mock_sm:
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'host': 'ftp.example.com',
                'port': 21,
                'username': 'testuser',
                'password': 'testpass'
            })
        }
        yield mock_sm


@pytest.fixture
def mock_ftp():
    """Mock FTP connection"""
    with patch('ftplib.FTP') as mock_ftp_class:
        mock_ftp_instance = Mock()
        mock_ftp_instance.connect = Mock()
        mock_ftp_instance.login = Mock()
        mock_ftp_instance.cwd = Mock()
        mock_ftp_instance.mkd = Mock()
        mock_ftp_instance.storbinary = Mock()
        mock_ftp_instance.quit = Mock()
        mock_ftp_class.return_value = mock_ftp_instance
        yield mock_ftp_instance


class TestFTPPathCorrectness:
    """Property tests for FTP upload path correctness"""
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(event_data=ftp_upload_events())
    def test_remote_directory_used_when_specified(
        self, 
        event_data, 
        mock_context, 
        mock_logger, 
        mock_secrets_manager, 
        mock_ftp
    ):
        """
        Property 23a: When remote_directory is specified, FTP should change to that directory
        
        For any valid FTP upload with a remote_directory specified,
        the system should call ftp.cwd(remote_directory) before uploading.
        
        Validates: Requirements 19.3
        """
        event, file_name, remote_directory = event_data
        
        # Only test cases where remote_directory is specified
        assume(remote_directory != '')
        
        # Execute FTP upload
        response = handle_ftp(event, mock_context)
        
        # Verify successful upload
        assert response['statusCode'] == 200
        
        # Verify that cwd was called with the remote directory
        mock_ftp.cwd.assert_called()
        
        # Get all calls to cwd
        cwd_calls = [call[0][0] for call in mock_ftp.cwd.call_args_list]
        
        # Verify remote_directory was used
        assert remote_directory in cwd_calls, \
            f"Expected cwd to be called with {remote_directory}, but got {cwd_calls}"
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(event_data=ftp_upload_events())
    def test_default_directory_when_not_specified(
        self, 
        event_data, 
        mock_context, 
        mock_logger, 
        mock_secrets_manager, 
        mock_ftp
    ):
        """
        Property 23b: When remote_directory is not specified, FTP should use default directory
        
        For any valid FTP upload without a remote_directory specified,
        the system should NOT call ftp.cwd() and upload to the default directory.
        
        Validates: Requirements 19.4
        """
        event, file_name, remote_directory = event_data
        
        # Only test cases where remote_directory is NOT specified
        assume(remote_directory == '')
        
        # Execute FTP upload
        response = handle_ftp(event, mock_context)
        
        # Verify successful upload
        assert response['statusCode'] == 200
        
        # Verify that cwd was NOT called (default directory used)
        assert mock_ftp.cwd.call_count == 0, \
            "Expected cwd NOT to be called when remote_directory is empty"
        
        # Verify file was still uploaded
        mock_ftp.storbinary.assert_called_once()
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(event_data=ftp_upload_events())
    def test_file_uploaded_to_correct_path(
        self, 
        event_data, 
        mock_context, 
        mock_logger, 
        mock_secrets_manager, 
        mock_ftp
    ):
        """
        Property 23c: File is uploaded with correct filename after directory change
        
        For any valid FTP upload, the file should be uploaded with the correct filename
        after changing to the appropriate directory (or default if not specified).
        
        Validates: Requirements 19.3, 19.4
        """
        event, file_name, remote_directory = event_data
        
        # Execute FTP upload
        response = handle_ftp(event, mock_context)
        
        # Verify successful upload
        assert response['statusCode'] == 200
        
        # Verify storbinary was called with correct filename
        mock_ftp.storbinary.assert_called_once()
        stor_command = mock_ftp.storbinary.call_args[0][0]
        
        # Extract filename from STOR command
        assert stor_command.startswith('STOR '), \
            f"Expected STOR command, got {stor_command}"
        
        uploaded_filename = stor_command[5:]  # Remove 'STOR ' prefix
        assert uploaded_filename == file_name, \
            f"Expected filename {file_name}, but got {uploaded_filename}"
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(event_data=ftp_upload_events())
    def test_directory_creation_when_not_exists(
        self, 
        event_data, 
        mock_context, 
        mock_logger, 
        mock_secrets_manager, 
        mock_ftp
    ):
        """
        Property 23d: System attempts to create directory if it doesn't exist
        
        For any valid FTP upload with a remote_directory that doesn't exist,
        the system should attempt to create it using mkd() before uploading.
        
        Validates: Requirements 19.3
        """
        event, file_name, remote_directory = event_data
        
        # Only test cases where remote_directory is specified
        assume(remote_directory != '')
        
        # Simulate directory not existing
        import ftplib
        mock_ftp.cwd.side_effect = [
            ftplib.error_perm('550 Directory not found'),  # First call fails
            None  # Second call succeeds after creation
        ]
        
        # Execute FTP upload
        response = handle_ftp(event, mock_context)
        
        # Verify successful upload
        assert response['statusCode'] == 200
        
        # Verify mkd was called to create the directory
        mock_ftp.mkd.assert_called_once_with(remote_directory)
        
        # Verify cwd was called twice (once failed, once succeeded)
        assert mock_ftp.cwd.call_count == 2
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(event_data=ftp_upload_events())
    def test_response_includes_correct_directory_info(
        self, 
        event_data, 
        mock_context, 
        mock_logger, 
        mock_secrets_manager, 
        mock_ftp
    ):
        """
        Property 23e: Response includes correct directory information
        
        For any valid FTP upload, the response should indicate the correct
        remote_directory used (or 'default' if not specified).
        
        Validates: Requirements 19.3, 19.4
        """
        event, file_name, remote_directory = event_data
        
        # Execute FTP upload
        response = handle_ftp(event, mock_context)
        
        # Verify successful upload
        assert response['statusCode'] == 200
        
        # Parse response body
        body = json.loads(response['body'])
        
        # Verify response includes directory information
        assert 'remote_directory' in body
        
        if remote_directory:
            assert body['remote_directory'] == remote_directory, \
                f"Expected remote_directory {remote_directory}, got {body['remote_directory']}"
        else:
            assert body['remote_directory'] == 'default', \
                f"Expected 'default' for empty remote_directory, got {body['remote_directory']}"
    
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        file_name=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='._-'),
            min_size=5,
            max_size=50
        ),
        remote_dir=valid_directory_paths()
    )
    def test_path_consistency_across_operations(
        self, 
        file_name, 
        remote_dir, 
        mock_context, 
        mock_logger, 
        mock_secrets_manager, 
        mock_ftp
    ):
        """
        Property 23f: Path consistency across multiple operations
        
        For any sequence of FTP uploads to the same directory,
        the directory path should be used consistently.
        
        Validates: Requirements 19.3
        """
        # Ensure file has extension
        if '.' not in file_name:
            file_name += '.txt'
        
        content = base64.b64encode(b'test content').decode()
        
        # Create two events with the same remote directory
        event1 = {
            'path': '/ftp',
            'httpMethod': 'POST',
            'body': json.dumps({
                'file_name': file_name,
                'file_content': content,
                'remote_directory': remote_dir
            })
        }
        
        event2 = {
            'path': '/ftp',
            'httpMethod': 'POST',
            'body': json.dumps({
                'file_name': 'another_' + file_name,
                'file_content': content,
                'remote_directory': remote_dir
            })
        }
        
        # Execute first upload
        response1 = handle_ftp(event1, mock_context)
        assert response1['statusCode'] == 200
        
        # Reset mock
        mock_ftp.reset_mock()
        
        # Execute second upload
        response2 = handle_ftp(event2, mock_context)
        assert response2['statusCode'] == 200
        
        # Verify both used the same directory
        body1 = json.loads(response1['body'])
        body2 = json.loads(response2['body'])
        
        assert body1['remote_directory'] == body2['remote_directory'], \
            "Same remote_directory should be used consistently"


class TestFTPPathEdgeCases:
    """Test edge cases for FTP path handling"""
    
    def test_empty_string_directory_treated_as_default(
        self, 
        mock_context, 
        mock_logger, 
        mock_secrets_manager, 
        mock_ftp
    ):
        """Test that empty string for remote_directory is treated as default"""
        event = {
            'path': '/ftp',
            'httpMethod': 'POST',
            'body': json.dumps({
                'file_name': 'test.csv',
                'file_content': base64.b64encode(b'test').decode(),
                'remote_directory': ''
            })
        }
        
        response = handle_ftp(event, mock_context)
        
        assert response['statusCode'] == 200
        assert mock_ftp.cwd.call_count == 0
        
        body = json.loads(response['body'])
        assert body['remote_directory'] == 'default'
    
    def test_root_directory_path(
        self, 
        mock_context, 
        mock_logger, 
        mock_secrets_manager, 
        mock_ftp
    ):
        """Test uploading to root directory"""
        event = {
            'path': '/ftp',
            'httpMethod': 'POST',
            'body': json.dumps({
                'file_name': 'test.csv',
                'file_content': base64.b64encode(b'test').decode(),
                'remote_directory': '/'
            })
        }
        
        response = handle_ftp(event, mock_context)
        
        assert response['statusCode'] == 200
        mock_ftp.cwd.assert_called_with('/')
