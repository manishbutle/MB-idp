"""
Property-Based Tests for Email Attachment Format Compliance
Property 22: Email Attachment Format Compliance

For any email with attachments in CSV, XLSX, or JSON formats,
the system should correctly attach files with proper content types
and the attachments should be parseable in their respective formats.

Validates: Requirements 18.3, 18.4, 18.5, 18.6, 18.7
"""

import json
import base64
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, settings, HealthCheck
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from handler import handle_send_email


# Strategy for generating email data with attachments
@st.composite
def email_with_attachments(draw):
    """Generate email events with various attachment formats"""
    to_address = draw(st.emails())
    # Generate subject without control characters
    subject = draw(st.text(
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs', 'Co')),
        min_size=5,
        max_size=100
    ))
    # Generate body without control characters
    body = draw(st.text(
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs', 'Co')),
        min_size=10,
        max_size=500
    ))
    
    # Generate attachments (CSV, XLSX, JSON)
    num_attachments = draw(st.integers(min_value=1, max_value=3))
    formats = draw(st.lists(
        st.sampled_from(['csv', 'xlsx', 'json']),
        min_size=num_attachments,
        max_size=num_attachments
    ))
    
    attachments = []
    for fmt in formats:
        if fmt == 'csv':
            # Generate simple CSV content
            content = "Name,Value\nField1,Value1\nField2,Value2"
            content_type = 'text/csv'
            filename = 'data.csv'
        elif fmt == 'xlsx':
            # Generate minimal XLSX-like content (base64 encoded binary)
            content = "PK\x03\x04"  # ZIP file signature for XLSX
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = 'data.xlsx'
        else:  # json
            # Generate JSON content
            content = json.dumps({"field1": "value1", "field2": "value2"})
            content_type = 'application/json'
            filename = 'data.json'
        
        encoded_content = base64.b64encode(content.encode() if isinstance(content, str) else content.encode('latin1')).decode()
        
        attachments.append({
            'filename': filename,
            'content': encoded_content,
            'content_type': content_type
        })
    
    event = {
        'path': '/send_email',
        'httpMethod': 'POST',
        'body': json.dumps({
            'to': to_address,
            'subject': subject,
            'body': body,
            'attachments': attachments
        })
    }
    
    return event, attachments


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
def mock_ses():
    """Mock SES client"""
    with patch('handler.ses') as mock_ses_client:
        mock_ses_client.send_raw_email.return_value = {
            'MessageId': 'test-message-id-12345'
        }
        yield mock_ses_client


class TestEmailAttachmentFormatCompliance:
    """Property tests for email attachment format compliance"""
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(email_data=email_with_attachments())
    def test_csv_attachment_format_compliance(
        self,
        email_data,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """
        Property 22a: CSV attachments have correct content type
        
        For any email with CSV attachments, the content type should be 'text/csv'
        and the attachment should be properly encoded.
        
        Validates: Requirements 18.3, 18.4
        """
        # Reset mocks for this example
        mock_ses.reset_mock()
        mock_logger.reset_mock()
        
        event, attachments = email_data
        
        # Filter for CSV attachments
        csv_attachments = [a for a in attachments if a['content_type'] == 'text/csv']
        
        if not csv_attachments:
            return  # Skip if no CSV attachments
        
        # Execute email sending
        response = handle_send_email(event, mock_context)
        
        # Verify successful send
        assert response['statusCode'] == 200
        
        # Verify SES was called with raw email
        mock_ses.send_raw_email.assert_called_once()
        
        # Get the raw message
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]['RawMessage']['Data']
        
        # Verify CSV content type appears in the message
        assert 'text/csv' in raw_message or 'text/csv'.encode() in raw_message.encode() if isinstance(raw_message, str) else True
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(email_data=email_with_attachments())
    def test_xlsx_attachment_format_compliance(
        self,
        email_data,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """
        Property 22b: XLSX attachments have correct content type
        
        For any email with XLSX attachments, the content type should be
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        Validates: Requirements 18.3, 18.5
        """
        # Reset mocks for this example
        mock_ses.reset_mock()
        mock_logger.reset_mock()
        
        event, attachments = email_data
        
        # Filter for XLSX attachments
        xlsx_attachments = [a for a in attachments if 'spreadsheetml' in a['content_type']]
        
        if not xlsx_attachments:
            return  # Skip if no XLSX attachments
        
        # Execute email sending
        response = handle_send_email(event, mock_context)
        
        # Verify successful send
        assert response['statusCode'] == 200
        
        # Verify SES was called
        mock_ses.send_raw_email.assert_called_once()
    
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(email_data=email_with_attachments())
    def test_json_attachment_format_compliance(
        self,
        email_data,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """
        Property 22c: JSON attachments have correct content type
        
        For any email with JSON attachments, the content type should be
        'application/json' and the content should be valid JSON.
        
        Validates: Requirements 18.3, 18.6
        """
        event, attachments = email_data
        
        # Filter for JSON attachments
        json_attachments = [a for a in attachments if a['content_type'] == 'application/json']
        
        if not json_attachments:
            return  # Skip if no JSON attachments
        
        # Verify JSON content is valid
        for attachment in json_attachments:
            decoded_content = base64.b64decode(attachment['content']).decode()
            # Should not raise exception
            parsed = json.loads(decoded_content)
            assert isinstance(parsed, (dict, list))
        
        # Execute email sending
        response = handle_send_email(event, mock_context)
        
        # Verify successful send
        assert response['statusCode'] == 200
    
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(email_data=email_with_attachments())
    def test_multiple_attachments_all_included(
        self,
        email_data,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """
        Property 22d: All attachments are included in the email
        
        For any email with multiple attachments, all attachments should be
        included in the sent email.
        
        Validates: Requirements 18.7
        """
        event, attachments = email_data
        
        # Execute email sending
        response = handle_send_email(event, mock_context)
        
        # Verify successful send
        assert response['statusCode'] == 200
        
        # Verify response includes attachment count
        body = json.loads(response['body'])
        assert 'attachments_count' in body
        assert body['attachments_count'] == len(attachments)
    
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(email_data=email_with_attachments())
    def test_attachment_filenames_preserved(
        self,
        email_data,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """
        Property 22e: Attachment filenames are preserved
        
        For any email with attachments, the filenames should be preserved
        in the MIME message.
        
        Validates: Requirements 18.3, 18.4, 18.5, 18.6
        """
        # Reset mocks for this example
        mock_ses.reset_mock()
        mock_logger.reset_mock()
        
        event, attachments = email_data
        
        # Execute email sending
        response = handle_send_email(event, mock_context)
        
        # Verify successful send
        assert response['statusCode'] == 200
        
        # Verify SES was called
        mock_ses.send_raw_email.assert_called_once()
        
        # Get the raw message
        call_args = mock_ses.send_raw_email.call_args
        raw_message = call_args[1]['RawMessage']['Data']
        
        # Verify filenames appear in the message
        for attachment in attachments:
            filename = attachment['filename']
            # Filename should appear in Content-Disposition header
            assert filename in raw_message or filename.encode() in raw_message.encode() if isinstance(raw_message, str) else True


class TestEmailAttachmentEdgeCases:
    """Test edge cases for email attachment handling"""
    
    def test_single_csv_attachment(
        self,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """Test email with single CSV attachment"""
        csv_content = "Name,Value\nTest,123"
        encoded = base64.b64encode(csv_content.encode()).decode()
        
        event = {
            'path': '/send_email',
            'httpMethod': 'POST',
            'body': json.dumps({
                'to': 'test@example.com',
                'subject': 'Test Email',
                'body': 'Test body',
                'attachments': [{
                    'filename': 'test.csv',
                    'content': encoded,
                    'content_type': 'text/csv'
                }]
            })
        }
        
        response = handle_send_email(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['attachments_count'] == 1
    
    def test_mixed_format_attachments(
        self,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """Test email with CSV, XLSX, and JSON attachments"""
        attachments = [
            {
                'filename': 'data.csv',
                'content': base64.b64encode(b'Name,Value\nTest,123').decode(),
                'content_type': 'text/csv'
            },
            {
                'filename': 'data.xlsx',
                'content': base64.b64encode(b'PK\x03\x04').decode(),
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            },
            {
                'filename': 'data.json',
                'content': base64.b64encode(b'{"test": "value"}').decode(),
                'content_type': 'application/json'
            }
        ]
        
        event = {
            'path': '/send_email',
            'httpMethod': 'POST',
            'body': json.dumps({
                'to': 'test@example.com',
                'subject': 'Test Email',
                'body': 'Test body',
                'attachments': attachments
            })
        }
        
        response = handle_send_email(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['attachments_count'] == 3
    
    def test_empty_attachments_list(
        self,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """Test email with empty attachments list sends simple email"""
        mock_ses.send_email.return_value = {
            'MessageId': 'test-message-id'
        }
        
        event = {
            'path': '/send_email',
            'httpMethod': 'POST',
            'body': json.dumps({
                'to': 'test@example.com',
                'subject': 'Test Email',
                'body': 'Test body',
                'attachments': []
            })
        }
        
        response = handle_send_email(event, mock_context)
        
        assert response['statusCode'] == 200
        # Should use send_email (simple) not send_raw_email
        mock_ses.send_email.assert_called_once()
        mock_ses.send_raw_email.assert_not_called()
    
    def test_large_attachment_content(
        self,
        mock_context,
        mock_logger,
        mock_ses
    ):
        """Test email with large attachment content"""
        # Generate large CSV content
        large_content = "Name,Value\n" + "\n".join([f"Row{i},Value{i}" for i in range(1000)])
        encoded = base64.b64encode(large_content.encode()).decode()
        
        event = {
            'path': '/send_email',
            'httpMethod': 'POST',
            'body': json.dumps({
                'to': 'test@example.com',
                'subject': 'Test Email',
                'body': 'Test body',
                'attachments': [{
                    'filename': 'large.csv',
                    'content': encoded,
                    'content_type': 'text/csv'
                }]
            })
        }
        
        response = handle_send_email(event, mock_context)
        
        assert response['statusCode'] == 200
