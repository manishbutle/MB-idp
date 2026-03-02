#!/usr/bin/env python3
"""
DynamoDB Seed Data Script
Generates sample data for development and testing
Includes multi-tenant test data
"""

import boto3
from botocore.exceptions import ClientError
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json

def hash_password(password):
    """Hash password using SHA-256 with salt (matching Lambda handler)"""
    import secrets
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def generate_timestamp(days_ago=0):
    """Generate ISO 8601 timestamp"""
    dt = datetime.utcnow() - timedelta(days=days_ago)
    return dt.isoformat() + 'Z'

def seed_roles(dynamodb):
    """Seed idp_roles table"""
    print("Seeding idp_roles...")
    table = dynamodb.Table('idp_roles')
    
    roles = [
        {
            'role_id': 'role_user',
            'role_name': 'User',
            'permissions': ['process_document', 'view_history', 'manage_profile'],
            'created_date': generate_timestamp(365)
        },
        {
            'role_id': 'role_system_user',
            'role_name': 'System User',
            'permissions': ['process_document', 'view_history', 'manage_profile', 'add_credit', 'view_all_users'],
            'created_date': generate_timestamp(365)
        }
    ]
    
    for role in roles:
        try:
            table.put_item(Item=role)
            print(f"  ✓ Created role: {role['role_name']}")
        except ClientError as e:
            print(f"  ✗ Error creating role {role['role_name']}: {e}")
    
    print()

def seed_users(dynamodb):
    """Seed idp_users table with multi-tenant data"""
    print("Seeding idp_users...")
    table = dynamodb.Table('idp_users')
    
    # Password: "password123" for all test users
    password_hash = hash_password('password123')
    
    users = [
        # Tenant A users
        {
            'email': 'john.doe@tenanta.com',
            'password_hash': password_hash,
            'first_name': 'John',
            'last_name': 'Doe',
            'contact_number': '+1-555-0101',
            'tenant': 'tenant_a',
            'role': 'User',
            'created_date': generate_timestamp(180),
            'modified_date': generate_timestamp(180),
            'is_active': True
        },
        {
            'email': 'admin@tenanta.com',
            'password_hash': password_hash,
            'first_name': 'Admin',
            'last_name': 'User A',
            'contact_number': '+1-555-0102',
            'tenant': 'tenant_a',
            'role': 'System User',
            'created_date': generate_timestamp(365),
            'modified_date': generate_timestamp(365),
            'is_active': True
        },
        # Tenant B users
        {
            'email': 'jane.smith@tenantb.com',
            'password_hash': password_hash,
            'first_name': 'Jane',
            'last_name': 'Smith',
            'contact_number': '+1-555-0201',
            'tenant': 'tenant_b',
            'role': 'User',
            'created_date': generate_timestamp(90),
            'modified_date': generate_timestamp(90),
            'is_active': True
        },
        {
            'email': 'admin@tenantb.com',
            'password_hash': password_hash,
            'first_name': 'Admin',
            'last_name': 'User B',
            'contact_number': '+1-555-0202',
            'tenant': 'tenant_b',
            'role': 'System User',
            'created_date': generate_timestamp(365),
            'modified_date': generate_timestamp(365),
            'is_active': True
        },
        # Tenant C users
        {
            'email': 'bob.wilson@tenantc.com',
            'password_hash': password_hash,
            'first_name': 'Bob',
            'last_name': 'Wilson',
            'contact_number': '+1-555-0301',
            'tenant': 'tenant_c',
            'role': 'User',
            'created_date': generate_timestamp(30),
            'modified_date': generate_timestamp(30),
            'is_active': True
        }
    ]
    
    for user in users:
        try:
            table.put_item(Item=user)
            print(f"  ✓ Created user: {user['email']} (Tenant: {user['tenant']}, Role: {user['role']})")
        except ClientError as e:
            print(f"  ✗ Error creating user {user['email']}: {e}")
    
    print()

def seed_rates(dynamodb):
    """Seed idp_rates table"""
    print("Seeding idp_rates...")
    table = dynamodb.Table('idp_rates')
    
    rates = [
        {
            'rate_id': 'rate_per_page_tenant_a',
            'tenant': 'tenant_a',
            'rate_type': 'per_page',
            'amount': Decimal('0.50'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        },
        {
            'rate_id': 'rate_per_token_tenant_a',
            'tenant': 'tenant_a',
            'rate_type': 'per_token',
            'amount': Decimal('0.0001'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        },
        {
            'rate_id': 'rate_base_tenant_a',
            'tenant': 'tenant_a',
            'rate_type': 'base',
            'amount': Decimal('0.10'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        },
        {
            'rate_id': 'rate_per_page_tenant_b',
            'tenant': 'tenant_b',
            'rate_type': 'per_page',
            'amount': Decimal('0.75'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        },
        {
            'rate_id': 'rate_per_token_tenant_b',
            'tenant': 'tenant_b',
            'rate_type': 'per_token',
            'amount': Decimal('0.00015'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        },
        {
            'rate_id': 'rate_base_tenant_b',
            'tenant': 'tenant_b',
            'rate_type': 'base',
            'amount': Decimal('0.15'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        },
        {
            'rate_id': 'rate_per_page_tenant_c',
            'tenant': 'tenant_c',
            'rate_type': 'per_page',
            'amount': Decimal('0.60'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        },
        {
            'rate_id': 'rate_per_token_tenant_c',
            'tenant': 'tenant_c',
            'rate_type': 'per_token',
            'amount': Decimal('0.00012'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        },
        {
            'rate_id': 'rate_base_tenant_c',
            'tenant': 'tenant_c',
            'rate_type': 'base',
            'amount': Decimal('0.12'),
            'effective_date': generate_timestamp(365),
            'expiry_date': generate_timestamp(-365)
        }
    ]
    
    for rate in rates:
        try:
            table.put_item(Item=rate)
            print(f"  ✓ Created rate: {rate['rate_type']} for {rate['tenant']} (${rate['amount']})")
        except ClientError as e:
            print(f"  ✗ Error creating rate {rate['rate_id']}: {e}")
    
    print()

def seed_document_types(dynamodb):
    """Seed idp_document_type table with multi-tenant data"""
    print("Seeding idp_document_type...")
    table = dynamodb.Table('idp_document_type')
    
    document_types = [
        # Tenant A document types
        {
            'document_type_id': str(uuid.uuid4()),
            'tenant': 'tenant_a',
            'document_type_name': 'Invoice',
            'classification_keywords': ['invoice', 'bill', 'payment due', 'amount due'],
            'default_prompt_id': 'prompt_invoice_tenant_a',
            'created_date': generate_timestamp(365)
        },
        {
            'document_type_id': str(uuid.uuid4()),
            'tenant': 'tenant_a',
            'document_type_name': 'Purchase Order',
            'classification_keywords': ['purchase order', 'PO', 'order number', 'vendor'],
            'default_prompt_id': 'prompt_po_tenant_a',
            'created_date': generate_timestamp(365)
        },
        {
            'document_type_id': str(uuid.uuid4()),
            'tenant': 'tenant_a',
            'document_type_name': 'Market Report',
            'classification_keywords': ['market report', 'analysis', 'forecast', 'trends'],
            'default_prompt_id': 'prompt_market_tenant_a',
            'created_date': generate_timestamp(365)
        },
        # Tenant B document types
        {
            'document_type_id': str(uuid.uuid4()),
            'tenant': 'tenant_b',
            'document_type_name': 'Invoice',
            'classification_keywords': ['invoice', 'bill', 'payment due', 'amount due'],
            'default_prompt_id': 'prompt_invoice_tenant_b',
            'created_date': generate_timestamp(365)
        },
        {
            'document_type_id': str(uuid.uuid4()),
            'tenant': 'tenant_b',
            'document_type_name': 'Receipt',
            'classification_keywords': ['receipt', 'paid', 'transaction', 'payment received'],
            'default_prompt_id': 'prompt_receipt_tenant_b',
            'created_date': generate_timestamp(365)
        },
        # Tenant C document types
        {
            'document_type_id': str(uuid.uuid4()),
            'tenant': 'tenant_c',
            'document_type_name': 'Invoice',
            'classification_keywords': ['invoice', 'bill', 'payment due', 'amount due'],
            'default_prompt_id': 'prompt_invoice_tenant_c',
            'created_date': generate_timestamp(365)
        }
    ]
    
    for doc_type in document_types:
        try:
            table.put_item(Item=doc_type)
            print(f"  ✓ Created document type: {doc_type['document_type_name']} for {doc_type['tenant']}")
        except ClientError as e:
            print(f"  ✗ Error creating document type {doc_type['document_type_name']}: {e}")
    
    print()

def seed_datapoints(dynamodb):
    """Seed idp_datapoints table with multi-tenant prompts"""
    print("Seeding idp_datapoints...")
    table = dynamodb.Table('idp_datapoints')
    
    datapoints = [
        # Tenant A prompts
        {
            'prompt_id': 'prompt_invoice_tenant_a',
            'tenant': 'tenant_a',
            'prompt_name': 'Invoice Extraction',
            'description': 'Extract key fields from invoices',
            'prompt': 'Extract the following fields from this invoice: Invoice Number, Invoice Date, Vendor Name, Vendor Address, Total Amount, Tax Amount, Due Date, Payment Terms',
            'datapoints': ['Invoice Number', 'Invoice Date', 'Vendor Name', 'Vendor Address', 'Total Amount', 'Tax Amount', 'Due Date', 'Payment Terms'],
            'created_by': 'admin@tenanta.com',
            'created_date': generate_timestamp(365),
            'modified_by': 'admin@tenanta.com',
            'modified_date': generate_timestamp(365)
        },
        {
            'prompt_id': 'prompt_po_tenant_a',
            'tenant': 'tenant_a',
            'prompt_name': 'Purchase Order Extraction',
            'description': 'Extract key fields from purchase orders',
            'prompt': 'Extract the following fields from this purchase order: PO Number, PO Date, Vendor Name, Ship To Address, Item Description, Quantity, Unit Price, Total Amount',
            'datapoints': ['PO Number', 'PO Date', 'Vendor Name', 'Ship To Address', 'Item Description', 'Quantity', 'Unit Price', 'Total Amount'],
            'created_by': 'admin@tenanta.com',
            'created_date': generate_timestamp(365),
            'modified_by': 'admin@tenanta.com',
            'modified_date': generate_timestamp(365)
        },
        {
            'prompt_id': 'prompt_market_tenant_a',
            'tenant': 'tenant_a',
            'prompt_name': 'Market Report Extraction',
            'description': 'Extract key insights from market reports',
            'prompt': 'Extract the following fields from this market report: Report Title, Report Date, Market Segment, Key Findings, Growth Rate, Market Size, Forecast Period',
            'datapoints': ['Report Title', 'Report Date', 'Market Segment', 'Key Findings', 'Growth Rate', 'Market Size', 'Forecast Period'],
            'created_by': 'admin@tenanta.com',
            'created_date': generate_timestamp(365),
            'modified_by': 'admin@tenanta.com',
            'modified_date': generate_timestamp(365)
        },
        # Tenant B prompts
        {
            'prompt_id': 'prompt_invoice_tenant_b',
            'tenant': 'tenant_b',
            'prompt_name': 'Invoice Extraction',
            'description': 'Extract key fields from invoices',
            'prompt': 'Extract the following fields from this invoice: Invoice Number, Date, Supplier Name, Total Amount, Tax, Subtotal',
            'datapoints': ['Invoice Number', 'Date', 'Supplier Name', 'Total Amount', 'Tax', 'Subtotal'],
            'created_by': 'admin@tenantb.com',
            'created_date': generate_timestamp(365),
            'modified_by': 'admin@tenantb.com',
            'modified_date': generate_timestamp(365)
        },
        {
            'prompt_id': 'prompt_receipt_tenant_b',
            'tenant': 'tenant_b',
            'prompt_name': 'Receipt Extraction',
            'description': 'Extract key fields from receipts',
            'prompt': 'Extract the following fields from this receipt: Receipt Number, Date, Merchant Name, Items, Total Amount, Payment Method',
            'datapoints': ['Receipt Number', 'Date', 'Merchant Name', 'Items', 'Total Amount', 'Payment Method'],
            'created_by': 'admin@tenantb.com',
            'created_date': generate_timestamp(365),
            'modified_by': 'admin@tenantb.com',
            'modified_date': generate_timestamp(365)
        },
        # Tenant C prompts
        {
            'prompt_id': 'prompt_invoice_tenant_c',
            'tenant': 'tenant_c',
            'prompt_name': 'Invoice Extraction',
            'description': 'Extract key fields from invoices',
            'prompt': 'Extract the following fields from this invoice: Invoice ID, Invoice Date, Vendor, Amount Due, Payment Terms',
            'datapoints': ['Invoice ID', 'Invoice Date', 'Vendor', 'Amount Due', 'Payment Terms'],
            'created_by': 'bob.wilson@tenantc.com',
            'created_date': generate_timestamp(30),
            'modified_by': 'bob.wilson@tenantc.com',
            'modified_date': generate_timestamp(30)
        }
    ]
    
    for datapoint in datapoints:
        try:
            table.put_item(Item=datapoint)
            print(f"  ✓ Created prompt: {datapoint['prompt_name']} for {datapoint['tenant']}")
        except ClientError as e:
            print(f"  ✗ Error creating prompt {datapoint['prompt_name']}: {e}")
    
    print()

def seed_transactions(dynamodb):
    """Seed idp_transactions table with sample transactions"""
    print("Seeding idp_transactions...")
    table = dynamodb.Table('idp_transactions')
    
    transactions = [
        # Tenant A transactions
        {
            'transaction_id': str(uuid.uuid4()),
            'user_email': 'john.doe@tenanta.com',
            'tenant': 'tenant_a',
            'action': 'Top-up',
            'amount': Decimal('100.00'),
            'timestamp': generate_timestamp(180),
            'remark': 'Initial credit'
        },
        {
            'transaction_id': str(uuid.uuid4()),
            'user_email': 'john.doe@tenanta.com',
            'tenant': 'tenant_a',
            'processing_id': str(uuid.uuid4()),
            'action': 'Utilized',
            'amount': Decimal('-2.50'),
            'pages': 5,
            'timestamp': generate_timestamp(30),
            'remark': 'Invoice processing'
        },
        {
            'transaction_id': str(uuid.uuid4()),
            'user_email': 'john.doe@tenanta.com',
            'tenant': 'tenant_a',
            'processing_id': str(uuid.uuid4()),
            'action': 'Utilized',
            'amount': Decimal('-1.20'),
            'pages': 2,
            'timestamp': generate_timestamp(15),
            'remark': 'PO processing'
        },
        {
            'transaction_id': str(uuid.uuid4()),
            'user_email': 'admin@tenanta.com',
            'tenant': 'tenant_a',
            'action': 'Admin Credit',
            'amount': Decimal('50.00'),
            'timestamp': generate_timestamp(10),
            'remark': 'Bonus credit from admin'
        },
        # Tenant B transactions
        {
            'transaction_id': str(uuid.uuid4()),
            'user_email': 'jane.smith@tenantb.com',
            'tenant': 'tenant_b',
            'action': 'Top-up',
            'amount': Decimal('75.00'),
            'timestamp': generate_timestamp(90),
            'remark': 'Initial credit'
        },
        {
            'transaction_id': str(uuid.uuid4()),
            'user_email': 'jane.smith@tenantb.com',
            'tenant': 'tenant_b',
            'processing_id': str(uuid.uuid4()),
            'action': 'Utilized',
            'amount': Decimal('-3.75'),
            'pages': 5,
            'timestamp': generate_timestamp(20),
            'remark': 'Invoice processing'
        },
        # Tenant C transactions
        {
            'transaction_id': str(uuid.uuid4()),
            'user_email': 'bob.wilson@tenantc.com',
            'tenant': 'tenant_c',
            'action': 'Top-up',
            'amount': Decimal('50.00'),
            'timestamp': generate_timestamp(30),
            'remark': 'Initial credit'
        }
    ]
    
    for transaction in transactions:
        try:
            table.put_item(Item=transaction)
            action_type = transaction['action']
            amount = transaction['amount']
            user = transaction['user_email']
            print(f"  ✓ Created transaction: {action_type} ${amount} for {user}")
        except ClientError as e:
            print(f"  ✗ Error creating transaction: {e}")
    
    print()

def seed_settings(dynamodb):
    """Seed idp_settings table"""
    print("Seeding idp_settings...")
    table = dynamodb.Table('idp_settings')
    
    settings = [
        {
            'setting_key': 'default_email_server',
            'tenant': 'global',
            'setting_value': 'smtp.example.com',
            'modified_date': generate_timestamp(365)
        },
        {
            'setting_key': 'max_document_pages',
            'tenant': 'global',
            'setting_value': '100',
            'modified_date': generate_timestamp(365)
        },
        {
            'setting_key': 'session_timeout_minutes',
            'tenant': 'global',
            'setting_value': '60',
            'modified_date': generate_timestamp(365)
        }
    ]
    
    for setting in settings:
        try:
            table.put_item(Item=setting)
            print(f"  ✓ Created setting: {setting['setting_key']} = {setting['setting_value']}")
        except ClientError as e:
            print(f"  ✗ Error creating setting {setting['setting_key']}: {e}")
    
    print()

def seed_all(region='us-east-1', endpoint_url=None):
    """Seed all tables with sample data"""
    
    # Create DynamoDB resource
    if endpoint_url:
        dynamodb = boto3.resource('dynamodb', region_name=region, endpoint_url=endpoint_url)
    else:
        dynamodb = boto3.resource('dynamodb', region_name=region)
    
    print(f"Seeding DynamoDB tables in region: {region}")
    if endpoint_url:
        print(f"Using endpoint: {endpoint_url}")
    print()
    
    try:
        seed_roles(dynamodb)
        seed_users(dynamodb)
        seed_rates(dynamodb)
        seed_document_types(dynamodb)
        seed_datapoints(dynamodb)
        seed_transactions(dynamodb)
        seed_settings(dynamodb)
        
        print("=" * 60)
        print("✓ All seed data created successfully!")
        print()
        print("Test Credentials:")
        print("  Password for all users: password123")
        print()
        print("Tenant A Users:")
        print("  - john.doe@tenanta.com (User)")
        print("  - admin@tenanta.com (System User)")
        print()
        print("Tenant B Users:")
        print("  - jane.smith@tenantb.com (User)")
        print("  - admin@tenantb.com (System User)")
        print()
        print("Tenant C Users:")
        print("  - bob.wilson@tenantc.com (User)")
        print("=" * 60)
        
        return True
    except Exception as e:
        print(f"✗ Error seeding data: {e}")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed DynamoDB tables with sample data')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--endpoint-url', help='DynamoDB endpoint URL (for local development)')
    
    args = parser.parse_args()
    
    success = seed_all(region=args.region, endpoint_url=args.endpoint_url)
    
    sys.exit(0 if success else 1)
