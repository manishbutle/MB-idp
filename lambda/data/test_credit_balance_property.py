"""
Property-Based Test for Credit Balance Calculation
Feature: ai-document-processing
Property 11: Credit Balance Calculation

**Validates: Requirements 22.2, 22.4, 22.5, 22.6**

For any user, the available balance should equal the sum of all transaction amounts
in idp_transactions table for that user, where top-ups are positive and processing
costs are negative.
"""

import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from decimal import Decimal
from hypothesis import given, settings, strategies as st
from hypothesis import assume

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
    
    from handler import handle_available_balance, get_user_from_token


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
def transaction_amount(draw, action):
    """Generate a transaction amount based on action type"""
    # Generate amount with 2 decimal places for currency
    amount = draw(st.floats(
        min_value=0.01,
        max_value=10000.0,
        allow_nan=False,
        allow_infinity=False
    ))
    
    # Round to 2 decimal places
    amount = round(amount, 2)
    
    # Utilized transactions are negative, others are positive
    if action == 'Utilized':
        return -abs(amount)
    else:
        return abs(amount)


@st.composite
def transaction_item(draw, user_email, tenant):
    """Generate a transaction item for a specific user and tenant"""
    action = draw(st.sampled_from(['Utilized', 'Top-up', 'Admin Credit']))
    amount = draw(transaction_amount(action))
    
    transaction = {
        'transaction_id': draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': action,
        'amount': amount,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': draw(st.text(min_size=0, max_size=100))
    }
    
    # Add processing_id for Utilized transactions
    if action == 'Utilized':
        transaction['processing_id'] = draw(st.uuids()).hex
        transaction['pages'] = draw(st.integers(min_value=1, max_value=100))
    
    return transaction


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
        self.request_id = 'test-request-id'
    
    def get_remaining_time_in_millis(self):
        return 30000


# Property Tests

@settings(max_examples=30, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    data=st.data()
)
def test_balance_equals_sum_of_transactions(user_email, tenant, data):
    """
    Property 11.1: Balance Equals Sum of Transactions
    
    For any user with a set of transactions, the available balance should equal
    the sum of all transaction amounts.
    
    **Validates: Requirements 22.2, 22.4, 22.5, 22.6**
    """
    # Generate transactions for the user
    num_transactions = data.draw(st.integers(min_value=1, max_value=20))
    transactions = [data.draw(transaction_item(user_email, tenant)) for _ in range(num_transactions)]
    
    # Calculate expected balance
    expected_balance = sum(Decimal(str(t['amount'])) for t in transactions)
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': user_email,
            'tenant': tenant
        }
        
        # Mock DynamoDB transactions query
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'path': '/available_balance',
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': tenant
                }
            }
        }
        
        # Call handler
        response = handle_available_balance(event, MockLambdaContext())
        
        # Verify response
        assert response['statusCode'] == 200, \
            f"Expected status 200, got {response['statusCode']}"
        
        body = json.loads(response['body'])
        actual_balance = Decimal(str(body['available_balance']))
        
        # Property: Balance should equal sum of all transaction amounts
        assert actual_balance == expected_balance, \
            f"Balance mismatch: expected {expected_balance}, got {actual_balance}"


@settings(max_examples=25, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    data=st.data()
)
def test_balance_with_mixed_transactions(user_email, tenant, data):
    """
    Property 11.2: Balance with Mixed Transactions
    
    For any user with both top-ups (positive) and processing costs (negative),
    the balance should correctly reflect the sum of positive and negative amounts.
    
    **Validates: Requirements 22.2, 22.4, 22.5**
    """
    num_topups = data.draw(st.integers(min_value=1, max_value=10))
    num_utilized = data.draw(st.integers(min_value=1, max_value=10))
    
    # Generate top-up transactions (positive amounts)
    topup_transactions = []
    for _ in range(num_topups):
        action = data.draw(st.sampled_from(['Top-up', 'Admin Credit']))
        amount = round(data.draw(st.floats(min_value=0.01, max_value=1000.0)), 2)
        topup_transactions.append({
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': action,
            'amount': abs(amount),  # Positive
            'timestamp': datetime.utcnow().isoformat(),
            'remark': ''
        })
    
    # Generate utilized transactions (negative amounts)
    utilized_transactions = []
    for _ in range(num_utilized):
        amount = round(data.draw(st.floats(min_value=0.01, max_value=500.0)), 2)
        utilized_transactions.append({
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': 'Utilized',
            'amount': -abs(amount),  # Negative
            'timestamp': datetime.utcnow().isoformat(),
            'processing_id': data.draw(st.uuids()).hex,
            'pages': data.draw(st.integers(min_value=1, max_value=50)),
            'remark': ''
        })
    
    all_transactions = topup_transactions + utilized_transactions
    
    # Calculate expected balance
    expected_balance = sum(Decimal(str(t['amount'])) for t in all_transactions)
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': user_email,
            'tenant': tenant
        }
        
        # Mock DynamoDB transactions query
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': all_transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'path': '/available_balance',
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': tenant
                }
            }
        }
        
        # Call handler
        response = handle_available_balance(event, MockLambdaContext())
        
        # Verify response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        actual_balance = Decimal(str(body['available_balance']))
        
        # Property 1: Balance should equal sum of all amounts
        assert actual_balance == expected_balance, \
            f"Balance mismatch: expected {expected_balance}, got {actual_balance}"
        
        # Property 2: Verify sign correctness
        total_topups = sum(Decimal(str(t['amount'])) for t in topup_transactions)
        total_utilized = sum(Decimal(str(t['amount'])) for t in utilized_transactions)
        
        assert total_topups >= 0, \
            f"Top-ups should be positive, got {total_topups}"
        assert total_utilized <= 0, \
            f"Utilized amounts should be negative, got {total_utilized}"


@settings(max_examples=20, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id()
)
def test_balance_with_no_transactions(user_email, tenant):
    """
    Property 11.3: Balance with No Transactions
    
    For any user with no transactions, the available balance should be zero.
    
    **Validates: Requirements 22.6**
    """
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': user_email,
            'tenant': tenant
        }
        
        # Mock DynamoDB transactions query - no transactions
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': []
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'path': '/available_balance',
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': tenant
                }
            }
        }
        
        # Call handler
        response = handle_available_balance(event, MockLambdaContext())
        
        # Verify response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        actual_balance = Decimal(str(body['available_balance']))
        
        # Property: Balance should be zero with no transactions
        assert actual_balance == Decimal('0'), \
            f"Balance should be 0 with no transactions, got {actual_balance}"


@settings(max_examples=25, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    data=st.data()
)
def test_balance_calculation_precision(user_email, tenant, data):
    """
    Property 11.4: Balance Calculation Precision
    
    For any user with transactions involving decimal amounts, the balance
    calculation should maintain precision without floating-point errors.
    
    **Validates: Requirements 22.2, 22.6**
    """
    num_transactions = data.draw(st.integers(min_value=1, max_value=15))
    
    # Generate transactions with precise decimal amounts
    transactions = []
    expected_sum = Decimal('0')
    
    for _ in range(num_transactions):
        action = data.draw(st.sampled_from(['Utilized', 'Top-up', 'Admin Credit']))
        
        # Generate amount with 2 decimal places
        amount = round(data.draw(st.floats(min_value=0.01, max_value=999.99)), 2)
        
        if action == 'Utilized':
            amount = -abs(amount)
        else:
            amount = abs(amount)
        
        transactions.append({
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': action,
            'amount': amount,
            'timestamp': datetime.utcnow().isoformat(),
            'remark': ''
        })
        
        expected_sum += Decimal(str(amount))
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': user_email,
            'tenant': tenant
        }
        
        # Mock DynamoDB transactions query
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'path': '/available_balance',
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': tenant
                }
            }
        }
        
        # Call handler
        response = handle_available_balance(event, MockLambdaContext())
        
        # Verify response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        actual_balance = Decimal(str(body['available_balance']))
        
        # Property: Balance should match expected sum with precision
        # Allow for minimal floating-point conversion tolerance
        difference = abs(actual_balance - expected_sum)
        assert difference < Decimal('0.01'), \
            f"Balance precision error: expected {expected_sum}, got {actual_balance}, diff {difference}"


@settings(max_examples=20, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    initial_topup=st.floats(min_value=100.0, max_value=1000.0),
    data=st.data()
)
def test_balance_decreases_with_processing(user_email, tenant, initial_topup, data):
    """
    Property 11.5: Balance Decreases with Processing
    
    For any user who tops up and then processes documents, the final balance
    should be less than or equal to the initial top-up amount.
    
    **Validates: Requirements 22.2, 22.4, 22.5**
    """
    initial_topup = round(initial_topup, 2)
    num_processing = data.draw(st.integers(min_value=1, max_value=10))
    
    # Create initial top-up transaction
    transactions = [{
        'transaction_id': data.draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': 'Top-up',
        'amount': initial_topup,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': 'Initial top-up'
    }]
    
    # Create processing transactions (negative amounts)
    total_utilized = Decimal('0')
    for _ in range(num_processing):
        cost = round(data.draw(st.floats(min_value=0.01, max_value=50.0)), 2)
        transactions.append({
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': 'Utilized',
            'amount': -abs(cost),
            'timestamp': datetime.utcnow().isoformat(),
            'processing_id': data.draw(st.uuids()).hex,
            'pages': data.draw(st.integers(min_value=1, max_value=20)),
            'remark': ''
        })
        total_utilized += Decimal(str(cost))
    
    expected_balance = Decimal(str(initial_topup)) - total_utilized
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': user_email,
            'tenant': tenant
        }
        
        # Mock DynamoDB transactions query
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'path': '/available_balance',
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': tenant
                }
            }
        }
        
        # Call handler
        response = handle_available_balance(event, MockLambdaContext())
        
        # Verify response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        actual_balance = Decimal(str(body['available_balance']))
        
        # Property 1: Balance should equal initial top-up minus utilized
        difference = abs(actual_balance - expected_balance)
        assert difference < Decimal('0.01'), \
            f"Balance calculation error: expected {expected_balance}, got {actual_balance}"
        
        # Property 2: Final balance should be less than or equal to initial top-up
        assert actual_balance <= Decimal(str(initial_topup)), \
            f"Balance {actual_balance} should not exceed initial top-up {initial_topup}"


@settings(max_examples=20, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    data=st.data()
)
def test_balance_with_admin_credits(user_email, tenant, data):
    """
    Property 11.6: Balance with Admin Credits
    
    For any user receiving admin credits and regular top-ups, the balance
    should correctly sum all positive transactions regardless of source.
    
    **Validates: Requirements 22.4, 22.5, 22.6**
    """
    num_admin_credits = data.draw(st.integers(min_value=1, max_value=5))
    num_topups = data.draw(st.integers(min_value=1, max_value=5))
    
    transactions = []
    expected_balance = Decimal('0')
    
    # Add admin credit transactions
    for _ in range(num_admin_credits):
        amount = round(data.draw(st.floats(min_value=10.0, max_value=500.0)), 2)
        transactions.append({
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': 'Admin Credit',
            'amount': amount,
            'timestamp': datetime.utcnow().isoformat(),
            'remark': 'Admin credit added'
        })
        expected_balance += Decimal(str(amount))
    
    # Add regular top-up transactions
    for _ in range(num_topups):
        amount = round(data.draw(st.floats(min_value=10.0, max_value=500.0)), 2)
        transactions.append({
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': 'Top-up',
            'amount': amount,
            'timestamp': datetime.utcnow().isoformat(),
            'remark': 'User top-up'
        })
        expected_balance += Decimal(str(amount))
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': user_email,
            'tenant': tenant
        }
        
        # Mock DynamoDB transactions query
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'path': '/available_balance',
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': tenant
                }
            }
        }
        
        # Call handler
        response = handle_available_balance(event, MockLambdaContext())
        
        # Verify response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        actual_balance = Decimal(str(body['available_balance']))
        
        # Property: Balance should equal sum of all admin credits and top-ups
        difference = abs(actual_balance - expected_balance)
        assert difference < Decimal('0.01'), \
            f"Balance mismatch: expected {expected_balance}, got {actual_balance}"
        
        # Property: Balance should be positive (only positive transactions)
        assert actual_balance >= 0, \
            f"Balance should be non-negative with only positive transactions, got {actual_balance}"


@settings(max_examples=15, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    transaction_sequence=st.lists(
        st.sampled_from(['topup', 'utilized', 'admin']),
        min_size=3,
        max_size=15
    ),
    data=st.data()
)
def test_balance_with_transaction_sequence(user_email, tenant, transaction_sequence, data):
    """
    Property 11.7: Balance with Transaction Sequence
    
    For any sequence of transactions (top-ups, processing, admin credits),
    the final balance should equal the cumulative sum of all transactions
    in the order they occurred.
    
    **Validates: Requirements 22.2, 22.4, 22.5, 22.6**
    """
    transactions = []
    expected_balance = Decimal('0')
    
    for action_type in transaction_sequence:
        amount = round(data.draw(st.floats(min_value=0.01, max_value=200.0)), 2)
        
        if action_type == 'topup':
            action = 'Top-up'
            amount = abs(amount)
        elif action_type == 'utilized':
            action = 'Utilized'
            amount = -abs(amount)
        else:  # admin
            action = 'Admin Credit'
            amount = abs(amount)
        
        transaction = {
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': action,
            'amount': amount,
            'timestamp': datetime.utcnow().isoformat(),
            'remark': ''
        }
        
        if action == 'Utilized':
            transaction['processing_id'] = data.draw(st.uuids()).hex
            transaction['pages'] = data.draw(st.integers(min_value=1, max_value=20))
        
        transactions.append(transaction)
        expected_balance += Decimal(str(amount))
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock user authentication
        mock_get_user.return_value = {
            'email': user_email,
            'tenant': tenant
        }
        
        # Mock DynamoDB transactions query
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'path': '/available_balance',
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': tenant
                }
            }
        }
        
        # Call handler
        response = handle_available_balance(event, MockLambdaContext())
        
        # Verify response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        actual_balance = Decimal(str(body['available_balance']))
        
        # Property: Balance should equal cumulative sum of all transactions
        difference = abs(actual_balance - expected_balance)
        assert difference < Decimal('0.01'), \
            f"Balance mismatch after {len(transactions)} transactions: expected {expected_balance}, got {actual_balance}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
