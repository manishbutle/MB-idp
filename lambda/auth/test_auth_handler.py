"""
Unit tests for Auth Lambda function
Tests authentication, session management, password reset, and registration
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import handler


# Mock Lambda context
class MockLambdaContext:
    """Mock Lambda context for testing"""
    def __init__(self):
        self.function_name = 'test-function'
        self.function_version = '$LATEST'
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        self.memory_limit_in_mb = 128
        self.aws_request_id = 'test-request-id'
        self.log_group_name = '/aws/lambda/test-function'
        self.log_stream_name = '2024/01/01/[$LATEST]test'
    
    def get_remaining_time_in_millis(self):
        return 30000


class TestAuthentication:
    """Tests for user authentication"""
    
    @patch('handler.dynamodb')
    @patch('handler.cognito')
    def test_auth_success(self, mock_cognito, mock_dynamodb):
        """Test successful authentication"""
        # Mock user data
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'email': 'test@example.com',
                'password_hash': handler.hash_password('password123'),
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'User',
                'tenant': 'tenant1',
                'is_active': True
            }
        }
        
        # Mock Cognito session
        mock_cognito.admin_user_global_sign_out.return_value = {}
        mock_cognito.admin_initiate_auth.return_value = {
            'AuthenticationResult': {'IdToken': 'test_token_123'}
        }
        
        # Create event
        event = {
            'path': '/auth',
            'body': json.dumps({
                'email': 'test@example.com',
                'password': 'password123'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'token' in body
        assert body['user']['email'] == 'test@example.com'
    
    @patch('handler.dynamodb')
    def test_auth_invalid_credentials(self, mock_dynamodb):
        """Test authentication with invalid credentials returns 401"""
        # Mock user data
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'email': 'test@example.com',
                'password_hash': handler.hash_password('correct_password'),
                'is_active': True
            }
        }
        
        # Create event with wrong password
        event = {
            'path': '/auth',
            'body': json.dumps({
                'email': 'test@example.com',
                'password': 'wrong_password'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error'] == 'Unauthorized'
    
    @patch('handler.dynamodb')
    def test_auth_user_not_found(self, mock_dynamodb):
        """Test authentication with non-existent user returns 401"""
        # Mock no user found
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}
        
        # Create event
        event = {
            'path': '/auth',
            'body': json.dumps({
                'email': 'nonexistent@example.com',
                'password': 'password123'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions
        assert response['statusCode'] == 401


class TestPasswordReset:
    """Tests for password reset functionality"""
    
    @patch('handler.ses')
    @patch('handler.dynamodb')
    def test_forget_password_success(self, mock_dynamodb, mock_ses):
        """Test password reset request"""
        # Mock user exists
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {'email': 'test@example.com'}
        }
        mock_table.update_item.return_value = {}
        
        # Mock SES
        mock_ses.send_email.return_value = {}
        
        # Create event
        event = {
            'path': '/forget_password',
            'body': json.dumps({'email': 'test@example.com'})
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'reset link' in body['message'].lower()
    
    @patch('handler.dynamodb')
    def test_reset_password_invalid_token(self, mock_dynamodb):
        """Test password reset with invalid token"""
        # Mock no user found with token
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.scan.return_value = {'Items': []}
        
        # Create event
        event = {
            'path': '/reset_password',
            'body': json.dumps({
                'token': 'invalid_token',
                'new_password': 'newpassword123'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'invalid' in body['message'].lower() or 'expired' in body['message'].lower()


class TestUserRegistration:
    """Tests for user registration"""
    
    @patch('handler.dynamodb')
    def test_sign_up_success(self, mock_dynamodb):
        """Test successful user registration"""
        # Mock no existing user
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}
        mock_table.put_item.return_value = {}
        
        # Create event
        event = {
            'path': '/sign_up',
            'body': json.dumps({
                'email': 'newuser@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'contact_number': '1234567890',
                'password': 'password123',
                'confirm_password': 'password123'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'registered successfully' in body['message'].lower()
    
    @patch('handler.dynamodb')
    def test_sign_up_duplicate_email(self, mock_dynamodb):
        """Test registration with duplicate email returns 409"""
        # Mock existing user
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {'email': 'existing@example.com'}
        }
        
        # Create event
        event = {
            'path': '/sign_up',
            'body': json.dumps({
                'email': 'existing@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'contact_number': '1234567890',
                'password': 'password123',
                'confirm_password': 'password123'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'already exists' in body['message'].lower()
    
    @patch('handler.dynamodb')
    def test_sign_up_password_mismatch(self, mock_dynamodb):
        """Test registration with mismatched passwords"""
        # Create event
        event = {
            'path': '/sign_up',
            'body': json.dumps({
                'email': 'newuser@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'contact_number': '1234567890',
                'password': 'password123',
                'confirm_password': 'different_password'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'do not match' in body['message'].lower()


class TestPasswordHashing:
    """Tests for password hashing functionality"""
    
    def test_password_hash_irreversibility(self):
        """Test that password hashes cannot be reversed"""
        password = 'test_password_123'
        hashed = handler.hash_password(password)
        
        # Hash should not contain the original password
        assert password not in hashed
        
        # Hash should be different each time (due to salt)
        hashed2 = handler.hash_password(password)
        assert hashed != hashed2
        
        # Both hashes should verify correctly
        assert handler.verify_password(password, hashed)
        assert handler.verify_password(password, hashed2)
    
    def test_password_verification(self):
        """Test password verification"""
        password = 'correct_password'
        hashed = handler.hash_password(password)
        
        # Correct password should verify
        assert handler.verify_password(password, hashed)
        
        # Wrong password should not verify
        assert not handler.verify_password('wrong_password', hashed)


class TestSessionManagement:
    """Tests for session management"""
    
    @patch('handler.cognito')
    def test_destroy_previous_sessions(self, mock_cognito):
        """Test that previous sessions are destroyed on new login"""
        mock_cognito.admin_user_global_sign_out.return_value = {}
        
        result = handler.destroy_previous_sessions('test@example.com')
        
        # Should call Cognito to sign out
        mock_cognito.admin_user_global_sign_out.assert_called_once()
        assert result is True
    
    @patch('handler.dynamodb')
    def test_session_token_expiration(self, mock_dynamodb):
        """Test password reset with expired token"""
        # Mock user with expired reset token
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Create expired token (24 hours + 1 minute ago)
        expired_time = datetime.utcnow() - timedelta(hours=24, minutes=1)
        
        mock_table.scan.return_value = {
            'Items': [{
                'email': 'test@example.com',
                'reset_token': 'valid_token_format',
                'reset_token_expiry': expired_time.isoformat(),
                'tenant': 'tenant1'
            }]
        }
        
        # Create event with valid token format but expired
        event = {
            'path': '/reset_password',
            'body': json.dumps({
                'token': 'valid_token_format',
                'new_password': 'newpassword123'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions - should reject expired token
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'expired' in body['message'].lower() or 'invalid' in body['message'].lower()
    
    @patch('handler.dynamodb')
    def test_session_token_not_expired(self, mock_dynamodb):
        """Test password reset with valid non-expired token"""
        # Mock user with valid reset token
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Create non-expired token (1 hour ago)
        valid_time = datetime.utcnow() + timedelta(hours=1)
        
        mock_table.scan.return_value = {
            'Items': [{
                'email': 'test@example.com',
                'reset_token': 'valid_token',
                'reset_token_expiry': valid_time.isoformat(),
                'tenant': 'tenant1'
            }]
        }
        
        mock_table.update_item.return_value = {}
        
        # Create event with valid token
        event = {
            'path': '/reset_password',
            'body': json.dumps({
                'token': 'valid_token',
                'new_password': 'newpassword123'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions - should accept valid token
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'successfully' in body['message'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
