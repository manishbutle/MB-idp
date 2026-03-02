"""
Property-Based Test for Datapoint Extraction Completeness
Feature: ai-document-processing
Property 26: Datapoint Extraction Completeness

**Validates: Requirements 11.6, 11.7**

For any document processed with a specific prompt, the extracted results should include
all datapoints defined in that prompt, with each datapoint having either an extracted
value or a null/empty indicator.
"""

import json
import pytest
from unittest.mock import Mock, patch
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
    mock_logger_module.create_logger.return_value = mock_logger
    sys.modules['logger_util'] = mock_logger_module
    
    from handler import extract_datapoints


# Custom strategies for generating test data

@st.composite
def document_text(draw):
    """Generate document text content"""
    return draw(st.text(min_size=100, max_size=5000))


@st.composite
def datapoint_name(draw):
    """Generate a valid datapoint field name"""
    return draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_'
        )
    ).filter(lambda x: x[0].isalpha() if x else False))


@st.composite
def prompt_config(draw):
    """Generate a prompt configuration with datapoints"""
    num_datapoints = draw(st.integers(min_value=1, max_value=15))
    datapoints = [draw(datapoint_name()) for _ in range(num_datapoints)]
    # Ensure unique datapoint names
    datapoints = list(set(datapoints))
    
    return {
        'prompt_id': draw(st.uuids()).hex,
        'prompt_name': draw(st.text(min_size=1, max_size=50)),
        'prompt': draw(st.text(min_size=10, max_size=500)),
        'datapoints': datapoints
    }


# Property Tests

@settings(max_examples=30, deadline=None)
@given(
    text_content=document_text(),
    config=prompt_config()
)
def test_extraction_includes_all_datapoints(text_content, config):
    """
    Property 26.1: Extraction Includes All Datapoints
    
    For any document processed with a specific prompt, the extracted results
    should include all datapoints defined in that prompt.
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least one datapoint
    assume(len(config['datapoints']) > 0)
    
    with patch('handler.bedrock_runtime') as mock_bedrock:
        # Mock Bedrock response with some extracted values
        def invoke_model_side_effect(**kwargs):
            # Generate mock extracted data (some fields present, some missing)
            extracted_data = {}
            for i, datapoint in enumerate(config['datapoints']):
                # Randomly include some datapoints in the response
                if i % 2 == 0:
                    extracted_data[datapoint] = f"value_{i}"
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': json.dumps(extracted_data)}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 50
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        extracted_data = result['extracted_data']
        
        # Property 1: All datapoints from config should be present in result
        for datapoint in config['datapoints']:
            assert datapoint in extracted_data, \
                f"Datapoint '{datapoint}' missing from extraction results"
        
        # Property 2: Result should not have extra datapoints not in config
        # (except for special fields like 'raw_extraction')
        for key in extracted_data.keys():
            if key not in ['raw_extraction']:
                assert key in config['datapoints'], \
                    f"Unexpected datapoint '{key}' in extraction results"


@settings(max_examples=30, deadline=None)
@given(
    text_content=document_text(),
    config=prompt_config()
)
def test_missing_datapoints_have_null_indicator(text_content, config):
    """
    Property 26.2: Missing Datapoints Have Null Indicator
    
    For any datapoint that cannot be extracted from the document, the result
    should include that datapoint with a null or empty indicator.
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least one datapoint
    assume(len(config['datapoints']) > 0)
    
    with patch('handler.bedrock_runtime') as mock_bedrock:
        # Mock Bedrock response with NO extracted values (all missing)
        def invoke_model_side_effect(**kwargs):
            # Return empty extraction
            extracted_data = {}
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': json.dumps(extracted_data)}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 10
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        extracted_data = result['extracted_data']
        
        # Property 1: All datapoints should be present
        for datapoint in config['datapoints']:
            assert datapoint in extracted_data, \
                f"Missing datapoint '{datapoint}' should still be present in results"
        
        # Property 2: Missing datapoints should have None value
        for datapoint in config['datapoints']:
            assert extracted_data[datapoint] is None, \
                f"Missing datapoint '{datapoint}' should have None value, got {extracted_data[datapoint]}"


@settings(max_examples=25, deadline=None)
@given(
    text_content=document_text(),
    config=prompt_config()
)
def test_extraction_completeness_with_partial_results(text_content, config):
    """
    Property 26.3: Extraction Completeness with Partial Results
    
    For any document where only some datapoints can be extracted, the result
    should include all datapoints: extracted ones with values, missing ones with null.
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least 2 datapoints
    assume(len(config['datapoints']) >= 2)
    
    with patch('handler.bedrock_runtime') as mock_bedrock:
        # Mock Bedrock response with partial extraction
        def invoke_model_side_effect(**kwargs):
            # Extract only the first half of datapoints
            extracted_data = {}
            half = len(config['datapoints']) // 2
            for i in range(half):
                extracted_data[config['datapoints'][i]] = f"extracted_value_{i}"
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': json.dumps(extracted_data)}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 30
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        extracted_data = result['extracted_data']
        
        # Property 1: All datapoints should be present
        assert len(extracted_data) >= len(config['datapoints']), \
            f"Result should contain at least {len(config['datapoints'])} datapoints"
        
        for datapoint in config['datapoints']:
            assert datapoint in extracted_data, \
                f"Datapoint '{datapoint}' missing from results"
        
        # Property 2: Some datapoints should have values
        values_present = sum(1 for dp in config['datapoints'] if extracted_data[dp] is not None)
        assert values_present > 0, \
            "At least some datapoints should have extracted values"
        
        # Property 3: Some datapoints should be None (missing)
        values_missing = sum(1 for dp in config['datapoints'] if extracted_data[dp] is None)
        assert values_missing > 0, \
            "At least some datapoints should be None (missing)"


@settings(max_examples=25, deadline=None)
@given(
    text_content=document_text(),
    config=prompt_config()
)
def test_extraction_result_structure(text_content, config):
    """
    Property 26.4: Extraction Result Structure
    
    For any extraction operation, the result should have the correct structure
    with extracted_data, input_tokens, output_tokens, and model_id fields.
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least one datapoint
    assume(len(config['datapoints']) > 0)
    
    with patch('handler.bedrock_runtime') as mock_bedrock:
        # Mock Bedrock response
        def invoke_model_side_effect(**kwargs):
            extracted_data = {dp: f"value_{dp}" for dp in config['datapoints']}
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': json.dumps(extracted_data)}],
                'usage': {
                    'input_tokens': 150,
                    'output_tokens': 75
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        
        # Property 1: Result should have required fields
        required_fields = ['extracted_data', 'input_tokens', 'output_tokens', 'model_id']
        for field in required_fields:
            assert field in result, \
                f"Result missing required field: '{field}'"
        
        # Property 2: extracted_data should be a dict
        assert isinstance(result['extracted_data'], dict), \
            f"extracted_data should be a dict, got {type(result['extracted_data'])}"
        
        # Property 3: Token counts should be non-negative integers
        assert isinstance(result['input_tokens'], int), \
            f"input_tokens should be int, got {type(result['input_tokens'])}"
        assert result['input_tokens'] >= 0, \
            f"input_tokens should be non-negative, got {result['input_tokens']}"
        
        assert isinstance(result['output_tokens'], int), \
            f"output_tokens should be int, got {type(result['output_tokens'])}"
        assert result['output_tokens'] >= 0, \
            f"output_tokens should be non-negative, got {result['output_tokens']}"
        
        # Property 4: model_id should be a non-empty string
        assert isinstance(result['model_id'], str), \
            f"model_id should be string, got {type(result['model_id'])}"
        assert len(result['model_id']) > 0, \
            "model_id should not be empty"


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
@given(
    text_content=document_text(),
    config=prompt_config()
)
def test_extraction_handles_json_in_markdown(text_content, config):
    """
    Property 26.5: Extraction Handles JSON in Markdown
    
    For any extraction where Bedrock returns JSON wrapped in markdown code blocks,
    the system should correctly parse the JSON and include all datapoints.
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least one datapoint
    assume(len(config['datapoints']) > 0)
    
    with patch('handler.bedrock_runtime') as mock_bedrock:
        # Mock Bedrock response with JSON in markdown code block
        def invoke_model_side_effect(**kwargs):
            extracted_data = {dp: f"value_{dp}" for dp in config['datapoints'][:3]}
            json_str = json.dumps(extracted_data)
            
            # Wrap in markdown code block
            markdown_response = f"```json\n{json_str}\n```"
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': markdown_response}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 50
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        extracted_data = result['extracted_data']
        
        # Property 1: All datapoints should be present
        for datapoint in config['datapoints']:
            assert datapoint in extracted_data, \
                f"Datapoint '{datapoint}' missing after parsing markdown JSON"
        
        # Property 2: Extracted datapoints should have values
        for i, datapoint in enumerate(config['datapoints'][:3]):
            assert extracted_data[datapoint] is not None, \
                f"Datapoint '{datapoint}' should have a value"


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
@given(
    text_content=document_text(),
    config=prompt_config()
)
def test_extraction_handles_invalid_json_response(text_content, config):
    """
    Property 26.6: Extraction Handles Invalid JSON Response
    
    For any extraction where Bedrock returns invalid JSON, the system should
    still include all datapoints with None values and store the raw response.
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least one datapoint
    assume(len(config['datapoints']) > 0)
    
    with patch('handler.bedrock_runtime') as mock_bedrock:
        # Mock Bedrock response with invalid JSON
        def invoke_model_side_effect(**kwargs):
            # Return invalid JSON
            invalid_json = "This is not valid JSON { incomplete"
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': invalid_json}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 20
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        extracted_data = result['extracted_data']
        
        # Property 1: All datapoints should still be present
        for datapoint in config['datapoints']:
            assert datapoint in extracted_data, \
                f"Datapoint '{datapoint}' should be present even with invalid JSON"
        
        # Property 2: All datapoints should have None value
        for datapoint in config['datapoints']:
            assert extracted_data[datapoint] is None, \
                f"Datapoint '{datapoint}' should be None when JSON parsing fails"
        
        # Property 3: Raw extraction should be stored
        assert 'raw_extraction' in extracted_data, \
            "raw_extraction should be present when JSON parsing fails"


@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
@given(
    text_content=document_text(),
    config=prompt_config(),
    num_retries=st.integers(min_value=1, max_value=2)
)
def test_extraction_completeness_after_retry(text_content, config, num_retries):
    """
    Property 26.7: Extraction Completeness After Retry
    
    For any extraction that requires retry due to transient errors, the final
    result should still include all datapoints with appropriate values or null.
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least one datapoint
    assume(len(config['datapoints']) > 0)
    
    with patch('handler.bedrock_runtime') as mock_bedrock, \
         patch('time.sleep'):  # Mock sleep to speed up test
        
        call_count = [0]
        
        def invoke_model_side_effect(**kwargs):
            call_count[0] += 1
            
            # Fail first N-1 attempts
            if call_count[0] < num_retries:
                from botocore.exceptions import ClientError
                raise ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                    'InvokeModel'
                )
            
            # Success on final attempt
            extracted_data = {dp: f"value_{dp}" for dp in config['datapoints']}
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': json.dumps(extracted_data)}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 50
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        extracted_data = result['extracted_data']
        
        # Property 1: All datapoints should be present after retry
        for datapoint in config['datapoints']:
            assert datapoint in extracted_data, \
                f"Datapoint '{datapoint}' missing after retry"
        
        # Property 2: All datapoints should have values (successful extraction)
        for datapoint in config['datapoints']:
            assert extracted_data[datapoint] is not None, \
                f"Datapoint '{datapoint}' should have value after successful retry"
        
        # Property 3: Should have attempted the expected number of times
        assert call_count[0] == num_retries, \
            f"Expected {num_retries} Bedrock calls, got {call_count[0]}"


@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
@given(
    text_content=document_text(),
    config=prompt_config()
)
def test_extraction_datapoint_count_matches_config(text_content, config):
    """
    Property 26.8: Extraction Datapoint Count Matches Config
    
    For any extraction, the number of datapoints in the result should match
    the number of datapoints defined in the prompt configuration.
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least one datapoint
    assume(len(config['datapoints']) > 0)
    
    with patch('handler.bedrock_runtime') as mock_bedrock:
        # Mock Bedrock response
        def invoke_model_side_effect(**kwargs):
            # Return some extracted values
            extracted_data = {}
            for i, dp in enumerate(config['datapoints']):
                if i % 3 == 0:
                    extracted_data[dp] = f"value_{i}"
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': json.dumps(extracted_data)}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 40
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        extracted_data = result['extracted_data']
        
        # Count datapoints (excluding special fields like raw_extraction)
        actual_datapoints = [k for k in extracted_data.keys() if k in config['datapoints']]
        
        # Property: Number of datapoints should match config
        assert len(actual_datapoints) == len(config['datapoints']), \
            f"Expected {len(config['datapoints'])} datapoints, got {len(actual_datapoints)}"


@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.data_too_large])
@given(
    text_content=document_text(),
    config=prompt_config()
)
def test_extraction_preserves_datapoint_names(text_content, config):
    """
    Property 26.9: Extraction Preserves Datapoint Names
    
    For any extraction, the datapoint names in the result should exactly match
    the datapoint names defined in the prompt configuration (case-sensitive).
    
    **Validates: Requirements 11.6, 11.7**
    """
    # Ensure we have at least one datapoint
    assume(len(config['datapoints']) > 0)
    
    with patch('handler.bedrock_runtime') as mock_bedrock:
        # Mock Bedrock response
        def invoke_model_side_effect(**kwargs):
            extracted_data = {dp: f"value_{dp}" for dp in config['datapoints']}
            
            mock_response = {}
            mock_body = Mock()
            mock_body.read.return_value = json.dumps({
                'content': [{'text': json.dumps(extracted_data)}],
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 50
                }
            }).encode('utf-8')
            mock_response['body'] = mock_body
            
            return mock_response
        
        mock_bedrock.invoke_model.side_effect = invoke_model_side_effect
        
        # Call extraction
        result = extract_datapoints(text_content, config)
        extracted_data = result['extracted_data']
        
        # Property: All config datapoint names should be present exactly as defined
        for datapoint in config['datapoints']:
            assert datapoint in extracted_data, \
                f"Datapoint name '{datapoint}' not preserved in results"
            
            # Check case sensitivity
            lowercase_match = datapoint.lower() in [k.lower() for k in extracted_data.keys()]
            exact_match = datapoint in extracted_data.keys()
            
            assert exact_match, \
                f"Datapoint name '{datapoint}' should be case-sensitive match"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
