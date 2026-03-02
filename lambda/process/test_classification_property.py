"""
Property-Based Test for Document Type Classification Consistency
Feature: ai-document-processing
Property 25: Document Type Classification Consistency

**Validates: Requirements 11.3, 11.4**

For any document processed multiple times with the same content, the Bedrock_Agent
should classify it as the same document type consistently.
"""

import json
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, settings, strategies as st, assume

# Mock AWS services before importing handler
with patch('boto3.resource'), patch('boto3.client'):
    from handler import classify_document


# Custom strategies for generating test data

@st.composite
def tenant_id(draw):
    """Generate a valid tenant ID"""
    return draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-_'
    )))


@st.composite
def document_text(draw):
    """Generate document text content"""
    # Generate text that resembles different document types
    doc_type = draw(st.sampled_from(['invoice', 'purchase_order', 'market_report', 'other']))
    
    if doc_type == 'invoice':
        return draw(st.text(min_size=100, max_size=2000)) + " INVOICE " + draw(st.text(min_size=50, max_size=500))
    elif doc_type == 'purchase_order':
        return draw(st.text(min_size=100, max_size=2000)) + " PURCHASE ORDER " + draw(st.text(min_size=50, max_size=500))
    elif doc_type == 'market_report':
        return draw(st.text(min_size=100, max_size=2000)) + " MARKET REPORT " + draw(st.text(min_size=50, max_size=500))
    else:
        return draw(st.text(min_size=100, max_size=2000))


@st.composite
def document_type_name(draw):
    """Generate a valid document type name"""
    return draw(st.sampled_from(['Invoice', 'Purchase Order', 'Market Report', 'Other']))


# Property Tests

@settings(max_examples=30, deadline=None)
@given(
    text_content=document_text(),
    tenant=tenant_id(),
    num_classifications=st.integers(min_value=2, max_value=5)
)
def test_classification_consistency_same_content(text_content, tenant, num_classifications):
    """
    Property 25.1: Classification Consistency for Same Content
    
    For any document processed multiple times with the same content, the
    Bedrock_Agent should classify it as the same document type consistently.
    
    This verifies that:
    1. Multiple classifications of identical content produce identical results
    2. The classification is deterministic (not random)
    3. The document type remains stable across repeated calls
    
    **Validates: Requirements 11.3, 11.4**
    """
    # Mock Bedrock response to be deterministic based on content
    def mock_bedrock_response(text):
        """Deterministic classification based on text content"""
        text_lower = text.lower()
        if 'invoice' in text_lower:
            return 'Invoice'
        elif 'purchase order' in text_lower:
            return 'Purchase Order'
        elif 'market report' in text_lower:
            return 'Market Report'
        else:
            return 'Other'
    
    classification_results = []
    
    with patch('handler.bedrock_runtime') as mock_bedrock, \
         patch('handler.dynamodb') as mock_dynamodb:
        
        # Mock Bedrock invoke_model to return consistent classification
        def invoke_model_side_effect(**kwargs):
            body = json.loads(kwargs['body'])
            prompt = body['messages'][0]['content']
            
            # Extract document text from prompt
            doc_text = prompt.split('Document text:')[1].split('Respond with')[0].strip()
            
            # Deterministic classification
            doc_type = mock_bedrock_response(doc_text)
            
            # Mock response
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': doc_type}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 10
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Mock DynamoDB document type table
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': [{
                'document_type_id': 'test-doc-type-id',
                'document_type_name': mock_bedrock_response(text_content),
                'default_prompt_id': 'test-prompt-id'
            }]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Classify the same document multiple times
        for i in range(num_classifications):
            result = classify_document(text_content, tenant)
            classification_results.append(result['document_type'])
        
        # Property 1: All classifications should be identical
        assert len(set(classification_results)) == 1, \
            f"Classification inconsistency detected: got {set(classification_results)} for same content"
        
        # Property 2: All results should be non-empty
        for doc_type in classification_results:
            assert doc_type is not None and len(doc_type) > 0, \
                "Document type should not be empty"
        
        # Property 3: All results should be one of the valid document types
        valid_types = ['Invoice', 'Purchase Order', 'Market Report', 'Other']
        for doc_type in classification_results:
            assert doc_type in valid_types, \
                f"Document type '{doc_type}' is not a valid type"


@settings(max_examples=20, deadline=None)
@given(
    text_content=document_text(),
    tenant=tenant_id()
)
def test_classification_determinism(text_content, tenant):
    """
    Property 25.2: Classification Determinism
    
    For any document content, classifying it twice should produce the exact
    same result, demonstrating that the classification is deterministic.
    
    **Validates: Requirements 11.3, 11.4**
    """
    with patch('handler.bedrock_runtime') as mock_bedrock, \
         patch('handler.dynamodb') as mock_dynamodb:
        
        # Track Bedrock calls
        bedrock_calls = []
        
        def invoke_model_side_effect(**kwargs):
            body = json.loads(kwargs['body'])
            prompt = body['messages'][0]['content']
            
            # Store the call
            bedrock_calls.append(prompt)
            
            # Deterministic response based on content hash
            text_hash = hash(prompt)
            doc_types = ['Invoice', 'Purchase Order', 'Market Report', 'Other']
            doc_type = doc_types[abs(text_hash) % len(doc_types)]
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': doc_type}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 10
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': [{
                'document_type_id': 'test-doc-type-id',
                'document_type_name': 'Invoice',
                'default_prompt_id': 'test-prompt-id'
            }]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Classify twice
        result1 = classify_document(text_content, tenant)
        result2 = classify_document(text_content, tenant)
        
        # Property 1: Both classifications should be identical
        assert result1['document_type'] == result2['document_type'], \
            f"Classification not deterministic: first={result1['document_type']}, second={result2['document_type']}"
        
        # Property 2: Both prompts sent to Bedrock should be identical
        assert len(bedrock_calls) == 2, \
            f"Expected 2 Bedrock calls, got {len(bedrock_calls)}"
        assert bedrock_calls[0] == bedrock_calls[1], \
            "Prompts sent to Bedrock are different for same content"


@settings(max_examples=20, deadline=None)
@given(
    text_content=document_text(),
    tenant=tenant_id(),
    num_retries=st.integers(min_value=1, max_value=3)
)
def test_classification_consistency_after_retry(text_content, tenant, num_retries):
    """
    Property 25.3: Classification Consistency After Retry
    
    For any document that requires retry due to transient errors, the final
    classification should be consistent with what would have been returned
    on the first attempt (if it had succeeded).
    
    **Validates: Requirements 11.3, 11.4**
    """
    with patch('handler.bedrock_runtime') as mock_bedrock, \
         patch('handler.dynamodb') as mock_dynamodb, \
         patch('time.sleep'):  # Mock sleep to speed up test
        
        # Determine the "correct" classification for this content
        expected_doc_type = 'Invoice' if 'invoice' in text_content.lower() else 'Other'
        
        call_count = [0]
        
        def invoke_model_side_effect(**kwargs):
            call_count[0] += 1
            
            # Fail first N-1 attempts, succeed on Nth attempt
            if call_count[0] < num_retries:
                from botocore.exceptions import ClientError
                raise ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                    'InvokeModel'
                )
            
            # Success on final attempt
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': expected_doc_type}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 10
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': [{
                'document_type_id': 'test-doc-type-id',
                'document_type_name': expected_doc_type,
                'default_prompt_id': 'test-prompt-id'
            }]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Classify (will retry internally)
        result = classify_document(text_content, tenant)
        
        # Property 1: Classification should succeed after retries
        assert result['document_type'] == expected_doc_type, \
            f"Classification after retry returned wrong type: expected '{expected_doc_type}', got '{result['document_type']}'"
        
        # Property 2: Should have attempted the expected number of times
        assert call_count[0] == num_retries, \
            f"Expected {num_retries} Bedrock calls, got {call_count[0]}"


@settings(max_examples=15, deadline=None)
@given(
    text_content=document_text(),
    tenant=tenant_id()
)
def test_classification_returns_valid_document_type(text_content, tenant):
    """
    Property 25.4: Classification Returns Valid Document Type
    
    For any document content, the classification should always return one of
    the predefined valid document types, never an arbitrary or invalid value.
    
    **Validates: Requirements 11.3, 11.4**
    """
    valid_document_types = ['Invoice', 'Purchase Order', 'Market Report', 'Other']
    
    with patch('handler.bedrock_runtime') as mock_bedrock, \
         patch('handler.dynamodb') as mock_dynamodb:
        
        # Mock Bedrock to return a valid document type
        def invoke_model_side_effect(**kwargs):
            # Simulate Bedrock returning one of the valid types
            import random
            doc_type = random.choice(valid_document_types)
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': doc_type}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 10
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': [{
                'document_type_id': 'test-doc-type-id',
                'document_type_name': 'Invoice',
                'default_prompt_id': 'test-prompt-id'
            }]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Classify
        result = classify_document(text_content, tenant)
        
        # Property: Result should be one of the valid document types
        assert result['document_type'] in valid_document_types, \
            f"Invalid document type returned: '{result['document_type']}' not in {valid_document_types}"


@settings(max_examples=15, deadline=None)
@given(
    text_content=document_text(),
    tenant=tenant_id()
)
def test_classification_includes_required_metadata(text_content, tenant):
    """
    Property 25.5: Classification Includes Required Metadata
    
    For any document classification, the result should include all required
    metadata fields: document_type, document_type_id, default_prompt_id, and
    duration_ms.
    
    **Validates: Requirements 11.3, 11.4**
    """
    with patch('handler.bedrock_runtime') as mock_bedrock, \
         patch('handler.dynamodb') as mock_dynamodb:
        
        # Mock Bedrock
        def invoke_model_side_effect(**kwargs):
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': 'Invoice'}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 10
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': [{
                'document_type_id': 'test-doc-type-id',
                'document_type_name': 'Invoice',
                'default_prompt_id': 'test-prompt-id'
            }]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Classify
        result = classify_document(text_content, tenant)
        
        # Property 1: Result should contain all required fields
        required_fields = ['document_type', 'document_type_id', 'default_prompt_id', 'duration_ms']
        for field in required_fields:
            assert field in result, \
                f"Classification result missing required field: '{field}'"
        
        # Property 2: document_type should be non-empty
        assert result['document_type'] is not None and len(result['document_type']) > 0, \
            "document_type should not be empty"
        
        # Property 3: duration_ms should be a positive number
        assert isinstance(result['duration_ms'], (int, float)), \
            f"duration_ms should be a number, got {type(result['duration_ms'])}"
        assert result['duration_ms'] >= 0, \
            f"duration_ms should be non-negative, got {result['duration_ms']}"


@settings(max_examples=10, deadline=None)
@given(
    text_content=document_text(),
    tenant=tenant_id()
)
def test_classification_handles_missing_document_type_config(text_content, tenant):
    """
    Property 25.6: Classification Handles Missing Document Type Config
    
    For any document classification, if the document type is not found in the
    idp_document_type table, the system should still return the classification
    with null values for document_type_id and default_prompt_id.
    
    **Validates: Requirements 11.3, 11.4**
    """
    with patch('handler.bedrock_runtime') as mock_bedrock, \
         patch('handler.dynamodb') as mock_dynamodb:
        
        # Mock Bedrock
        def invoke_model_side_effect(**kwargs):
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': 'Invoice'}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 10
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Mock DynamoDB to return no items (document type not found)
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': []  # No configuration found
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Classify
        result = classify_document(text_content, tenant)
        
        # Property 1: Classification should still succeed
        assert result['document_type'] == 'Invoice', \
            "Classification should succeed even without document type config"
        
        # Property 2: document_type_id and default_prompt_id should be None
        assert result['document_type_id'] is None, \
            "document_type_id should be None when config not found"
        assert result['default_prompt_id'] is None, \
            "default_prompt_id should be None when config not found"
        
        # Property 3: duration_ms should still be present
        assert 'duration_ms' in result, \
            "duration_ms should be present even when config not found"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
