"""
Auth Lambda Function
Handles user authentication, session management, password reset, and registration
"""

import json
import os
import uuid
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from logger_util import create_logger

logger = create_logger('auth')
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')
ses = boto3.client('ses')

# Environment variables
USERS_TABLE = os.environ.get('USERS_TABLE', 'idp_users')
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', '')
COGNITO_CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID', '')
SES_FROM_EMAIL = os.environ.get('SES_FROM_EMAIL', 'noreply@example.com')
RESET_TOKEN_EXPIRY_HOURS = 24


# Helper functions

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


def generate_reset_token() -> str:
    """Generate secure reset token"""
    return secrets.token_urlsafe(32)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Query user from DynamoDB by email"""
    try:
        table = dynamodb.Table(USERS_TABLE)
        response = table.get_item(Key={'email': email})
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Error querying user: {e}")
        return None


def create_session(user_email: str, user_data: Dict[str, Any]) -> Optional[str]:
    """Create session token"""
    try:
        # Check if Cognito is configured
        if COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID:
            # Use Cognito for session management
            response = cognito.admin_initiate_auth(
                UserPoolId=COGNITO_USER_POOL_ID,
                ClientId=COGNITO_CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': user_email,
                    'PASSWORD': user_data.get('password_hash', '')
                }
            )
            return response['AuthenticationResult']['IdToken']
        else:
            # Generate a simple token for development using UUID
            # Store token data in a way that doesn't use base64 with = padding
            import uuid
            import hashlib
            
            token_data = {
                'email': user_email,
                'tenant': user_data.get('tenant', ''),
                'role': user_data.get('role', 'User'),
                'exp': int(time.time()) + 3600  # 1 hour expiry
            }
            
            # Create a unique token ID
            token_id = str(uuid.uuid4()).replace('-', '')
            
            # Create a hash of the token data (no = padding)
            token_json = json.dumps(token_data)
            token_hash = hashlib.sha256(token_json.encode()).hexdigest()
            
            # Combine token_id and hash (no = characters)
            # Format: dev_token_{token_id}_{hash}_{base64_data_no_padding}
            import base64
            token_b64 = base64.urlsafe_b64encode(token_json.encode()).decode().replace('=', '')
            
            return f"dev_token_{token_id}_{token_b64}"
    except ClientError as e:
        logger.log_error(f"Error creating session: {e}")
        return None


def destroy_previous_sessions(user_email: str) -> bool:
    """Destroy all previous sessions for user"""
    try:
        # Only use Cognito if configured
        if COGNITO_USER_POOL_ID:
            cognito.admin_user_global_sign_out(
                UserPoolId=COGNITO_USER_POOL_ID,
                Username=user_email
            )
        return True
    except ClientError as e:
        logger.warning(f"Error destroying sessions: {e}")
        return False


def send_reset_email(email: str, reset_token: str) -> bool:
    """Send password reset email via SES"""
    try:
        reset_link = f"https://extension.example.com/reset?token={reset_token}"
        
        ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': 'Password Reset Request'},
                'Body': {
                    'Text': {
                        'Data': f'Click the following link to reset your password: {reset_link}\n\n'
                                f'This link will expire in {RESET_TOKEN_EXPIRY_HOURS} hours.'
                    },
                    'Html': {
                        'Data': f'<p>Click the following link to reset your password:</p>'
                                f'<p><a href="{reset_link}">{reset_link}</a></p>'
                                f'<p>This link will expire in {RESET_TOKEN_EXPIRY_HOURS} hours.</p>'
                    }
                }
            }
        )
        return True
    except ClientError as e:
        logger.error(f"Error sending email: {e}")
        return False


@tracer.capture_method
def handle_auth(event, context):
    """Handle user authentication"""
    start_time = time.time()
    logger.log_execution_start("handle_auth", operation="user_authentication")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        password = body.get('password', '')
        
        # Set context for logging
        logger.set_context(
            request_id=context.request_id if hasattr(context, 'request_id') else 'unknown',
            user_email=email
        )
        
        # Validate input
        if not email or not password:
            logger.log_warning("Authentication failed: missing credentials")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Email and password are required'
                })
            }
        
        # Query user from DynamoDB
        user = get_user_by_email(email)
        
        if not user:
            logger.log_authentication_attempt(email, "failure", reason="user_not_found")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Invalid credentials'
                })
            }
        
        # Add tenant to context
        logger.set_context(tenant=user.get('tenant', ''))
        
        # Check if user is active
        if not user.get('is_active', True):
            logger.log_authentication_attempt(email, "failure", reason="account_inactive")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Account is inactive'
                })
            }
        
        # Verify password hash
        if not verify_password(password, user.get('password_hash', '')):
            logger.log_authentication_attempt(email, "failure", reason="invalid_password")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Invalid credentials'
                })
            }
        
        # Destroy previous sessions
        destroy_previous_sessions(email)
        
        # Create new session
        session_token = create_session(email, user)
        
        if not session_token:
            logger.log_error("Failed to create session", user_email=email)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': 'Failed to create session'
                })
            }
        
        # Log successful authentication
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_authentication_attempt(email, "success", duration_ms=duration_ms)
        logger.log_execution_complete("handle_auth", duration_ms=duration_ms, status="success")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'token': session_token,
                'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                'role': user.get('role', 'User'),
                'tenant': user.get('tenant', ''),
                'user': {
                    'email': user['email'],
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'role': user.get('role', 'User'),
                    'tenant': user.get('tenant', '')
                }
            })
        }
        
    except json.JSONDecodeError:
        logger.log_error("Invalid JSON in request body")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_error("Unexpected error in handle_auth", error=e, duration_ms=duration_ms)
        logger.log_execution_complete("handle_auth", duration_ms=duration_ms, status="error")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }


@tracer.capture_method
def handle_forget_password(event, context):
    """Handle password reset request"""
    start_time = time.time()
    logger.log_execution_start("handle_forget_password", operation="password_reset_request")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        
        # Set context for logging
        logger.set_context(
            request_id=context.request_id if hasattr(context, 'request_id') else 'unknown',
            user_email=email
        )
        
        # Validate input
        if not email:
            logger.log_warning("Password reset failed: missing email")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Email is required'
                })
            }
        
        # Query user from DynamoDB
        user = get_user_by_email(email)
        
        if not user:
            # For security, don't reveal if user exists
            logger.log_info("Password reset requested for non-existent user", user_email=email)
            duration_ms = int((time.time() - start_time) * 1000)
            logger.log_execution_complete("handle_forget_password", duration_ms=duration_ms, status="success")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'If the email exists, a reset link has been sent'
                })
            }
        
        # Generate reset token
        reset_token = generate_reset_token()
        expiry = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRY_HOURS)
        
        # Store reset token in DynamoDB
        try:
            table = dynamodb.Table(USERS_TABLE)
            table.update_item(
                Key={'email': email},
                UpdateExpression='SET reset_token = :token, reset_token_expiry = :expiry',
                ExpressionAttributeValues={
                    ':token': reset_token,
                    ':expiry': expiry.isoformat()
                }
            )
            logger.log_database_operation(USERS_TABLE, "update_item", status="success", user_email=email)
        except ClientError as e:
            logger.log_error("Error storing reset token", error=e, user_email=email)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': 'Failed to process reset request'
                })
            }
        
        # Send reset email
        if not send_reset_email(email, reset_token):
            logger.log_warning("Failed to send reset email", user_email=email)
            # Don't fail the request, log for async retry
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_info("Password reset email sent", user_email=email, duration_ms=duration_ms)
        logger.log_execution_complete("handle_forget_password", duration_ms=duration_ms, status="success")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'If the email exists, a reset link has been sent'
            })
        }
        
    except json.JSONDecodeError:
        logger.log_error("Invalid JSON in request body")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_error("Unexpected error in handle_forget_password", error=e, duration_ms=duration_ms)
        logger.log_execution_complete("handle_forget_password", duration_ms=duration_ms, status="error")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }


@tracer.capture_method
def handle_reset_password(event, context):
    """Handle password reset"""
    start_time = time.time()
    logger.log_execution_start("handle_reset_password", operation="password_reset")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        reset_token = body.get('token', '').strip()
        new_password = body.get('new_password', '')
        
        # Set context for logging
        logger.set_context(
            request_id=context.request_id if hasattr(context, 'request_id') else 'unknown'
        )
        
        # Validate input
        if not reset_token or not new_password:
            logger.log_warning("Password reset failed: missing token or password")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Token and new password are required'
                })
            }
        
        # Find user by reset token
        try:
            table = dynamodb.Table(USERS_TABLE)
            # Scan for user with matching reset token (in production, use GSI)
            response = table.scan(
                FilterExpression='reset_token = :token',
                ExpressionAttributeValues={':token': reset_token}
            )
            
            if not response.get('Items'):
                logger.log_warning("Invalid reset token provided")
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Bad Request',
                        'message': 'Invalid or expired reset token'
                    })
                }
            
            user = response['Items'][0]
            user_email = user['email']
            
            # Add user context
            logger.set_context(user_email=user_email, tenant=user.get('tenant', ''))
            
            # Check token expiry
            expiry_str = user.get('reset_token_expiry', '')
            if expiry_str:
                expiry = datetime.fromisoformat(expiry_str)
                if datetime.utcnow() > expiry:
                    logger.log_warning("Expired reset token", user_email=user_email)
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'error': 'Bad Request',
                            'message': 'Invalid or expired reset token'
                        })
                    }
            
            # Hash new password
            new_password_hash = hash_password(new_password)
            
            # Update password and clear reset token
            table.update_item(
                Key={'email': user['email']},
                UpdateExpression='SET password_hash = :pwd, reset_token = :null, reset_token_expiry = :null, modified_date = :now',
                ExpressionAttributeValues={
                    ':pwd': new_password_hash,
                    ':null': None,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.log_info("Password reset successfully", user_email=user_email, duration_ms=duration_ms)
            logger.log_execution_complete("handle_reset_password", duration_ms=duration_ms, status="success")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Password reset successfully'
                })
            }
            
        except ClientError as e:
            logger.log_error("Error resetting password", error=e)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': 'Failed to reset password'
                })
            }
        
    except json.JSONDecodeError:
        logger.log_error("Invalid JSON in request body")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_error("Unexpected error in handle_reset_password", error=e, duration_ms=duration_ms)
        logger.log_execution_complete("handle_reset_password", duration_ms=duration_ms, status="error")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }


@tracer.capture_method
def handle_sign_up(event, context):
    """Handle user registration"""
    start_time = time.time()
    logger.log_execution_start("handle_sign_up", operation="user_registration")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        first_name = body.get('first_name', '').strip()
        last_name = body.get('last_name', '').strip()
        contact_number = body.get('contact_number', '').strip()
        password = body.get('password', '')
        confirm_password = body.get('confirm_password', '')
        tenant = body.get('tenant', 'default')  # Default tenant if not provided
        
        # Set context for logging
        logger.set_context(
            request_id=context.request_id if hasattr(context, 'request_id') else 'unknown',
            user_email=email,
            tenant=tenant
        )
        
        # Validate input
        if not all([email, first_name, last_name, password, confirm_password]):
            logger.log_warning("Registration failed: missing required fields")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'All fields are required'
                })
            }
        
        # Validate password confirmation
        if password != confirm_password:
            logger.log_warning("Registration failed: password mismatch")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Passwords do not match'
                })
            }
        
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            logger.log_warning("Duplicate registration attempt", user_email=email)
            return {
                'statusCode': 409,
                'body': json.dumps({
                    'error': 'Conflict',
                    'message': 'An account with this email already exists'
                })
            }
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user record
        try:
            table = dynamodb.Table(USERS_TABLE)
            now = datetime.utcnow().isoformat()
            
            user_item = {
                'email': email,
                'password_hash': password_hash,
                'first_name': first_name,
                'last_name': last_name,
                'contact_number': contact_number,
                'tenant': tenant,
                'role': 'User',  # Default role
                'created_date': now,
                'modified_date': now,
                'is_active': True
            }
            
            table.put_item(Item=user_item)
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.log_info("User registered successfully", user_email=email, duration_ms=duration_ms)
            logger.log_database_operation(USERS_TABLE, "put_item", status="success", user_email=email)
            logger.log_execution_complete("handle_sign_up", duration_ms=duration_ms, status="success")
            
            return {
                'statusCode': 201,
                'body': json.dumps({
                    'message': 'User registered successfully',
                    'user': {
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name
                    }
                })
            }
            
        except ClientError as e:
            logger.log_error("Error creating user", error=e, user_email=email)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': 'Failed to create user account'
                })
            }
        
    except json.JSONDecodeError:
        logger.log_error("Invalid JSON in request body")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_error("Unexpected error in handle_sign_up", error=e, duration_ms=duration_ms)
        logger.log_execution_complete("handle_sign_up", duration_ms=duration_ms, status="error")
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
        if path == '/auth':
            result = handle_auth(event, context)
        elif path == '/forget_password':
            result = handle_forget_password(event, context)
        elif path == '/reset_password':
            result = handle_reset_password(event, context)
        elif path == '/sign_up':
            result = handle_sign_up(event, context)
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
