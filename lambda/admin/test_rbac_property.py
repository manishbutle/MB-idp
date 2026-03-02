"""
Property-Based Test for Role-Based Access Control
Feature: ai-document-processing
Property 10: Role-Based Access Control

**Validates: Requirements 9.1, 9.2, 9.5, 13.6, 13.7**

For any user attempting to access the Admin tab or call the add_credit API, 
access should be granted if and only if the user has System_User role.
"""

import json
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, settings, strategies as st, assume

# Mock AWS services and logger before importing handler
with patch('boto3.resource'):
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
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    mock_logger.set_context = Mock()
    mock_logger.clear_context = Mock()
    mock_logger_module.create_logger.return_value = mock_logger
    sys.modules['logger_util'] = mock_logger_module
    
    from handler import handle_add_credit, validate_system_user


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
def user_role(draw):
    """Generate a user role"""
    return draw(st.sampled_from([
        'User',
        'System_User',
        'system_user',
        'SYSTEM_USER',
        'SystemUser',
        'Admin',
        'Manager',
        'Guest',
        ''
    ]))


@st.composite
def user_with_role(draw):
    """Generate a user with a specific role"""
    return {
        'email': draw(email_address()),
        'tenant': draw(tenant_id()),
        'role': draw(user_role())
    }


@st.composite
def add_credit_request(draw):
    """Generate an add_credit request"""
    return {
        'admin_user': draw(user_with_role()),
        'target_email': draw(email_address()),
        'amount': float(draw(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('1000.00'), places=2))),
        'remark': draw(st.text(min_size=0, max_size=200))
    }


# Property Tests

@settings(max_examples=40, deadline=None)
@given(
    request=add_credit_request()
)
def test_rbac_system_user_access_granted(request):
    """
    Property 10.1: System_User Access Granted
    
    For any user with System_User role (case-insensitive), access to add_credit
    API should be granted.
    
    **Validates: Requirements 9.1, 9.2, 9.5, 13.6**
    """
    # Force admin user to have System_User role
    admin_user = request['admin_user'].copy()
    admin_user['role'] = 'System_User'
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user, \
         patch('handler.get_user_by_email') as mock_get_target:
        
        # Mock authentication
        mock_get_user.return_value = admin_user
        
        # Mock target user exists
        mock_get_target.return_value = {
            'email': request['target_email'],
            'tenant': 'target-tenant'
        }
        
        # Mock DynamoDB table
        mock_table = Mock()
        mock_table.put_item.return_value = {}
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'body': json.dumps({
                'email': request['target_email'],
                'amount': request['amount'],
                'remark': request['remark']
            })
        }
        
        # Call API
        response = handle_add_credit(event, Mock())
        
        # Property: System_User should be granted access (200 OK)
        assert response['statusCode'] == 200, \
            f"System_User should be granted access, got status {response['statusCode']}"
        
        body = json.loads(response['body'])
        assert 'message' in body, \
            "Response should contain success message"
        assert 'Credit added successfully' in body['message'], \
            "Response should indicate successful credit addition"


@settings(max_examples=40, deadline=None)
@given(
    request=add_credit_request()
)
def test_rbac_non_system_user_access_denied(request):
    """
    Property 10.2: Non-System_User Access Denied
    
    For any user without System_User role, access to add_credit API should
    be denied with 403 Forbidden.
    
    **Validates: Requirements 9.2, 9.5, 13.6, 13.7**
    """
    # Ensure admin user does NOT have System_User role
    admin_user = request['admin_user'].copy()
    assume(admin_user['role'].lower() not in ['system_user', 'system user', 'systemuser'])
    
    with patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock authentication
        mock_get_user.return_value = admin_user
        
        # Create event
        event = {
            'body': json.dumps({
                'email': request['target_email'],
                'amount': request['amount'],
                'remark': request['remark']
            })
        }
        
        # Call API
        response = handle_add_credit(event, Mock())
        
        # Property: Non-System_User should be denied access (403 Forbidden)
        assert response['statusCode'] == 403, \
            f"Non-System_User should be denied access, got status {response['statusCode']}"
        
        body = json.loads(response['body'])
        assert 'error' in body, \
            "Response should contain error field"
        assert 'Forbidden' in body['error'], \
            "Error should indicate forbidden access"
        assert 'System_User role required' in body['message'], \
            "Message should indicate System_User role requirement"


@settings(max_examples=30, deadline=None)
@given(
    request=add_credit_request()
)
def test_rbac_case_insensitive_role_check(request):
    """
    Property 10.3: Case-Insensitive Role Check
    
    For any user with System_User role in any case variation (system_user,
    SYSTEM_USER, SystemUser), access should be granted.
    
    **Validates: Requirements 9.1, 9.2, 13.6**
    """
    # Test different case variations of System_User
    role_variations = ['System_User', 'system_user', 'SYSTEM_USER', 'SystemUser', 'system user']
    
    for role_variant in role_variations:
        admin_user = request['admin_user'].copy()
        admin_user['role'] = role_variant
        
        with patch('handler.dynamodb') as mock_dynamodb, \
             patch('handler.get_user_from_token') as mock_get_user, \
             patch('handler.get_user_by_email') as mock_get_target:
            
            # Mock authentication
            mock_get_user.return_value = admin_user
            
            # Mock target user exists
            mock_get_target.return_value = {
                'email': request['target_email'],
                'tenant': 'target-tenant'
            }
            
            # Mock DynamoDB table
            mock_table = Mock()
            mock_table.put_item.return_value = {}
            mock_dynamodb.Table.return_value = mock_table
            
            # Create event
            event = {
                'body': json.dumps({
                    'email': request['target_email'],
                    'amount': request['amount'],
                    'remark': request['remark']
                })
            }
            
            # Call API
            response = handle_add_credit(event, Mock())
            
            # Property: All case variations should be granted access
            assert response['statusCode'] == 200, \
                f"Role variant '{role_variant}' should be granted access, got status {response['statusCode']}"


@settings(max_examples=20, deadline=None)
@given(
    request=add_credit_request()
)
def test_rbac_unauthenticated_access_denied(request):
    """
    Property 10.4: Unauthenticated Access Denied
    
    For any request without valid authentication, access should be denied
    with 401 Unauthorized, regardless of role.
    
    **Validates: Requirements 9.5, 13.6**
    """
    with patch('handler.get_user_from_token') as mock_get_user:
        
        # Mock authentication failure
        mock_get_user.return_value = None
        
        # Create event
        event = {
            'body': json.dumps({
                'email': request['target_email'],
                'amount': request['amount'],
                'remark': request['remark']
            })
        }
        
        # Call API
        response = handle_add_credit(event, Mock())
        
        # Property: Unauthenticated requests should be denied (401 Unauthorized)
        assert response['statusCode'] == 401, \
            f"Unauthenticated request should be denied, got status {response['statusCode']}"
        
        body = json.loads(response['body'])
        assert 'error' in body, \
            "Response should contain error field"
        assert 'Unauthorized' in body['error'], \
            "Error should indicate unauthorized access"


@settings(max_examples=20, deadline=None)
@given(
    user=user_with_role()
)
def test_rbac_validate_system_user_function(user):
    """
    Property 10.5: Validate System User Function Correctness
    
    For any user, the validate_system_user function should return True if and
    only if the user's role is a case-insensitive variant of System_User.
    
    **Validates: Requirements 9.1, 9.2, 13.6**
    """
    result = validate_system_user(user)
    
    # Property: Function should return True only for System_User variants
    is_system_user_role = user.get('role', '').lower() in ['system_user', 'system user', 'systemuser']
    
    assert result == is_system_user_role, \
        f"validate_system_user should return {is_system_user_role} for role '{user.get('role')}', got {result}"


@settings(max_examples=15, deadline=None)
@given(
    request=add_credit_request()
)
def test_rbac_admin_metadata_recorded(request):
    """
    Property 10.6: Admin Metadata Recorded
    
    For any successful admin credit addition, the transaction should record
    the admin user's email and tenant as metadata.
    
    **Validates: Requirements 9.3, 9.4, 9.6, 22.8**
    """
    # Force admin user to have System_User role
    admin_user = request['admin_user'].copy()
    admin_user['role'] = 'System_User'
    
    captured_transaction = {}
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.get_user_from_token') as mock_get_user, \
         patch('handler.get_user_by_email') as mock_get_target:
        
        # Mock authentication
        mock_get_user.return_value = admin_user
        
        # Mock target user exists
        mock_get_target.return_value = {
            'email': request['target_email'],
            'tenant': 'target-tenant'
        }
        
        # Mock DynamoDB table and capture transaction
        mock_table = Mock()
        
        def capture_put_item(Item):
            captured_transaction.update(Item)
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        mock_dynamodb.Table.return_value = mock_table
        
        # Create event
        event = {
            'body': json.dumps({
                'email': request['target_email'],
                'amount': request['amount'],
                'remark': request['remark']
            })
        }
        
        # Call API
        response = handle_add_credit(event, Mock())
        
        # Property 1: Transaction should be created
        assert response['statusCode'] == 200
        assert len(captured_transaction) > 0, \
            "Transaction should be created"
        
        # Property 2: Transaction should contain admin metadata
        assert 'admin_email' in captured_transaction, \
            "Transaction should contain admin_email"
        assert captured_transaction['admin_email'] == admin_user['email'], \
            f"Admin email should be {admin_user['email']}, got {captured_transaction.get('admin_email')}"
        
        assert 'admin_tenant' in captured_transaction, \
            "Transaction should contain admin_tenant"
        assert captured_transaction['admin_tenant'] == admin_user['tenant'], \
            f"Admin tenant should be {admin_user['tenant']}, got {captured_transaction.get('admin_tenant')}"
        
        # Property 3: Transaction action should be 'Admin Credit'
        assert captured_transaction['action'] == 'Admin Credit', \
            f"Transaction action should be 'Admin Credit', got {captured_transaction.get('action')}"


@settings(max_examples=15, deadline=None)
@given(
    request=add_credit_request()
)
def test_rbac_role_check_before_validation(request):
    """
    Property 10.7: Role Check Before Validation
    
    For any add_credit request, the role check should occur before any
    validation of the request parameters (email, amount).
    
    **Validates: Requirements 9.5, 13.6**
    """
    # Use a non-System_User role
    admin_user = request['admin_user'].copy()
    admin_user['role'] = 'User'  # Not System_User
    
    with patch('handler.get_user_from_token') as mock_get_user, \
         patch('handler.get_user_by_email') as mock_get_target:
        
        # Mock authentication
        mock_get_user.return_value = admin_user
        
        # Create event with INVALID parameters (should not matter)
        event = {
            'body': json.dumps({
                'email': '',  # Invalid: empty email
                'amount': -100,  # Invalid: negative amount
                'remark': request['remark']
            })
        }
        
        # Call API
        response = handle_add_credit(event, Mock())
        
        # Property: Should return 403 Forbidden (role check) not 400 Bad Request (validation)
        assert response['statusCode'] == 403, \
            f"Role check should occur before validation, expected 403, got {response['statusCode']}"
        
        # Property: get_user_by_email should NOT be called (role check failed first)
        mock_get_target.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
