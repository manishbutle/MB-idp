"""
Lambda Authorizer for API Gateway
Validates session tokens and enforces authentication
"""
import json
import os
import boto3
from typing import Dict, Any

# Initialize AWS clients
cognito_client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

# Environment variables
USER_POOL_ID = os.environ.get('USER_POOL_ID', '')
USERS_TABLE = os.environ.get('USERS_TABLE', 'idp_users')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda authorizer handler for API Gateway
    
    Args:
        event: API Gateway authorizer event
        context: Lambda context
        
    Returns:
        IAM policy document allowing or denying access
    """
    try:
        # Extract token from Authorization header
        token = event.get('authorizationToken', '')
        
        if not token:
            print("No authorization token provided")
            raise Exception('Unauthorized')
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Validate token with Cognito
        user_info = validate_token(token)
        
        if not user_info:
            print("Token validation failed")
            raise Exception('Unauthorized')
        
        # Extract user details
        email = user_info.get('email', '')
        tenant = user_info.get('custom:tenant', '')
        role = user_info.get('custom:role', 'User')
        
        # Generate IAM policy
        policy = generate_policy(
            principal_id=email,
            effect='Allow',
            resource=event['methodArn'],
            context={
                'email': email,
                'tenant': tenant,
                'role': role
            }
        )
        
        print(f"Authorization successful for user: {email}")
        return policy
        
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        # Return deny policy
        return generate_policy(
            principal_id='user',
            effect='Deny',
            resource=event['methodArn']
        )


def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token with Cognito
    
    Args:
        token: JWT access token
        
    Returns:
        User information from token
    """
    try:
        # Get user information from Cognito
        response = cognito_client.get_user(
            AccessToken=token
        )
        
        # Extract user attributes
        user_info = {}
        for attr in response.get('UserAttributes', []):
            user_info[attr['Name']] = attr['Value']
        
        return user_info
        
    except cognito_client.exceptions.NotAuthorizedException:
        print("Token is not authorized")
        return None
    except cognito_client.exceptions.UserNotFoundException:
        print("User not found")
        return None
    except Exception as e:
        print(f"Token validation error: {str(e)}")
        return None


def generate_policy(principal_id: str, effect: str, resource: str, 
                    context: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Generate IAM policy document
    
    Args:
        principal_id: User identifier
        effect: 'Allow' or 'Deny'
        resource: API Gateway resource ARN
        context: Additional context to pass to Lambda
        
    Returns:
        IAM policy document
    """
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    # Add context if provided
    if context:
        policy['context'] = context
    
    return policy


def verify_role_access(role: str, endpoint: str) -> bool:
    """
    Verify if user role has access to specific endpoint
    
    Args:
        role: User role (User, System User)
        endpoint: API endpoint path
        
    Returns:
        True if access is allowed, False otherwise
    """
    # Admin endpoints require System User role
    admin_endpoints = ['/add_credit']
    
    if endpoint in admin_endpoints:
        return role == 'System User'
    
    # All other authenticated endpoints allow any role
    return True
