# Infrastructure - CloudFormation Templates

This directory contains AWS CloudFormation templates for deploying the AI Document Processing infrastructure.

## Templates

### 1. dynamodb-tables.yaml
Creates all 9 DynamoDB tables:
- idp_users
- idp_roles
- idp_transactions
- idp_history
- idp_metadata
- idp_datapoints
- idp_document_type
- idp_rates
- idp_settings

### 2. iam-roles.yaml
Creates IAM roles for Lambda functions:
- auth-lambda-role
- process-lambda-role
- data-lambda-role
- admin-lambda-role
- integration-lambda-role

### 3. api-gateway.yaml
Creates API Gateway with 16 REST endpoints and CORS configuration.

## Deployment

### Quick Deploy (Recommended)

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

### Manual Deployment

Deploy stacks in this order:

1. **DynamoDB Tables:**
```bash
aws cloudformation deploy \
  --template-file dynamodb-tables.yaml \
  --stack-name ai-document-processing-dynamodb \
  --region us-east-1
```

2. **IAM Roles:**
```bash
aws cloudformation deploy \
  --template-file iam-roles.yaml \
  --stack-name ai-document-processing-iam \
  --region us-east-1 \
  --capabilities CAPABILITY_NAMED_IAM
```

3. **API Gateway:**
```bash
aws cloudformation deploy \
  --template-file api-gateway.yaml \
  --stack-name ai-document-processing-api \
  --region us-east-1
```

## Deletion

To delete all stacks:

**Linux/Mac:**
```bash
chmod +x delete.sh
./delete.sh
```

**Windows:**
```cmd
aws cloudformation delete-stack --stack-name ai-document-processing-api
aws cloudformation delete-stack --stack-name ai-document-processing-iam
aws cloudformation delete-stack --stack-name ai-document-processing-dynamodb
```

## Outputs

After deployment, get the API Gateway URL:
```bash
aws cloudformation describe-stacks \
  --stack-name ai-document-processing-api \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
  --output text
```

## Cost Estimation

- DynamoDB: Pay-per-request pricing
- API Gateway: Pay per request
- Lambda: Pay per invocation and duration
- Textract: Pay per page processed
- Bedrock: Pay per token

Estimated monthly cost for moderate usage: $50-200
