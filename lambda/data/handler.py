"""
Data Lambda Function
Handles data retrieval, user statistics, and profile management
"""

import json
import os
import hashlib
import secrets
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from logger_util import create_logger

logger = create_logger('data')
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')

# Environment variables
USERS_TABLE = os.environ.get('USERS_TABLE', 'idp_users')
DATAPOINTS_TABLE = os.environ.get('DATAPOINTS_TABLE', 'idp_datapoints')
HISTORY_TABLE = os.environ.get('HISTORY_TABLE', 'idp_history')
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', 'idp_transactions')


# Helper functions

def create_response(status_code: int, body: dict) -> dict:
    """Create HTTP response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body, default=str)
    }


def get_user_from_token(event: dict) -> Optional[Dict[str, Any]]:
    """Extract user information from session token"""
    token = None
    
    # Try to get from POST body first (for endpoints that use POST)
    if event.get('httpMethod') == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
            token = body.get('auth_token')
            if token:
                logger.log_info("Token found in POST body")
        except:
            pass
    
    # Try to get from query parameter
    if not token:
        query_params = event.get('queryStringParameters') or {}
        token = query_params.get('auth_token')
        if token:
            logger.log_info("Token found in query params")
    
    # Fallback to headers
    if not token:
        headers = event.get('headers', {})
        auth_header = headers.get('X-Auth-Token') or headers.get('x-auth-token') or headers.get('Authorization') or headers.get('authorization')
        
        if auth_header:
            token = auth_header
            # Remove Bearer prefix if present
            if token.startswith('Bearer '):
                token = token.replace('Bearer ', '')
            logger.log_info("Token found in headers")
    
    if token:
        logger.log_info(f"Token starts with: {token[:20]}...")
        
        # Parse development token (format: dev_token_{uuid}_{base64_json_no_padding})
        if token.startswith('dev_token_'):
            try:
                import base64
                # Remove dev_token_ prefix
                token_parts = token.replace('dev_token_', '').split('_', 1)
                if len(token_parts) == 2:
                    token_id, token_b64 = token_parts
                else:
                    token_b64 = token_parts[0]
                
                # Add padding if needed for URL-safe base64
                padding = 4 - (len(token_b64) % 4)
                if padding != 4:
                    token_b64 += '=' * padding
                
                token_json = base64.urlsafe_b64decode(token_b64).decode()
                token_data = json.loads(token_json)
                
                logger.log_info(f"Token parsed successfully for user: {token_data.get('email')}")
                
                return {
                    'email': token_data.get('email'),
                    'tenant': token_data.get('tenant')
                }
            except Exception as e:
                logger.log_error(f"Error parsing development token: {e}")
                return None
        else:
            logger.log_warning("Token doesn't start with dev_token_")
    else:
        logger.log_warning("No token found in body, query params, or headers")
    
    # Fallback: try to get from request context (for Cognito authorizer)
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    user_email = authorizer.get('user_email') or event.get('user_email')
    tenant = authorizer.get('tenant') or event.get('tenant')
    
    if user_email and tenant:
        logger.log_info(f"User found from request context: {user_email}")
        return {
            'email': user_email,
            'tenant': tenant
        }
    
    logger.log_warning("No user information found in token or request context")
    return None


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash"""
    try:
        salt, pwd_hash = stored_hash.split('$')
        computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return computed_hash == pwd_hash
    except (ValueError, AttributeError):
        return False


# Handler functions

@tracer.capture_method
def handle_datapoints(event, context):
    """Fetch all prompts for tenant"""
    logger.log_info("Datapoints request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return create_response(401, {
                'error': 'Unauthorized',
                'message': 'Invalid or missing authentication token'
            })
        
        tenant = user['tenant']
        logger.log_info(f"Fetching datapoints for tenant: {tenant}")
        
        # Query datapoints table filtered by tenant
        datapoints_table = dynamodb.Table(DATAPOINTS_TABLE)
        
        response = datapoints_table.query(
            IndexName='tenant-prompt_name-index',
            KeyConditionExpression='tenant = :tenant',
            ExpressionAttributeValues={
                ':tenant': tenant
            }
        )
        
        prompts = response.get('Items', [])
        
        logger.log_info(f"Found {len(prompts)} prompts for tenant: {tenant}")
        
        return create_response(200, {
            'prompts': prompts
        })
        
    except ClientError as e:
        logger.log_error(f"Error fetching datapoints: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'Failed to fetch datapoints'
        })
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_datapoints: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        })


@tracer.capture_method
def handle_reset_prompts(event, context):
    """Reload prompts from master data"""
    logger.log_info("Reset prompts request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return create_response(401, {
                'error': 'Unauthorized',
                'message': 'Invalid or missing authentication token'
            })
        
        tenant = user['tenant']
        logger.log_info(f"Resetting prompts for tenant: {tenant}")
        
        # Query datapoints table filtered by tenant (same as handle_datapoints)
        # In a real system, this might reload from a master configuration
        datapoints_table = dynamodb.Table(DATAPOINTS_TABLE)
        
        response = datapoints_table.query(
            IndexName='tenant-prompt_name-index',
            KeyConditionExpression='tenant = :tenant',
            ExpressionAttributeValues={
                ':tenant': tenant
            }
        )
        
        prompts = response.get('Items', [])
        
        logger.log_info(f"Reset complete: {len(prompts)} prompts for tenant: {tenant}")
        
        return create_response(200, {
            'message': 'Prompts reloaded successfully',
            'prompts': prompts
        })
        
    except ClientError as e:
        logger.log_error(f"Error resetting prompts: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'Failed to reset prompts'
        })
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_reset_prompts: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        })


@tracer.capture_method
def handle_history(event, context):
    """Fetch processing history with pagination"""
    logger.log_info("History request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return create_response(401, {
                'error': 'Unauthorized',
                'message': 'Invalid or missing authentication token'
            })
        
        user_email = user['email']
        tenant = user['tenant']
        
        # Parse query parameters for pagination
        query_params = event.get('queryStringParameters') or {}
        page_size = int(query_params.get('page_size', 20))
        last_key = query_params.get('last_key')
        
        # Validate page size
        if page_size < 1 or page_size > 100:
            return create_response(400, {
                'error': 'Bad Request',
                'message': 'Page size must be between 1 and 100'
            })
        
        logger.log_info(f"Fetching history for user: {user_email}, page_size: {page_size}")
        
        # Query history table filtered by user_email and tenant
        history_table = dynamodb.Table(HISTORY_TABLE)
        
        query_kwargs = {
            'IndexName': 'user_email-timestamp-index',
            'KeyConditionExpression': 'user_email = :email',
            'ExpressionAttributeValues': {
                ':email': user_email,
                ':tenant': tenant
            },
            'FilterExpression': 'tenant = :tenant',
            'Limit': page_size,
            'ScanIndexForward': False  # Sort by timestamp descending (newest first)
        }
        
        # Add pagination token if provided
        if last_key:
            try:
                query_kwargs['ExclusiveStartKey'] = json.loads(last_key)
            except json.JSONDecodeError:
                return create_response(400, {
                    'error': 'Bad Request',
                    'message': 'Invalid pagination token'
                })
        
        response = history_table.query(**query_kwargs)
        
        history_records = response.get('Items', [])
        next_key = response.get('LastEvaluatedKey')
        
        logger.log_info(f"Found {len(history_records)} history records for user: {user_email}")
        
        result = {
            'success': True,
            'records': history_records,
            'page_size': page_size,
            'has_more': next_key is not None,
            'total_pages': 1  # Simplified pagination
        }
        
        if next_key:
            result['next_key'] = json.dumps(next_key, default=str)
        
        return create_response(200, result)
        
    except ClientError as e:
        logger.log_error(f"Error fetching history: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'Failed to fetch history'
        })
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_history: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        })


@tracer.capture_method
def handle_mytransactions(event, context):
    """Fetch transaction history with pagination and calculate remaining balance"""
    logger.log_info("My transactions request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return create_response(401, {
                'error': 'Unauthorized',
                'message': 'Invalid or missing authentication token'
            })
        
        user_email = user['email']
        tenant = user['tenant']
        
        # Parse query parameters for pagination
        query_params = event.get('queryStringParameters') or {}
        page_size = int(query_params.get('page_size', 20))
        last_key = query_params.get('last_key')
        
        # Validate page size
        if page_size < 1 or page_size > 100:
            return create_response(400, {
                'error': 'Bad Request',
                'message': 'Page size must be between 1 and 100'
            })
        
        logger.log_info(f"Fetching transactions for user: {user_email}, page_size: {page_size}")
        
        # Query ALL transactions to calculate running balance correctly
        # We need all transactions sorted by timestamp ascending to calculate balance
        transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
        
        all_transactions = []
        scan_kwargs = {
            'IndexName': 'user_email-timestamp-index',
            'KeyConditionExpression': 'user_email = :email',
            'ExpressionAttributeValues': {
                ':email': user_email,
                ':tenant': tenant
            },
            'FilterExpression': 'tenant = :tenant',
            'ScanIndexForward': True  # Sort by timestamp ascending (oldest first)
        }
        
        # Fetch all transactions (handle pagination)
        while True:
            response = transactions_table.query(**scan_kwargs)
            all_transactions.extend(response.get('Items', []))
            
            if 'LastEvaluatedKey' not in response:
                break
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        
        # Calculate running balance for each transaction
        running_balance = Decimal('0')
        for transaction in all_transactions:
            amount = transaction.get('amount', 0)
            # Convert to Decimal for precise calculation
            if isinstance(amount, (int, float)):
                amount = Decimal(str(amount))
            
            running_balance += amount
            transaction['remaining_balance'] = float(running_balance)
        
        # Reverse to show newest first
        all_transactions.reverse()
        
        # Apply pagination to the result
        start_idx = (int(last_key) if last_key and last_key.isdigit() else 0)
        end_idx = start_idx + page_size
        paginated_transactions = all_transactions[start_idx:end_idx]
        
        has_more = end_idx < len(all_transactions)
        next_page_key = str(end_idx) if has_more else None
        
        logger.log_info(f"Returning {len(paginated_transactions)} transactions with balance for user: {user_email}")
        
        result = {
            'success': True,
            'transactions': paginated_transactions,
            'page_size': page_size,
            'has_more': has_more
        }
        
        if next_page_key:
            result['next_key'] = next_page_key
        
        return create_response(200, result)
        
    except ClientError as e:
        logger.log_error(f"Error fetching transactions: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'Failed to fetch transactions'
        })
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_mytransactions: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        })


@tracer.capture_method
def handle_total_document_processed(event, context):
    """Get total count of documents processed by user"""
    logger.log_info("Total document processed request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return create_response(401, {
                'error': 'Unauthorized',
                'message': 'Invalid or missing authentication token'
            })
        
        user_email = user['email']
        tenant = user['tenant']
        
        logger.log_info(f"Counting documents for user: {user_email}")
        
        # Query history table to count all processing records
        history_table = dynamodb.Table(HISTORY_TABLE)
        
        # Use query with count
        response = history_table.query(
            IndexName='user_email-timestamp-index',
            KeyConditionExpression='user_email = :email',
            ExpressionAttributeValues={
                ':email': user_email,
                ':tenant': tenant
            },
            FilterExpression='tenant = :tenant',
            Select='COUNT'
        )
        
        count = response.get('Count', 0)
        
        logger.log_info(f"Total documents processed for {user_email}: {count}")
        
        return create_response(200, {
            'success': True,
            'count': count
        })
        
    except ClientError as e:
        logger.log_error(f"Error counting documents: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'Failed to count documents'
        })
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_total_document_processed: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        })


@tracer.capture_method
def handle_available_balance(event, context):
    """Calculate available credit balance for user"""
    logger.log_info("Available balance request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return create_response(401, {
                'error': 'Unauthorized',
                'message': 'Invalid or missing authentication token'
            })
        
        user_email = user['email']
        tenant = user['tenant']
        
        logger.log_info(f"Calculating balance for user: {user_email}")
        
        # Query ALL transactions for user (handle pagination)
        transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
        
        all_transactions = []
        query_kwargs = {
            'IndexName': 'user_email-timestamp-index',
            'KeyConditionExpression': 'user_email = :email',
            'ExpressionAttributeValues': {
                ':email': user_email,
                ':tenant': tenant
            },
            'FilterExpression': 'tenant = :tenant'
        }
        
        # Fetch all transactions (handle pagination)
        while True:
            response = transactions_table.query(**query_kwargs)
            all_transactions.extend(response.get('Items', []))
            
            if 'LastEvaluatedKey' not in response:
                break
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        
        # Sum all transaction amounts
        balance = Decimal('0')
        for transaction in all_transactions:
            amount = transaction.get('amount', 0)
            # Convert to Decimal for precise calculation
            if isinstance(amount, (int, float)):
                balance += Decimal(str(amount))
            else:
                balance += amount
        
        logger.log_info(f"Available balance for {user_email}: {balance} (from {len(all_transactions)} transactions)")
        
        return create_response(200, {
            'success': True,
            'balance': float(balance)
        })
        
    except ClientError as e:
        logger.log_error(f"Error calculating balance: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'Failed to calculate balance'
        })
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_available_balance: {e}")
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        })


@tracer.capture_method
def handle_profile_change(event, context):
    """Update user profile information"""
    logger.log_info("Profile change request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Invalid or missing authentication token'
                })
            }
        
        user_email = user['email']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        first_name = body.get('first_name', '').strip()
        last_name = body.get('last_name', '').strip()
        
        # Validate input
        if not first_name or not last_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'First name and last name are required'
                })
            }
        
        logger.log_info(f"Updating profile for user: {user_email}")
        
        # Update user record in DynamoDB
        users_table = dynamodb.Table(USERS_TABLE)
        
        users_table.update_item(
            Key={'email': user_email},
            UpdateExpression='SET first_name = :first, last_name = :last, modified_date = :now',
            ExpressionAttributeValues={
                ':first': first_name,
                ':last': last_name,
                ':now': datetime.utcnow().isoformat()
            }
        )
        
        logger.log_info(f"Profile updated successfully for user: {user_email}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Profile updated successfully',
                'user': {
                    'email': user_email,
                    'first_name': first_name,
                    'last_name': last_name
                }
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except ClientError as e:
        logger.log_error(f"Error updating profile: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to update profile'
            })
        }
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_profile_change: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }


@tracer.capture_method
def handle_password_change(event, context):
    """Change user password with validation"""
    logger.log_info("Password change request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Invalid or missing authentication token'
                })
            }
        
        user_email = user['email']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        current_password = body.get('current_password', '')
        new_password = body.get('new_password', '')
        confirm_password = body.get('confirm_password', '')
        
        # Validate input
        if not all([current_password, new_password, confirm_password]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'All password fields are required'
                })
            }
        
        # Validate new password matches confirmation
        if new_password != confirm_password:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'New password and confirmation do not match'
                })
            }
        
        logger.log_info(f"Changing password for user: {user_email}")
        
        # Get current user record
        users_table = dynamodb.Table(USERS_TABLE)
        response = users_table.get_item(Key={'email': user_email})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': 'User not found'
                })
            }
        
        user_record = response['Item']
        
        # Verify current password
        if not verify_password(current_password, user_record.get('password_hash', '')):
            logger.log_warning(f"Invalid current password for user: {user_email}")
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Current password is incorrect'
                })
            }
        
        # Hash new password
        new_password_hash = hash_password(new_password)
        
        # Update password
        users_table.update_item(
            Key={'email': user_email},
            UpdateExpression='SET password_hash = :pwd, modified_date = :now',
            ExpressionAttributeValues={
                ':pwd': new_password_hash,
                ':now': datetime.utcnow().isoformat()
            }
        )
        
        logger.log_info(f"Password changed successfully for user: {user_email}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Password changed successfully'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except ClientError as e:
        logger.log_error(f"Error changing password: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to change password'
            })
        }
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_password_change: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }


@tracer.capture_method
def handle_top_up(event, context):
    """Process credit top-up"""
    logger.log_info("Top-up request received")
    
    try:
        # Get user from token
        user = get_user_from_token(event)
        if not user:
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Invalid or missing authentication token'
                })
            }
        
        user_email = user['email']
        tenant = user['tenant']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        amount = body.get('amount')
        remark = body.get('remark', '').strip()
        payment_transaction_id = body.get('payment_transaction_id', '')  # From payment gateway
        
        # Validate input
        if not amount or amount <= 0:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Amount must be greater than zero'
                })
            }
        
        logger.log_info(f"Processing top-up for user: {user_email}, amount: {amount}")
        
        # Create transaction record
        transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)
        
        import uuid
        transaction_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        transaction = {
            'transaction_id': transaction_id,
            'user_email': user_email,
            'tenant': tenant,
            'action': 'Top-up',
            'amount': float(amount),  # Positive for top-up
            'timestamp': timestamp,
            'remark': remark or f'Credit top-up: {payment_transaction_id}'
        }
        
        transactions_table.put_item(Item=transaction)
        
        logger.log_info(f"Top-up transaction created: {transaction_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Credit top-up successful',
                'transaction_id': transaction_id,
                'amount': amount
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except ClientError as e:
        logger.log_error(f"Error processing top-up: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to process top-up'
            })
        }
    except Exception as e:
        logger.log_error(f"Unexpected error in handle_top_up: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }


@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Main Lambda handler"""
    start_time = time.time()
    path = event.get('path', '')
    
    # Set initial context
    logger.set_context(
        request_id=context.request_id if hasattr(context, 'request_id') else 'unknown'
    )
    
    logger.log_execution_start("lambda_handler", path=path, http_method=event.get('httpMethod', ''))
    
    try:
        if path == '/datapoints':
            result = handle_datapoints(event, context)
        elif path == '/reset_prompts':
            result = handle_reset_prompts(event, context)
        elif path == '/history':
            result = handle_history(event, context)
        elif path == '/mytransactions':
            result = handle_mytransactions(event, context)
        elif path == '/total_document_processed':
            result = handle_total_document_processed(event, context)
        elif path == '/available_balance':
            result = handle_available_balance(event, context)
        elif path == '/profile_change':
            result = handle_profile_change(event, context)
        elif path == '/password_change':
            result = handle_password_change(event, context)
        elif path == '/top_up':
            result = handle_top_up(event, context)
        else:
            result = {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
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


