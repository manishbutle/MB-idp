#!/bin/bash
# Validate CloudFormation templates

set -e

echo "Validating CloudFormation templates..."

echo "Validating dynamodb-tables.yaml..."
aws cloudformation validate-template \
  --template-body file://dynamodb-tables.yaml \
  > /dev/null && echo "✓ dynamodb-tables.yaml is valid"

echo "Validating iam-roles.yaml..."
aws cloudformation validate-template \
  --template-body file://iam-roles.yaml \
  > /dev/null && echo "✓ iam-roles.yaml is valid"

echo "Validating api-gateway.yaml..."
aws cloudformation validate-template \
  --template-body file://api-gateway.yaml \
  > /dev/null && echo "✓ api-gateway.yaml is valid"

echo ""
echo "All templates are valid!"
