"""
Admin Lambda Function
Handles administrative credit management
"""

import json
import os
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from logger_util import create_logger

logger = create_logger('admin')
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')

# Environment variables
USERS_TABLE = os.environ.get('USERS_TABLE', 'idp_users')
ROLES_TABLE = os.environ.get('ROLES_TABLE', 'idp_roles')
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', 'idp_transactions')


# Helper functions

def get_user_from_token(event: dict) -> Optional[Dict[str, Any]]:
    """Extract user information from session token"""
    # In production, this would validate the token with Cognito
    # For now, we'll extract user_email from the request context
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    user_email = authorizer.get('user_email') or event.get('user_email')
    tenant = authorizer.get('tenant') or event.get('tenant')
    role = authorizer.get('role') or event.get('role')
    
    if not user_email or not tenant:
        return None
    
    return {
        'email': user_email,
        'tenant': tenant,
        'role': role
    }


def validate_system_user(user: Dict[str, Any]) -> bool:
    """
    Validate that the user has System_User role
    
    Args:
        user: User dict containing email, tenant, and role
        
    Returns:
        True if user has System_User role, False otherwise
    """
    role = user.get('role', '')
    
    # Check if role is System_User (case-insensitive, handle variations)
    is_system_user = role.lower() in ['system_user', 'system user', 'systemuser']
    
    logger.log_info(f"Role validation for {user.get('email')}: role={role}, is_system_user={is_system_user}")
    
    return is_system_user


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Query user from DynamoDB by email"""
    try:
        table = dynamodb.Table(USERS_TABLE)
        response = table.get_item(Key={'email': email})
        return response.get('Item')
    except ClientError as e:
        logger.log_error(f"Error querying user: {e}")
        return None


@tracer.capture_method
def handle_add_credit(event, context):
    """
    Add credit to user account (System_User only)
    
    Requirements: 9.3, 9.4, 9.5, 9.6, 22.8
    """
    logger.log_info("Add credit request received")
    
    try:
        # Get admin user from token
        admin_user = get_user_from_token(event)
        if not admin_user:
            logger.log_warning("Unauthorized: Invalid or missing authentication token")
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Invalid or missing authentication token'
                })
            }
        
        # Validate System_User role
        if not validate_system_user(admin_user):
            logger.log_warning(f"Forbidden: User {admin_user['email']} does not have System_User role")
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Forbidden',
                    'message': 'You do not have permission to perform this action. System_User role required.'
                })
            }
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        target_email = body.get('email')
        credit_amount = body.get('amount')
        remark = body.get('remark', '')
        
        # Validate required fields
        if not target_email or credit_amount is None:
            logger.log_error("Missing required fields: email or amount")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Missing required fields: email and amount'
                })
            }
        
        # Validate credit amount
        try:
            credit_amount = float(credit_amount)
            if credit_amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError) as e:
            logger.log_error(f"Invalid credit amount: {credit_amount}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Invalid credit amount. Must be a positive number.'
                })
            }
        
        # Check if target user exists
        target_user = get_user_by_email(target_email)
        if not target_user:
            logger.log_error(f"Target user not found: {target_email}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': f'User with email {target_email} not found'
                })
            }
        
        target_tenant = target_user.get('tenant')
        
        logger.log_info(f"Adding {credit_amount} credits to user {target_email} by admin {admin_user['email']}")
        
        # Create admin transaction record
        transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
        
        transaction_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        transaction = {
            'transaction_id': transaction_id,
            'user_email': target_email,
            'tenant': target_tenant,
            'action': 'Admin Credit',
            'amount': credit_amount,  # Positive for credit addition
            'timestamp': timestamp,
            'remark': remark or f'Admin credit added by {admin_user["email"]}',
            'admin_email': admin_user['email'],  # Metadata indicating admin action
            'admin_tenant': admin_user['tenant']
        }
        
        try:
            transactions_table.put_item(Item=transaction)
            logger.log_info(f"Admin transaction created: {transaction_id}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Credit added successfully',
                    'transaction_id': transaction_id,
                    'user_email': target_email,
                    'amount': credit_amount,
                    'timestamp': timestamp
                })
            }
            
        except ClientError as e:
            logger.log_error(f"Error creating transaction", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': 'Failed to add credit. Please try again.'
                })
            }
    
    except Exception as e:
        logger.log_error(f"Unexpected error in add_credit", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred. Please try again later.'
            })
        }


@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Main Lambda handler for admin operations"""
    start_time = time.time()
    
    # Set initial context
    logger.set_context(
        request_id=context.request_id if hasattr(context, 'request_id') else 'unknown'
    )
    
    # Route to appropriate handler based on path
    path = event.get('path', '')
    http_method = event.get('httpMethod', '')
    
    logger.log_execution_start("lambda_handler", path=path, http_method=http_method)
    
    try:
        if path == '/add_credit' and http_method == 'POST':
            result = handle_add_credit(event, context)
        else:
            # Default response for unknown paths
            result = {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': 'Endpoint not found'
                })
            }
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_execution_complete("lambda_handler", duration_ms=duration_ms, status_code=result.get('statusCode'))
        
        return result
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_error("Unexpected error in lambda_handler", error=e, duration_ms=duration_ms)
        logger.log_execution_complete("lambda_handler", duration_ms=duration_ms, status="error")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error'})
        }
    finally:
        logger.clear_context()

