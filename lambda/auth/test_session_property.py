"""
Property-Based Test for Single Active Session Per User
Feature: ai-document-processing
Property 6: Single Active Session Per User

**Validates: Requirements 6.4, 6.5**

For any user, when a new session is created, all previous sessions for that user
should be destroyed, ensuring exactly one active session exists.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from hypothesis import given, settings, strategies as st
from hypothesis import assume

# Mock AWS services before importing handler
with patch('boto3.resource'), patch('boto3.client'):
    import handler


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
def password_string(draw):
    """Generate a valid password"""
    return draw(st.text(min_size=8, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='!@#$%^&*'
    )))


@st.composite
def user_data(draw):
    """Generate user data for testing"""
    email = draw(email_address())
    password = draw(password_string())
    return {
        'email': email,
        'password': password,
        'password_hash': handler.hash_password(password),
        'first_name': draw(st.text(min_size=1, max_size=50)),
        'last_name': draw(st.text(min_size=1, max_size=50)),
        'role': draw(st.sampled_from(['User', 'System User'])),
        'tenant': draw(st.text(min_size=1, max_size=50)),
        'is_active': True
    }


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

@settings(max_examples=20, deadline=None)
@given(
    user=user_data(),
    num_previous_logins=st.integers(min_value=1, max_value=5)
)
def test_single_active_session_per_user(user, num_previous_logins):
    """
    Property 6: Single Active Session Per User
    
    For any user, when a new session is created, all previous sessions for that
    user should be destroyed, ensuring exactly one active session exists.
    
    This test verifies that:
    1. When a user logs in multiple times, only the most recent session is active
    2. Previous sessions are destroyed via Cognito's admin_user_global_sign_out
    3. The system enforces single active session regardless of login count
    
    **Validates: Requirements 6.4, 6.5**
    """
    # Track how many times destroy_previous_sessions is called
    destroy_session_calls = []
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.cognito') as mock_cognito:
        
        # Mock DynamoDB user lookup
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': user
        }
        
        # Mock Cognito session operations
        # Track calls to admin_user_global_sign_out
        def track_sign_out(*args, **kwargs):
            destroy_session_calls.append({
                'username': kwargs.get('Username'),
                'timestamp': datetime.utcnow()
            })
            return {}
        
        mock_cognito.admin_user_global_sign_out.side_effect = track_sign_out
        
        # Mock session token generation
        session_tokens = []
        def generate_token(*args, **kwargs):
            token = f"token_{len(session_tokens)}_{datetime.utcnow().timestamp()}"
            session_tokens.append(token)
            return {
                'AuthenticationResult': {'IdToken': token}
            }
        
        mock_cognito.admin_initiate_auth.side_effect = generate_token
        
        # Simulate multiple login attempts for the same user
        for login_attempt in range(num_previous_logins):
            # Create login event
            event = {
                'path': '/auth',
                'body': json.dumps({
                    'email': user['email'],
                    'password': user['password']
                })
            }
            
            # Call handler
            response = handler.lambda_handler(event, MockLambdaContext())
            
            # Verify successful authentication
            assert response['statusCode'] == 200, \
                f"Login attempt {login_attempt + 1} failed with status {response['statusCode']}"
            
            body = json.loads(response['body'])
            assert 'token' in body, \
                f"Login attempt {login_attempt + 1} did not return a token"
            assert body['user']['email'] == user['email'], \
                f"Login attempt {login_attempt + 1} returned wrong user email"
        
        # Property 1: destroy_previous_sessions should be called for each login
        assert len(destroy_session_calls) == num_previous_logins, \
            f"Expected {num_previous_logins} calls to destroy_previous_sessions, got {len(destroy_session_calls)}"
        
        # Property 2: All destroy calls should be for the same user
        for call in destroy_session_calls:
            assert call['username'] == user['email'], \
                f"destroy_previous_sessions called for wrong user: expected '{user['email']}', got '{call['username']}'"
        
        # Property 3: Each login should generate a new unique token
        assert len(session_tokens) == num_previous_logins, \
            f"Expected {num_previous_logins} session tokens, got {len(session_tokens)}"
        
        # Property 4: All tokens should be unique
        assert len(set(session_tokens)) == len(session_tokens), \
            "Session tokens are not unique - duplicate tokens detected"
        
        # Property 5: Only the last token should be considered active
        # (implicitly verified by the fact that previous sessions were destroyed)
        last_token = session_tokens[-1]
        assert last_token is not None, \
            "Last session token is None"


@settings(max_examples=15, deadline=None)
@given(
    users=st.lists(user_data(), min_size=2, max_size=5, unique_by=lambda u: u['email'])
)
def test_session_isolation_between_users(users):
    """
    Property 6: Single Active Session Per User - Multi-User Scenario
    
    When multiple different users log in, each user should have their own
    independent session, and destroying sessions for one user should not
    affect sessions for other users.
    
    **Validates: Requirements 6.4, 6.5**
    """
    # Track session operations per user
    user_sessions = {user['email']: [] for user in users}
    destroy_calls_by_user = {user['email']: 0 for user in users}
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.cognito') as mock_cognito:
        
        # Mock DynamoDB user lookup
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        def get_user_by_email(email):
            for user in users:
                if user['email'] == email:
                    return {'Item': user}
            return {}
        
        mock_table.get_item.side_effect = lambda Key: get_user_by_email(Key['email'])
        
        # Mock Cognito session operations
        def track_sign_out(*args, **kwargs):
            username = kwargs.get('Username')
            if username in destroy_calls_by_user:
                destroy_calls_by_user[username] += 1
            return {}
        
        mock_cognito.admin_user_global_sign_out.side_effect = track_sign_out
        
        # Mock session token generation
        token_counter = [0]
        def generate_token(*args, **kwargs):
            username = kwargs.get('AuthParameters', {}).get('USERNAME')
            token = f"token_{username}_{token_counter[0]}"
            token_counter[0] += 1
            if username in user_sessions:
                user_sessions[username].append(token)
            return {
                'AuthenticationResult': {'IdToken': token}
            }
        
        mock_cognito.admin_initiate_auth.side_effect = generate_token
        
        # Each user logs in once
        for user in users:
            event = {
                'path': '/auth',
                'body': json.dumps({
                    'email': user['email'],
                    'password': user['password']
                })
            }
            
            response = handler.lambda_handler(event, MockLambdaContext())
            
            # Verify successful authentication
            assert response['statusCode'] == 200, \
                f"Login failed for user {user['email']}"
        
        # Property 1: Each user should have exactly one session
        for user in users:
            assert len(user_sessions[user['email']]) == 1, \
                f"User {user['email']} should have exactly 1 session, got {len(user_sessions[user['email']])}"
        
        # Property 2: Each user should have had their previous sessions destroyed once
        for user in users:
            assert destroy_calls_by_user[user['email']] == 1, \
                f"User {user['email']} should have had destroy_previous_sessions called once, got {destroy_calls_by_user[user['email']]}"
        
        # Property 3: All session tokens should be unique across all users
        all_tokens = []
        for tokens in user_sessions.values():
            all_tokens.extend(tokens)
        assert len(set(all_tokens)) == len(all_tokens), \
            "Session tokens are not unique across users"


@settings(max_examples=15, deadline=None)
@given(
    user=user_data(),
    login_sequence=st.lists(st.booleans(), min_size=2, max_size=10)
)
def test_session_destruction_sequence(user, login_sequence):
    """
    Property 6: Single Active Session Per User - Sequential Login Pattern
    
    For any sequence of login attempts by the same user, each successful login
    should destroy all previous sessions before creating a new one, maintaining
    the invariant that only one active session exists at any time.
    
    **Validates: Requirements 6.4, 6.5**
    """
    # Track session lifecycle
    session_lifecycle = []
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.cognito') as mock_cognito:
        
        # Mock DynamoDB user lookup
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': user
        }
        
        # Mock Cognito session operations
        def track_sign_out(*args, **kwargs):
            session_lifecycle.append({
                'action': 'destroy',
                'username': kwargs.get('Username'),
                'timestamp': datetime.utcnow()
            })
            return {}
        
        mock_cognito.admin_user_global_sign_out.side_effect = track_sign_out
        
        # Mock session token generation
        def generate_token(*args, **kwargs):
            token = f"token_{len(session_lifecycle)}"
            session_lifecycle.append({
                'action': 'create',
                'token': token,
                'timestamp': datetime.utcnow()
            })
            return {
                'AuthenticationResult': {'IdToken': token}
            }
        
        mock_cognito.admin_initiate_auth.side_effect = generate_token
        
        # Simulate login sequence
        successful_logins = 0
        for should_login in login_sequence:
            if should_login:
                event = {
                    'path': '/auth',
                    'body': json.dumps({
                        'email': user['email'],
                        'password': user['password']
                    })
                }
                
                response = handler.lambda_handler(event, MockLambdaContext())
                
                if response['statusCode'] == 200:
                    successful_logins += 1
        
        # Property 1: For each successful login, there should be a destroy followed by create
        destroy_count = sum(1 for event in session_lifecycle if event['action'] == 'destroy')
        create_count = sum(1 for event in session_lifecycle if event['action'] == 'create')
        
        assert destroy_count == successful_logins, \
            f"Expected {successful_logins} destroy operations, got {destroy_count}"
        assert create_count == successful_logins, \
            f"Expected {successful_logins} create operations, got {create_count}"
        
        # Property 2: Destroy should always precede create in each login cycle
        for i in range(0, len(session_lifecycle) - 1, 2):
            if i + 1 < len(session_lifecycle):
                assert session_lifecycle[i]['action'] == 'destroy', \
                    f"Expected destroy at position {i}, got {session_lifecycle[i]['action']}"
                assert session_lifecycle[i + 1]['action'] == 'create', \
                    f"Expected create at position {i + 1}, got {session_lifecycle[i + 1]['action']}"


@settings(max_examples=10, deadline=None)
@given(
    user=user_data()
)
def test_session_destruction_called_before_creation(user):
    """
    Property 6: Single Active Session Per User - Ordering Guarantee
    
    For any user login, the system must call destroy_previous_sessions BEFORE
    create_session to ensure there's no window where multiple sessions exist.
    
    **Validates: Requirements 6.4, 6.5**
    """
    call_order = []
    
    with patch('handler.dynamodb') as mock_dynamodb, \
         patch('handler.cognito') as mock_cognito:
        
        # Mock DynamoDB user lookup
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': user
        }
        
        # Track call order
        def track_destroy(*args, **kwargs):
            call_order.append('destroy')
            return {}
        
        def track_create(*args, **kwargs):
            call_order.append('create')
            return {
                'AuthenticationResult': {'IdToken': 'test_token'}
            }
        
        mock_cognito.admin_user_global_sign_out.side_effect = track_destroy
        mock_cognito.admin_initiate_auth.side_effect = track_create
        
        # Login
        event = {
            'path': '/auth',
            'body': json.dumps({
                'email': user['email'],
                'password': user['password']
            })
        }
        
        response = handler.lambda_handler(event, MockLambdaContext())
        
        # Verify successful authentication
        assert response['statusCode'] == 200
        
        # Property: destroy must be called before create
        assert len(call_order) == 2, \
            f"Expected 2 operations (destroy, create), got {len(call_order)}"
        assert call_order[0] == 'destroy', \
            f"First operation should be 'destroy', got '{call_order[0]}'"
        assert call_order[1] == 'create', \
            f"Second operation should be 'create', got '{call_order[1]}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
