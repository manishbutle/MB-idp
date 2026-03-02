"""
Property-Based Test for Insufficient Balance Rejection
Feature: ai-document-processing
Property 12: Insufficient Balance Rejection

**Validates: Requirements 22.3**

For any document processing request where the user's available balance is less than
the calculated cost, the system should reject the request with an insufficient balance
error before processing begins.
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
    mock_logger.log_execution_start = Mock()
    mock_logger.log_processing_stage = Mock()
    mock_logger.log_api_call = Mock()
    mock_logger.log_database_operation = Mock()
    mock_logger.set_context = Mock()
    mock_logger_module.create_logger.return_value = mock_logger
    sys.modules['logger_util'] = mock_logger_module
    
    from handler import deduct_credit, get_user_balance


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
def processing_cost(draw):
    """Generate a processing cost"""
    cost = draw(st.floats(
        min_value=0.01,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False
    ))
    return round(cost, 2)


@st.composite
def transaction_item(draw, user_email, tenant, action):
    """Generate a transaction item"""
    if action == 'Utilized':
        amount = -abs(draw(st.floats(min_value=0.01, max_value=500.0)))
    else:
        amount = abs(draw(st.floats(min_value=0.01, max_value=1000.0)))
    
    amount = round(amount, 2)
    
    transaction = {
        'transaction_id': draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': action,
        'amount': amount,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': draw(st.text(min_size=0, max_size=100))
    }
    
    if action == 'Utilized':
        transaction['processing_id'] = draw(st.uuids()).hex
        transaction['pages'] = draw(st.integers(min_value=1, max_value=100))
    
    return transaction


# Property Tests

@settings(max_examples=50, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    current_balance=st.floats(min_value=0.0, max_value=100.0),
    required_cost=st.floats(min_value=0.01, max_value=1000.0),
    data=st.data()
)
def test_insufficient_balance_rejection(user_email, tenant, current_balance, required_cost, data):
    """
    Property 12.1: Insufficient Balance Rejection
    
    For any document processing request where the user's available balance is less
    than the calculated cost, the system should reject the request with an
    insufficient balance error.
    
    **Validates: Requirements 22.3**
    """
    # Ensure balance is insufficient
    current_balance = round(current_balance, 2)
    required_cost = round(required_cost, 2)
    assume(Decimal(str(current_balance)) < Decimal(str(required_cost)))
    
    # Generate transactions that sum to current_balance
    transactions = []
    remaining_balance = Decimal(str(current_balance))
    
    # Create a few top-up transactions that sum to current_balance
    num_topups = data.draw(st.integers(min_value=1, max_value=5))
    for i in range(num_topups):
        if i == num_topups - 1:
            # Last transaction gets the remaining balance
            amount = float(remaining_balance)
        else:
            # Random portion of remaining balance
            max_amount = float(remaining_balance) * 0.8
            amount = round(data.draw(st.floats(min_value=0.01, max_value=max(0.01, max_amount))), 2)
            remaining_balance -= Decimal(str(amount))
        
        transactions.append({
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': 'Top-up',
            'amount': amount,
            'timestamp': datetime.utcnow().isoformat(),
            'remark': 'Test top-up'
        })
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock transactions table
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Attempt to deduct credit
        processing_id = data.draw(st.uuids()).hex
        pages = data.draw(st.integers(min_value=1, max_value=50))
        
        # Property: Should raise exception for insufficient balance
        with pytest.raises(Exception) as exc_info:
            deduct_credit(
                user_email=user_email,
                tenant=tenant,
                cost=Decimal(str(required_cost)),
                processing_id=processing_id,
                pages=pages
            )
        
        # Property 1: Exception message should mention insufficient balance
        assert 'Insufficient balance' in str(exc_info.value), \
            f"Exception should mention 'Insufficient balance', got: {str(exc_info.value)}"
        
        # Property 2: Exception should include required and available amounts
        error_message = str(exc_info.value)
        assert str(required_cost) in error_message or f"{required_cost:.2f}" in error_message, \
            f"Exception should include required cost {required_cost}"
        assert str(current_balance) in error_message or f"{current_balance:.2f}" in error_message, \
            f"Exception should include available balance {current_balance}"
        
        # Property 3: No transaction should be created (verify put_item was not called)
        if hasattr(mock_table, 'put_item'):
            mock_table.put_item.assert_not_called()


@settings(max_examples=40, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    data=st.data()
)
def test_zero_balance_rejection(user_email, tenant, data):
    """
    Property 12.2: Zero Balance Rejection
    
    For any user with zero balance, any processing request with non-zero cost
    should be rejected with insufficient balance error.
    
    **Validates: Requirements 22.3**
    """
    required_cost = round(data.draw(st.floats(min_value=0.01, max_value=100.0)), 2)
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock transactions table with no transactions (zero balance)
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': []
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Attempt to deduct credit
        processing_id = data.draw(st.uuids()).hex
        pages = data.draw(st.integers(min_value=1, max_value=50))
        
        # Property: Should raise exception for zero balance
        with pytest.raises(Exception) as exc_info:
            deduct_credit(
                user_email=user_email,
                tenant=tenant,
                cost=Decimal(str(required_cost)),
                processing_id=processing_id,
                pages=pages
            )
        
        # Property: Exception should mention insufficient balance
        assert 'Insufficient balance' in str(exc_info.value), \
            f"Exception should mention 'Insufficient balance' for zero balance"


@settings(max_examples=40, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    balance=st.floats(min_value=0.01, max_value=100.0),
    cost_multiplier=st.floats(min_value=1.01, max_value=10.0),
    data=st.data()
)
def test_rejection_when_cost_exceeds_balance(user_email, tenant, balance, cost_multiplier, data):
    """
    Property 12.3: Rejection When Cost Exceeds Balance
    
    For any user balance and any cost that exceeds that balance (cost > balance),
    the processing request should be rejected.
    
    **Validates: Requirements 22.3**
    """
    balance = round(balance, 2)
    required_cost = round(balance * cost_multiplier, 2)
    
    # Ensure cost is definitely greater than balance
    assume(Decimal(str(required_cost)) > Decimal(str(balance)))
    
    # Create transactions that sum to balance
    transactions = [{
        'transaction_id': data.draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': 'Top-up',
        'amount': balance,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': 'Initial balance'
    }]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock transactions table
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Attempt to deduct credit
        processing_id = data.draw(st.uuids()).hex
        pages = data.draw(st.integers(min_value=1, max_value=50))
        
        # Property: Should raise exception
        with pytest.raises(Exception) as exc_info:
            deduct_credit(
                user_email=user_email,
                tenant=tenant,
                cost=Decimal(str(required_cost)),
                processing_id=processing_id,
                pages=pages
            )
        
        # Property: Exception should mention insufficient balance
        assert 'Insufficient balance' in str(exc_info.value)


@settings(max_examples=35, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    initial_balance=st.floats(min_value=10.0, max_value=100.0),
    data=st.data()
)
def test_rejection_after_multiple_deductions(user_email, tenant, initial_balance, data):
    """
    Property 12.4: Rejection After Multiple Deductions
    
    For any user who has made multiple processing requests, when the cumulative
    cost exceeds the initial balance, subsequent requests should be rejected.
    
    **Validates: Requirements 22.3**
    """
    initial_balance = round(initial_balance, 2)
    
    # Generate multiple processing costs that together exceed initial balance
    num_successful = data.draw(st.integers(min_value=1, max_value=5))
    successful_costs = []
    total_utilized = Decimal('0')
    
    for _ in range(num_successful):
        # Each cost is a fraction of remaining balance
        remaining = Decimal(str(initial_balance)) - total_utilized
        if remaining <= Decimal('0.01'):
            break
        max_cost = float(remaining) * 0.8
        cost = round(data.draw(st.floats(min_value=0.01, max_value=max(0.01, max_cost))), 2)
        successful_costs.append(cost)
        total_utilized += Decimal(str(cost))
    
    # Final cost that should fail (exceeds remaining balance)
    remaining_balance = Decimal(str(initial_balance)) - total_utilized
    final_cost = round(float(remaining_balance) + data.draw(st.floats(min_value=0.01, max_value=10.0)), 2)
    
    # Ensure final cost exceeds remaining balance
    assume(Decimal(str(final_cost)) > remaining_balance)
    
    # Create transaction history
    transactions = [{
        'transaction_id': data.draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': 'Top-up',
        'amount': initial_balance,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': 'Initial top-up'
    }]
    
    # Add utilized transactions
    for cost in successful_costs:
        transactions.append({
            'transaction_id': data.draw(st.uuids()).hex,
            'user_email': user_email,
            'tenant': tenant,
            'action': 'Utilized',
            'amount': -cost,
            'timestamp': datetime.utcnow().isoformat(),
            'processing_id': data.draw(st.uuids()).hex,
            'pages': data.draw(st.integers(min_value=1, max_value=20)),
            'remark': 'Processing'
        })
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock transactions table
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Attempt final deduction that should fail
        processing_id = data.draw(st.uuids()).hex
        pages = data.draw(st.integers(min_value=1, max_value=50))
        
        # Property: Should raise exception for insufficient balance
        with pytest.raises(Exception) as exc_info:
            deduct_credit(
                user_email=user_email,
                tenant=tenant,
                cost=Decimal(str(final_cost)),
                processing_id=processing_id,
                pages=pages
            )
        
        # Property: Exception should mention insufficient balance
        assert 'Insufficient balance' in str(exc_info.value)


@settings(max_examples=30, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    balance=st.floats(min_value=0.01, max_value=50.0),
    cost_difference=st.floats(min_value=0.01, max_value=1.0),
    data=st.data()
)
def test_rejection_with_small_deficit(user_email, tenant, balance, cost_difference, data):
    """
    Property 12.5: Rejection with Small Deficit
    
    For any user balance, even if the cost exceeds the balance by a very small
    amount (e.g., $0.01), the request should still be rejected. No rounding
    tolerance should allow insufficient balance.
    
    **Validates: Requirements 22.3**
    """
    balance = round(balance, 2)
    cost_difference = round(cost_difference, 2)
    required_cost = balance + cost_difference
    
    # Ensure cost is greater than balance (even by small amount)
    assume(Decimal(str(required_cost)) > Decimal(str(balance)))
    
    # Create transaction with exact balance
    transactions = [{
        'transaction_id': data.draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': 'Top-up',
        'amount': balance,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': 'Balance'
    }]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock transactions table
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Attempt to deduct credit
        processing_id = data.draw(st.uuids()).hex
        pages = data.draw(st.integers(min_value=1, max_value=50))
        
        # Property: Should raise exception even for small deficit
        with pytest.raises(Exception) as exc_info:
            deduct_credit(
                user_email=user_email,
                tenant=tenant,
                cost=Decimal(str(required_cost)),
                processing_id=processing_id,
                pages=pages
            )
        
        # Property: Exception should mention insufficient balance
        assert 'Insufficient balance' in str(exc_info.value), \
            f"Should reject even with small deficit of {cost_difference}"


@settings(max_examples=30, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    balance=st.floats(min_value=1.0, max_value=100.0),
    data=st.data()
)
def test_rejection_prevents_negative_balance(user_email, tenant, balance, data):
    """
    Property 12.6: Rejection Prevents Negative Balance
    
    For any user, the insufficient balance check should prevent the balance
    from ever becoming negative. This ensures financial integrity.
    
    **Validates: Requirements 22.3**
    """
    balance = round(balance, 2)
    
    # Generate cost that would result in negative balance
    excess_amount = round(data.draw(st.floats(min_value=0.01, max_value=50.0)), 2)
    required_cost = balance + excess_amount
    
    # Create transaction with balance
    transactions = [{
        'transaction_id': data.draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': 'Top-up',
        'amount': balance,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': 'Balance'
    }]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock transactions table
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Attempt to deduct credit
        processing_id = data.draw(st.uuids()).hex
        pages = data.draw(st.integers(min_value=1, max_value=50))
        
        # Property: Should raise exception to prevent negative balance
        with pytest.raises(Exception) as exc_info:
            deduct_credit(
                user_email=user_email,
                tenant=tenant,
                cost=Decimal(str(required_cost)),
                processing_id=processing_id,
                pages=pages
            )
        
        # Property 1: Exception should mention insufficient balance
        assert 'Insufficient balance' in str(exc_info.value)
        
        # Property 2: Verify balance calculation would have been negative
        would_be_balance = Decimal(str(balance)) - Decimal(str(required_cost))
        assert would_be_balance < 0, \
            f"Test setup error: balance {balance} - cost {required_cost} should be negative"


@settings(max_examples=25, deadline=None)
@given(
    user_email=email_address(),
    tenant=tenant_id(),
    balance=st.floats(min_value=0.01, max_value=100.0),
    data=st.data()
)
def test_exact_balance_match_succeeds(user_email, tenant, balance, data):
    """
    Property 12.7: Exact Balance Match Succeeds (Boundary Test)
    
    For any user whose balance exactly matches the required cost, the request
    should succeed (not be rejected). This tests the boundary condition.
    
    **Validates: Requirements 22.3**
    """
    balance = round(balance, 2)
    required_cost = balance  # Exact match
    
    # Create transaction with exact balance
    transactions = [{
        'transaction_id': data.draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': 'Top-up',
        'amount': balance,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': 'Balance'
    }]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock transactions table
        mock_table = Mock()
        mock_table.query.return_value = {
            'Items': transactions
        }
        mock_table.put_item.return_value = {}
        mock_dynamodb.Table.return_value = mock_table
        
        # Attempt to deduct credit
        processing_id = data.draw(st.uuids()).hex
        pages = data.draw(st.integers(min_value=1, max_value=50))
        
        # Property: Should succeed when balance exactly matches cost
        result = deduct_credit(
            user_email=user_email,
            tenant=tenant,
            cost=Decimal(str(required_cost)),
            processing_id=processing_id,
            pages=pages
        )
        
        # Property 1: Should return transaction details
        assert 'transaction_id' in result, \
            "Should return transaction_id on success"
        assert 'new_balance' in result, \
            "Should return new_balance on success"
        
        # Property 2: New balance should be zero
        assert result['new_balance'] == 0.0, \
            f"New balance should be 0.0 when cost equals balance, got {result['new_balance']}"
        
        # Property 3: Transaction should be created
        mock_table.put_item.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
