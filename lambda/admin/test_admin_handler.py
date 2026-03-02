"""
Unit tests for Admin Lambda handler
Tests non-System User rejection, invalid credit amount, and target user not found scenarios
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

# Import handler functions
from handler import (
    handle_add_credit,
    validate_system_user,
    get_user_by_email,
    get_user_from_token
)


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource"""
    with patch('handler.dynamodb') as mock_db:
        yield mock_db


@pytest.fixture
def mock_logger():
    """Mock logger to prevent actual logging during tests"""
    with patch('handler.logger') as mock_log:
        # Mock all logger methods
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
def mock_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = 'test-request-id'
    context.function_name = 'test-admin-function'
    return context


@pytest.fixture
def system_user_event():
    """Event with System_User role"""
    return {
        'path': '/add_credit',
        'httpMethod': 'POST',
        'user_email': 'admin@example.com',
        'tenant': 'tenant1',
        'role': 'System_User',
        'body': json.dumps({
            'email': 'user@example.com',
            'amount': 100.0,
            'remark': 'Test credit'
        })
    }


@pytest.fixture
def regular_user_event():
    """Event with regular User role"""
    return {
        'path': '/add_credit',
        'httpMethod': 'POST',
        'user_email': 'user@example.com',
        'tenant': 'tenant1',
        'role': 'User',
        'body': json.dumps({
            'email': 'target@example.com',
            'amount': 100.0
        })
    }


class TestValidateSystemUser:
    """Test validate_system_user function"""
    
    def test_system_user_role_valid(self, mock_logger):
        """Test that System_User role is validated correctly"""
        user = {'email': 'admin@example.com', 'role': 'System_User'}
        assert validate_system_user(user) is True
    
    def test_system_user_role_case_insensitive(self, mock_logger):
        """Test that role validation is case-insensitive"""
        user = {'email': 'admin@example.com', 'role': 'system_user'}
        assert validate_system_user(user) is True
        
        user = {'email': 'admin@example.com', 'role': 'SYSTEM_USER'}
        assert validate_system_user(user) is True
    
    def test_system_user_role_with_space(self, mock_logger):
        """Test that 'system user' with space is accepted"""
        user = {'email': 'admin@example.com', 'role': 'system user'}
        assert validate_system_user(user) is True
    
    def test_regular_user_role_invalid(self, mock_logger):
        """Test that regular User role is rejected"""
        user = {'email': 'user@example.com', 'role': 'User'}
        assert validate_system_user(user) is False
    
    def test_empty_role_invalid(self, mock_logger):
        """Test that empty role is rejected"""
        user = {'email': 'user@example.com', 'role': ''}
        assert validate_system_user(user) is False
    
    def test_missing_role_invalid(self, mock_logger):
        """Test that missing role is rejected"""
        user = {'email': 'user@example.com'}
        assert validate_system_user(user) is False


class TestHandleAddCredit:
    """Test handle_add_credit function"""
    
    def test_non_system_user_rejection(self, mock_dynamodb, mock_logger, mock_context, regular_user_event):
        """
        Test that non-System User is rejected with 403 Forbidden
        Requirements: 9.5
        """
        response = handle_add_credit(regular_user_event, mock_context)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error'] == 'Forbidden'
        assert 'System_User role required' in body['message']
    
    def test_invalid_credit_amount_negative(self, mock_dynamodb, mock_logger, mock_context, system_user_event):
        """
        Test that negative credit amount is rejected with 400 Bad Request
        Requirements: 9.7
        """
        # Modify event to have negative amount
        body = json.loads(system_user_event['body'])
        body['amount'] = -50.0
        system_user_event['body'] = json.dumps(body)
        
        response = handle_add_credit(system_user_event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'positive number' in body['message']
    
    def test_invalid_credit_amount_zero(self, mock_dynamodb, mock_logger, mock_context, system_user_event):
        """
        Test that zero credit amount is rejected with 400 Bad Request
        Requirements: 9.7
        """
        # Modify event to have zero amount
        body = json.loads(system_user_event['body'])
        body['amount'] = 0
        system_user_event['body'] = json.dumps(body)
        
        response = handle_add_credit(system_user_event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'positive number' in body['message']
    
    def test_invalid_credit_amount_non_numeric(self, mock_dynamodb, mock_logger, mock_context, system_user_event):
        """
        Test that non-numeric credit amount is rejected with 400 Bad Request
        Requirements: 9.7
        """
        # Modify event to have non-numeric amount
        body = json.loads(system_user_event['body'])
        body['amount'] = 'invalid'
        system_user_event['body'] = json.dumps(body)
        
        response = handle_add_credit(system_user_event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'positive number' in body['message']
    
    def test_target_user_not_found(self, mock_dynamodb, mock_logger, mock_context, system_user_event):
        """
        Test that non-existent target user returns 404 Not Found
        Requirements: 9.8
        """
        # Mock get_item to return no user
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # No 'Item' key means user not found
        mock_dynamodb.Table.return_value = mock_table
        
        response = handle_add_credit(system_user_event, mock_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'Not Found'
        assert 'not found' in body['message']
    
    def test_missing_email_field(self, mock_dynamodb, mock_logger, mock_context, system_user_event):
        """
        Test that missing email field returns 400 Bad Request
        Requirements: 9.7
        """
        # Modify event to remove email
        body = json.loads(system_user_event['body'])
        del body['email']
        system_user_event['body'] = json.dumps(body)
        
        response = handle_add_credit(system_user_event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'Missing required fields' in body['message']
    
    def test_missing_amount_field(self, mock_dynamodb, mock_logger, mock_context, system_user_event):
        """
        Test that missing amount field returns 400 Bad Request
        Requirements: 9.7
        """
        # Modify event to remove amount
        body = json.loads(system_user_event['body'])
        del body['amount']
        system_user_event['body'] = json.dumps(body)
        
        response = handle_add_credit(system_user_event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'Missing required fields' in body['message']
    
    def test_successful_credit_addition(self, mock_dynamodb, mock_logger, mock_context, system_user_event):
        """
        Test successful credit addition by System_User
        Requirements: 9.3, 9.4, 9.6
        """
        # Mock get_item to return a valid user
        mock_users_table = Mock()
        mock_users_table.get_item.return_value = {
            'Item': {
                'email': 'user@example.com',
                'tenant': 'tenant1',
                'first_name': 'Test',
                'last_name': 'User'
            }
        }
        
        # Mock put_item for transactions table
        mock_transactions_table = Mock()
        mock_transactions_table.put_item.return_value = {}
        
        # Configure dynamodb.Table to return appropriate mocks
        def table_side_effect(table_name):
            if 'users' in table_name.lower():
                return mock_users_table
            elif 'transactions' in table_name.lower():
                return mock_transactions_table
            return Mock()
        
        mock_dynamodb.Table.side_effect = table_side_effect
        
        response = handle_add_credit(system_user_event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Credit added successfully'
        assert body['user_email'] == 'user@example.com'
        assert body['amount'] == 100.0
        assert 'transaction_id' in body
        assert 'timestamp' in body
        
        # Verify transaction was created
        mock_transactions_table.put_item.assert_called_once()
        transaction = mock_transactions_table.put_item.call_args[1]['Item']
        assert transaction['action'] == 'Admin Credit'
        assert transaction['amount'] == 100.0
        assert transaction['user_email'] == 'user@example.com'
        assert transaction['admin_email'] == 'admin@example.com'
    
    def test_unauthorized_missing_token(self, mock_dynamodb, mock_logger, mock_context):
        """
        Test that missing authentication token returns 401 Unauthorized
        """
        event = {
            'path': '/add_credit',
            'httpMethod': 'POST',
            'body': json.dumps({
                'email': 'user@example.com',
                'amount': 100.0
            })
        }
        
        response = handle_add_credit(event, mock_context)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error'] == 'Unauthorized'
    
    def test_database_error_handling(self, mock_dynamodb, mock_logger, mock_context, system_user_event):
        """
        Test that database errors are handled gracefully
        """
        # Mock get_item to return a valid user
        mock_users_table = Mock()
        mock_users_table.get_item.return_value = {
            'Item': {
                'email': 'user@example.com',
                'tenant': 'tenant1'
            }
        }
        
        # Mock put_item to raise an exception
        from botocore.exceptions import ClientError
        mock_transactions_table = Mock()
        mock_transactions_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Database error'}},
            'PutItem'
        )
        
        def table_side_effect(table_name):
            if 'users' in table_name.lower():
                return mock_users_table
            elif 'transactions' in table_name.lower():
                return mock_transactions_table
            return Mock()
        
        mock_dynamodb.Table.side_effect = table_side_effect
        
        response = handle_add_credit(system_user_event, mock_context)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'Internal Server Error'
