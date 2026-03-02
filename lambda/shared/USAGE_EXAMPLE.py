"""
Example usage of the logging utility in Lambda functions

This file demonstrates how to integrate the structured logger
into your Lambda function handlers.
"""

import json
import time
from typing import Dict, Any
from aws_lambda_powertools.utilities.typing import LambdaContext

# Import the logging utility
from shared.logger_util import create_logger

# Create logger instance at module level
logger = create_logger('example-service')


def example_lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Example Lambda handler demonstrating logging utility usage
    """
    start_time = time.time()
    
    # Set context from Lambda event and context
    logger.set_context(
        request_id=context.aws_request_id,
        user_email=event.get('user_email'),
        tenant=event.get('tenant')
    )
    
    # Log execution start
    logger.log_execution_start('example_lambda_handler')
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Log info with custom fields
        logger.log_info(
            'Processing request',
            operation=body.get('operation'),
            item_count=len(body.get('items', []))
        )
        
        # Simulate AWS API call
        api_start = time.time()
        result = call_aws_service(body)
        api_duration = int((time.time() - api_start) * 1000)
        
        # Log API call
        logger.log_api_call(
            'dynamodb',
            'put_item',
            duration_ms=api_duration,
            status='success',
            items_processed=len(result)
        )
        
        # Log execution completion
        total_duration = int((time.time() - start_time) * 1000)
        logger.log_execution_complete(
            'example_lambda_handler',
            duration_ms=total_duration,
            status='success',
            items_processed=len(result)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Success',
                'result': result
            })
        }
        
    except ValueError as e:
        # Log validation error without stack trace
        logger.log_error(
            'Validation error',
            error=e,
            include_stacktrace=False
        )
        
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': str(e)
            })
        }
        
    except Exception as e:
        # Log unexpected error with stack trace
        logger.log_error(
            'Unexpected error in Lambda handler',
            error=e,
            operation=body.get('operation')
        )
        
        total_duration = int((time.time() - start_time) * 1000)
        logger.log_execution_complete(
            'example_lambda_handler',
            duration_ms=total_duration,
            status='failure'
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }


def call_aws_service(data: Dict[str, Any]) -> list:
    """
    Example function that calls AWS service
    """
    logger.log_info('Calling AWS service', service='dynamodb')
    
    try:
        # Simulate AWS service call
        result = [{'id': i, 'data': data} for i in range(3)]
        
        # Log database operation
        logger.log_database_operation(
            'example_table',
            'put_item',
            status='success',
            items_count=len(result)
        )
        
        return result
        
    except Exception as e:
        logger.log_error(
            'AWS service call failed',
            error=e,
            service='dynamodb'
        )
        raise


def example_authentication_handler(event: dict, context: LambdaContext) -> dict:
    """
    Example authentication handler demonstrating auth logging
    """
    logger.set_context(request_id=context.aws_request_id)
    logger.log_execution_start('example_authentication_handler')
    
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')
        
        # Validate credentials (example)
        if not email or not password:
            logger.log_authentication_attempt(
                email or 'unknown',
                'failure',
                reason='missing_credentials'
            )
            
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing credentials'})
            }
        
        # Simulate authentication check
        if password == 'wrong':
            logger.log_authentication_attempt(
                email,
                'failure',
                reason='invalid_password'
            )
            
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid credentials'})
            }
        
        # Success
        logger.log_authentication_attempt(email, 'success')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Authentication successful',
                'token': 'example-token'
            })
        }
        
    except Exception as e:
        logger.log_error('Authentication handler error', error=e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal error'})
        }


def example_processing_handler(event: dict, context: LambdaContext) -> dict:
    """
    Example document processing handler demonstrating stage logging
    """
    processing_id = 'proc-123'
    
    logger.set_context(
        request_id=context.aws_request_id,
        user_email=event.get('user_email'),
        tenant=event.get('tenant')
    )
    
    logger.log_execution_start('example_processing_handler', processing_id=processing_id)
    
    try:
        # Stage 1: Digitization
        stage_start = time.time()
        digitize_result = digitize_document(event.get('document'))
        stage_duration = int((time.time() - stage_start) * 1000)
        
        logger.log_processing_stage(
            'digitization',
            processing_id,
            duration_ms=stage_duration,
            pages=digitize_result['pages']
        )
        
        # Stage 2: Classification
        stage_start = time.time()
        classify_result = classify_document(digitize_result['text'])
        stage_duration = int((time.time() - stage_start) * 1000)
        
        logger.log_processing_stage(
            'classification',
            processing_id,
            duration_ms=stage_duration,
            document_type=classify_result['type']
        )
        
        # Stage 3: Extraction
        stage_start = time.time()
        extract_result = extract_data(digitize_result['text'])
        stage_duration = int((time.time() - stage_start) * 1000)
        
        logger.log_processing_stage(
            'extraction',
            processing_id,
            duration_ms=stage_duration,
            fields_extracted=len(extract_result)
        )
        
        logger.log_execution_complete('example_processing_handler', processing_id=processing_id)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processing_id': processing_id,
                'result': extract_result
            })
        }
        
    except Exception as e:
        logger.log_error(
            'Processing failed',
            error=e,
            processing_id=processing_id
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def digitize_document(document: str) -> Dict[str, Any]:
    """Example digitization function"""
    logger.log_info('Digitizing document')
    return {'text': 'Sample text', 'pages': 3}


def classify_document(text: str) -> Dict[str, Any]:
    """Example classification function"""
    logger.log_info('Classifying document')
    return {'type': 'Invoice'}


def extract_data(text: str) -> Dict[str, Any]:
    """Example extraction function"""
    logger.log_info('Extracting data')
    return {'invoice_number': '12345', 'amount': 100.00}


# Example of using logger with warnings
def example_with_warnings():
    """Example showing warning logs"""
    logger.log_warning(
        'Document type not found, using default',
        document_type='Unknown',
        fallback='Default'
    )
    
    logger.log_warning(
        'Rate limit approaching',
        current_rate=95,
        limit=100,
        user_email='user@example.com'
    )


# Example of clearing context
def example_context_management():
    """Example showing context management"""
    # Set context for first operation
    logger.set_context(
        request_id='req-1',
        user_email='user1@example.com',
        tenant='tenant-1'
    )
    
    logger.log_info('Processing for user 1')
    
    # Clear context before processing for different user
    logger.clear_context()
    
    # Set new context
    logger.set_context(
        request_id='req-2',
        user_email='user2@example.com',
        tenant='tenant-2'
    )
    
    logger.log_info('Processing for user 2')
