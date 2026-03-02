"""
Property-Based Test for Credit Cost Calculation
Feature: ai-document-processing
Property 13: Credit Cost Calculation

**Validates: Requirements 22.1**

For any document processing operation, the credit cost should be calculated based on
the idp_rates table using the document's page count and token count, and the calculation
should be deterministic and consistent.
"""

import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
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
    
    from handler import calculate_credit_cost


# Custom strategies for generating test data

@st.composite
def tenant_id(draw):
    """Generate a valid tenant ID"""
    return draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-_'
    )))


@st.composite
def page_count(draw):
    """Generate a valid page count"""
    return draw(st.integers(min_value=1, max_value=1000))


@st.composite
def token_count(draw):
    """Generate a valid token count"""
    return draw(st.integers(min_value=0, max_value=100000))


@st.composite
def rate_amount(draw):
    """Generate a valid rate amount"""
    amount = draw(st.floats(
        min_value=0.0,
        max_value=10.0,
        allow_nan=False,
        allow_infinity=False
    ))
    return round(amount, 4)


# Property Tests

@settings(max_examples=50, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count(),
    base_rate=rate_amount(),
    page_rate=rate_amount(),
    token_rate=rate_amount()
)
def test_cost_calculation_deterministic(tenant, pages, input_tokens, output_tokens, 
                                       base_rate, page_rate, token_rate):
    """
    Property 13.1: Cost Calculation is Deterministic
    
    For any given set of inputs (pages, tokens, rates), calculating the cost
    multiple times should always produce the same result.
    
    **Validates: Requirements 22.1**
    """
    # Create rate items
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'base-rate',
            'tenant': tenant,
            'rate_type': 'base',
            'amount': base_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': page_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': token_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost multiple times
        cost1 = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        cost2 = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        cost3 = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Property: All calculations should produce the same result
        assert cost1 == cost2 == cost3, \
            f"Cost calculation not deterministic: {cost1}, {cost2}, {cost3}"


@settings(max_examples=50, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count(),
    base_rate=rate_amount(),
    page_rate=rate_amount(),
    token_rate=rate_amount()
)
def test_cost_calculation_formula(tenant, pages, input_tokens, output_tokens,
                                 base_rate, page_rate, token_rate):
    """
    Property 13.2: Cost Calculation Formula Correctness
    
    For any document processing operation, the calculated cost should equal:
    base_cost + (page_rate * pages) + (token_rate * total_tokens)
    
    **Validates: Requirements 22.1**
    """
    # Create rate items
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'base-rate',
            'tenant': tenant,
            'rate_type': 'base',
            'amount': base_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': page_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': token_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost
        actual_cost = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Calculate expected cost using formula
        expected_cost = (
            Decimal(str(base_rate)) +
            (Decimal(str(page_rate)) * Decimal(str(pages))) +
            (Decimal(str(token_rate)) * Decimal(str(input_tokens + output_tokens)))
        )
        
        # Property: Actual cost should match formula
        assert actual_cost == expected_cost, \
            f"Cost formula mismatch: expected {expected_cost}, got {actual_cost}"


@settings(max_examples=40, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count(),
    page_rate=rate_amount(),
    token_rate=rate_amount()
)
def test_cost_increases_with_pages(tenant, pages, input_tokens, output_tokens,
                                  page_rate, token_rate):
    """
    Property 13.3: Cost Increases with Page Count
    
    For any document, if we increase the page count while keeping tokens constant,
    the cost should increase (or stay the same if page_rate is 0).
    
    **Validates: Requirements 22.1**
    """
    assume(page_rate > 0)  # Only test when page rate is positive
    assume(pages < 999)  # Leave room to add pages
    
    # Create rate items
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'base-rate',
            'tenant': tenant,
            'rate_type': 'base',
            'amount': 0.0,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': page_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': token_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost with original pages
        cost1 = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Calculate cost with more pages
        cost2 = calculate_credit_cost(pages + 1, input_tokens, output_tokens, tenant)
        
        # Property: Cost should increase with more pages
        assert cost2 > cost1, \
            f"Cost should increase with more pages: {pages} pages = {cost1}, {pages+1} pages = {cost2}"


@settings(max_examples=40, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count(),
    page_rate=rate_amount(),
    token_rate=rate_amount()
)
def test_cost_increases_with_tokens(tenant, pages, input_tokens, output_tokens,
                                   page_rate, token_rate):
    """
    Property 13.4: Cost Increases with Token Count
    
    For any document, if we increase the token count while keeping pages constant,
    the cost should increase (or stay the same if token_rate is 0).
    
    **Validates: Requirements 22.1**
    """
    assume(token_rate > 0)  # Only test when token rate is positive
    assume(input_tokens + output_tokens < 99000)  # Leave room to add tokens
    
    # Create rate items
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'base-rate',
            'tenant': tenant,
            'rate_type': 'base',
            'amount': 0.0,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': page_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': token_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost with original tokens
        cost1 = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Calculate cost with more tokens (add 1000 tokens)
        cost2 = calculate_credit_cost(pages, input_tokens + 1000, output_tokens, tenant)
        
        # Property: Cost should increase with more tokens
        assert cost2 > cost1, \
            f"Cost should increase with more tokens: original = {cost1}, +1000 tokens = {cost2}"


@settings(max_examples=35, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count()
)
def test_cost_with_default_rates(tenant, pages, input_tokens, output_tokens):
    """
    Property 13.5: Cost Calculation with Default Rates
    
    When the rates table query fails or returns no rates, the system should
    use default rates and still calculate a valid cost.
    
    **Validates: Requirements 22.1**
    """
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table to raise an error
        mock_table = Mock()
        from botocore.exceptions import ClientError
        mock_table.scan.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}},
            'Scan'
        )
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost (should use default rates)
        cost = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Property 1: Cost should be non-negative
        assert cost >= 0, \
            f"Cost should be non-negative even with default rates, got {cost}"
        
        # Property 2: Cost should match default formula
        # Default rates: per_page = 0.10, per_token = 0.0001
        expected_cost = (
            (Decimal('0.10') * Decimal(str(pages))) +
            (Decimal('0.0001') * Decimal(str(input_tokens + output_tokens)))
        )
        
        assert cost == expected_cost, \
            f"Cost with default rates mismatch: expected {expected_cost}, got {cost}"


@settings(max_examples=30, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count(),
    base_rate=rate_amount(),
    page_rate=rate_amount(),
    token_rate=rate_amount()
)
def test_cost_is_non_negative(tenant, pages, input_tokens, output_tokens,
                             base_rate, page_rate, token_rate):
    """
    Property 13.6: Cost is Always Non-Negative
    
    For any document processing operation with any valid rates, the calculated
    cost should never be negative.
    
    **Validates: Requirements 22.1**
    """
    # Create rate items
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'base-rate',
            'tenant': tenant,
            'rate_type': 'base',
            'amount': base_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': page_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': token_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost
        cost = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Property: Cost should always be non-negative
        assert cost >= 0, \
            f"Cost should be non-negative, got {cost}"


@settings(max_examples=30, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count(),
    base_rate=rate_amount(),
    page_rate=rate_amount(),
    token_rate=rate_amount()
)
def test_cost_precision(tenant, pages, input_tokens, output_tokens,
                       base_rate, page_rate, token_rate):
    """
    Property 13.7: Cost Calculation Maintains Precision
    
    For any document processing operation, the cost calculation should maintain
    decimal precision without floating-point errors.
    
    **Validates: Requirements 22.1**
    """
    # Create rate items
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'base-rate',
            'tenant': tenant,
            'rate_type': 'base',
            'amount': base_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': page_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': token_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost
        cost = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Property 1: Cost should be a Decimal type
        assert isinstance(cost, Decimal), \
            f"Cost should be Decimal type for precision, got {type(cost)}"
        
        # Property 2: Recalculate manually and verify precision
        expected_cost = (
            Decimal(str(base_rate)) +
            (Decimal(str(page_rate)) * Decimal(str(pages))) +
            (Decimal(str(token_rate)) * Decimal(str(input_tokens + output_tokens)))
        )
        
        # Should match exactly (no floating-point errors)
        assert cost == expected_cost, \
            f"Precision error: expected {expected_cost}, got {cost}"


@settings(max_examples=25, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count(),
    page_rate=rate_amount(),
    token_rate=rate_amount()
)
def test_cost_with_zero_base_rate(tenant, pages, input_tokens, output_tokens,
                                 page_rate, token_rate):
    """
    Property 13.8: Cost Calculation with Zero Base Rate
    
    When base rate is zero, the cost should only depend on pages and tokens.
    
    **Validates: Requirements 22.1**
    """
    # Create rate items with zero base rate
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'base-rate',
            'tenant': tenant,
            'rate_type': 'base',
            'amount': 0.0,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': page_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': token_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost
        cost = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Calculate expected cost (no base rate)
        expected_cost = (
            (Decimal(str(page_rate)) * Decimal(str(pages))) +
            (Decimal(str(token_rate)) * Decimal(str(input_tokens + output_tokens)))
        )
        
        # Property: Cost should match formula without base rate
        assert cost == expected_cost, \
            f"Cost with zero base rate mismatch: expected {expected_cost}, got {cost}"


@settings(max_examples=25, deadline=None)
@given(
    tenant=tenant_id(),
    base_rate=rate_amount()
)
def test_cost_with_zero_pages_and_tokens(tenant, base_rate):
    """
    Property 13.9: Cost with Zero Pages and Tokens
    
    When pages and tokens are both zero, the cost should equal the base rate.
    
    **Validates: Requirements 22.1**
    """
    # Create rate items
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'base-rate',
            'tenant': tenant,
            'rate_type': 'base',
            'amount': base_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': 0.10,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': 0.0001,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost with zero pages and tokens
        cost = calculate_credit_cost(0, 0, 0, tenant)
        
        # Property: Cost should equal base rate
        expected_cost = Decimal(str(base_rate))
        assert cost == expected_cost, \
            f"Cost with zero pages/tokens should equal base rate: expected {expected_cost}, got {cost}"


@settings(max_examples=20, deadline=None)
@given(
    tenant=tenant_id(),
    pages=page_count(),
    input_tokens=token_count(),
    output_tokens=token_count(),
    page_rate=rate_amount(),
    token_rate=rate_amount()
)
def test_cost_with_missing_base_rate(tenant, pages, input_tokens, output_tokens,
                                    page_rate, token_rate):
    """
    Property 13.10: Cost Calculation with Missing Base Rate
    
    When base rate is not present in the rates table, the system should
    default to 0 for base rate and calculate cost correctly.
    
    **Validates: Requirements 22.1**
    """
    # Create rate items without base rate
    now = datetime.utcnow()
    rate_items = [
        {
            'rate_id': 'page-rate',
            'tenant': tenant,
            'rate_type': 'per_page',
            'amount': page_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        },
        {
            'rate_id': 'token-rate',
            'tenant': tenant,
            'rate_type': 'per_token',
            'amount': token_rate,
            'effective_date': (now - timedelta(days=30)).isoformat(),
            'expiry_date': (now + timedelta(days=30)).isoformat()
        }
    ]
    
    with patch('handler.dynamodb') as mock_dynamodb:
        # Mock rates table
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': rate_items
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Calculate cost
        cost = calculate_credit_cost(pages, input_tokens, output_tokens, tenant)
        
        # Calculate expected cost (base rate defaults to 0)
        expected_cost = (
            (Decimal(str(page_rate)) * Decimal(str(pages))) +
            (Decimal(str(token_rate)) * Decimal(str(input_tokens + output_tokens)))
        )
        
        # Property: Cost should match formula with base rate = 0
        assert cost == expected_cost, \
            f"Cost with missing base rate mismatch: expected {expected_cost}, got {cost}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
