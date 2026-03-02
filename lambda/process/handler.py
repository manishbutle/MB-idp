"""
Process Document Lambda Function
Orchestrates document processing pipeline with Textract and Bedrock
"""

import json
import boto3
import time
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional, List
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from logger_util import create_logger

logger = create_logger('process')
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')


def create_response(status_code: int, body: dict) -> dict:
    """
    Create API Gateway response with CORS headers
    
    Args:
        status_code: HTTP status code
        body: Response body dictionary
        
    Returns:
        Dict with statusCode, headers, and body
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }


@tracer.capture_method
def digitize_document(document_data: bytes, document_name: str) -> Dict[str, Any]:
    """
    Call Amazon Nova 2 Lite to digitize document and extract text
    
    Args:
        document_data: Binary document content
        document_name: Name of the document
        
    Returns:
        Dict containing extracted text and page count
        
    Raises:
        Exception: If Bedrock processing fails after retry
    """
    start_time = time.time()
    logger.log_info("Starting Amazon Nova 2 Lite digitization", document_name=document_name)
    
    max_retries = 1
    retry_delay = 1  # seconds
    
    # Convert document bytes to base64 for Bedrock
    import base64
    document_base64 = base64.b64encode(document_data).decode('utf-8')
    
    # Determine media type based on document content
    media_type = "image/jpeg"
    
    if document_data[:4] == b'%PDF':
        media_type = "application/pdf"
    elif document_data[:2] == b'\xff\xd8':
        media_type = "image/jpeg"
    elif document_data[:8] == b'\x89PNG\r\n\x1a\n':
        media_type = "image/png"
    elif document_data[:6] in [b'GIF87a', b'GIF89a']:
        media_type = "image/gif"
    elif document_data[:4] == b'RIFF' and len(document_data) > 12 and document_data[8:12] == b'WEBP':
        media_type = "image/webp"
    else:
        # Unsupported format
        logger.log_error("Unsupported document format", document_name=document_name)
        raise Exception(f"Unsupported document format for: {document_name}")
    
    for attempt in range(max_retries + 1):
        try:
            # Call Bedrock with Amazon Nova 2 Lite to extract text
            bedrock_start = time.time()
            response = bedrock_runtime.invoke_model(
                modelId='us.amazon.nova-2-lite-v1:0',
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    'messages': [
                        {
                            'role': 'user',
                            'content': [
                                {
                                    'document': {
                                        'format': media_type.split('/')[-1],
                                        'name': document_name,
                                        'source': {
                                            'bytes': document_base64
                                        }
                                    }
                                },
                                {
                                    'text': 'Extract all text from this document. Preserve the structure and formatting. At the very beginning of your response, state the total number of pages in the format "PAGES: X" where X is the number. Then provide the extracted text without any additional commentary.'
                                }
                            ]
                        }
                    ],
                    'inferenceConfig': {
                        'max_new_tokens': 4096,
                        'temperature': 0.1,
                        'top_p': 0.9
                    }
                })
            )
            bedrock_duration = int((time.time() - bedrock_start) * 1000)
            
            # Parse response
            response_body = json.loads(response['body'].read())
            extracted_text = response_body['output']['message']['content'][0]['text'].strip()
            
            # Extract token usage
            input_tokens = response_body.get('usage', {}).get('inputTokens', 0)
            output_tokens = response_body.get('usage', {}).get('outputTokens', 0)
            
            # Extract page count from response
            page_count = 1  # Default
            if extracted_text.startswith('PAGES:'):
                try:
                    # Extract page count from first line
                    first_line = extracted_text.split('\n')[0]
                    page_count = int(first_line.replace('PAGES:', '').strip())
                    # Remove the PAGES line from extracted text
                    extracted_text = '\n'.join(extracted_text.split('\n')[1:]).strip()
                except (ValueError, IndexError):
                    # If parsing fails, estimate from text length
                    page_count = max(1, len(extracted_text) // 2500)
            else:
                # Estimate from text length if PAGES not found
                page_count = max(1, len(extracted_text) // 2500)
            
            # Log Bedrock operation with metrics
            logger.log_api_call(
                "bedrock",
                "invoke_model_document",
                duration_ms=bedrock_duration,
                status="success",
                pages=page_count,
                characters=len(extracted_text),
                document_name=document_name,
                model_id='us.amazon.nova-2-lite-v1:0',
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            logger.log_info(
                "Amazon Nova 2 Lite completed successfully",
                pages=page_count,
                characters=len(extracted_text),
                duration_ms=bedrock_duration,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            return {
                'text': extracted_text,
                'page_count': page_count,
                'confidence': page_count,
                'duration_ms': bedrock_duration,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.log_api_call(
                "bedrock",
                "invoke_model_document",
                duration_ms=duration_ms,
                status="failure" if attempt >= max_retries else "retry",
                error_code=error_code,
                attempt=attempt + 1
            )
            
            if attempt < max_retries:
                logger.log_info(f"Retrying Bedrock in {retry_delay} seconds", attempt=attempt + 1)
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.log_error(
                    "Bedrock failed after all retries",
                    error=e,
                    attempts=max_retries + 1,
                    document_name=document_name
                )
                raise Exception(f"Document digitization failed: {str(e)}")
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.log_error("Unexpected error in Bedrock processing", error=e, duration_ms=duration_ms)
            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise Exception(f"Document digitization failed: {str(e)}")
    
    raise Exception("Bedrock processing failed")


@tracer.capture_method
def classify_document(text_content: str, tenant: str) -> Dict[str, Any]:
    """
    Use Bedrock to classify document type
    
    Args:
        text_content: Extracted text from document
        tenant: Tenant ID for filtering document types
        
    Returns:
        Dict containing document type and configuration
        
    Raises:
        Exception: If classification fails after retry
    """
    start_time = time.time()
    logger.log_info("Starting Bedrock classification", tenant=tenant)
    
    max_retries = 1
    retry_delay = 1  # seconds
    
    # Prepare classification prompt
    classification_prompt = f"""Analyze the following document text and classify it into one of these categories:
- Invoice
- Purchase Order
- Market Report
- Other

Document text:
{text_content[:2000]}

Respond with only the document type category."""
    
    for attempt in range(max_retries + 1):
        try:
            # Call Bedrock for classification
            bedrock_start = time.time()
            response = bedrock_runtime.invoke_model(
                modelId='us.amazon.nova-2-lite-v1:0',
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    'messages': [
                        {
                            'role': 'user',
                            'content': [
                                {
                                    'text': classification_prompt
                                }
                            ]
                        }
                    ],
                    'inferenceConfig': {
                        'max_new_tokens': 100,
                        'temperature': 0.1,
                        'top_p': 0.9
                    }
                })
            )
            bedrock_duration = int((time.time() - bedrock_start) * 1000)
            
            # Parse response
            response_body = json.loads(response['body'].read())
            document_type = response_body['output']['message']['content'][0]['text'].strip()
            
            # Get token usage (Requirement 21.6)
            input_tokens = response_body.get('usage', {}).get('inputTokens', 0)
            output_tokens = response_body.get('usage', {}).get('outputTokens', 0)
            
            # Log Bedrock operation with metrics (Requirement 21.6)
            logger.log_api_call(
                "bedrock",
                "invoke_model_classification",
                duration_ms=bedrock_duration,
                status="success",
                model_id='us.amazon.nova-2-lite-v1:0',
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                document_type=document_type
            )
            
            logger.log_info(
                "Document classified successfully",
                document_type=document_type,
                duration_ms=bedrock_duration,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            # Query idp_document_type table for configuration
            doc_type_table = dynamodb.Table('idp_document_type')
            
            try:
                doc_type_response = doc_type_table.query(
                    IndexName='tenant-document_type_name-index',
                    KeyConditionExpression='tenant = :tenant AND document_type_name = :doc_type',
                    ExpressionAttributeValues={
                        ':tenant': tenant,
                        ':doc_type': document_type
                    }
                )
                
                if doc_type_response['Items']:
                    doc_config = doc_type_response['Items'][0]
                    logger.log_database_operation(
                        'idp_document_type',
                        'query',
                        status='success',
                        document_type=document_type
                    )
                    return {
                        'document_type': document_type,
                        'document_type_id': doc_config['document_type_id'],
                        'default_prompt_id': doc_config.get('default_prompt_id'),
                        'duration_ms': bedrock_duration
                    }
                else:
                    logger.log_warning("No configuration found for document type", document_type=document_type)
                    return {
                        'document_type': document_type,
                        'document_type_id': None,
                        'default_prompt_id': None,
                        'duration_ms': bedrock_duration
                    }
                    
            except ClientError as e:
                logger.log_error("Error querying document type table", error=e)
                # Return classification without config
                return {
                    'document_type': document_type,
                    'document_type_id': None,
                    'default_prompt_id': None,
                    'duration_ms': bedrock_duration
                }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.log_api_call(
                "bedrock",
                "invoke_model_classification",
                duration_ms=duration_ms,
                status="failure" if attempt >= max_retries else "retry",
                error_code=error_code,
                attempt=attempt + 1
            )
            
            if attempt < max_retries:
                logger.log_info(f"Retrying Bedrock classification in {retry_delay} seconds", attempt=attempt + 1)
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.log_error(
                    "Bedrock classification failed after all retries",
                    error=e,
                    attempts=max_retries + 1
                )
                raise Exception(f"Document classification failed: {str(e)}")
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.log_error("Unexpected error in Bedrock classification", error=e, duration_ms=duration_ms)
            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise Exception(f"Document classification failed: {str(e)}")
    
    raise Exception("Bedrock classification failed")


@tracer.capture_method
def get_extraction_prompt(prompt_id: Optional[str], document_type: str, tenant: str) -> Dict[str, Any]:
    """
    Query idp_datapoints table for extraction prompt
    
    Args:
        prompt_id: Optional prompt ID from document type config
        document_type: Classified document type
        tenant: Tenant ID for filtering
        
    Returns:
        Dict containing prompt details
    """
    logger.log_info("Fetching extraction prompt", document_type=document_type, prompt_id=prompt_id)
    
    datapoints_table = dynamodb.Table('idp_datapoints')
    
    try:
        if prompt_id:
            # Get specific prompt by ID
            response = datapoints_table.get_item(Key={'prompt_id': prompt_id})
            if 'Item' in response:
                logger.log_info("Found prompt by ID", prompt_id=prompt_id)
                return response['Item']
        
        # Query by tenant and prompt name (using document type as prompt name)
        response = datapoints_table.query(
            IndexName='tenant-prompt_name-index',
            KeyConditionExpression='tenant = :tenant AND prompt_name = :prompt_name',
            ExpressionAttributeValues={
                ':tenant': tenant,
                ':prompt_name': document_type
            }
        )
        
        if response['Items']:
            logger.log_info("Found prompt by name", document_type=document_type)
            return response['Items'][0]
        
        # Use default generic prompt
        logger.log_warning("No prompt found, using default extraction", document_type=document_type)
        return {
            'prompt_id': 'default',
            'prompt_name': 'Default',
            'prompt': 'Extract all key information from this document including dates, amounts, names, and identifiers.',
            'datapoints': []
        }
        
    except ClientError as e:
        logger.log_error("Error querying datapoints table", error=e)
        # Return default prompt
        return {
            'prompt_id': 'default',
            'prompt_name': 'Default',
            'prompt': 'Extract all key information from this document.',
            'datapoints': []
        }


@tracer.capture_method
def extract_datapoints(text_content: str, prompt_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use Bedrock to extract datapoints from document
    
    Args:
        text_content: Extracted text from document
        prompt_config: Prompt configuration from idp_datapoints
        
    Returns:
        Dict containing extracted field-value pairs and token counts
        
    Raises:
        Exception: If extraction fails after retry
    """
    logger.log_info(f"Starting Bedrock datapoint extraction with prompt: {prompt_config.get('prompt_name')}")
    
    max_retries = 1
    retry_delay = 1  # seconds
    
    # Prepare extraction prompt
    extraction_prompt = f"""{prompt_config.get('prompt', 'Extract key information from this document.')}

Document text:
{text_content}

IMPORTANT: If the document contains multiple transactions/items/records (e.g., multiple invoices, line items, or entries), return them as an array of objects. If there is only one transaction, return it as a single object.

For multiple transactions, respond with:
{{"transactions": [
  {{"field1": "value1", "field2": "value2"}},
  {{"field1": "value3", "field2": "value4"}}
]}}

For a single transaction, respond with:
{{"field1": "value1", "field2": "value2"}}

If a field cannot be found, use null as the value."""
    
    for attempt in range(max_retries + 1):
        try:
            # Call Bedrock for extraction
            response = bedrock_runtime.invoke_model(
                modelId='us.amazon.nova-2-lite-v1:0',
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    'messages': [
                        {
                            'role': 'user',
                            'content': [
                                {
                                    'text': extraction_prompt
                                }
                            ]
                        }
                    ],
                    'inferenceConfig': {
                        'max_new_tokens': 2000,
                        'temperature': 0.1,
                        'top_p': 0.9
                    }
                })
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            extracted_text = response_body['output']['message']['content'][0]['text'].strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if '```json' in extracted_text:
                json_start = extracted_text.find('```json') + 7
                json_end = extracted_text.find('```', json_start)
                extracted_text = extracted_text[json_start:json_end].strip()
            elif '```' in extracted_text:
                json_start = extracted_text.find('```') + 3
                json_end = extracted_text.find('```', json_start)
                extracted_text = extracted_text[json_start:json_end].strip()
            
            # Parse extracted data
            try:
                extracted_data = json.loads(extracted_text)
            except json.JSONDecodeError:
                logger.log_warning("Failed to parse JSON from Bedrock response, using raw text")
                extracted_data = {'raw_extraction': extracted_text}
            
            # Get token usage
            input_tokens = response_body.get('usage', {}).get('inputTokens', 0)
            output_tokens = response_body.get('usage', {}).get('outputTokens', 0)
            
            logger.log_info(f"Extraction completed: {len(extracted_data)} fields, {input_tokens} input tokens, {output_tokens} output tokens")
            
            # Ensure all expected datapoints are present
            if prompt_config.get('datapoints'):
                for datapoint in prompt_config['datapoints']:
                    if datapoint not in extracted_data:
                        extracted_data[datapoint] = None
                        logger.log_warning(f"Datapoint not extracted: {datapoint}")
            
            return {
                'extracted_data': extracted_data,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model_id': 'us.amazon.nova-2-lite-v1:0'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.log_warning(f"Bedrock extraction attempt {attempt + 1} failed: {error_code}")
            
            if attempt < max_retries:
                logger.log_info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.log_error(f"Bedrock extraction failed after {max_retries + 1} attempts")
                raise Exception(f"Datapoint extraction failed: {str(e)}")
        
        except Exception as e:
            logger.log_error(f"Unexpected error in Bedrock extraction")
            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise Exception(f"Datapoint extraction failed: {str(e)}")
    
    raise Exception("Bedrock extraction failed")


@tracer.capture_method
def calculate_credit_cost(pages: int, input_tokens: int, output_tokens: int, tenant: str) -> Decimal:
    """
    Calculate credit cost based on idp_rates table
    
    Args:
        pages: Number of pages in document
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
        tenant: Tenant ID for rate lookup
        
    Returns:
        Decimal credit cost
    """
    logger.log_info(f"Calculating credit cost: {pages} pages, {input_tokens} input tokens, {output_tokens} output tokens")
    
    rates_table = dynamodb.Table('idp_rates')
    
    try:
        # Query current rates for tenant
        response = rates_table.scan(
            FilterExpression='tenant = :tenant AND effective_date <= :now AND (expiry_date > :now OR attribute_not_exists(expiry_date))',
            ExpressionAttributeValues={
                ':tenant': tenant,
                ':now': datetime.utcnow().isoformat()
            }
        )
        
        rates = {item['rate_type']: Decimal(str(item['amount'])) for item in response['Items']}
        
        # Calculate cost components
        base_cost = rates.get('base', Decimal('0'))
        page_cost = rates.get('per_page', Decimal('0.10')) * Decimal(str(pages))
        token_cost = rates.get('per_token', Decimal('0.0001')) * Decimal(str(input_tokens + output_tokens))
        
        total_cost = base_cost + page_cost + token_cost
        
        logger.log_info(f"Credit cost calculated: {total_cost} (base: {base_cost}, pages: {page_cost}, tokens: {token_cost})")
        
        return total_cost
        
    except ClientError as e:
        logger.log_error(f"Error querying rates table, using default rates")
        # Use default rates
        default_page_rate = Decimal('0.10')
        default_token_rate = Decimal('0.0001')
        total_cost = (default_page_rate * Decimal(str(pages))) + (default_token_rate * Decimal(str(input_tokens + output_tokens)))
        return total_cost


@tracer.capture_method
def get_user_balance(user_email: str) -> Decimal:
    """
    Calculate current user balance from transactions
    
    Args:
        user_email: User email address
        
    Returns:
        Decimal current balance
    """
    logger.log_info(f"Calculating balance for user: {user_email}")
    
    transactions_table = dynamodb.Table('idp_transactions')
    
    try:
        # Query all transactions for user
        response = transactions_table.query(
            IndexName='user_email-timestamp-index',
            KeyConditionExpression='user_email = :email',
            ExpressionAttributeValues={
                ':email': user_email
            }
        )
        
        # Sum all transaction amounts
        balance = Decimal('0')
        for transaction in response['Items']:
            balance += Decimal(str(transaction.get('amount', 0)))
        
        logger.log_info(f"Current balance for {user_email}: {balance}")
        return balance
        
    except ClientError as e:
        logger.log_error(f"Error querying transactions table")
        return Decimal('0')


@tracer.capture_method
def deduct_credit(user_email: str, tenant: str, cost: Decimal, processing_id: str, pages: int) -> Dict[str, Any]:
    """
    Deduct credit from user balance by creating transaction
    
    Args:
        user_email: User email address
        tenant: Tenant ID
        cost: Credit cost to deduct
        processing_id: Processing ID for reference
        pages: Number of pages processed
        
    Returns:
        Dict containing transaction details
        
    Raises:
        Exception: If balance is insufficient
    """
    logger.log_info(f"Deducting {cost} credits from user: {user_email}")
    
    # Check current balance
    current_balance = get_user_balance(user_email)
    
    if current_balance < cost:
        logger.log_warning(f"Insufficient balance: {current_balance} < {cost}")
        raise Exception(f"Insufficient balance. Required: {cost}, Available: {current_balance}")
    
    # Create transaction record
    transactions_table = dynamodb.Table('idp_transactions')
    
    transaction_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    transaction = {
        'transaction_id': transaction_id,
        'user_email': user_email,
        'tenant': tenant,
        'processing_id': processing_id,
        'action': 'Utilized',
        'amount': Decimal(str(-cost)),  # Negative for deduction, convert to Decimal
        'pages': pages,
        'timestamp': timestamp,
        'remark': f'Document processing: {processing_id}'
    }
    
    try:
        transactions_table.put_item(Item=transaction)
        logger.log_info(f"Transaction created: {transaction_id}")
        
        new_balance = current_balance - cost
        
        return {
            'transaction_id': transaction_id,
            'previous_balance': float(current_balance),
            'amount_deducted': float(cost),
            'new_balance': float(new_balance)
        }
        
    except ClientError as e:
        logger.log_error(f"Error creating transaction")
        raise Exception(f"Failed to deduct credit: {str(e)}")


@tracer.capture_method
def store_metadata(processing_data: Dict[str, Any]) -> None:
    """
    Store processing metadata in idp_metadata table
    
    Args:
        processing_data: Dict containing all metadata fields
    """
    logger.log_info(f"Storing metadata for processing: {processing_data['processing_id']}")
    
    metadata_table = dynamodb.Table('idp_metadata')
    
    metadata = {
        'processing_id': processing_data['processing_id'],
        'user_email': processing_data['user_email'],
        'tenant': processing_data['tenant'],
        'document_name': processing_data['document_name'],
        'prompt_name': processing_data['prompt_name'],
        'pages': processing_data['pages'],
        'creation_date': processing_data['creation_date'],
        'file_type': processing_data['file_type'],
        'file_size': processing_data['file_size'],
        'input_tokens': processing_data['input_tokens'],
        'output_tokens': processing_data['output_tokens'],
        'bedrock_digitization_duration_ms': processing_data.get('bedrock_digitization_duration_ms', 0),
        'bedrock_extraction_duration_ms': processing_data.get('bedrock_extraction_duration_ms', 0),
        'total_duration_ms': processing_data.get('total_duration_ms', 0),
        'digitization_confidence': processing_data.get('digitization_confidence', 0),
        'bedrock_model_id': processing_data.get('bedrock_model_id', ''),
        'credit_cost': processing_data['credit_cost']
    }
    
    try:
        metadata_table.put_item(Item=metadata)
        logger.log_info(f"Metadata stored successfully: {processing_data['processing_id']}")
    except ClientError as e:
        logger.log_error(f"Error storing metadata")
        raise Exception(f"Failed to store metadata: {str(e)}")


@tracer.capture_method
def store_history(processing_data: Dict[str, Any]) -> None:
    """
    Store processing history in idp_history table
    
    Args:
        processing_data: Dict containing history fields
    """
    logger.log_info(f"Storing history for processing: {processing_data['processing_id']}")
    
    history_table = dynamodb.Table('idp_history')
    
    history = {
        'processing_id': processing_data['processing_id'],
        'user_email': processing_data['user_email'],
        'tenant': processing_data['tenant'],
        'document_name': processing_data['document_name'],
        'document_type': processing_data['document_type'],
        'pages': processing_data['pages'],
        'extracted_values': processing_data['extracted_values'],
        'timestamp': processing_data['timestamp'],
        'file_type': processing_data['file_type'],
        'file_size': processing_data['file_size']
    }
    
    try:
        history_table.put_item(Item=history)
        logger.log_info(f"History stored successfully: {processing_data['processing_id']}")
    except ClientError as e:
        logger.log_error(f"Error storing history")
        raise Exception(f"Failed to store history: {str(e)}")


@tracer.capture_method
def store_transaction(transaction_data: Dict[str, Any]) -> None:
    """
    Store transaction record in idp_transactions table
    
    Args:
        transaction_data: Dict containing transaction fields
        
    Note: This is a wrapper for consistency, actual transaction
    is created in deduct_credit function
    """
    logger.log_info(f"Transaction already stored: {transaction_data.get('transaction_id')}")
    # Transaction is already created in deduct_credit function
    pass


@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Main Lambda handler for document processing
    Orchestrates the complete processing pipeline
    """
    start_time = time.time()
    processing_id = str(uuid.uuid4())
    
    # Set initial context
    logger.set_context(
        request_id=context.request_id if hasattr(context, 'request_id') else 'unknown',
        processing_id=processing_id
    )
    
    logger.log_execution_start("lambda_handler", processing_id=processing_id, operation="document_processing")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract required fields
        user_email = body.get('user_email')
        tenant = body.get('tenant')
        document_data = body.get('document_data')  # Base64 encoded
        document_name = body.get('document_name')
        file_type = body.get('file_type', 'pdf')
        file_size = body.get('file_size', 0)
        
        # Set user context
        logger.set_context(user_email=user_email, tenant=tenant)
        
        # Validate required fields
        if not all([user_email, tenant, document_data, document_name]):
            logger.log_error("Missing required fields in request", processing_id=processing_id)
            return create_response(400, {
                'error': 'Bad Request',
                'message': 'Missing required fields: user_email, tenant, document_data, document_name'
            })
        
        # Decode document data
        import base64
        document_bytes = base64.b64decode(document_data)
        
        logger.log_info(
            "Processing document",
            document_name=document_name,
            user_email=user_email,
            file_type=file_type,
            file_size=file_size
        )
        
        # Stage 1: Digitize document with Bedrock Claude Sonnet 4
        logger.log_processing_stage("digitization", processing_id, document_name=document_name)
        digitization_start = time.time()
        digitization_result = digitize_document(document_bytes, document_name)
        digitization_duration = digitization_result.get('duration_ms', int((time.time() - digitization_start) * 1000))
        
        text_content = digitization_result['text']
        page_count = digitization_result['page_count']
        digitization_confidence = digitization_result.get('confidence', page_count)
        digitization_input_tokens = digitization_result.get('input_tokens', 0)
        digitization_output_tokens = digitization_result.get('output_tokens', 0)
        
        logger.log_processing_stage("digitization", processing_id, duration_ms=digitization_duration, pages=page_count, status="complete")
        
        # Stage 2: Get extraction prompt (use prompt_id from request)
        logger.log_processing_stage("prompt_retrieval", processing_id)
        prompt_id = body.get('prompt_id')
        
        if not prompt_id:
            logger.log_error("Missing prompt_id in request", processing_id=processing_id)
            return create_response(400, {
                'error': 'Bad Request',
                'message': 'Missing required field: prompt_id'
            })
        
        prompt_config = get_extraction_prompt(prompt_id, None, tenant)
        prompt_name = prompt_config.get('prompt_name', 'Default')
        document_type = prompt_config.get('prompt_name', 'Unknown')
        
        logger.log_processing_stage("prompt_retrieval", processing_id, prompt_name=prompt_name, status="complete")
        
        # Stage 3: Extract datapoints with Bedrock (Requirement 21.6)
        logger.log_processing_stage("extraction", processing_id, prompt_name=prompt_name)
        extraction_start = time.time()
        extraction_result = extract_datapoints(text_content, prompt_config)
        extraction_duration = int((time.time() - extraction_start) * 1000)
        
        extracted_data = extraction_result['extracted_data']
        input_tokens = extraction_result['input_tokens']
        output_tokens = extraction_result['output_tokens']
        model_id = extraction_result['model_id']
        
        logger.log_processing_stage("extraction", processing_id, duration_ms=extraction_duration, fields_extracted=len(extracted_data), status="complete")
        
        # Stage 4: Calculate credit cost
        logger.log_processing_stage("credit_calculation", processing_id)
        # Include digitization tokens in total token count
        total_input_tokens = input_tokens + digitization_input_tokens
        total_output_tokens = output_tokens + digitization_output_tokens
        credit_cost = calculate_credit_cost(page_count, total_input_tokens, total_output_tokens, tenant)
        
        logger.log_processing_stage("credit_calculation", processing_id, credit_cost=float(credit_cost), status="complete")
        
        # Stage 5: Deduct credit (validates sufficient balance)
        logger.log_processing_stage("credit_deduction", processing_id)
        try:
            transaction_result = deduct_credit(user_email, tenant, credit_cost, processing_id, page_count)
            logger.log_processing_stage("credit_deduction", processing_id, amount=float(credit_cost), status="complete")
        except Exception as e:
            if "Insufficient balance" in str(e):
                logger.log_warning("Insufficient balance for user", user_email=user_email, required=float(credit_cost))
                return create_response(402, {
                    'error': 'Insufficient Balance',
                    'message': str(e),
                    'required': float(credit_cost),
                    'processing_id': processing_id
                })
            raise
        
        # Stage 6: Store metadata
        logger.log_processing_stage("metadata_storage", processing_id)
        creation_date = datetime.utcnow().isoformat()
        total_duration = int((time.time() - start_time) * 1000)
        
        metadata = {
            'processing_id': processing_id,
            'user_email': user_email,
            'tenant': tenant,
            'document_name': document_name,
            'prompt_name': prompt_name,
            'pages': page_count,
            'creation_date': creation_date,
            'file_type': file_type,
            'file_size': file_size,
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'bedrock_digitization_duration_ms': digitization_duration,
            'bedrock_extraction_duration_ms': extraction_duration,
            'total_duration_ms': total_duration,
            'digitization_confidence': digitization_confidence,
            'bedrock_model_id': model_id,
            'credit_cost': Decimal(str(credit_cost))
        }
        
        try:
            store_metadata(metadata)
            logger.log_processing_stage("metadata_storage", processing_id, status="complete")
        except Exception as e:
            # Rollback transaction on metadata storage failure
            logger.log_error("Metadata storage failed, rolling back transaction", error=e, processing_id=processing_id)
            rollback_transaction(user_email, tenant, credit_cost, processing_id, page_count)
            raise
        
        # Stage 7: Store history
        logger.log_processing_stage("history_storage", processing_id)
        history = {
            'processing_id': processing_id,
            'user_email': user_email,
            'tenant': tenant,
            'document_name': document_name,
            'document_type': document_type,
            'pages': page_count,
            'extracted_values': extracted_data,
            'timestamp': creation_date,
            'file_type': file_type,
            'file_size': file_size
        }
        
        try:
            store_history(history)
            logger.log_processing_stage("history_storage", processing_id, status="complete")
        except Exception as e:
            # Rollback transaction on history storage failure
            logger.log_error("History storage failed, rolling back transaction", error=e, processing_id=processing_id)
            rollback_transaction(user_email, tenant, credit_cost, processing_id, page_count)
            # Delete metadata
            try:
                metadata_table = dynamodb.Table('idp_metadata')
                metadata_table.delete_item(Key={'processing_id': processing_id})
            except:
                pass
            raise
        
        # Success - log completion (Requirement 21.1, 21.3)
        logger.log_info(
            "Document processing completed successfully",
            processing_id=processing_id,
            document_type=document_type,
            pages=page_count,
            total_duration_ms=total_duration,
            credit_cost=float(credit_cost)
        )
        
        logger.log_execution_complete(
            "lambda_handler",
            duration_ms=total_duration,
            status="success",
            processing_id=processing_id
        )
        
        return create_response(200, {
            'success': True,
            'message': 'Document processed successfully',
            'processing_id': processing_id,
            'document_type': document_type,
            'results': extracted_data,
            'metadata': {
                'processing_id': processing_id,
                'document_name': document_name,
                'prompt_name': prompt_name,
                'pages': page_count,
                'creation_date': creation_date,
                'file_type': file_type,
                'file_size': file_size,
                'input_tokens': total_input_tokens,
                'output_tokens': total_output_tokens,
                'credit_cost': float(credit_cost),
                'duration_ms': total_duration
            }
        })
        
    except Exception as e:
        # Log error with full context (Requirement 21.1, 21.2)
        total_duration = int((time.time() - start_time) * 1000)
        logger.log_error(
            "Document processing failed",
            error=e,
            processing_id=processing_id,
            duration_ms=total_duration,
            user_email=body.get('user_email') if 'body' in locals() else None,
            document_name=body.get('document_name') if 'body' in locals() else None
        )
        
        logger.log_execution_complete(
            "lambda_handler",
            duration_ms=total_duration,
            status="error",
            processing_id=processing_id
        )
        
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred during document processing',
            'processing_id': processing_id
        })
    finally:
        logger.clear_context()


@tracer.capture_method
def rollback_transaction(user_email: str, tenant: str, cost: Decimal, processing_id: str, pages: int) -> None:
    """
    Rollback transaction by creating a reversal transaction
    
    Args:
        user_email: User email address
        tenant: Tenant ID
        cost: Credit cost to reverse
        processing_id: Processing ID for reference
        pages: Number of pages
    """
    logger.log_info(f"Rolling back transaction for processing: {processing_id}")
    
    transactions_table = dynamodb.Table('idp_transactions')
    
    transaction_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    reversal_transaction = {
        'transaction_id': transaction_id,
        'user_email': user_email,
        'tenant': tenant,
        'processing_id': processing_id,
        'action': 'Rollback',
        'amount': Decimal(str(cost)),  # Positive to reverse deduction, convert to Decimal
        'pages': pages,
        'timestamp': timestamp,
        'remark': f'Rollback for failed processing: {processing_id}'
    }
    
    try:
        transactions_table.put_item(Item=reversal_transaction)
        logger.log_info(f"Transaction rolled back: {transaction_id}")
    except ClientError as e:
        logger.log_error(f"Error rolling back transaction")
        # Log for manual reconciliation
        logger.log_error(f"MANUAL RECONCILIATION REQUIRED: Failed to rollback {cost} credits for {user_email}, processing {processing_id}")


