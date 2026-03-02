#!/bin/bash
# Delete CloudFormation stacks for AI Document Processing

set -e

REGION=${AWS_REGION:-us-east-1}
STACK_PREFIX="ai-document-processing"

echo "Deleting stacks from region: $REGION"

# Delete in reverse order
echo "Deleting API Gateway stack..."
aws cloudformation delete-stack \
  --stack-name ${STACK_PREFIX}-api \
  --region $REGION

echo "Waiting for API Gateway stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name ${STACK_PREFIX}-api \
  --region $REGION

echo "Deleting IAM roles stack..."
aws cloudformation delete-stack \
  --stack-name ${STACK_PREFIX}-iam \
  --region $REGION

echo "Waiting for IAM roles stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name ${STACK_PREFIX}-iam \
  --region $REGION

echo "Deleting DynamoDB tables stack..."
aws cloudformation delete-stack \
  --stack-name ${STACK_PREFIX}-dynamodb \
  --region $REGION

echo "Waiting for DynamoDB tables stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name ${STACK_PREFIX}-dynamodb \
  --region $REGION

echo "All stacks deleted successfully!"
