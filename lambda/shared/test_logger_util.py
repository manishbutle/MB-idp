"""
Unit tests for logging utility module
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger_util import StructuredLogger, create_logger


class TestStructuredLogger:
    """Test cases for StructuredLogger class"""
    
    def test_logger_initialization(self):
        """Test logger initializes with service name"""
        logger = StructuredLogger('test-service')
        assert logger.service_name == 'test-service'
        assert logger.context_data == {}
    
    def test_set_context(self):
        """Test setting context data"""
        logger = StructuredLogger('test-service')
        
        logger.set_context(
            request_id='req-123',
            user_email='user@example.com',
            tenant='tenant-1',
            custom_field='custom_value'
        )
        
        assert logger.context_data['request_id'] == 'req-123'
        assert logger.context_data['user_email'] == 'user@example.com'
        assert logger.context_data['tenant'] == 'tenant-1'
        assert logger.context_data['custom_field'] == 'custom_value'
    
    def test_clear_context(self):
        """Test clearing context data"""
        logger = StructuredLogger('test-service')
        logger.set_context(request_id='req-123', user_email='user@example.com')
        
        assert len(logger.context_data) > 0
        
        logger.clear_context()
        
        assert logger.context_data == {}
    
    def test_build_log_data(self):
        """Test building structured log data"""
        logger = StructuredLogger('test-service')
        logger.set_context(request_id='req-123', user_email='user@example.com')
        
        log_data = logger._build_log_data(
            'Test message',
            processing_id='proc-456',
            pages=5
        )
        
        assert log_data['message'] == 'Test message'
        assert log_data['service'] == 'test-service'
        assert log_data['request_id'] == 'req-123'
        assert log_data['user_email'] == 'user@example.com'
        assert log_data['processing_id'] == 'proc-456'
        assert log_data['pages'] == 5
        assert 'timestamp' in log_data
    
    @patch('logger_util.Logger')
    def test_log_info(self, mock_logger_class):
        """Test logging info message"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.set_context(request_id='req-123')
        
        logger.log_info('Test info message', processing_id='proc-456')
        
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        assert call_args[0][0] == 'Test info message'
        assert 'extra' in call_args[1]
        assert call_args[1]['extra']['processing_id'] == 'proc-456'
    
    @patch('logger_util.Logger')
    def test_log_error_with_exception(self, mock_logger_class):
        """Test logging error with exception and stack trace"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            logger.log_error('Error occurred', error=e, processing_id='proc-456')
        
        mock_logger_instance.error.assert_called_once()
        call_args = mock_logger_instance.error.call_args
        assert call_args[0][0] == 'Error occurred'
        assert 'extra' in call_args[1]
        
        extra_data = call_args[1]['extra']
        assert extra_data['level'] == 'ERROR'
        assert extra_data['error_type'] == 'ValueError'
        assert extra_data['error_message'] == 'Test error'
        assert 'stack_trace' in extra_data
        assert extra_data['processing_id'] == 'proc-456'
    
    @patch('logger_util.Logger')
    def test_log_error_without_stacktrace(self, mock_logger_class):
        """Test logging error without stack trace"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            logger.log_error('Error occurred', error=e, include_stacktrace=False)
        
        call_args = mock_logger_instance.error.call_args
        extra_data = call_args[1]['extra']
        
        assert 'stack_trace' not in extra_data
        assert extra_data['error_type'] == 'ValueError'
        assert extra_data['error_message'] == 'Test error'
    
    @patch('logger_util.Logger')
    def test_log_warning(self, mock_logger_class):
        """Test logging warning message"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_warning('Test warning', document_type='Unknown')
        
        mock_logger_instance.warning.assert_called_once()
        call_args = mock_logger_instance.warning.call_args
        assert call_args[0][0] == 'Test warning'
        assert call_args[1]['extra']['level'] == 'WARNING'
        assert call_args[1]['extra']['document_type'] == 'Unknown'
    
    @patch('logger_util.Logger')
    def test_log_execution_start(self, mock_logger_class):
        """Test logging execution start"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_execution_start('lambda_handler', event_type='process_document')
        
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        
        extra_data = call_args[1]['extra']
        assert extra_data['function_name'] == 'lambda_handler'
        assert extra_data['execution_stage'] == 'start'
        assert extra_data['event_type'] == 'process_document'
    
    @patch('logger_util.Logger')
    def test_log_execution_complete(self, mock_logger_class):
        """Test logging execution completion"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_execution_complete('lambda_handler', duration_ms=1234, status='success')
        
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        
        extra_data = call_args[1]['extra']
        assert extra_data['function_name'] == 'lambda_handler'
        assert extra_data['execution_stage'] == 'complete'
        assert extra_data['duration_ms'] == 1234
        assert extra_data['status'] == 'success'
    
    @patch('logger_util.Logger')
    def test_log_api_call(self, mock_logger_class):
        """Test logging AWS API call"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_api_call(
            'textract',
            'detect_document_text',
            duration_ms=500,
            status='success',
            pages=3
        )
        
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        
        extra_data = call_args[1]['extra']
        assert extra_data['api_service'] == 'textract'
        assert extra_data['api_operation'] == 'detect_document_text'
        assert extra_data['api_status'] == 'success'
        assert extra_data['api_duration_ms'] == 500
        assert extra_data['pages'] == 3
    
    @patch('logger_util.Logger')
    def test_log_database_operation(self, mock_logger_class):
        """Test logging database operation"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_database_operation(
            'idp_metadata',
            'put_item',
            status='success',
            processing_id='proc-123'
        )
        
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        
        extra_data = call_args[1]['extra']
        assert extra_data['db_table'] == 'idp_metadata'
        assert extra_data['db_operation'] == 'put_item'
        assert extra_data['db_status'] == 'success'
        assert extra_data['processing_id'] == 'proc-123'
    
    @patch('logger_util.Logger')
    def test_log_processing_stage(self, mock_logger_class):
        """Test logging processing stage"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_processing_stage(
            'digitization',
            'proc-123',
            duration_ms=500,
            pages=3
        )
        
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        
        extra_data = call_args[1]['extra']
        assert extra_data['processing_stage'] == 'digitization'
        assert extra_data['processing_id'] == 'proc-123'
        assert extra_data['stage_duration_ms'] == 500
        assert extra_data['pages'] == 3
    
    @patch('logger_util.Logger')
    def test_log_authentication_attempt_success(self, mock_logger_class):
        """Test logging successful authentication"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_authentication_attempt('user@example.com', 'success')
        
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        
        extra_data = call_args[1]['extra']
        assert extra_data['auth_status'] == 'success'
        assert extra_data['user_email'] == 'user@example.com'
        assert 'auth_failure_reason' not in extra_data
    
    @patch('logger_util.Logger')
    def test_log_authentication_attempt_failure(self, mock_logger_class):
        """Test logging failed authentication"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_authentication_attempt(
            'user@example.com',
            'failure',
            reason='invalid_password'
        )
        
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        
        extra_data = call_args[1]['extra']
        assert extra_data['auth_status'] == 'failure'
        assert extra_data['user_email'] == 'user@example.com'
        assert extra_data['auth_failure_reason'] == 'invalid_password'
    
    @patch('logger_util.Logger')
    def test_get_powertools_logger(self, mock_logger_class):
        """Test getting underlying powertools logger"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        powertools_logger = logger.get_powertools_logger()
        
        assert powertools_logger == mock_logger_instance


class TestCreateLogger:
    """Test cases for create_logger factory function"""
    
    def test_create_logger(self):
        """Test factory function creates logger instance"""
        logger = create_logger('test-service')
        
        assert isinstance(logger, StructuredLogger)
        assert logger.service_name == 'test-service'
    
    def test_create_logger_with_different_services(self):
        """Test creating loggers for different services"""
        process_logger = create_logger('process')
        auth_logger = create_logger('auth')
        data_logger = create_logger('data')
        
        assert process_logger.service_name == 'process'
        assert auth_logger.service_name == 'auth'
        assert data_logger.service_name == 'data'


class TestLogFormatCompliance:
    """Test cases for log format compliance"""
    
    @patch('logger_util.Logger')
    def test_timestamp_format(self, mock_logger_class):
        """Test timestamp is in ISO 8601 format"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.log_info('Test message')
        
        call_args = mock_logger_instance.info.call_args
        timestamp = call_args[1]['extra']['timestamp']
        
        # Verify ISO 8601 format by parsing
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    @patch('logger_util.Logger')
    def test_standard_fields_present(self, mock_logger_class):
        """Test all standard fields are present in logs"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.set_context(
            request_id='req-123',
            user_email='user@example.com',
            tenant='tenant-1'
        )
        logger.log_info('Test message')
        
        call_args = mock_logger_instance.info.call_args
        extra_data = call_args[1]['extra']
        
        # Verify standard fields
        assert 'timestamp' in extra_data
        assert 'service' in extra_data
        assert 'message' in extra_data
        assert 'request_id' in extra_data
        assert 'user_email' in extra_data
        assert 'tenant' in extra_data
    
    @patch('logger_util.Logger')
    def test_error_includes_stack_trace(self, mock_logger_class):
        """Test error logging includes stack trace by default"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            logger.log_error('Error occurred', error=e)
        
        call_args = mock_logger_instance.error.call_args
        extra_data = call_args[1]['extra']
        
        assert 'stack_trace' in extra_data
        assert 'ValueError' in extra_data['stack_trace']
        assert 'Test error' in extra_data['stack_trace']


class TestSensitiveDataHandling:
    """Test cases for sensitive data sanitization"""
    
    @patch('logger_util.Logger')
    def test_no_password_in_logs(self, mock_logger_class):
        """Test that passwords are not logged"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        
        # Log authentication attempt without password
        logger.log_authentication_attempt('user@example.com', 'success')
        
        call_args = mock_logger_instance.info.call_args
        extra_data = call_args[1]['extra']
        
        # Verify no password field
        assert 'password' not in extra_data
        assert 'password_hash' not in extra_data
    
    @patch('logger_util.Logger')
    def test_user_email_included(self, mock_logger_class):
        """Test that user email is included in logs (not sensitive)"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        logger = StructuredLogger('test-service')
        logger.set_context(user_email='user@example.com')
        logger.log_info('Test message')
        
        call_args = mock_logger_instance.info.call_args
        extra_data = call_args[1]['extra']
        
        # User email should be present for audit purposes
        assert extra_data['user_email'] == 'user@example.com'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
