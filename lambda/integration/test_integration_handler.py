"""
Unit tests for Integration Lambda Function
"""

import json
import base64
import pytest
from unittest.mock import Mock, patch, MagicMock
from handler import lambda_handler, handle_ftp, handle_send_email, get_ftp_credentials


@pytest.fixture(autouse=True)
def mock_logger():
    """Mock logger for all tests"""
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


class TestGetFTPCredentials:
    """Test FTP credentials retrieval from Secrets Manager"""
    
    @patch('handler.secrets_manager')
    def test_get_ftp_credentials_success(self, mock_secrets_manager):
        """Test successful retrieval of FTP credentials"""
        # Arrange
        mock_credentials = {
            'host': 'ftp.example.com',
            'port': 21,
            'username': 'testuser',
            'password': 'testpass'
        }
        mock_secrets_manager.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_credentials)
        }
        
        # Act
        result = get_ftp_credentials('test-secret')
        
        # Assert
        assert result == mock_credentials
        mock_secrets_manager.get_secret_value.assert_called_once_with(SecretId='test-secret')
    
    @patch('handler.secrets_manager')
    def test_get_ftp_credentials_failure(self, mock_secrets_manager):
        """Test failure to retrieve FTP credentials"""
        # Arrange
        mock_secrets_manager.get_secret_value.side_effect = Exception('Secret not found')
        
        # Act & Assert
        with pytest.raises(Exception, match='Secret not found'):
            get_ftp_credentials('invalid-secret')


class TestHandleFTP:
    """Test FTP upload handler"""
    
    @patch('handler.secrets_manager')
    @patch('ftplib.FTP')
    def test_ftp_upload_success(self, mock_ftp_class, mock_secrets_manager):
        """Test successful FTP upload"""
        # Arrange
        mock_credentials = {
            'host': 'ftp.example.com',
            'port': 21,
            'username': 'testuser',
            'password': 'testpass'
        }
        mock_secrets_manager.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_credentials)
        }
        
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        
        file_content = b'test,data\n1,2'
        encoded_content = base64.b64encode(file_content).decode('utf-8')
        
        event = {
            'body': json.dumps({
                'file_name': 'test.csv',
                'file_content': encoded_content,
                'remote_directory': '/uploads'
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'File uploaded successfully'
        assert body['file_name'] == 'test.csv'
        assert body['remote_directory'] == '/uploads'
        
        # Verify FTP operations
        mock_ftp.connect.assert_called_once_with('ftp.example.com', 21, timeout=30)
        mock_ftp.login.assert_called_once_with('testuser', 'testpass')
        mock_ftp.cwd.assert_called_once_with('/uploads')
        mock_ftp.storbinary.assert_called_once()
        mock_ftp.quit.assert_called_once()
    
    @patch('handler.secrets_manager')
    @patch('ftplib.FTP')
    def test_ftp_upload_default_directory(self, mock_ftp_class, mock_secrets_manager):
        """Test FTP upload to default directory (no remote_directory specified)"""
        # Arrange
        mock_credentials = {
            'host': 'ftp.example.com',
            'port': 21,
            'username': 'testuser',
            'password': 'testpass'
        }
        mock_secrets_manager.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_credentials)
        }
        
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        
        file_content = b'test data'
        encoded_content = base64.b64encode(file_content).decode('utf-8')
        
        event = {
            'body': json.dumps({
                'file_name': 'test.txt',
                'file_content': encoded_content
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['remote_directory'] == 'default'
        
        # Verify cwd was not called (using default directory)
        mock_ftp.cwd.assert_not_called()
    
    @patch('handler.secrets_manager')
    @patch('ftplib.FTP')
    def test_ftp_upload_create_directory(self, mock_ftp_class, mock_secrets_manager):
        """Test FTP upload creates directory if it doesn't exist"""
        # Arrange
        mock_credentials = {
            'host': 'ftp.example.com',
            'port': 21,
            'username': 'testuser',
            'password': 'testpass'
        }
        mock_secrets_manager.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_credentials)
        }
        
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        
        # Simulate directory not existing on first cwd, then succeeding after mkd
        import ftplib
        mock_ftp.cwd.side_effect = [ftplib.error_perm('550 Directory not found'), None]
        
        file_content = b'test data'
        encoded_content = base64.b64encode(file_content).decode('utf-8')
        
        event = {
            'body': json.dumps({
                'file_name': 'test.txt',
                'file_content': encoded_content,
                'remote_directory': '/new_uploads'
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        mock_ftp.mkd.assert_called_once_with('/new_uploads')
        assert mock_ftp.cwd.call_count == 2
    
    def test_ftp_missing_file_name(self):
        """Test FTP upload with missing file_name"""
        # Arrange
        event = {
            'body': json.dumps({
                'file_content': 'dGVzdA=='
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'file_name' in body['message']
    
    def test_ftp_missing_file_content(self):
        """Test FTP upload with missing file_content"""
        # Arrange
        event = {
            'body': json.dumps({
                'file_name': 'test.txt'
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'file_content' in body['message']
    
    @patch('handler.secrets_manager')
    def test_ftp_invalid_base64_content(self, mock_secrets_manager):
        """Test FTP upload with invalid base64 content"""
        # Arrange
        mock_credentials = {
            'host': 'ftp.example.com',
            'port': 21,
            'username': 'testuser',
            'password': 'testpass'
        }
        mock_secrets_manager.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_credentials)
        }
        
        event = {
            'body': json.dumps({
                'file_name': 'test.txt',
                'file_content': 'not-valid-base64!!!'
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'encoding' in body['message']
    
    @patch('handler.secrets_manager')
    def test_ftp_credentials_retrieval_failure(self, mock_secrets_manager):
        """Test FTP upload when credentials cannot be retrieved"""
        # Arrange
        mock_secrets_manager.get_secret_value.side_effect = Exception('Secret not found')
        
        event = {
            'body': json.dumps({
                'file_name': 'test.txt',
                'file_content': base64.b64encode(b'test').decode('utf-8')
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'Internal Server Error'
        assert 'credentials' in body['message']
    
    @patch('handler.secrets_manager')
    def test_ftp_incomplete_credentials(self, mock_secrets_manager):
        """Test FTP upload with incomplete credentials"""
        # Arrange
        mock_credentials = {
            'host': 'ftp.example.com',
            # Missing username and password
        }
        mock_secrets_manager.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_credentials)
        }
        
        event = {
            'body': json.dumps({
                'file_name': 'test.txt',
                'file_content': base64.b64encode(b'test').decode('utf-8')
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'Configuration Error'
        assert 'Incomplete' in body['message']
    
    @patch('handler.secrets_manager')
    @patch('ftplib.FTP')
    def test_ftp_connection_failure(self, mock_ftp_class, mock_secrets_manager):
        """Test FTP upload with connection failure"""
        # Arrange
        mock_credentials = {
            'host': 'ftp.example.com',
            'port': 21,
            'username': 'testuser',
            'password': 'testpass'
        }
        mock_secrets_manager.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_credentials)
        }
        
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        mock_ftp.connect.side_effect = Exception('Connection refused')
        
        event = {
            'body': json.dumps({
                'file_name': 'test.txt',
                'file_content': base64.b64encode(b'test').decode('utf-8')
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error'] == 'Service Unavailable'
        assert 'connection failed' in body['message'].lower()
    
    @patch('handler.secrets_manager')
    @patch('ftplib.FTP')
    def test_ftp_permission_error(self, mock_ftp_class, mock_secrets_manager):
        """Test FTP upload with permission error"""
        # Arrange
        mock_credentials = {
            'host': 'ftp.example.com',
            'port': 21,
            'username': 'testuser',
            'password': 'testpass'
        }
        mock_secrets_manager.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_credentials)
        }
        
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        
        import ftplib
        mock_ftp.storbinary.side_effect = ftplib.error_perm('550 Permission denied')
        
        event = {
            'body': json.dumps({
                'file_name': 'test.txt',
                'file_content': base64.b64encode(b'test').decode('utf-8')
            })
        }
        context = Mock()
        
        # Act
        response = handle_ftp(event, context)
        
        # Assert
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error'] == 'Service Unavailable'
        assert 'permission' in body['message'].lower()


class TestLambdaHandler:
    """Test main Lambda handler routing"""
    
    @patch('handler.handle_ftp')
    def test_lambda_handler_routes_ftp(self, mock_handle_ftp):
        """Test Lambda handler routes to FTP handler"""
        # Arrange
        mock_handle_ftp.return_value = {'statusCode': 200, 'body': '{}'}
        event = {'path': '/ftp'}
        context = Mock()
        
        # Act
        response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        mock_handle_ftp.assert_called_once_with(event, context)
    
    @patch('handler.handle_send_email')
    def test_lambda_handler_routes_email(self, mock_handle_send_email):
        """Test Lambda handler routes to email handler"""
        # Arrange
        mock_handle_send_email.return_value = {'statusCode': 200, 'body': '{}'}
        event = {'path': '/send_email'}
        context = Mock()
        
        # Act
        response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        mock_handle_send_email.assert_called_once_with(event, context)
    
    def test_lambda_handler_unknown_path(self):
        """Test Lambda handler with unknown path"""
        # Arrange
        event = {'path': '/unknown'}
        context = Mock()
        
        # Act
        response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'Not found'


class TestHandleSendEmail:
    """Test email sending handler"""
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_simple_email_success(self, mock_ses):
        """Test successful simple email sending without attachments"""
        # Arrange
        mock_ses.send_email.return_value = {
            'MessageId': 'test-message-id-123'
        }
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Test Subject',
                'body': 'Test email body'
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Email sent successfully'
        assert body['message_id'] == 'test-message-id-123'
        
        # Verify SES call
        mock_ses.send_email.assert_called_once()
        call_args = mock_ses.send_email.call_args[1]
        assert call_args['Source'] == 'sender@example.com'
        assert call_args['Destination']['ToAddresses'] == ['recipient@example.com']
        assert call_args['Message']['Subject']['Data'] == 'Test Subject'
        assert call_args['Message']['Body']['Text']['Data'] == 'Test email body'
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_email_with_cc(self, mock_ses):
        """Test email sending with CC address"""
        # Arrange
        mock_ses.send_email.return_value = {
            'MessageId': 'test-message-id-456'
        }
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'cc': 'cc@example.com',
                'subject': 'Test Subject',
                'body': 'Test email body'
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        
        # Verify CC address is included
        call_args = mock_ses.send_email.call_args[1]
        assert call_args['Destination']['CcAddresses'] == ['cc@example.com']
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_email_with_csv_attachment(self, mock_ses):
        """Test email sending with CSV attachment (Requirement 18.4)"""
        # Arrange
        mock_ses.send_raw_email.return_value = {
            'MessageId': 'test-message-id-789'
        }
        
        csv_content = b'field1,field2\nvalue1,value2'
        encoded_csv = base64.b64encode(csv_content).decode('utf-8')
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Data Export',
                'body': 'Please find attached data',
                'attachments': [
                    {
                        'filename': 'data.csv',
                        'content': encoded_csv,
                        'content_type': 'text/csv'
                    }
                ]
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Email sent successfully'
        assert body['attachments_count'] == 1
        
        # Verify raw email was sent
        mock_ses.send_raw_email.assert_called_once()
        call_args = mock_ses.send_raw_email.call_args[1]
        assert call_args['Source'] == 'sender@example.com'
        assert 'recipient@example.com' in call_args['Destinations']
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_email_with_xlsx_attachment(self, mock_ses):
        """Test email sending with XLSX attachment (Requirement 18.5)"""
        # Arrange
        mock_ses.send_raw_email.return_value = {
            'MessageId': 'test-message-id-xlsx'
        }
        
        # Mock XLSX binary content
        xlsx_content = b'PK\x03\x04...'  # Simplified XLSX header
        encoded_xlsx = base64.b64encode(xlsx_content).decode('utf-8')
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Data Export',
                'body': 'Please find attached data',
                'attachments': [
                    {
                        'filename': 'data.xlsx',
                        'content': encoded_xlsx,
                        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    }
                ]
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['attachments_count'] == 1
        mock_ses.send_raw_email.assert_called_once()
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_email_with_json_attachment(self, mock_ses):
        """Test email sending with JSON attachment (Requirement 18.6)"""
        # Arrange
        mock_ses.send_raw_email.return_value = {
            'MessageId': 'test-message-id-json'
        }
        
        json_content = json.dumps({'field1': 'value1', 'field2': 'value2'}).encode('utf-8')
        encoded_json = base64.b64encode(json_content).decode('utf-8')
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Data Export',
                'body': 'Please find attached data',
                'attachments': [
                    {
                        'filename': 'data.json',
                        'content': encoded_json,
                        'content_type': 'application/json'
                    }
                ]
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['attachments_count'] == 1
        mock_ses.send_raw_email.assert_called_once()
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_email_with_multiple_attachments(self, mock_ses):
        """Test email sending with multiple attachments (Requirement 18.7)"""
        # Arrange
        mock_ses.send_raw_email.return_value = {
            'MessageId': 'test-message-id-multi'
        }
        
        csv_content = b'field1,field2\nvalue1,value2'
        json_content = json.dumps({'data': 'test'}).encode('utf-8')
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Multiple Attachments',
                'body': 'Please find attached files',
                'attachments': [
                    {
                        'filename': 'data.csv',
                        'content': base64.b64encode(csv_content).decode('utf-8'),
                        'content_type': 'text/csv'
                    },
                    {
                        'filename': 'data.json',
                        'content': base64.b64encode(json_content).decode('utf-8'),
                        'content_type': 'application/json'
                    }
                ]
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['attachments_count'] == 2
        mock_ses.send_raw_email.assert_called_once()
    
    def test_send_email_missing_to_address(self):
        """Test email sending with missing 'to' address"""
        # Arrange
        event = {
            'body': json.dumps({
                'subject': 'Test',
                'body': 'Test body'
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'to address' in body['message']
    
    def test_send_email_missing_subject(self):
        """Test email sending with missing subject"""
        # Arrange
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'body': 'Test body'
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'subject' in body['message']
    
    def test_send_email_missing_body(self):
        """Test email sending with missing body"""
        # Arrange
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Test'
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'body' in body['message']
    
    def test_send_email_invalid_json(self):
        """Test email sending with invalid JSON"""
        # Arrange
        event = {
            'body': 'not valid json'
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'JSON' in body['message']
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_email_ses_failure(self, mock_ses):
        """Test email sending when SES fails (Requirement 18.9)"""
        # Arrange
        mock_ses.send_email.side_effect = Exception('SES service unavailable')
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Test',
                'body': 'Test body'
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'Internal Server Error'
        assert 'Failed to send email' in body['message']
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_email_with_invalid_attachment(self, mock_ses):
        """Test email sending with invalid attachment (missing filename)"""
        # Arrange
        mock_ses.send_raw_email.return_value = {
            'MessageId': 'test-message-id'
        }
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Test',
                'body': 'Test body',
                'attachments': [
                    {
                        # Missing filename
                        'content': base64.b64encode(b'test').decode('utf-8'),
                        'content_type': 'text/plain'
                    }
                ]
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        # Should still succeed but skip invalid attachment
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['attachments_count'] == 1  # Count includes invalid attachment
    
    @patch('handler.ses')
    @patch.dict('os.environ', {'SES_SENDER_EMAIL': 'sender@example.com'})
    def test_send_email_with_invalid_base64_attachment(self, mock_ses):
        """Test email sending with invalid base64 attachment content"""
        # Arrange
        mock_ses.send_raw_email.return_value = {
            'MessageId': 'test-message-id'
        }
        
        event = {
            'body': json.dumps({
                'to': 'recipient@example.com',
                'subject': 'Test',
                'body': 'Test body',
                'attachments': [
                    {
                        'filename': 'test.txt',
                        'content': 'not-valid-base64!!!',
                        'content_type': 'text/plain'
                    }
                ]
            })
        }
        context = Mock()
        
        # Act
        response = handle_send_email(event, context)
        
        # Assert
        # Should still succeed but skip invalid attachment
        assert response['statusCode'] == 200
