"""
Unit tests for Process Document Lambda function
Tests document processing pipeline, credit management, and data storage
"""

import json
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import base64

# Mock the logger before importing handler
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

# Add the lambda/process directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import handler as handler


# Mock Lambda context
class MockLambdaContext:
    """Mock Lambda context for testing"""
    def __init__(self):
        self.function_name = 'test-function'
        self.function_version = '$LATEST'
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        self.memory_limit_in_mb = 128
        self.aws_request_id = 'test-request-id'
        self.log_group_name = '/aws/lambda/test-function'
        self.log_stream_name = '2024/01/01/[$LATEST]test'
    
    def get_remaining_time_in_millis(self):
        return 30000


class TestTextractIntegration:
    """Tests for Textract document digitization"""
    
    @patch('handler.textract')
    def test_digitize_document_success(self, mock_textract):
        """Test successful document digitization"""
        # Mock Textract response
        mock_textract.detect_document_text.return_value = {
            'Blocks': [
                {'BlockType': 'PAGE'},
                {'BlockType': 'LINE', 'Text': 'Invoice Number: 12345'},
                {'BlockType': 'LINE', 'Text': 'Total Amount: $100.00'}
            ],
            'DocumentMetadata': {'Pages': 1}
        }
        
        # Call function
        result = handler.digitize_document(b'fake_pdf_data', 'test.pdf')
        
        # Assertions
        assert 'text' in result
        assert 'page_count' in result
        assert result['page_count'] == 1
        assert 'Invoice Number' in result['text']
    
    @patch('handler.textract')
    @patch('handler.time.sleep')
    def test_digitize_document_retry_logic(self, mock_sleep, mock_textract):
        """Test Textract failure and retry logic"""
        from botocore.exceptions import ClientError
        
        # Mock first call fails, second succeeds
        mock_textract.detect_document_text.side_effect = [
            ClientError({'Error': {'Code': 'ThrottlingException'}}, 'detect_document_text'),
            {
                'Blocks': [
                    {'BlockType': 'PAGE'},
                    {'BlockType': 'LINE', 'Text': 'Test content'}
                ],
                'DocumentMetadata': {'Pages': 1}
            }
        ]
        
        # Call function
        result = handler.digitize_document(b'fake_pdf_data', 'test.pdf')
        
        # Should have retried
        assert mock_textract.detect_document_text.call_count == 2
        assert result['page_count'] == 1


class TestBedrockClassification:
    """Tests for Bedrock document classification"""
    
    @patch('handler.dynamodb')
    @patch('handler.bedrock_runtime')
    def test_classify_document_success(self, mock_bedrock, mock_dynamodb):
        """Test successful document classification"""
        # Mock Bedrock response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'content': [{'text': 'Invoice'}],
            'usage': {'input_tokens': 100, 'output_tokens': 10}
        }).encode()
        
        mock_bedrock.invoke_model.return_value = {'body': mock_response}
        
        # Mock DynamoDB document type lookup
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [{
                'document_type_id': 'doc_type_1',
                'document_type_name': 'Invoice',
                'default_prompt_id': 'prompt_1'
            }]
        }
        
        # Call function
        result = handler.classify_document('Invoice text content', 'tenant1')
        
        # Assertions
        assert result['document_type'] == 'Invoice'
        assert result['document_type_id'] == 'doc_type_1'
        assert result['default_prompt_id'] == 'prompt_1'
    
    @patch('handler.bedrock_runtime')
    @patch('handler.time.sleep')
    def test_classify_document_retry_logic(self, mock_sleep, mock_bedrock):
        """Test Bedrock failure and retry logic"""
        from botocore.exceptions import ClientError
        
        # Mock first call fails, second succeeds
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'content': [{'text': 'Invoice'}]
        }).encode()
        
        mock_bedrock.invoke_model.side_effect = [
            ClientError({'Error': {'Code': 'ThrottlingException'}}, 'invoke_model'),
            {'body': mock_response}
        ]
        
        # Call function (will use default config since DynamoDB not mocked)
        with patch('handler.dynamodb'):
            result = handler.classify_document('Test content', 'tenant1')
        
        # Should have retried
        assert mock_bedrock.invoke_model.call_count == 2


class TestDatapointExtraction:
    """Tests for Bedrock datapoint extraction"""
    
    @patch('handler.bedrock_runtime')
    def test_extract_datapoints_success(self, mock_bedrock):
        """Test successful datapoint extraction"""
        # Mock Bedrock response with JSON
        extracted_json = {
            'invoice_number': 'INV-12345',
            'invoice_date': '2024-01-15',
            'total_amount': '100.00'
        }
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'content': [{'text': f'```json\n{json.dumps(extracted_json)}\n```'}],
            'usage': {'input_tokens': 500, 'output_tokens': 50}
        }).encode()
        
        mock_bedrock.invoke_model.return_value = {'body': mock_response}
        
        # Call function
        prompt_config = {
            'prompt': 'Extract invoice details',
            'datapoints': ['invoice_number', 'invoice_date', 'total_amount']
        }
        result = handler.extract_datapoints('Invoice text', prompt_config)
        
        # Assertions
        assert 'extracted_data' in result
        assert result['extracted_data']['invoice_number'] == 'INV-12345'
        assert result['input_tokens'] == 500
        assert result['output_tokens'] == 50


class TestCreditManagement:
    """Tests for credit calculation and deduction"""
    
    @patch('handler.dynamodb')
    def test_calculate_credit_cost(self, mock_dynamodb):
        """Test credit cost calculation"""
        # Mock rates table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.scan.return_value = {
            'Items': [
                {'rate_type': 'base', 'amount': 0.50},
                {'rate_type': 'per_page', 'amount': 0.10},
                {'rate_type': 'per_token', 'amount': 0.0001}
            ]
        }
        
        # Call function
        cost = handler.calculate_credit_cost(5, 1000, 200, 'tenant1')
        
        # Expected: 0.50 (base) + 0.50 (5 pages * 0.10) + 0.12 (1200 tokens * 0.0001) = 1.12
        assert cost == Decimal('1.12')
    
    @patch('handler.dynamodb')
    def test_insufficient_balance_rejection(self, mock_dynamodb):
        """Test insufficient balance scenario"""
        # Mock transactions table with low balance
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [
                {'amount': 10.0},  # Only $10 available
                {'amount': -5.0}   # $5 used
            ]
        }
        
        # Try to deduct more than available
        with pytest.raises(Exception) as exc_info:
            handler.deduct_credit('test@example.com', 'tenant1', Decimal('10.00'), 'proc_123', 5)
        
        assert 'Insufficient balance' in str(exc_info.value)
    
    @patch('handler.dynamodb')
    def test_deduct_credit_success(self, mock_dynamodb):
        """Test successful credit deduction"""
        # Mock sufficient balance
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': [{'amount': 100.0}]  # $100 available
        }
        mock_table.put_item.return_value = {}
        
        # Call function
        result = handler.deduct_credit('test@example.com', 'tenant1', Decimal('5.00'), 'proc_123', 3)
        
        # Assertions
        assert 'transaction_id' in result
        assert result['amount_deducted'] == 5.0
        assert result['new_balance'] == 95.0


class TestDataStorage:
    """Tests for metadata and history storage"""
    
    @patch('handler.dynamodb')
    def test_store_metadata(self, mock_dynamodb):
        """Test metadata storage"""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.put_item.return_value = {}
        
        # Call function
        processing_data = {
            'processing_id': 'proc_123',
            'user_email': 'test@example.com',
            'tenant': 'tenant1',
            'document_name': 'test.pdf',
            'prompt_name': 'Invoice',
            'pages': 3,
            'creation_date': '2024-01-15T10:00:00',
            'file_type': 'pdf',
            'file_size': 1024,
            'input_tokens': 500,
            'output_tokens': 50,
            'credit_cost': 1.5
        }
        
        handler.store_metadata(processing_data)
        
        # Should have called put_item
        mock_table.put_item.assert_called_once()
    
    @patch('handler.dynamodb')
    def test_store_history(self, mock_dynamodb):
        """Test history storage"""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.put_item.return_value = {}
        
        # Call function
        processing_data = {
            'processing_id': 'proc_123',
            'user_email': 'test@example.com',
            'tenant': 'tenant1',
            'document_name': 'test.pdf',
            'document_type': 'Invoice',
            'pages': 3,
            'extracted_values': {'invoice_number': 'INV-123'},
            'timestamp': '2024-01-15T10:00:00',
            'file_type': 'pdf',
            'file_size': 1024
        }
        
        handler.store_history(processing_data)
        
        # Should have called put_item
        mock_table.put_item.assert_called_once()


class TestProcessingPipeline:
    """Tests for complete document processing pipeline"""
    
    @patch('handler.store_history')
    @patch('handler.store_metadata')
    @patch('handler.deduct_credit')
    @patch('handler.calculate_credit_cost')
    @patch('handler.extract_datapoints')
    @patch('handler.get_extraction_prompt')
    @patch('handler.classify_document')
    @patch('handler.digitize_document')
    def test_document_processing_pipeline_completeness(
        self, mock_digitize, mock_classify, mock_get_prompt, 
        mock_extract, mock_calc_cost, mock_deduct, mock_store_meta, mock_store_hist
    ):
        """Test complete document processing pipeline"""
        # Mock all stages
        mock_digitize.return_value = {
            'text': 'Invoice content',
            'page_count': 2,
            'confidence': 2
        }
        
        mock_classify.return_value = {
            'document_type': 'Invoice',
            'document_type_id': 'doc_1',
            'default_prompt_id': 'prompt_1'
        }
        
        mock_get_prompt.return_value = {
            'prompt_id': 'prompt_1',
            'prompt_name': 'Invoice',
            'prompt': 'Extract invoice data'
        }
        
        mock_extract.return_value = {
            'extracted_data': {'invoice_number': 'INV-123'},
            'input_tokens': 500,
            'output_tokens': 50,
            'model_id': 'claude-3-haiku'
        }
        
        mock_calc_cost.return_value = Decimal('1.50')
        
        mock_deduct.return_value = {
            'transaction_id': 'trans_123',
            'previous_balance': 100.0,
            'amount_deducted': 1.50,
            'new_balance': 98.50
        }
        
        # Create event
        document_data = base64.b64encode(b'fake_pdf_content').decode()
        event = {
            'body': json.dumps({
                'user_email': 'test@example.com',
                'tenant': 'tenant1',
                'document_data': document_data,
                'document_name': 'test.pdf',
                'file_type': 'pdf',
                'file_size': 1024
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Assertions - all stages should be called
        assert response['statusCode'] == 200
        mock_digitize.assert_called_once()
        mock_classify.assert_called_once()
        mock_get_prompt.assert_called_once()
        mock_extract.assert_called_once()
        mock_calc_cost.assert_called_once()
        mock_deduct.assert_called_once()
        mock_store_meta.assert_called_once()
        mock_store_hist.assert_called_once()
    
    @patch('handler.rollback_transaction')
    @patch('handler.store_metadata')
    @patch('handler.deduct_credit')
    @patch('handler.calculate_credit_cost')
    @patch('handler.extract_datapoints')
    @patch('handler.get_extraction_prompt')
    @patch('handler.classify_document')
    @patch('handler.digitize_document')
    def test_transaction_rollback_on_failure(
        self, mock_digitize, mock_classify, mock_get_prompt, 
        mock_extract, mock_calc_cost, mock_deduct, mock_store_meta, mock_rollback
    ):
        """Test transaction rollback on failure"""
        # Mock successful stages up to metadata storage
        mock_digitize.return_value = {'text': 'content', 'page_count': 1, 'confidence': 1}
        mock_classify.return_value = {'document_type': 'Invoice', 'document_type_id': None, 'default_prompt_id': None}
        mock_get_prompt.return_value = {'prompt_id': 'p1', 'prompt_name': 'Invoice', 'prompt': 'Extract'}
        mock_extract.return_value = {'extracted_data': {}, 'input_tokens': 100, 'output_tokens': 10, 'model_id': 'claude'}
        mock_calc_cost.return_value = Decimal('1.0')
        mock_deduct.return_value = {'transaction_id': 't1', 'previous_balance': 10.0, 'amount_deducted': 1.0, 'new_balance': 9.0}
        
        # Mock metadata storage failure
        mock_store_meta.side_effect = Exception('Storage failed')
        
        # Create event
        document_data = base64.b64encode(b'fake_pdf').decode()
        event = {
            'body': json.dumps({
                'user_email': 'test@example.com',
                'tenant': 'tenant1',
                'document_data': document_data,
                'document_name': 'test.pdf'
            })
        }
        
        # Call handler
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Should rollback transaction
        mock_rollback.assert_called_once()
        assert response['statusCode'] == 500


class TestDocumentTypeNotFound:
    """Test default prompt usage when document type not found"""
    
    @patch('handler.dynamodb')
    @patch('handler.bedrock_runtime')
    def test_document_type_not_found_uses_default(self, mock_bedrock, mock_dynamodb):
        """Test that default prompt is used when document type not found"""
        # Mock Bedrock classification
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'content': [{'text': 'Unknown Type'}]
        }).encode()
        mock_bedrock.invoke_model.return_value = {'body': mock_response}
        
        # Mock DynamoDB returns no document type
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {'Items': []}
        
        # Call classify_document
        result = handler.classify_document('Unknown document', 'tenant1')
        
        # Should return None for IDs
        assert result['document_type_id'] is None
        assert result['default_prompt_id'] is None
        
        # Now test get_extraction_prompt with None prompt_id
        prompt = handler.get_extraction_prompt(None, 'Unknown Type', 'tenant1')
        
        # Should return default prompt
        assert prompt['prompt_id'] == 'default'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
