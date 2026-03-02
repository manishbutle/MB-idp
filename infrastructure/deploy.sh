#!/bin/bash
# Deploy CloudFormation stacks for AI Document Processing

set -e

REGION=${AWS_REGION:-us-east-1}
STACK_PREFIX="ai-document-processing"

echo "Deploying to region: $REGION"

# Deploy DynamoDB tables
echo "Deploying DynamoDB tables..."
aws cloudformation deploy \
  --template-file dynamodb-tables.yaml \
  --stack-name ${STACK_PREFIX}-dynamodb \
  --region $REGION \
  --no-fail-on-empty-changeset

# Deploy IAM roles
echo "Deploying IAM roles..."
aws cloudformation deploy \
  --template-file iam-roles.yaml \
  --stack-name ${STACK_PREFIX}-iam \
  --region $REGION \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset

# Deploy API Gateway
echo "Deploying API Gateway..."
aws cloudformation deploy \
  --template-file api-gateway.yaml \
  --stack-name ${STACK_PREFIX}-api \
  --region $REGION \
  --no-fail-on-empty-changeset

echo "Deployment complete!"
echo ""
echo "Getting API Gateway URL..."
aws cloudformation describe-stacks \
  --stack-name ${STACK_PREFIX}-api \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
  --output text
