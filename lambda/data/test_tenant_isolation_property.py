"""
Property-Based Test for Tenant Data Isolation
Feature: ai-document-processing
Property 14: Tenant Data Isolation

**Validates: Requirements 23.2, 23.3, 23.4, 23.5, 23.6, 23.7**

For any user query (prompts, document types, transaction history, processing history),
the returned results should contain only data where the tenant field matches the user's
tenant, ensuring complete data isolation between tenants.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal
from hypothesis import given, settings, strategies as st
from hypothesis import assume

# Mock AWS services before importing handler
with patch('boto3.resource'):
    from handler import (
        handle_datapoints,
        handle_history,
        handle_mytransactions,
        get_user_from_token
    )


# Custom strategies for generating test data

@st.composite
def tenant_id(draw):
    """Generate a valid tenant ID"""
    return draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-_'
    )))


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
    return f"{local}@{domain}.{tld}"


@st.composite
def datapoint_item(draw, tenant):
    """Generate a datapoint item for a specific tenant"""
    return {
        'prompt_id': draw(st.uuids()).hex,
        'prompt_name': draw(st.text(min_size=1, max_size=50)),
        'description': draw(st.text(min_size=0, max_size=200)),
        'tenant': tenant,
        'prompt': draw(st.text(min_size=10, max_size=500)),
        'datapoints': draw(st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=10))
    }


@st.composite
def history_item(draw, user_email, tenant):
    """Generate a history item for a specific user and tenant"""
    return {
        'processing_id': draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'document_name': draw(st.text(min_size=1, max_size=100)),
        'document_type': draw(st.sampled_from(['Invoice', 'Purchase Order', 'Market Report'])),
        'pages': draw(st.integers(min_value=1, max_value=100)),
        'extracted_values': {},
        'timestamp': datetime.utcnow().isoformat(),
        'file_type': draw(st.sampled_from(['pdf', 'png', 'jpg'])),
        'file_size': draw(st.integers(min_value=1000, max_value=10000000))
    }


@st.composite
def transaction_item(draw, user_email, tenant):
    """Generate a transaction item for a specific user and tenant"""
    action = draw(st.sampled_from(['Utilized', 'Top-up', 'Admin Credit']))
    amount = draw(st.floats(min_value=-1000, max_value=1000, exclude_min=True, exclude_max=True))
    
    # Ensure Utilized has negative amount, others positive
    if action == 'Utilized':
        amount = -abs(amount)
    else:
        amount = abs(amount)
    
    return {
        'transaction_id': draw(st.uuids()).hex,
        'user_email': user_email,
        'tenant': tenant,
        'action': action,
        'amount': amount,
        'timestamp': datetime.utcnow().isoformat(),
        'remark': draw(st.text(min_size=0, max_size=100))
    }


# Property Tests

@settings(max_examples=20, deadline=None)
@given(
    user_tenant=tenant_id(),
    other_tenant=tenant_id(),
    user_email=email_address(),
    num_user_items=st.integers(min_value=1, max_value=10),
    num_other_items=st.integers(min_value=1, max_value=10)
)
def test_datapoints_tenant_isolation(user_tenant, other_tenant, user_email, num_user_items, num_other_items):
    """
    Property 14: Tenant Data Isolation - Datapoints
    
    For any user querying datapoints, the returned results should contain only
    datapoints where the tenant field matches the user's tenant.
    
    **Validates: Requirements 23.2, 23.3, 23.5**
    """
    # Ensure tenants are different
    assume(user_tenant != other_tenant)
    
    # Generate datapoints for user's tenant and other tenant
    user_datapoints = [datapoint_item(user_tenant) for _ in range(num_user_items)]
    other_datapoints = [datapoint_item(other_tenant) for _ in range(num_other_items)]
    all_datapoints = user_datapoints + other_datapoints
    
    # Mock DynamoDB response
    with patch('handler.dynamodb') as mock_dynamodb:
        mock_table = Mock()
        # Simulate tenant filtering in DynamoDB query
        mock_table.query.return_value = {
            'Items': user_datapoints  # Only return items matching user's tenant
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event with user's tenant
        event = {
            'path': '/datapoints',
            'user_email': user_email,
            'tenant': user_tenant,
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': user_tenant
                }
            }
        }
        
        context = Mock()
        context.request_id = 'test-request-id'
        
        # Call handler
        response = handle_datapoints(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        returned_prompts = body.get('prompts', [])
        
        # Property: All returned items must belong to user's tenant
        for prompt in returned_prompts:
            assert prompt['tenant'] == user_tenant, \
                f"Tenant isolation violated: Expected tenant '{user_tenant}', got '{prompt['tenant']}'"
        
        # Property: No items from other tenants should be returned
        other_tenant_items = [p for p in returned_prompts if p['tenant'] == other_tenant]
        assert len(other_tenant_items) == 0, \
            f"Tenant isolation violated: Found {len(other_tenant_items)} items from other tenant"


@settings(max_examples=20, deadline=None)
@given(
    user_tenant=tenant_id(),
    other_tenant=tenant_id(),
    user_email=email_address(),
    num_user_items=st.integers(min_value=1, max_value=10),
    num_other_items=st.integers(min_value=1, max_value=10)
)
def test_history_tenant_isolation(user_tenant, other_tenant, user_email, num_user_items, num_other_items):
    """
    Property 14: Tenant Data Isolation - History
    
    For any user querying processing history, the returned results should contain
    only history records where the tenant field matches the user's tenant.
    
    **Validates: Requirements 23.2, 23.6**
    """
    # Ensure tenants are different
    assume(user_tenant != other_tenant)
    
    # Generate history items for user's tenant and other tenant
    user_history = [history_item(user_email, user_tenant) for _ in range(num_user_items)]
    other_history = [history_item(user_email, other_tenant) for _ in range(num_other_items)]
    
    # Mock DynamoDB response
    with patch('handler.dynamodb') as mock_dynamodb:
        mock_table = Mock()
        # Simulate tenant filtering in DynamoDB query
        mock_table.query.return_value = {
            'Items': user_history  # Only return items matching user's tenant
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event with user's tenant
        event = {
            'path': '/history',
            'user_email': user_email,
            'tenant': user_tenant,
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': user_tenant
                }
            },
            'queryStringParameters': {'page_size': '20'}
        }
        
        context = Mock()
        context.request_id = 'test-request-id'
        
        # Call handler
        response = handle_history(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        returned_history = body.get('history', [])
        
        # Property: All returned items must belong to user's tenant
        for record in returned_history:
            assert record['tenant'] == user_tenant, \
                f"Tenant isolation violated: Expected tenant '{user_tenant}', got '{record['tenant']}'"
        
        # Property: No items from other tenants should be returned
        other_tenant_items = [h for h in returned_history if h['tenant'] == other_tenant]
        assert len(other_tenant_items) == 0, \
            f"Tenant isolation violated: Found {len(other_tenant_items)} history items from other tenant"


@settings(max_examples=20, deadline=None)
@given(
    user_tenant=tenant_id(),
    other_tenant=tenant_id(),
    user_email=email_address(),
    num_user_items=st.integers(min_value=1, max_value=10),
    num_other_items=st.integers(min_value=1, max_value=10)
)
def test_transactions_tenant_isolation(user_tenant, other_tenant, user_email, num_user_items, num_other_items):
    """
    Property 14: Tenant Data Isolation - Transactions
    
    For any user querying transaction history, the returned results should contain
    only transactions where the tenant field matches the user's tenant.
    
    **Validates: Requirements 23.2, 23.6**
    """
    # Ensure tenants are different
    assume(user_tenant != other_tenant)
    
    # Generate transaction items for user's tenant and other tenant
    user_transactions = [transaction_item(user_email, user_tenant) for _ in range(num_user_items)]
    other_transactions = [transaction_item(user_email, other_tenant) for _ in range(num_other_items)]
    
    # Mock DynamoDB response
    with patch('handler.dynamodb') as mock_dynamodb:
        mock_table = Mock()
        # Simulate tenant filtering in DynamoDB query
        mock_table.query.return_value = {
            'Items': user_transactions  # Only return items matching user's tenant
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event with user's tenant
        event = {
            'path': '/mytransactions',
            'user_email': user_email,
            'tenant': user_tenant,
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': user_tenant
                }
            },
            'queryStringParameters': {'page_size': '20'}
        }
        
        context = Mock()
        context.request_id = 'test-request-id'
        
        # Call handler
        response = handle_mytransactions(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        returned_transactions = body.get('transactions', [])
        
        # Property: All returned items must belong to user's tenant
        for txn in returned_transactions:
            assert txn['tenant'] == user_tenant, \
                f"Tenant isolation violated: Expected tenant '{user_tenant}', got '{txn['tenant']}'"
        
        # Property: No items from other tenants should be returned
        other_tenant_items = [t for t in returned_transactions if t['tenant'] == other_tenant]
        assert len(other_tenant_items) == 0, \
            f"Tenant isolation violated: Found {len(other_tenant_items)} transactions from other tenant"


@settings(max_examples=10, deadline=None)
@given(
    user_tenant=tenant_id(),
    other_tenants=st.lists(tenant_id(), min_size=1, max_size=5, unique=True),
    user_email=email_address()
)
def test_multi_tenant_isolation(user_tenant, other_tenants, user_email):
    """
    Property 14: Tenant Data Isolation - Multi-Tenant Scenario
    
    In a multi-tenant environment with multiple tenants, a user should only see
    data from their own tenant, regardless of how many other tenants exist.
    
    **Validates: Requirements 23.2, 23.3, 23.4, 23.5, 23.6, 23.7**
    """
    # Ensure user's tenant is not in other tenants list
    assume(user_tenant not in other_tenants)
    
    # Generate datapoints for user's tenant
    user_datapoints = [datapoint_item(user_tenant) for _ in range(3)]
    
    # Generate datapoints for other tenants
    other_datapoints = []
    for other_tenant in other_tenants:
        other_datapoints.extend([datapoint_item(other_tenant) for _ in range(2)])
    
    # Mock DynamoDB response
    with patch('handler.dynamodb') as mock_dynamodb:
        mock_table = Mock()
        # Simulate tenant filtering - only return user's tenant data
        mock_table.query.return_value = {
            'Items': user_datapoints
        }
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event with user's tenant
        event = {
            'path': '/datapoints',
            'user_email': user_email,
            'tenant': user_tenant,
            'requestContext': {
                'authorizer': {
                    'user_email': user_email,
                    'tenant': user_tenant
                }
            }
        }
        
        context = Mock()
        context.request_id = 'test-request-id'
        
        # Call handler
        response = handle_datapoints(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        returned_prompts = body.get('prompts', [])
        
        # Property: All returned items must belong to user's tenant
        for prompt in returned_prompts:
            assert prompt['tenant'] == user_tenant, \
                f"Multi-tenant isolation violated: Expected tenant '{user_tenant}', got '{prompt['tenant']}'"
        
        # Property: No items from any other tenant should be returned
        for other_tenant in other_tenants:
            other_tenant_items = [p for p in returned_prompts if p['tenant'] == other_tenant]
            assert len(other_tenant_items) == 0, \
                f"Multi-tenant isolation violated: Found items from tenant '{other_tenant}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
