# Lambda Shared Utilities

This directory contains shared utility modules used across all Lambda functions.

## Logging Utility

The `logger_util.py` module provides structured logging with standard fields for all Lambda functions.

### Features

- **Structured Logging**: All logs include standard fields (timestamp, service, request_id, user_email, tenant)
- **Context Management**: Set context once and have it included in all subsequent logs
- **Error Logging**: Automatic stack trace capture for exceptions
- **Specialized Log Methods**: Pre-built methods for common logging scenarios (API calls, database operations, processing stages, authentication)
- **AWS Lambda Powertools Integration**: Built on top of AWS Lambda Powertools Logger

### Installation

Add the shared directory to your Lambda function's Python path or copy the module to your Lambda function directory.

### Basic Usage

```python
from shared.logger_util import create_logger

# Create logger instance
logger = create_logger('process')

# Set context (will be included in all subsequent logs)
logger.set_context(
    request_id=context.aws_request_id,
    user_email='user@example.com',
    tenant='tenant-1'
)

# Log messages
logger.log_info('Processing started', processing_id='proc-123')
logger.log_warning('Document type not found', document_type='Unknown')

# Log errors with stack traces
try:
    # some operation
except Exception as e:
    logger.log_error('Failed to process document', error=e, processing_id='proc-123')
```

### Standard Fields

All log messages automatically include:

- `timestamp`: ISO 8601 formatted timestamp
- `service`: Lambda service name (e.g., 'process', 'auth', 'data')
- `message`: Log message
- `request_id`: AWS Lambda request ID (if set in context)
- `user_email`: User email address (if set in context)
- `tenant`: Tenant ID (if set in context)

### Specialized Logging Methods

#### Execution Logging

```python
# Log function execution start
logger.log_execution_start('lambda_handler', event_type='process_document')

# Log function execution completion
logger.log_execution_complete('lambda_handler', duration_ms=1234, status='success')
```

#### API Call Logging

```python
# Log AWS service API calls
logger.log_api_call(
    'textract',
    'detect_document_text',
    duration_ms=500,
    status='success',
    pages=3
)
```

#### Database Operation Logging

```python
# Log DynamoDB operations
logger.log_database_operation(
    'idp_metadata',
    'put_item',
    status='success',
    processing_id='proc-123'
)
```

#### Processing Stage Logging

```python
# Log document processing pipeline stages
logger.log_processing_stage(
    'digitization',
    'proc-123',
    duration_ms=500,
    pages=3
)
```

#### Authentication Logging

```python
# Log authentication attempts
logger.log_authentication_attempt(
    'user@example.com',
    'success'
)

# Log failed authentication with reason
logger.log_authentication_attempt(
    'user@example.com',
    'failure',
    reason='invalid_password'
)
```

### Context Management

```python
# Set context at the beginning of Lambda handler
logger.set_context(
    request_id=context.aws_request_id,
    user_email=event.get('user_email'),
    tenant=event.get('tenant')
)

# All subsequent logs will include these fields
logger.log_info('Processing started')  # Includes request_id, user_email, tenant

# Clear context when needed
logger.clear_context()
```

### Error Logging

```python
# Log error with exception and stack trace
try:
    result = process_document(data)
except Exception as e:
    logger.log_error(
        'Document processing failed',
        error=e,
        processing_id='proc-123',
        document_name='invoice.pdf'
    )
    raise

# Log error without stack trace
logger.log_error(
    'Validation failed',
    error=validation_error,
    include_stacktrace=False
)
```

### Custom Fields

Add custom fields to any log message:

```python
logger.log_info(
    'Document processed',
    processing_id='proc-123',
    document_name='invoice.pdf',
    pages=5,
    credit_cost=0.50,
    custom_field='custom_value'
)
```

### Integration with Lambda Handler

```python
from shared.logger_util import create_logger
import time

logger = create_logger('process')

def lambda_handler(event, context):
    start_time = time.time()
    
    # Set context
    logger.set_context(
        request_id=context.aws_request_id,
        user_email=event.get('user_email'),
        tenant=event.get('tenant')
    )
    
    # Log execution start
    logger.log_execution_start('lambda_handler')
    
    try:
        # Your Lambda logic here
        result = process_document(event)
        
        # Log execution completion
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_execution_complete(
            'lambda_handler',
            duration_ms=duration_ms,
            status='success'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        # Log error
        logger.log_error('Lambda execution failed', error=e)
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.log_execution_complete(
            'lambda_handler',
            duration_ms=duration_ms,
            status='failure'
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### Testing

Run the unit tests:

```bash
cd lambda/shared
pytest test_logger_util.py -v
```

### Requirements

Add to your Lambda function's `requirements.txt`:

```
aws-lambda-powertools>=2.0.0
```

## Best Practices

1. **Create logger once**: Create the logger instance at module level, not inside functions
2. **Set context early**: Set context at the beginning of your Lambda handler
3. **Use specialized methods**: Use the specialized logging methods (log_api_call, log_database_operation, etc.) for better log structure
4. **Include relevant fields**: Add custom fields that help with debugging and monitoring
5. **Log errors with context**: Always include relevant context when logging errors (processing_id, document_name, etc.)
6. **Clear sensitive data**: Never log passwords, tokens, or other sensitive credentials
7. **Use appropriate log levels**: Use log_info for normal operations, log_warning for recoverable issues, log_error for failures
