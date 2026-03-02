"""
Unit tests for Lambda Authorizer
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from handler import (
    lambda_handler,
    validate_token,
    generate_policy,
    verify_role_access
)


class TestLambdaAuthorizer:
    """Test cases for Lambda Authorizer"""
    
    def test_generate_policy_allow(self):
        """Test generating Allow policy"""
        policy = generate_policy(
            principal_id='test@example.com',
            effect='Allow',
            resource='arn:aws:execute-api:us-east-1:123456789012:abcdef/*/GET/test',
            context={'email': 'test@example.com', 'tenant': 'tenant1'}
        )
        
        assert policy['principalId'] == 'test@example.com'
        assert policy['policyDocument']['Statement'][0]['Effect'] == 'Allow'
        assert policy['context']['email'] == 'test@example.com'
    
    def test_generate_policy_deny(self):
        """Test generating Deny policy"""
        policy = generate_policy(
            principal_id='user',
            effect='Deny',
            resource='arn:aws:execute-api:us-east-1:123456789012:abcdef/*/GET/test'
        )
        
        assert policy['principalId'] == 'user'
        assert policy['policyDocument']['Statement'][0]['Effect'] == 'Deny'
        assert 'context' not in policy
    
    def test_verify_role_access_admin_endpoint_system_user(self):
        """Test System User can access admin endpoints"""
        assert verify_role_access('System User', '/add_credit') is True
    
    def test_verify_role_access_admin_endpoint_regular_user(self):
        """Test regular User cannot access admin endpoints"""
        assert verify_role_access('User', '/add_credit') is False
    
    def test_verify_role_access_regular_endpoint(self):
        """Test any role can access regular endpoints"""
        assert verify_role_access('User', '/process_document') is True
        assert verify_role_access('System User', '/process_document') is True
    
    @patch('handler.cognito_client')
    def test_validate_token_success(self, mock_cognito):
        """Test successful token validation"""
        mock_cognito.get_user.return_value = {
            'UserAttributes': [
                {'Name': 'email', 'Value': 'test@example.com'},
                {'Name': 'custom:tenant', 'Value': 'tenant1'},
                {'Name': 'custom:role', 'Value': 'User'}
            ]
        }
        
        user_info = validate_token('valid_token')
        
        assert user_info is not None
        assert user_info['email'] == 'test@example.com'
        assert user_info['custom:tenant'] == 'tenant1'
        assert user_info['custom:role'] == 'User'
    
    @patch('handler.cognito_client')
    def test_validate_token_not_authorized(self, mock_cognito):
        """Test token validation with unauthorized token"""
        from botocore.exceptions import ClientError
        
        mock_cognito.get_user.side_effect = ClientError(
            {'Error': {'Code': 'NotAuthorizedException'}},
            'GetUser'
        )
        mock_cognito.exceptions.NotAuthorizedException = ClientError
        
        user_info = validate_token('invalid_token')
        
        assert user_info is None
    
    @patch('handler.validate_token')
    def test_lambda_handler_success(self, mock_validate):
        """Test successful authorization"""
        mock_validate.return_value = {
            'email': 'test@example.com',
            'custom:tenant': 'tenant1',
            'custom:role': 'User'
        }
        
        event = {
            'authorizationToken': 'Bearer valid_token',
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:abcdef/*/POST/process_document'
        }
        
        result = lambda_handler(event, None)
        
        assert result['principalId'] == 'test@example.com'
        assert result['policyDocument']['Statement'][0]['Effect'] == 'Allow'
        assert result['context']['email'] == 'test@example.com'
    
    @patch('handler.validate_token')
    def test_lambda_handler_no_token(self, mock_validate):
        """Test authorization with no token"""
        event = {
            'authorizationToken': '',
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:abcdef/*/POST/process_document'
        }
        
        result = lambda_handler(event, None)
        
        assert result['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    
    @patch('handler.validate_token')
    def test_lambda_handler_invalid_token(self, mock_validate):
        """Test authorization with invalid token"""
        mock_validate.return_value = None
        
        event = {
            'authorizationToken': 'Bearer invalid_token',
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:abcdef/*/POST/process_document'
        }
        
        result = lambda_handler(event, None)
        
        assert result['policyDocument']['Statement'][0]['Effect'] == 'Deny'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
