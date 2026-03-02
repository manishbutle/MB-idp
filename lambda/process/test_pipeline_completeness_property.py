"""
Property-Based Test for Document Processing Pipeline Completeness
Feature: ai-document-processing
Property 1: Document Processing Pipeline Completeness

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11**

For any valid document submitted for processing, the system should complete all pipeline 
stages (digitization, classification, extraction) and store results in all three tables 
(idp_metadata, idp_history, idp_transactions) with a unique Processing_ID.
"""

import json
import pytest
import base64
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from hypothesis import given, settings, strategies as st, assume, HealthCheck

# Mock AWS services and logger before importing handler
with patch('boto3.resource'), patch('boto3.client'):
    # Mock the logger_util module
    import sys
    from unittest.mock import MagicMock
    mock_logger_module = MagicMock()
    mock_logger = MagicMock()
    mock_logger.log_info = Mock()
    mock_logger.log_warning = Mock()
    mock_logger.log_error = Mock()
    mock_logger.log_execution_start = Mock()
    mock_logger.log_execution_complete = Mock()
    mock_logger.log_processing_stage = Mock()
    mock_logger.log_api_call = Mock()
    mock_logger.log_database_operation = Mock()
    mock_logger.set_context = Mock()
    mock_logger.clear_context = Mock()
    mock_logger_module.create_logger.return_value = mock_logger
    sys.modules['logger_util'] = mock_logger_module
    
    from handler import lambda_handler


# Custom strategies for generating test data

@st.composite
def email_address(draw):
    """Generate a valid email address"""
    local = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd')
    )))
    domain = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd')
    )))
    tld = draw(st.sampled_from(['com', 'org', 'net', 'edu']))
    return f"{local}@{domain}.{tld}".lower()


@st.composite
def tenant_id(draw):
    """Generate a valid tenant ID"""
    return draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-_'
    )))


@st.composite
def document_name(draw):
    """Generate a valid document name"""
    name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-_. '
    )))
    extension = draw(st.sampled_from(['pdf', 'jpg', 'png', 'tiff', 'doc', 'docx']))
    return f"{name}.{extension}"


@st.composite
def file_type(draw):
    """Generate a valid file type"""
    return draw(st.sampled_from(['application/pdf', 'image/jpeg', 'image/png', 'image/tiff', 
                                  'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']))


@st.composite
def document_content(draw):
    """Generate sample document content"""
    return draw(st.text(min_size=100, max_size=1000, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Ps', 'Pe', 'Zs')
    )))


@st.composite
def processing_request(draw):
    """Generate a complete document processing request"""
    content = draw(document_content())
    # Encode content as base64 to simulate document data
    document_data = base64.b64encode(content.encode()).decode()
    
    return {
        'user_email': draw(email_address()),
        'tenant': draw(tenant_id()),
        'document_data': document_data,
        'document_name': draw(document_name()),
        'file_type': draw(file_type()),
        'file_size': draw(st.integers(min_value=1000, max_value=10000000))
    }


# Property Tests

@settings(max_examples=30, deadline=None)
@given(
    request_data=processing_request()
)
def test_pipeline_completes_all_stages_successfully(request_data):
    """
    Property 1.1: Pipeline Completes All Stages Successfully
    
    For any valid document processing request, the pipeline should complete
    all 8 stages: digitization, classification, prompt retrieval, extraction,
    credit calculation, credit deduction, metadata storage, and history storage.
    
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
    """
    # Mock all external dependencies
    with patch('handler.digitize_document') as mock_digitize, \
         patch('handler.classify_document') as mock_classify, \
         patch('handler.get_extraction_prompt') as mock_get_prompt, \
         patch('handler.extract_datapoints') as mock_extract, \
         patch('handler.calculate_credit_cost') as mock_calc_cost, \
         patch('handler.deduct_credit') as mock_deduct, \
         patch('handler.store_metadata') as mock_store_meta, \
         patch('handler.store_history') as mock_store_hist, \
         patch('handler.get_user_balance') as mock_balance:
        
        # Configure mocks to return valid responses
        mock_digitize.return_value = {
            'text': 'Sample extracted text content',
            'page_count': 3,
            'confidence': 0.95,
            'duration_ms': 1500
        }
        
        mock_classify.return_value = {
            'document_type': 'invoice',
            'default_prompt_id': 'prompt-123',
            'duration_ms': 800
        }
        
        mock_get_prompt.return_value = {
            'prompt_name': 'Invoice Extraction',
            'prompt': 'Extract invoice data...',
            'datapoints': ['invoice_number', 'total_amount']
        }
        
        mock_extract.return_value = {
            'extracted_data': {'invoice_number': 'INV-001', 'total_amount': '100.00'},
            'input_tokens': 500,
            'output_tokens': 150,
            'model_id': 'anthropic.claude-v2'
        }
        
        mock_calc_cost.return_value = Decimal('2.50')
        mock_balance.return_value = Decimal('10.00')
        mock_deduct.return_value = {'transaction_id': 'txn-123'}
        
        # Create event
        event = {
            'body': json.dumps(request_data)
        }
        
        # Mock context
        context = Mock()
        context.request_id = 'test-request-123'
        
        # Execute pipeline
        response = lambda_handler(event, context)
        
        # Property 1: Pipeline should complete successfully
        assert response['statusCode'] == 200, \
            f"Pipeline should complete successfully, got status {response['statusCode']}"
        
        # Property 2: All stages should be called
        mock_digitize.assert_called_once()
        mock_classify.assert_called_once()
        mock_get_prompt.assert_called_once()
        mock_extract.assert_called_once()
        mock_calc_cost.assert_called_once()
        mock_deduct.assert_called_once()
        mock_store_meta.assert_called_once()
        mock_store_hist.assert_called_once()
        
        # Property 3: Response should contain processing results
        response_body = json.loads(response['body'])
        assert 'processing_id' in response_body, \
            "Response should contain processing_id"
        assert 'document_type' in response_body, \
            "Response should contain document_type"
        assert 'extracted_data' in response_body, \
            "Response should contain extracted_data"
        assert 'metadata' in response_body, \
            "Response should contain metadata"


@settings(max_examples=25, deadline=None)
@given(
    request_data=processing_request()
)
def test_pipeline_stores_data_in_all_three_tables(request_data):
    """
    Property 1.2: Pipeline Stores Data in All Three Tables
    
    For any successful document processing, data should be stored in all three
    DynamoDB tables: idp_metadata, idp_history, and idp_transactions.
    
    **Validates: Requirements 1.8, 1.9, 1.10, 1.11**
    """
    # Track storage calls
    metadata_stored = {}
    history_stored = {}
    transaction_stored = {}
    
    with patch('handler.digitize_document') as mock_digitize, \
         patch('handler.classify_document') as mock_classify, \
         patch('handler.get_extraction_prompt') as mock_get_prompt, \
         patch('handler.extract_datapoints') as mock_extract, \
         patch('handler.calculate_credit_cost') as mock_calc_cost, \
         patch('handler.deduct_credit') as mock_deduct, \
         patch('handler.store_metadata') as mock_store_meta, \
         patch('handler.store_history') as mock_store_hist, \
         patch('handler.get_user_balance') as mock_balance:
        
        # Configure mocks
        mock_digitize.return_value = {
            'text': 'Sample text', 'page_count': 2, 'confidence': 0.9, 'duration_ms': 1000
        }
        mock_classify.return_value = {
            'document_type': 'receipt', 'default_prompt_id': 'prompt-456', 'duration_ms': 600
        }
        mock_get_prompt.return_value = {
            'prompt_name': 'Receipt Extraction', 'prompt': 'Extract receipt data...'
        }
        mock_extract.return_value = {
            'extracted_data': {'merchant': 'Store ABC', 'amount': '25.99'},
            'input_tokens': 300, 'output_tokens': 100, 'model_id': 'anthropic.claude-3-haiku'
        }
        mock_calc_cost.return_value = Decimal('1.75')
        mock_balance.return_value = Decimal('20.00')
        mock_deduct.return_value = {'transaction_id': 'txn-456'}
        
        # Capture storage calls
        def capture_metadata(data):
            metadata_stored.update(data)
        
        def capture_history(data):
            history_stored.update(data)
        
        mock_store_meta.side_effect = capture_metadata
        mock_store_hist.side_effect = capture_history
        
        # Execute pipeline
        event = {'body': json.dumps(request_data)}
        context = Mock()
        context.request_id = 'test-request-456'
        
        response = lambda_handler(event, context)
        
        # Property 1: All storage functions should be called
        mock_store_meta.assert_called_once()
        mock_store_hist.assert_called_once()
        mock_deduct.assert_called_once()  # This stores transaction
        
        # Property 2: Metadata should be stored with all required fields
        required_metadata_fields = [
            'processing_id', 'user_email', 'tenant', 'document_name',
            'prompt_name', 'pages', 'creation_date', 'file_type', 'file_size',
            'input_tokens', 'output_tokens', 'credit_cost'
        ]
        for field in required_metadata_fields:
            assert field in metadata_stored, \
                f"Metadata should contain {field}"
        
        # Property 3: History should be stored with all required fields
        required_history_fields = [
            'processing_id', 'user_email', 'tenant', 'document_name',
            'document_type', 'pages', 'extracted_values', 'timestamp'
        ]
        for field in required_history_fields:
            assert field in history_stored, \
                f"History should contain {field}"
        
        # Property 4: Same processing_id should be used across all tables
        assert metadata_stored['processing_id'] == history_stored['processing_id'], \
            "Same processing_id should be used for metadata and history"


@settings(max_examples=20, deadline=None)
@given(
    request_data=processing_request()
)
def test_pipeline_generates_unique_processing_id(request_data):
    """
    Property 1.3: Pipeline Generates Unique Processing ID
    
    For any document processing request, a unique Processing_ID should be
    generated and used consistently across all storage operations.
    
    **Validates: Requirements 1.7**
    """
    response_processing_ids = []
    metadata_processing_ids = []
    history_processing_ids = []
    
    with patch('handler.digitize_document') as mock_digitize, \
         patch('handler.classify_document') as mock_classify, \
         patch('handler.get_extraction_prompt') as mock_get_prompt, \
         patch('handler.extract_datapoints') as mock_extract, \
         patch('handler.calculate_credit_cost') as mock_calc_cost, \
         patch('handler.deduct_credit') as mock_deduct, \
         patch('handler.store_metadata') as mock_store_meta, \
         patch('handler.store_history') as mock_store_hist, \
         patch('handler.get_user_balance') as mock_balance:
        
        # Configure mocks
        mock_digitize.return_value = {
            'text': 'Text', 'page_count': 1, 'confidence': 0.8, 'duration_ms': 500
        }
        mock_classify.return_value = {
            'document_type': 'form', 'default_prompt_id': 'prompt-789', 'duration_ms': 400
        }
        mock_get_prompt.return_value = {
            'prompt_name': 'Form Extraction', 'prompt': 'Extract form data...'
        }
        mock_extract.return_value = {
            'extracted_data': {'field1': 'value1'},
            'input_tokens': 200, 'output_tokens': 50, 'model_id': 'anthropic.claude-v2'
        }
        mock_calc_cost.return_value = Decimal('1.00')
        mock_balance.return_value = Decimal('15.00')
        mock_deduct.return_value = {'transaction_id': 'txn-789'}
        
        # Capture processing IDs from storage calls
        def capture_metadata_id(data):
            metadata_processing_ids.append(data['processing_id'])
        
        def capture_history_id(data):
            history_processing_ids.append(data['processing_id'])
        
        mock_store_meta.side_effect = capture_metadata_id
        mock_store_hist.side_effect = capture_history_id
        
        # Execute pipeline multiple times
        for i in range(3):
            event = {'body': json.dumps(request_data)}
            context = Mock()
            context.request_id = f'test-request-{i}'
            
            response = lambda_handler(event, context)
            
            # Extract processing_id from response
            response_body = json.loads(response['body'])
            response_processing_ids.append(response_body['processing_id'])
        
        # Property 1: All response processing IDs should be unique
        assert len(response_processing_ids) == len(set(response_processing_ids)), \
            f"All response processing IDs should be unique, got duplicates in {response_processing_ids}"
        
        # Property 2: Metadata and history should use same processing_id as response for each call
        assert len(metadata_processing_ids) == 3, \
            f"Should have 3 metadata processing IDs, got {len(metadata_processing_ids)}"
        assert len(history_processing_ids) == 3, \
            f"Should have 3 history processing IDs, got {len(history_processing_ids)}"
        
        for i in range(3):
            assert response_processing_ids[i] == metadata_processing_ids[i], \
                f"Response and metadata processing IDs should match for call {i}"
            assert response_processing_ids[i] == history_processing_ids[i], \
                f"Response and history processing IDs should match for call {i}"
        
        # Property 3: All processing IDs should be valid UUIDs
        import uuid
        for processing_id in response_processing_ids:
            try:
                uuid.UUID(processing_id)
            except ValueError:
                pytest.fail(f"Processing ID is not a valid UUID: {processing_id}")


@settings(max_examples=20, deadline=None)
@given(
    request_data=processing_request()
)
def test_pipeline_handles_insufficient_balance_gracefully(request_data):
    """
    Property 1.4: Pipeline Handles Insufficient Balance Gracefully
    
    For any document processing request where the user has insufficient balance,
    the pipeline should stop at the credit deduction stage and return a 402 error
    without storing any data.
    
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
    """
    with patch('handler.digitize_document') as mock_digitize, \
         patch('handler.classify_document') as mock_classify, \
         patch('handler.get_extraction_prompt') as mock_get_prompt, \
         patch('handler.extract_datapoints') as mock_extract, \
         patch('handler.calculate_credit_cost') as mock_calc_cost, \
         patch('handler.deduct_credit') as mock_deduct, \
         patch('handler.store_metadata') as mock_store_meta, \
         patch('handler.store_history') as mock_store_hist, \
         patch('handler.get_user_balance') as mock_balance:
        
        # Configure mocks for successful stages
        mock_digitize.return_value = {
            'text': 'Text', 'page_count': 5, 'confidence': 0.9, 'duration_ms': 2000
        }
        mock_classify.return_value = {
            'document_type': 'invoice', 'default_prompt_id': 'prompt-999', 'duration_ms': 1000
        }
        mock_get_prompt.return_value = {
            'prompt_name': 'Invoice Extraction', 'prompt': 'Extract invoice...'
        }
        mock_extract.return_value = {
            'extracted_data': {'total': '500.00'},
            'input_tokens': 1000, 'output_tokens': 300, 'model_id': 'anthropic.claude-v2'
        }
        mock_calc_cost.return_value = Decimal('10.00')
        mock_balance.return_value = Decimal('5.00')  # Insufficient balance
        
        # Configure deduct_credit to raise insufficient balance error
        mock_deduct.side_effect = Exception("Insufficient balance: required 10.00, available 5.00")
        
        # Execute pipeline
        event = {'body': json.dumps(request_data)}
        context = Mock()
        context.request_id = 'test-insufficient-balance'
        
        response = lambda_handler(event, context)
        
        # Property 1: Should return 402 Payment Required
        assert response['statusCode'] == 402, \
            f"Should return 402 for insufficient balance, got {response['statusCode']}"
        
        # Property 2: Early stages should complete
        mock_digitize.assert_called_once()
        mock_classify.assert_called_once()
        mock_get_prompt.assert_called_once()
        mock_extract.assert_called_once()
        mock_calc_cost.assert_called_once()
        mock_deduct.assert_called_once()
        
        # Property 3: Storage stages should not be called
        mock_store_meta.assert_not_called()
        mock_store_hist.assert_not_called()
        
        # Property 4: Response should contain error details
        response_body = json.loads(response['body'])
        assert 'error' in response_body, \
            "Response should contain error field"
        assert 'required' in response_body, \
            "Response should contain required amount"
        assert 'processing_id' in response_body, \
            "Response should contain processing_id for tracking"


@settings(max_examples=15, deadline=None)
@given(
    request_data=processing_request()
)
def test_pipeline_rollback_on_storage_failure(request_data):
    """
    Property 1.5: Pipeline Rollback on Storage Failure
    
    For any document processing request where storage fails after credit deduction,
    the pipeline should rollback the transaction to maintain data consistency.
    
    **Validates: Requirements 1.8, 1.9, 1.10, 1.11**
    """
    with patch('handler.digitize_document') as mock_digitize, \
         patch('handler.classify_document') as mock_classify, \
         patch('handler.get_extraction_prompt') as mock_get_prompt, \
         patch('handler.extract_datapoints') as mock_extract, \
         patch('handler.calculate_credit_cost') as mock_calc_cost, \
         patch('handler.deduct_credit') as mock_deduct, \
         patch('handler.store_metadata') as mock_store_meta, \
         patch('handler.store_history') as mock_store_hist, \
         patch('handler.rollback_transaction') as mock_rollback, \
         patch('handler.get_user_balance') as mock_balance:
        
        # Configure mocks for successful stages
        mock_digitize.return_value = {
            'text': 'Text', 'page_count': 2, 'confidence': 0.85, 'duration_ms': 1200
        }
        mock_classify.return_value = {
            'document_type': 'receipt', 'default_prompt_id': 'prompt-rollback', 'duration_ms': 700
        }
        mock_get_prompt.return_value = {
            'prompt_name': 'Receipt Extraction', 'prompt': 'Extract receipt...'
        }
        mock_extract.return_value = {
            'extracted_data': {'amount': '75.50'},
            'input_tokens': 400, 'output_tokens': 120, 'model_id': 'anthropic.claude-3-sonnet'
        }
        mock_calc_cost.return_value = Decimal('3.25')
        mock_balance.return_value = Decimal('25.00')
        mock_deduct.return_value = {'transaction_id': 'txn-rollback'}
        
        # Configure metadata storage to fail
        mock_store_meta.side_effect = Exception("DynamoDB write failed")
        
        # Execute pipeline
        event = {'body': json.dumps(request_data)}
        context = Mock()
        context.request_id = 'test-rollback'
        
        response = lambda_handler(event, context)
        
        # Property 1: Should return 500 Internal Server Error
        assert response['statusCode'] == 500, \
            f"Should return 500 for storage failure, got {response['statusCode']}"
        
        # Property 2: Credit deduction should have been called
        mock_deduct.assert_called_once()
        
        # Property 3: Metadata storage should have been attempted
        mock_store_meta.assert_called_once()
        
        # Property 4: Rollback should have been called
        mock_rollback.assert_called_once()
        
        # Property 5: History storage should not be called after metadata failure
        mock_store_hist.assert_not_called()


@settings(max_examples=15, deadline=None)
@given(
    request_data=processing_request()
)
def test_pipeline_validates_required_fields(request_data):
    """
    Property 1.6: Pipeline Validates Required Fields
    
    For any document processing request missing required fields,
    the pipeline should return a 400 Bad Request error without processing.
    
    **Validates: Requirements 1.1**
    """
    # Test with missing user_email
    incomplete_request = request_data.copy()
    del incomplete_request['user_email']
    
    event = {'body': json.dumps(incomplete_request)}
    context = Mock()
    context.request_id = 'test-validation'
    
    with patch('handler.digitize_document') as mock_digitize:
        response = lambda_handler(event, context)
        
        # Property 1: Should return 400 Bad Request
        assert response['statusCode'] == 400, \
            f"Should return 400 for missing fields, got {response['statusCode']}"
        
        # Property 2: Should not call any processing stages
        mock_digitize.assert_not_called()
        
        # Property 3: Response should contain error message
        response_body = json.loads(response['body'])
        assert 'error' in response_body, \
            "Response should contain error field"
        assert 'Bad Request' in response_body['error'], \
            "Error should indicate bad request"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])