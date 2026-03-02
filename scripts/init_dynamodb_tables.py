#!/usr/bin/env python3
"""
DynamoDB Table Initialization Script
Creates all 9 tables for the AI Document Processing system
"""

import boto3
from botocore.exceptions import ClientError
import sys

def create_table_if_not_exists(dynamodb, table_name, key_schema, attribute_definitions, 
                                global_secondary_indexes=None):
    """Create a DynamoDB table if it doesn't already exist"""
    try:
        # Check if table exists
        dynamodb.describe_table(TableName=table_name)
        print(f"✓ Table {table_name} already exists")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # Table doesn't exist, create it
            try:
                params = {
                    'TableName': table_name,
                    'KeySchema': key_schema,
                    'AttributeDefinitions': attribute_definitions,
                    'BillingMode': 'PAY_PER_REQUEST',
                    'Tags': [
                        {'Key': 'Application', 'Value': 'AI-Document-Processing'}
                    ]
                }
                
                if global_secondary_indexes:
                    params['GlobalSecondaryIndexes'] = global_secondary_indexes
                
                dynamodb.create_table(**params)
                
                # Wait for table to be created
                waiter = dynamodb.get_waiter('table_exists')
                waiter.wait(TableName=table_name)
                
                print(f"✓ Created table {table_name}")
                return True
            except ClientError as create_error:
                print(f"✗ Error creating table {table_name}: {create_error}")
                return False
        else:
            print(f"✗ Error checking table {table_name}: {e}")
            return False

def init_tables(region='us-east-1', endpoint_url=None):
    """Initialize all DynamoDB tables"""
    
    # Create DynamoDB client
    if endpoint_url:
        dynamodb = boto3.client('dynamodb', region_name=region, endpoint_url=endpoint_url)
    else:
        dynamodb = boto3.client('dynamodb', region_name=region)
    
    print(f"Initializing DynamoDB tables in region: {region}")
    if endpoint_url:
        print(f"Using endpoint: {endpoint_url}")
    print()
    
    success_count = 0
    total_tables = 9
    
    # 1. idp_users table
    if create_table_if_not_exists(
        dynamodb,
        'idp_users',
        key_schema=[
            {'AttributeName': 'email', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'email', 'AttributeType': 'S'},
            {'AttributeName': 'tenant', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'tenant-email-index',
                'KeySchema': [
                    {'AttributeName': 'tenant', 'KeyType': 'HASH'},
                    {'AttributeName': 'email', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    ):
        success_count += 1
    
    # 2. idp_roles table
    if create_table_if_not_exists(
        dynamodb,
        'idp_roles',
        key_schema=[
            {'AttributeName': 'role_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'role_id', 'AttributeType': 'S'}
        ]
    ):
        success_count += 1
    
    # 3. idp_transactions table
    if create_table_if_not_exists(
        dynamodb,
        'idp_transactions',
        key_schema=[
            {'AttributeName': 'transaction_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'transaction_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_email', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'user_email-timestamp-index',
                'KeySchema': [
                    {'AttributeName': 'user_email', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    ):
        success_count += 1
    
    # 4. idp_history table
    if create_table_if_not_exists(
        dynamodb,
        'idp_history',
        key_schema=[
            {'AttributeName': 'processing_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'processing_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_email', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'user_email-timestamp-index',
                'KeySchema': [
                    {'AttributeName': 'user_email', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    ):
        success_count += 1
    
    # 5. idp_metadata table
    if create_table_if_not_exists(
        dynamodb,
        'idp_metadata',
        key_schema=[
            {'AttributeName': 'processing_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'processing_id', 'AttributeType': 'S'}
        ]
    ):
        success_count += 1
    
    # 6. idp_datapoints table
    if create_table_if_not_exists(
        dynamodb,
        'idp_datapoints',
        key_schema=[
            {'AttributeName': 'prompt_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'prompt_id', 'AttributeType': 'S'},
            {'AttributeName': 'tenant', 'AttributeType': 'S'},
            {'AttributeName': 'prompt_name', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'tenant-prompt_name-index',
                'KeySchema': [
                    {'AttributeName': 'tenant', 'KeyType': 'HASH'},
                    {'AttributeName': 'prompt_name', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    ):
        success_count += 1
    
    # 7. idp_document_type table
    if create_table_if_not_exists(
        dynamodb,
        'idp_document_type',
        key_schema=[
            {'AttributeName': 'document_type_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'document_type_id', 'AttributeType': 'S'},
            {'AttributeName': 'tenant', 'AttributeType': 'S'},
            {'AttributeName': 'document_type_name', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'tenant-document_type_name-index',
                'KeySchema': [
                    {'AttributeName': 'tenant', 'KeyType': 'HASH'},
                    {'AttributeName': 'document_type_name', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    ):
        success_count += 1
    
    # 8. idp_rates table
    if create_table_if_not_exists(
        dynamodb,
        'idp_rates',
        key_schema=[
            {'AttributeName': 'rate_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'rate_id', 'AttributeType': 'S'}
        ]
    ):
        success_count += 1
    
    # 9. idp_settings table
    if create_table_if_not_exists(
        dynamodb,
        'idp_settings',
        key_schema=[
            {'AttributeName': 'setting_key', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'setting_key', 'AttributeType': 'S'}
        ]
    ):
        success_count += 1
    
    print()
    print(f"Summary: {success_count}/{total_tables} tables initialized successfully")
    
    return success_count == total_tables

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize DynamoDB tables')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--endpoint-url', help='DynamoDB endpoint URL (for local development)')
    
    args = parser.parse_args()
    
    success = init_tables(region=args.region, endpoint_url=args.endpoint_url)
    
    sys.exit(0 if success else 1)
