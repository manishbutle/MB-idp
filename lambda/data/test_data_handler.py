"""
Unit tests for Data Lambda function
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal
import sys

# Mock the logger before importing handler
mock_logger_module = MagicMock()
mock_logger = MagicMock()
mock_logger.log_info = Mock()
mock_logger.log_warning = Mock()
mock_logger.log_error = Mock()
mock_logger.info = Mock()
mock_logger.warning = Mock()
mock_logger.error = Mock()
mock_logger_module.create_logger.return_value = mock_logger
sys.modules['logger_util'] = mock_logger_module

# Mock AWS services before importing handler
with patch('boto3.resource'):
    from handler import (
        handle_datapoints,
        handle_reset_prompts,
        handle_history,
        handle_mytransactions,
        handle_total_document_processed,
        handle_available_balance,
        handle_profile_change,
        handle_password_change,
        handle_top_up,
        lambda_handler
    )


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource"""
    with patch('handler.dynamodb') as mock_db:
        yield mock_db


@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = 'test-data-lambda'
    context.request_id = 'test-request-id'
    return context


@pytest.fixture
def auth_event():
    """Event with authentication"""
    return {
        'path': '/datapoints',
        'user_email': 'test@example.com',
        'tenant': 'test-tenant',
        'requestContext': {
            'authorizer': {
                'user_email': 'test@example.com',
                'tenant': 'test-tenant'
            }
        }
    }


def test_handle_datapoints_success(mock_dynamodb, mock_context, auth_event):
    """Test successful datapoints retrieval"""
    # Mock DynamoDB response
    mock_table = Mock()
    mock_table.query.return_value = {
        'Items': [
            {
                'prompt_id': 'prompt-1',
                'prompt_name': 'Invoice',
                'description': 'Invoice extraction',
                'tenant': 'test-tenant'
            }
        ]
    }
    mock_dynamodb.Table.return_value = mock_table
    
    response = handle_datapoints(auth_event, mock_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'prompts' in body
    assert len(body['prompts']) == 1


def test_handle_datapoints_unauthorized(mock_dynamodb, mock_context):
    """Test datapoints without authentication"""
    event = {'path': '/datapoints'}
    
    response = handle_datapoints(event, mock_context)
    
    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert 'error' in body


def test_handle_history_with_pagination(mock_dynamodb, mock_context, auth_event):
    """Test history retrieval with pagination"""
    auth_event['path'] = '/history'
    auth_event['queryStringParameters'] = {'page_size': '10'}
    
    # Mock DynamoDB response
    mock_table = Mock()
    mock_table.query.return_value = {
        'Items': [
            {
                'processing_id': 'proc-1',
                'document_name': 'test.pdf',
                'pages': 5
            }
        ],
        'LastEvaluatedKey': {'processing_id': 'proc-1'}
    }
    mock_dynamodb.Table.return_value = mock_table
    
    response = handle_history(auth_event, mock_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'history' in body
    assert body['has_more'] is True


def test_handle_history_invalid_page_size(mock_dynamodb, mock_context, auth_event):
    """Test history with invalid page size"""
    auth_event['path'] = '/history'
    auth_event['queryStringParameters'] = {'page_size': '200'}
    
    response = handle_history(auth_event, mock_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body


def test_handle_mytransactions_success(mock_dynamodb, mock_context, auth_event):
    """Test transaction history retrieval"""
    auth_event['path'] = '/mytransactions'
    
    # Mock DynamoDB response
    mock_table = Mock()
    mock_table.query.return_value = {
        'Items': [
            {
                'transaction_id': 'txn-1',
                'action': 'Utilized',
                'amount': -10.5
            }
        ]
    }
    mock_dynamodb.Table.return_value = mock_table
    
    response = handle_mytransactions(auth_event, mock_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'transactions' in body


def test_handle_total_document_processed(mock_dynamodb, mock_context, auth_event):
    """Test document count retrieval"""
    auth_event['path'] = '/total_document_processed'
    
    # Mock DynamoDB response
    mock_table = Mock()
    mock_table.query.return_value = {'Count': 42}
    mock_dynamodb.Table.return_value = mock_table
    
    response = handle_total_document_processed(auth_event, mock_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['total_documents'] == 42


def test_handle_available_balance(mock_dynamodb, mock_context, auth_event):
    """Test balance calculation"""
    auth_event['path'] = '/available_balance'
    
    # Mock DynamoDB response with transactions
    mock_table = Mock()
    mock_table.query.return_value = {
        'Items': [
            {'amount': 100.0},
            {'amount': -10.5},
            {'amount': -5.25}
        ]
    }
    mock_dynamodb.Table.return_value = mock_table
    
    response = handle_available_balance(auth_event, mock_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['available_balance'] == 84.25


def test_handle_profile_change_success(mock_dynamodb, mock_context, auth_event):
    """Test profile update"""
    auth_event['path'] = '/profile_change'
    auth_event['body'] = json.dumps({
        'first_name': 'John',
        'last_name': 'Doe'
    })
    
    # Mock DynamoDB update
    mock_table = Mock()
    mock_dynamodb.Table.return_value = mock_table
    
    response = handle_profile_change(auth_event, mock_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Profile updated successfully'


def test_handle_profile_change_missing_fields(mock_dynamodb, mock_context, auth_event):
    """Test profile update with missing fields"""
    auth_event['path'] = '/profile_change'
    auth_event['body'] = json.dumps({'first_name': 'John'})
    
    response = handle_profile_change(auth_event, mock_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body


def test_handle_password_change_success(mock_dynamodb, mock_context, auth_event):
    """Test password change"""
    auth_event['path'] = '/password_change'
    auth_event['body'] = json.dumps({
        'current_password': 'oldpass',
        'new_password': 'newpass',
        'confirm_password': 'newpass'
    })
    
    # Mock DynamoDB get and update
    mock_table = Mock()
    mock_table.get_item.return_value = {
        'Item': {
            'email': 'test@example.com',
            'password_hash': 'abc123$hashedpassword'
        }
    }
    mock_dynamodb.Table.return_value = mock_table
    
    with patch('handler.verify_password', return_value=True):
        response = handle_password_change(auth_event, mock_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Password changed successfully'


def test_handle_password_change_mismatch(mock_dynamodb, mock_context, auth_event):
    """Test password change with mismatched passwords"""
    auth_event['path'] = '/password_change'
    auth_event['body'] = json.dumps({
        'current_password': 'oldpass',
        'new_password': 'newpass',
        'confirm_password': 'different'
    })
    
    response = handle_password_change(auth_event, mock_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'do not match' in body['message']


def test_handle_top_up_success(mock_dynamodb, mock_context, auth_event):
    """Test credit top-up"""
    auth_event['path'] = '/top_up'
    auth_event['body'] = json.dumps({
        'amount': 100.0,
        'remark': 'Test top-up'
    })
    
    # Mock DynamoDB put
    mock_table = Mock()
    mock_dynamodb.Table.return_value = mock_table
    
    response = handle_top_up(auth_event, mock_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Credit top-up successful'
    assert body['amount'] == 100.0


def test_handle_top_up_invalid_amount(mock_dynamodb, mock_context, auth_event):
    """Test top-up with invalid amount"""
    auth_event['path'] = '/top_up'
    auth_event['body'] = json.dumps({'amount': -50})
    
    response = handle_top_up(auth_event, mock_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'greater than zero' in body['message']


def test_lambda_handler_routing(mock_dynamodb, mock_context, auth_event):
    """Test Lambda handler routes to correct function"""
    # Mock table for datapoints
    mock_table = Mock()
    mock_table.query.return_value = {'Items': []}
    mock_dynamodb.Table.return_value = mock_table
    
    # Test datapoints route
    auth_event['path'] = '/datapoints'
    response = lambda_handler(auth_event, mock_context)
    assert response['statusCode'] == 200
    
    # Test not found route
    auth_event['path'] = '/unknown'
    response = lambda_handler(auth_event, mock_context)
    assert response['statusCode'] == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
