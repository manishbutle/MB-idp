"""
Property-Based Test for Transaction History Completeness
Feature: ai-document-processing
Property 24: Transaction History Completeness

**Validates: Requirements 22.4, 22.5, 22.8**

For any user with transaction records, the transaction history should include all 
transactions (both credits and debits) with complete information, and the sum of 
all transaction amounts should equal the current balance.
"""

import json
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from hypothesis import given, settings, strategies as st, assume

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
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    mock_logger_module.create_logger.return_value = mock_logger
    sys.modules['logger_util'] = mock_logger_module
    
    from handler import handle_mytransactions, handle_available_balance


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
def transaction_record(draw, user_email, tenant):
    """Generate a single transaction record"""
    action = draw(st.sampled_from(['Utilized', 'Top-up', 'Admin Credit']))
    
    # Utilized transactions are negative, others are positive
    if action == 'Utilized':
        amount = -abs(draw(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('100.00'), places=2)))
        pages = draw(st.integers(min_value=1, max_value=50))
        processing_id = f"proc-{draw(st.uuids())}"
    else:
        amount = abs(draw(st.decimals(min_value=Decimal('1.00'), max_value=Decimal('500.00'), places=2)))
        pages = None
        processing_id = None
    
    return {
        'transaction_id': f"txn-{draw(st.uuids())}",
        'user_email': user_email,
        'tenant': tenant,
        'processing_id': processing_id,
        'action': action,
        'amount': float(amount),
        'pages': pages,
        'timestamp': (datetime.now() - timedelta(days=draw(st.integers(min_value=0, max_value=365)))).isoformat(),
        'remark': draw(st.text(min_size=0, max_size=100)) if action != 'Utilized' else None
    }


@st.composite
def transaction_history(draw):
    """Generate a complete transaction history for a user"""
    user_email = draw(email_address())
    tenant = draw(tenant_id())
    
    # Generate 5-50 transactions
    num_transactions = draw(st.integers(min_value=5, max_value=50))
    transactions = [draw(transaction_record(user_email, tenant)) for _ in range(num_transactions)]
    
    # Sort by timestamp descending (newest first)
    transactions.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return {
        'user_email': user_email,
        'tenant': tenant,
        'transactions': transactions
    }


# Property Tests

@settings(max_examples=30, deadline=None)
@given(
    history=transaction_history()
)
def test_transaction_history_includes_all_transactions(history):
    """
    Property 24.1: Transaction History Includes All Transactions
    
    For any user with transaction records, the mytransactions API should return
    all transactions when paginating through the complete history.
    
    **Validates: Requirements 22.4, 22.5**
    """
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': history['user_email'],
            'tenant': history['tenant']
        }
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Simulate pagination - return transactions in pages of 20
        page_size = 20
        all_returned_transactions = []
        
        for page_start in range(0, len(history['transactions']), page_size):
            page_end = min(page_start + page_size, len(history['transactions']))
            page_transactions = history['transactions'][page_start:page_end]
            
            has_more = page_end < len(history['transactions'])
            last_key = {'transaction_id': page_transactions[-1]['transaction_id']} if has_more else None
            
            mock_table.query.return_value = {
                'Items': page_transactions,
                'LastEvaluatedKey': last_key
            }
            
            # Call API
            event = {
                'queryStringParameters': {'page_size': str(page_size)}
            }
            
            response = handle_mytransactions(event, Mock())
            
            # Parse response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            
            all_returned_transactions.extend(body['transactions'])
            
            # If no more pages, break
            if not body.get('has_more'):
                break
        
        # Property 1: All transactions should be returned
        assert len(all_returned_transactions) == len(history['transactions']), \
            f"Should return all {len(history['transactions'])} transactions, got {len(all_returned_transactions)}"
        
        # Property 2: Transaction IDs should match
        returned_ids = {t['transaction_id'] for t in all_returned_transactions}
        expected_ids = {t['transaction_id'] for t in history['transactions']}
        assert returned_ids == expected_ids, \
            "Returned transaction IDs should match expected IDs"


@settings(max_examples=25, deadline=None)
@given(
    history=transaction_history()
)
def test_transaction_history_contains_complete_information(history):
    """
    Property 24.2: Transaction History Contains Complete Information
    
    For any transaction in the history, all required fields should be present
    and contain valid values.
    
    **Validates: Requirements 22.4, 22.5**
    """
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': history['user_email'],
            'tenant': history['tenant']
        }
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': history['transactions'][:20],  # First page
            'LastEvaluatedKey': None
        }
        
        # Call API
        event = {'queryStringParameters': {}}
        response = handle_mytransactions(event, Mock())
        
        # Parse response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        transactions = body['transactions']
        
        # Property 1: All transactions should have required fields
        required_fields = ['transaction_id', 'user_email', 'tenant', 'action', 'amount', 'timestamp']
        
        for txn in transactions:
            for field in required_fields:
                assert field in txn, \
                    f"Transaction should contain field '{field}'"
                assert txn[field] is not None, \
                    f"Field '{field}' should not be None"
        
        # Property 2: Utilized transactions should have processing_id and pages
        for txn in transactions:
            if txn['action'] == 'Utilized':
                assert 'processing_id' in txn, \
                    "Utilized transaction should have processing_id"
                assert 'pages' in txn, \
                    "Utilized transaction should have pages"
                assert txn['amount'] < 0, \
                    "Utilized transaction amount should be negative"
        
        # Property 3: Top-up and Admin Credit transactions should have positive amounts
        for txn in transactions:
            if txn['action'] in ['Top-up', 'Admin Credit']:
                assert txn['amount'] > 0, \
                    f"{txn['action']} transaction amount should be positive"


@settings(max_examples=20, deadline=None)
@given(
    history=transaction_history()
)
def test_transaction_history_sum_equals_balance(history):
    """
    Property 24.3: Transaction History Sum Equals Balance
    
    For any user, the sum of all transaction amounts in the history should
    equal the current available balance.
    
    **Validates: Requirements 22.4, 22.5, 22.8**
    """
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': history['user_email'],
            'tenant': history['tenant']
        }
        
        # Calculate expected balance
        expected_balance = sum(Decimal(str(t['amount'])) for t in history['transactions'])
        
        # Mock DynamoDB table for transactions
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock query for all transactions
        mock_table.query.return_value = {
            'Items': history['transactions']
        }
        
        # Call available_balance API
        event = {}
        response = handle_available_balance(event, Mock())
        
        # Parse response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        actual_balance = Decimal(str(body['available_balance']))
        
        # Property: Balance should equal sum of all transactions
        assert actual_balance == expected_balance, \
            f"Balance {actual_balance} should equal sum of transactions {expected_balance}"


@settings(max_examples=20, deadline=None)
@given(
    history=transaction_history()
)
def test_transaction_history_sorted_by_timestamp_descending(history):
    """
    Property 24.4: Transaction History Sorted by Timestamp Descending
    
    For any transaction history, transactions should be returned in descending
    order by timestamp (newest first).
    
    **Validates: Requirements 22.4**
    """
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': history['user_email'],
            'tenant': history['tenant']
        }
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': history['transactions'][:20],  # First page
            'LastEvaluatedKey': None
        }
        
        # Call API
        event = {'queryStringParameters': {}}
        response = handle_mytransactions(event, Mock())
        
        # Parse response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        transactions = body['transactions']
        
        # Property: Transactions should be sorted by timestamp descending
        if len(transactions) > 1:
            for i in range(len(transactions) - 1):
                current_timestamp = datetime.fromisoformat(transactions[i]['timestamp'])
                next_timestamp = datetime.fromisoformat(transactions[i + 1]['timestamp'])
                
                assert current_timestamp >= next_timestamp, \
                    f"Transactions should be sorted by timestamp descending, but {current_timestamp} < {next_timestamp}"


@settings(max_examples=15, deadline=None)
@given(
    history=transaction_history()
)
def test_transaction_history_pagination_consistency(history):
    """
    Property 24.5: Transaction History Pagination Consistency
    
    For any transaction history, paginating through all pages should return
    the same transactions as fetching all at once (if that were possible).
    
    **Validates: Requirements 22.4, 22.5**
    """
    # Ensure we have enough transactions to test pagination
    assume(len(history['transactions']) > 10)
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': history['user_email'],
            'tenant': history['tenant']
        }
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Test with different page sizes
        page_sizes = [5, 10, 20]
        
        for page_size in page_sizes:
            all_paginated_transactions = []
            
            # Simulate pagination
            for page_start in range(0, len(history['transactions']), page_size):
                page_end = min(page_start + page_size, len(history['transactions']))
                page_transactions = history['transactions'][page_start:page_end]
                
                has_more = page_end < len(history['transactions'])
                last_key = {'transaction_id': page_transactions[-1]['transaction_id']} if has_more else None
                
                mock_table.query.return_value = {
                    'Items': page_transactions,
                    'LastEvaluatedKey': last_key
                }
                
                # Call API
                event = {
                    'queryStringParameters': {'page_size': str(page_size)}
                }
                
                response = handle_mytransactions(event, Mock())
                
                # Parse response
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                
                all_paginated_transactions.extend(body['transactions'])
                
                # If no more pages, break
                if not body.get('has_more'):
                    break
            
            # Property: Paginated results should match original transactions
            assert len(all_paginated_transactions) == len(history['transactions']), \
                f"Paginated results (page_size={page_size}) should have {len(history['transactions'])} transactions, got {len(all_paginated_transactions)}"
            
            # Transaction IDs should match
            paginated_ids = [t['transaction_id'] for t in all_paginated_transactions]
            expected_ids = [t['transaction_id'] for t in history['transactions']]
            
            assert paginated_ids == expected_ids, \
                f"Paginated transaction IDs (page_size={page_size}) should match expected order"


@settings(max_examples=15, deadline=None)
@given(
    history=transaction_history()
)
def test_transaction_history_tenant_isolation(history):
    """
    Property 24.6: Transaction History Tenant Isolation
    
    For any user, the transaction history should only include transactions
    for their tenant, not transactions from other tenants.
    
    **Validates: Requirements 22.4, 22.5, 23.2, 23.6**
    """
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': history['user_email'],
            'tenant': history['tenant']
        }
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            'Items': history['transactions'][:20],  # First page
            'LastEvaluatedKey': None
        }
        
        # Call API
        event = {'queryStringParameters': {}}
        response = handle_mytransactions(event, Mock())
        
        # Parse response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        transactions = body['transactions']
        
        # Property: All transactions should belong to the user's tenant
        for txn in transactions:
            assert txn['tenant'] == history['tenant'], \
                f"Transaction should belong to tenant {history['tenant']}, got {txn['tenant']}"
            assert txn['user_email'] == history['user_email'], \
                f"Transaction should belong to user {history['user_email']}, got {txn['user_email']}"


@settings(max_examples=10, deadline=None)
@given(
    history=transaction_history()
)
def test_transaction_history_page_size_validation(history):
    """
    Property 24.7: Transaction History Page Size Validation
    
    For any transaction history request, invalid page sizes should be rejected
    with appropriate error messages.
    
    **Validates: Requirements 22.4**
    """
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': history['user_email'],
            'tenant': history['tenant']
        }
        
        # Test invalid page sizes
        invalid_page_sizes = [0, -1, 101, 1000]
        
        for invalid_size in invalid_page_sizes:
            event = {
                'queryStringParameters': {'page_size': str(invalid_size)}
            }
            
            response = handle_mytransactions(event, Mock())
            
            # Property: Should return 400 Bad Request for invalid page size
            assert response['statusCode'] == 400, \
                f"Should return 400 for invalid page_size {invalid_size}, got {response['statusCode']}"
            
            body = json.loads(response['body'])
            assert 'error' in body, \
                "Error response should contain 'error' field"
            assert 'Bad Request' in body['error'], \
                "Error should indicate bad request"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
