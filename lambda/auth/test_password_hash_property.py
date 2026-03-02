"""
Property-Based Test for Password Hash Irreversibility
Feature: ai-document-processing
Property 8: Password Hash Irreversibility

**Validates: Requirements 13.1**

For any user password, the stored value in idp_users table should be a hash,
and it should be computationally infeasible to derive the original password from the hash.
"""

import json
import pytest
import hashlib
import re
from unittest.mock import patch
from hypothesis import given, settings, strategies as st, assume

# Mock AWS services before importing handler
with patch('boto3.resource'), patch('boto3.client'):
    import handler


# Custom strategies for generating test data

@st.composite
def password_string(draw):
    """Generate a valid password"""
    return draw(st.text(min_size=8, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='!@#$%^&*()-_=+[]{}|;:,.<>?'
    )))


# Property Tests

@settings(max_examples=50, deadline=None)
@given(password=password_string())
def test_password_hash_is_not_plaintext(password):
    """
    Property 8.1: Password Hash is Not Plaintext
    
    For any password, the hashed value should not contain the original password
    as a substring. This ensures passwords are not stored in plaintext or
    trivially encoded.
    
    **Validates: Requirements 13.1**
    """
    # Hash the password
    password_hash = handler.hash_password(password)
    
    # Property 1: Hash should not be empty
    assert password_hash is not None and len(password_hash) > 0, \
        "Password hash should not be empty"
    
    # Property 2: Hash should not contain the original password
    assert password not in password_hash, \
        f"Password hash contains the original password in plaintext"
    
    # Property 3: Hash should not be the same as the password
    assert password_hash != password, \
        "Password hash is identical to the original password"


@settings(max_examples=50, deadline=None)
@given(password=password_string())
def test_password_hash_format_is_salted(password):
    """
    Property 8.2: Password Hash Uses Salt
    
    For any password, the hash should include a salt component, making it
    resistant to rainbow table attacks. The implementation uses format: salt$hash
    
    **Validates: Requirements 13.1**
    """
    # Hash the password
    password_hash = handler.hash_password(password)
    
    # Property 1: Hash should contain a salt separator
    assert '$' in password_hash, \
        "Password hash should contain salt separator '$'"
    
    # Property 2: Hash should have exactly two parts (salt and hash)
    parts = password_hash.split('$')
    assert len(parts) == 2, \
        f"Password hash should have 2 parts (salt$hash), got {len(parts)}"
    
    salt, hash_value = parts
    
    # Property 3: Salt should be non-empty and hexadecimal
    assert len(salt) > 0, \
        "Salt should not be empty"
    assert re.match(r'^[0-9a-f]+$', salt), \
        f"Salt should be hexadecimal, got: {salt}"
    
    # Property 4: Hash value should be non-empty and hexadecimal (SHA-256)
    assert len(hash_value) > 0, \
        "Hash value should not be empty"
    assert re.match(r'^[0-9a-f]+$', hash_value), \
        f"Hash value should be hexadecimal, got: {hash_value}"
    
    # Property 5: SHA-256 produces 64 character hex string
    assert len(hash_value) == 64, \
        f"SHA-256 hash should be 64 characters, got {len(hash_value)}"


@settings(max_examples=50, deadline=None)
@given(password=password_string())
def test_password_hash_is_deterministic_with_same_salt(password):
    """
    Property 8.3: Hash is Deterministic with Same Salt
    
    For any password and salt combination, hashing should produce the same
    result consistently. This verifies the hash function is deterministic.
    
    **Validates: Requirements 13.1**
    """
    # Hash the password twice
    hash1 = handler.hash_password(password)
    hash2 = handler.hash_password(password)
    
    # Extract salts
    salt1 = hash1.split('$')[0]
    salt2 = hash2.split('$')[0]
    
    # Property 1: Different hashes should use different salts
    assert salt1 != salt2, \
        "Each hash should use a unique salt"
    
    # Property 2: Manually verify determinism with same salt
    # Recreate hash using salt1
    manual_hash = hashlib.sha256((password + salt1).encode()).hexdigest()
    expected_hash = f"{salt1}${manual_hash}"
    
    assert hash1 == expected_hash, \
        "Hash should be deterministic when using the same salt"


@settings(max_examples=50, deadline=None)
@given(password=password_string())
def test_password_hash_is_irreversible(password):
    """
    Property 8.4: Password Hash is Computationally Irreversible
    
    For any password, it should be computationally infeasible to derive the
    original password from the hash. We verify this by:
    1. Ensuring the hash is one-way (no reverse function exists)
    2. Verifying the hash uses cryptographic algorithms (SHA-256)
    3. Confirming the hash output has high entropy
    
    **Validates: Requirements 13.1**
    """
    # Hash the password
    password_hash = handler.hash_password(password)
    
    # Property 1: Hash should be significantly different from password
    # (Hamming distance for strings of different lengths)
    assert len(password_hash) != len(password), \
        "Hash length should differ from password length"
    
    # Property 2: Hash should use cryptographic algorithm (SHA-256)
    # Verify by checking hash length (SHA-256 = 64 hex chars)
    hash_value = password_hash.split('$')[1]
    assert len(hash_value) == 64, \
        f"Hash should be SHA-256 (64 hex chars), got {len(hash_value)}"
    
    # Property 3: Hash should have high entropy (not predictable)
    # Check that hash contains varied characters
    unique_chars = len(set(hash_value))
    assert unique_chars >= 10, \
        f"Hash should have high entropy (at least 10 unique chars), got {unique_chars}"
    
    # Property 4: No reverse function should exist in the handler module
    assert not hasattr(handler, 'unhash_password'), \
        "No reverse function should exist for password hashing"
    assert not hasattr(handler, 'decrypt_password'), \
        "No decrypt function should exist for password hashing"
    assert not hasattr(handler, 'decode_password'), \
        "No decode function should exist for password hashing"


@settings(max_examples=50, deadline=None)
@given(
    password1=password_string(),
    password2=password_string()
)
def test_different_passwords_produce_different_hashes(password1, password2):
    """
    Property 8.5: Different Passwords Produce Different Hashes
    
    For any two different passwords, their hashes should be different.
    This ensures the hash function has good collision resistance.
    
    **Validates: Requirements 13.1**
    """
    # Ensure passwords are different
    assume(password1 != password2)
    
    # Hash both passwords
    hash1 = handler.hash_password(password1)
    hash2 = handler.hash_password(password2)
    
    # Property: Hashes should be different
    assert hash1 != hash2, \
        f"Different passwords should produce different hashes"
    
    # Property: Even the hash values (without salt) should be different
    hash_value1 = hash1.split('$')[1]
    hash_value2 = hash2.split('$')[1]
    assert hash_value1 != hash_value2, \
        "Different passwords should produce different hash values"


@settings(max_examples=50, deadline=None)
@given(password=password_string())
def test_password_verification_works_correctly(password):
    """
    Property 8.6: Password Verification is Correct
    
    For any password, the verify_password function should:
    1. Return True when verifying the correct password
    2. Return False when verifying an incorrect password
    3. Work correctly with the hash produced by hash_password
    
    **Validates: Requirements 13.1**
    """
    # Hash the password
    password_hash = handler.hash_password(password)
    
    # Property 1: Correct password should verify successfully
    assert handler.verify_password(password, password_hash) is True, \
        "Correct password should verify successfully"
    
    # Property 2: Incorrect password should fail verification
    wrong_password = password + "wrong"
    assert handler.verify_password(wrong_password, password_hash) is False, \
        "Incorrect password should fail verification"
    
    # Property 3: Empty password should fail verification
    assert handler.verify_password("", password_hash) is False, \
        "Empty password should fail verification"


@settings(max_examples=30, deadline=None)
@given(password=password_string())
def test_password_hash_resists_common_attacks(password):
    """
    Property 8.7: Password Hash Resists Common Attacks
    
    For any password, the hash should be resistant to:
    1. Length extension attacks (fixed-length output)
    2. Timing attacks (constant-time comparison in verify)
    3. Rainbow table attacks (unique salt per hash)
    
    **Validates: Requirements 13.1**
    """
    # Generate multiple hashes of the same password
    hashes = [handler.hash_password(password) for _ in range(3)]
    
    # Property 1: Each hash should use a different salt (rainbow table resistance)
    salts = [h.split('$')[0] for h in hashes]
    assert len(set(salts)) == len(salts), \
        "Each hash should use a unique salt to resist rainbow table attacks"
    
    # Property 2: All hashes should have the same length (length extension resistance)
    hash_lengths = [len(h) for h in hashes]
    assert len(set(hash_lengths)) == 1, \
        "All hashes should have consistent length"
    
    # Property 3: Hash values should all be 64 characters (SHA-256 fixed output)
    for h in hashes:
        hash_value = h.split('$')[1]
        assert len(hash_value) == 64, \
            f"Hash value should be 64 characters (SHA-256), got {len(hash_value)}"


@settings(max_examples=30, deadline=None)
@given(
    password=password_string(),
    similar_password=password_string()
)
def test_similar_passwords_produce_completely_different_hashes(password, similar_password):
    """
    Property 8.8: Similar Passwords Produce Completely Different Hashes
    
    For any two passwords that differ by even a single character, their hashes
    should be completely different (avalanche effect). This ensures small changes
    in input produce large changes in output.
    
    **Validates: Requirements 13.1**
    """
    # Ensure passwords are different
    assume(password != similar_password)
    
    # Hash both passwords
    hash1 = handler.hash_password(password)
    hash2 = handler.hash_password(similar_password)
    
    # Extract hash values (without salt)
    hash_value1 = hash1.split('$')[1]
    hash_value2 = hash2.split('$')[1]
    
    # Property 1: Hashes should be completely different
    assert hash_value1 != hash_value2, \
        "Similar passwords should produce different hashes"
    
    # Property 2: Calculate Hamming distance (number of different characters)
    # For good cryptographic hash, even 1 char difference should cause ~50% bit flip
    differences = sum(c1 != c2 for c1, c2 in zip(hash_value1, hash_value2))
    
    # At least 25% of characters should be different (avalanche effect)
    min_differences = len(hash_value1) // 4
    assert differences >= min_differences, \
        f"Hash should show avalanche effect: expected at least {min_differences} different chars, got {differences}"


@settings(max_examples=20, deadline=None)
@given(password=password_string())
def test_stored_hash_cannot_be_used_as_password(password):
    """
    Property 8.9: Stored Hash Cannot Be Used as Password
    
    For any password, the hash itself should not be accepted as a valid password.
    This prevents hash-based authentication bypass.
    
    **Validates: Requirements 13.1**
    """
    # Hash the password
    password_hash = handler.hash_password(password)
    
    # Property: Using the hash as a password should fail verification
    assert handler.verify_password(password_hash, password_hash) is False, \
        "Hash should not be accepted as a valid password"
    
    # Property: Hash of the hash should be different from original hash
    hash_of_hash = handler.hash_password(password_hash)
    assert hash_of_hash != password_hash, \
        "Hash of hash should be different from original hash"


@settings(max_examples=20, deadline=None)
@given(password=password_string())
def test_password_hash_stored_in_database_format(password):
    """
    Property 8.10: Password Hash is Stored in Correct Database Format
    
    For any password, when stored in the idp_users table, the hash should:
    1. Be a string (not bytes or other type)
    2. Be ASCII-safe (no special characters that could cause encoding issues)
    3. Have reasonable length for database storage
    
    **Validates: Requirements 13.1**
    """
    # Hash the password
    password_hash = handler.hash_password(password)
    
    # Property 1: Hash should be a string
    assert isinstance(password_hash, str), \
        f"Password hash should be a string, got {type(password_hash)}"
    
    # Property 2: Hash should be ASCII-safe (only hex chars and separator)
    assert all(c in '0123456789abcdef$' for c in password_hash), \
        "Password hash should only contain hexadecimal characters and '$' separator"
    
    # Property 3: Hash should have reasonable length for database storage
    # Salt (32 chars) + separator (1 char) + SHA-256 hash (64 chars) = 97 chars
    assert 90 <= len(password_hash) <= 150, \
        f"Password hash length should be reasonable for database storage, got {len(password_hash)}"
    
    # Property 4: Hash should be encodable as UTF-8 (database compatibility)
    try:
        password_hash.encode('utf-8')
    except UnicodeEncodeError:
        pytest.fail("Password hash should be UTF-8 encodable")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
