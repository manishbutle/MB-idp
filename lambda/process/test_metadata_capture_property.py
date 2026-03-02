"""
Property-Based Test for Metadata Capture Completeness
Feature: ai-document-processing
Property 27: Metadata Capture Completeness

**Validates: Requirements 1.8**

For any processing operation, the idp_metadata table should contain all required fields:
Processing_ID, Document Name, Prompt Name, Pages, Creation Date, File Type, File Size,
Input Tokens, Output Tokens, and LLM KPIs.
"""

import json
import pytest
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
    mock_logger.log_processing_stage = Mock()
    mock_logger.log_api_call = Mock()
    mock_logger.log_database_operation = Mock()
    mock_logger.set_context = Mock()
    mock_logger_module.create_logger.return_value = mock_logger
    sys.modules['logger_util'] = mock_logger_module
    
    from handler import store_metadata


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
def prompt_name(draw):
    """Generate a valid prompt name"""
    return draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-_ '
    )))


@st.composite
def file_type(draw):
    """Generate a valid file type"""
    return draw(st.sampled_from(['application/pdf', 'image/jpeg', 'image/png', 'image/tiff', 
                                  'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']))


@st.composite
def processing_data(draw):
    """Generate complete processing data with all required metadata fields"""
    return {
        'processing_id': str(draw(st.uuids())),
        'user_email': draw(email_address()),
        'tenant': draw(tenant_id()),
        'document_name': draw(document_name()),
        'prompt_name': draw(prompt_name()),
        'pages': draw(st.integers(min_value=1, max_value=1000)),
        'creation_date': datetime.now().isoformat(),
        'file_type': draw(file_type()),
        'file_size': draw(st.integers(min_value=1, max_value=100000000)),  # 1 byte to 100MB
        'input_tokens': draw(st.integers(min_value=1, max_value=100000)),
        'output_tokens': draw(st.integers(min_value=1, max_value=50000)),
        'textract_duration_ms': draw(st.integers(min_value=100, max_value=30000)),
        'bedrock_classification_duration_ms': draw(st.integers(min_value=50, max_value=5000)),
        'bedrock_extraction_duration_ms': draw(st.integers(min_value=100, max_value=10000)),
        'total_duration_ms': draw(st.integers(min_value=250, max_value=45000)),
        'textract_confidence': draw(st.floats(min_value=0.0, max_value=1.0)),
        'bedrock_model_id': draw(st.sampled_from(['anthropic.claude-v2', 'anthropic.claude-3-sonnet', 
                                                   'anthropic.claude-3-haiku', 'amazon.titan-text-express-v1'])),
        'credit_cost': draw(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('100.00'), places=2))
    }


# Property Tests

@settings(max_examples=50, deadline=None)
@given(
    data=processing_data()
)
def test_metadata_contains_all_required_fields(data):
    """
    Property 27.1: Metadata Contains All Required Fields
    
    For any processing operation, the metadata stored in idp_metadata table
    should contain all required fields as specified in Requirement 1.8.
    
    Required fields:
    - Processing_ID
    - Document Name
    - Prompt Name
    - Pages
    - Creation Date
    - File Type
    - File Size
    - Input Tokens
    - Output Tokens
    - LLM KPIs (textract_duration_ms, bedrock_classification_duration_ms, 
                bedrock_extraction_duration_ms, total_duration_ms, 
                textract_confidence, bedrock_model_id)
    
    **Validates: Requirements 1.8**
    """
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property 1: All required fields should be present
        required_fields = [
            'processing_id',
            'document_name',
            'prompt_name',
            'pages',
            'creation_date',
            'file_type',
            'file_size',
            'input_tokens',
            'output_tokens',
            'textract_duration_ms',
            'bedrock_classification_duration_ms',
            'bedrock_extraction_duration_ms',
            'total_duration_ms',
            'textract_confidence',
            'bedrock_model_id',
            'credit_cost'
        ]
        
        for field in required_fields:
            assert field in captured_item, \
                f"Required field '{field}' missing from metadata"
        
        # Property 2: No required field should be None
        for field in required_fields:
            assert captured_item[field] is not None, \
                f"Required field '{field}' should not be None"


@settings(max_examples=40, deadline=None)
@given(
    data=processing_data()
)
def test_metadata_field_values_match_input(data):
    """
    Property 27.2: Metadata Field Values Match Input
    
    For any processing operation, the values stored in the metadata table
    should exactly match the values provided in the processing data.
    
    **Validates: Requirements 1.8**
    """
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property: All field values should match input
        assert captured_item['processing_id'] == data['processing_id']
        assert captured_item['user_email'] == data['user_email']
        assert captured_item['tenant'] == data['tenant']
        assert captured_item['document_name'] == data['document_name']
        assert captured_item['prompt_name'] == data['prompt_name']
        assert captured_item['pages'] == data['pages']
        assert captured_item['creation_date'] == data['creation_date']
        assert captured_item['file_type'] == data['file_type']
        assert captured_item['file_size'] == data['file_size']
        assert captured_item['input_tokens'] == data['input_tokens']
        assert captured_item['output_tokens'] == data['output_tokens']
        assert captured_item['credit_cost'] == data['credit_cost']


@settings(max_examples=30, deadline=None)
@given(
    data=processing_data()
)
def test_metadata_llm_kpis_completeness(data):
    """
    Property 27.3: Metadata LLM KPIs Completeness
    
    For any processing operation, all LLM performance KPIs should be captured
    in the metadata, including duration metrics, confidence scores, and model ID.
    
    **Validates: Requirements 1.8**
    """
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property 1: All LLM KPI fields should be present
        llm_kpi_fields = [
            'textract_duration_ms',
            'bedrock_classification_duration_ms',
            'bedrock_extraction_duration_ms',
            'total_duration_ms',
            'textract_confidence',
            'bedrock_model_id'
        ]
        
        for field in llm_kpi_fields:
            assert field in captured_item, \
                f"LLM KPI field '{field}' missing from metadata"
        
        # Property 2: Duration metrics should be non-negative
        assert captured_item['textract_duration_ms'] >= 0, \
            "textract_duration_ms should be non-negative"
        assert captured_item['bedrock_classification_duration_ms'] >= 0, \
            "bedrock_classification_duration_ms should be non-negative"
        assert captured_item['bedrock_extraction_duration_ms'] >= 0, \
            "bedrock_extraction_duration_ms should be non-negative"
        assert captured_item['total_duration_ms'] >= 0, \
            "total_duration_ms should be non-negative"
        
        # Property 3: Confidence should be between 0 and 1
        assert 0 <= captured_item['textract_confidence'] <= 1, \
            f"textract_confidence should be between 0 and 1, got {captured_item['textract_confidence']}"
        
        # Property 4: Model ID should be non-empty
        assert len(captured_item['bedrock_model_id']) > 0, \
            "bedrock_model_id should not be empty"


@settings(max_examples=30, deadline=None)
@given(
    data=processing_data()
)
def test_metadata_handles_optional_fields_with_defaults(data):
    """
    Property 27.4: Metadata Handles Optional Fields with Defaults
    
    For any processing operation where optional LLM KPI fields are missing,
    the metadata should use default values (0 for numeric fields, empty string
    for model_id) rather than failing or storing None.
    
    **Validates: Requirements 1.8**
    """
    # Remove optional fields from data
    data_without_optional = {
        'processing_id': data['processing_id'],
        'user_email': data['user_email'],
        'tenant': data['tenant'],
        'document_name': data['document_name'],
        'prompt_name': data['prompt_name'],
        'pages': data['pages'],
        'creation_date': data['creation_date'],
        'file_type': data['file_type'],
        'file_size': data['file_size'],
        'input_tokens': data['input_tokens'],
        'output_tokens': data['output_tokens'],
        'credit_cost': data['credit_cost']
    }
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata without optional fields
        store_metadata(data_without_optional)
        
        # Property 1: Optional fields should have default values
        assert captured_item['textract_duration_ms'] == 0, \
            "textract_duration_ms should default to 0"
        assert captured_item['bedrock_classification_duration_ms'] == 0, \
            "bedrock_classification_duration_ms should default to 0"
        assert captured_item['bedrock_extraction_duration_ms'] == 0, \
            "bedrock_extraction_duration_ms should default to 0"
        assert captured_item['total_duration_ms'] == 0, \
            "total_duration_ms should default to 0"
        assert captured_item['textract_confidence'] == 0, \
            "textract_confidence should default to 0"
        assert captured_item['bedrock_model_id'] == '', \
            "bedrock_model_id should default to empty string"
        
        # Property 2: Required fields should still be present
        assert captured_item['processing_id'] == data['processing_id']
        assert captured_item['document_name'] == data['document_name']
        assert captured_item['pages'] == data['pages']


@settings(max_examples=25, deadline=None)
@given(
    data=processing_data()
)
def test_metadata_token_counts_are_positive(data):
    """
    Property 27.5: Metadata Token Counts Are Positive
    
    For any processing operation, the input_tokens and output_tokens fields
    should be positive integers, as they represent actual token usage.
    
    **Validates: Requirements 1.8**
    """
    # Ensure token counts are positive
    assume(data['input_tokens'] > 0)
    assume(data['output_tokens'] > 0)
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property 1: Token counts should be positive
        assert captured_item['input_tokens'] > 0, \
            f"input_tokens should be positive, got {captured_item['input_tokens']}"
        assert captured_item['output_tokens'] > 0, \
            f"output_tokens should be positive, got {captured_item['output_tokens']}"
        
        # Property 2: Token counts should be integers
        assert isinstance(captured_item['input_tokens'], int), \
            f"input_tokens should be int, got {type(captured_item['input_tokens'])}"
        assert isinstance(captured_item['output_tokens'], int), \
            f"output_tokens should be int, got {type(captured_item['output_tokens'])}"


@settings(max_examples=25, deadline=None)
@given(
    data=processing_data()
)
def test_metadata_pages_count_is_positive(data):
    """
    Property 27.6: Metadata Pages Count Is Positive
    
    For any processing operation, the pages field should be a positive integer,
    as documents must have at least one page.
    
    **Validates: Requirements 1.8**
    """
    # Ensure pages is positive
    assume(data['pages'] > 0)
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property 1: Pages should be positive
        assert captured_item['pages'] > 0, \
            f"pages should be positive, got {captured_item['pages']}"
        
        # Property 2: Pages should be an integer
        assert isinstance(captured_item['pages'], int), \
            f"pages should be int, got {type(captured_item['pages'])}"


@settings(max_examples=25, deadline=None)
@given(
    data=processing_data()
)
def test_metadata_file_size_is_positive(data):
    """
    Property 27.7: Metadata File Size Is Positive
    
    For any processing operation, the file_size field should be a positive integer,
    as files must have non-zero size.
    
    **Validates: Requirements 1.8**
    """
    # Ensure file_size is positive
    assume(data['file_size'] > 0)
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property 1: File size should be positive
        assert captured_item['file_size'] > 0, \
            f"file_size should be positive, got {captured_item['file_size']}"
        
        # Property 2: File size should be an integer
        assert isinstance(captured_item['file_size'], int), \
            f"file_size should be int, got {type(captured_item['file_size'])}"


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
@given(
    data=processing_data()
)
def test_metadata_processing_id_is_valid_uuid(data):
    """
    Property 27.8: Metadata Processing ID Is Valid UUID
    
    For any processing operation, the processing_id field should be a valid
    UUID string, ensuring unique identification of each processing operation.
    
    **Validates: Requirements 1.8**
    """
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property 1: Processing ID should be present
        assert 'processing_id' in captured_item, \
            "processing_id should be present in metadata"
        
        # Property 2: Processing ID should be a valid UUID
        import uuid
        try:
            uuid.UUID(captured_item['processing_id'])
        except ValueError:
            pytest.fail(f"processing_id is not a valid UUID: {captured_item['processing_id']}")
        
        # Property 3: Processing ID should match input
        assert captured_item['processing_id'] == data['processing_id'], \
            "processing_id should match input value"


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
@given(
    data=processing_data()
)
def test_metadata_creation_date_is_valid_timestamp(data):
    """
    Property 27.9: Metadata Creation Date Is Valid Timestamp
    
    For any processing operation, the creation_date field should be a valid
    ISO format timestamp string.
    
    **Validates: Requirements 1.8**
    """
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property 1: Creation date should be present
        assert 'creation_date' in captured_item, \
            "creation_date should be present in metadata"
        
        # Property 2: Creation date should be a valid ISO format timestamp
        try:
            datetime.fromisoformat(captured_item['creation_date'])
        except ValueError:
            pytest.fail(f"creation_date is not a valid ISO timestamp: {captured_item['creation_date']}")
        
        # Property 3: Creation date should match input
        assert captured_item['creation_date'] == data['creation_date'], \
            "creation_date should match input value"


@settings(max_examples=20, deadline=None)
@given(
    data=processing_data()
)
def test_metadata_credit_cost_is_positive(data):
    """
    Property 27.10: Metadata Credit Cost Is Positive
    
    For any processing operation, the credit_cost field should be a positive
    decimal value, as processing always incurs a cost.
    
    **Validates: Requirements 1.8**
    """
    # Ensure credit_cost is positive
    assume(data['credit_cost'] > 0)
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock DynamoDB table
        mock_table = Mock()
        captured_item = {}
        
        def capture_put_item(Item):
            captured_item.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Store metadata
        store_metadata(data)
        
        # Property 1: Credit cost should be positive
        assert captured_item['credit_cost'] > 0, \
            f"credit_cost should be positive, got {captured_item['credit_cost']}"
        
        # Property 2: Credit cost should be a Decimal
        assert isinstance(captured_item['credit_cost'], Decimal), \
            f"credit_cost should be Decimal, got {type(captured_item['credit_cost'])}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
