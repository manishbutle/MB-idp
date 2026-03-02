# API Gateway Configuration

This document describes the API Gateway configuration for the AI Document Processing system.

## Overview

The API Gateway provides a RESTful interface for the browser extension to interact with backend Lambda functions. It includes:

- **16 REST API endpoints** for all system operations
- **Cognito User Pool authentication** for secure access
- **CORS configuration** for Chrome/Edge extension origins
- **Rate limiting** (100 req/min per user, 1000 req/min per tenant)
- **Request validation** for all endpoints
- **Lambda proxy integration** for seamless backend communication

## Architecture

```
Browser Extension
    ↓ HTTPS
API Gateway (REST API)
    ↓
Cognito Authorizer (validates JWT tokens)
    ↓
Lambda Functions (Auth, Process, Data, Admin, Integration)
```

## Endpoints

### Public Endpoints (No Authentication)

| Endpoint | Method | Lambda | Description |
|----------|--------|--------|-------------|
| `/auth` | POST | Auth | User login |
| `/forget_password` | POST | Auth | Request password reset |
| `/reset_password` | POST | Auth | Submit new password |
| `/sign_up` | POST | Auth | Register new user |

### Authenticated Endpoints (Cognito JWT Required)

| Endpoint | Method | Lambda | Description |
|----------|--------|--------|-------------|
| `/process_document` | POST | Process | Process document |
| `/datapoints` | GET | Data | Fetch prompts |
| `/reset_prompts` | POST | Data | Reload prompts |
| `/history` | GET | Data | Fetch processing history |
| `/mytransactions` | GET | Data | Fetch transactions |
| `/total_document_processed` | GET | Data | Get document count |
| `/available_balance` | GET | Data | Get credit balance |
| `/profile_change` | POST | Data | Update profile |
| `/password_change` | POST | Data | Change password |
| `/top_up` | POST | Data | Process credit top-up |
| `/ftp` | POST | Integration | Upload to FTP |
| `/send_email` | POST | Integration | Send email |

### Admin Endpoints (System User Role Required)

| Endpoint | Method | Lambda | Description |
|----------|--------|--------|-------------|
| `/add_credit` | POST | Admin | Add credit to user |

## Authentication

### Cognito User Pool

The system uses AWS Cognito User Pool for authentication:

- **Username**: Email address
- **Password Policy**: Min 8 chars, uppercase, lowercase, numbers, symbols
- **Token Validity**: 
  - Access Token: 1 hour
  - ID Token: 1 hour
  - Refresh Token: 30 days
- **Custom Attributes**:
  - `tenant`: User's tenant ID
  - `role`: User role (User, System User)

### Authorization Flow

1. User logs in via `/auth` endpoint
2. Lambda validates credentials against DynamoDB
3. Lambda creates Cognito session and returns JWT tokens
4. Extension stores tokens in Local Storage
5. Extension includes `Authorization: Bearer <token>` header in subsequent requests
6. API Gateway Cognito Authorizer validates JWT token
7. If valid, request proceeds to Lambda with user context
8. If invalid, API Gateway returns 401 Unauthorized

### Lambda Authorizer

In addition to Cognito, a custom Lambda authorizer provides:

- Token validation with Cognito
- Role-based access control (RBAC)
- User context injection (email, tenant, role)
- Admin endpoint protection

## CORS Configuration

### Allowed Origins

- Chrome extensions: `chrome-extension://*`
- Edge extensions: `edge-extension://*`

### Allowed Headers

- `Content-Type`
- `Authorization`

### Allowed Methods

- `GET`
- `POST`
- `OPTIONS`

### Implementation

- **OPTIONS methods**: Mock integration returning CORS headers
- **Gateway Responses**: CORS headers on 4XX and 5XX errors
- **Method Responses**: CORS headers on all method responses

## Rate Limiting

### Throttling

- **Burst Limit**: 1000 requests (tenant-level)
- **Rate Limit**: 100 requests/minute (user-level)

### Usage Plan

- **Monthly Quota**: 100,000 requests per API key
- **Throttle Settings**: Applied at stage level

### Implementation

```yaml
MethodSettings:
  - ResourcePath: '/*'
    HttpMethod: '*'
    ThrottlingBurstLimit: 100
    ThrottlingRateLimit: 100
```

## Request Validation

All endpoints use request body validation:

```yaml
RequestValidator:
  ValidateRequestBody: true
  ValidateRequestParameters: false
```

This ensures:
- Request body conforms to expected schema
- Invalid requests are rejected before reaching Lambda
- Reduced Lambda invocations and costs

## Lambda Integration

### AWS_PROXY Integration

All endpoints use `AWS_PROXY` integration type:

- Request is passed directly to Lambda
- Lambda returns response in API Gateway format
- Automatic handling of headers, status codes, body

### Integration Request

```yaml
Integration:
  Type: AWS_PROXY
  IntegrationHttpMethod: POST
  Uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${LambdaArn}/invocations'
```

### Lambda Response Format

```python
{
    "statusCode": 200,
    "headers": {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    },
    "body": json.dumps({
        "message": "Success",
        "data": {...}
    })
}
```

## Deployment

### CloudFormation Stack

Deploy the API Gateway using CloudFormation:

```bash
aws cloudformation create-stack \
  --stack-name idp-api-gateway \
  --template-body file://api-gateway.yaml \
  --parameters \
    ParameterKey=CognitoUserPoolArn,ParameterValue=<user-pool-arn> \
    ParameterKey=AuthLambdaArn,ParameterValue=<auth-lambda-arn> \
    ParameterKey=ProcessLambdaArn,ParameterValue=<process-lambda-arn> \
    ParameterKey=DataLambdaArn,ParameterValue=<data-lambda-arn> \
    ParameterKey=AdminLambdaArn,ParameterValue=<admin-lambda-arn> \
    ParameterKey=IntegrationLambdaArn,ParameterValue=<integration-lambda-arn> \
  --capabilities CAPABILITY_IAM
```

### Deployment Dependencies

1. Deploy Cognito User Pool (`cognito-auth.yaml`)
2. Deploy Lambda functions
3. Deploy API Gateway (`api-gateway.yaml`)
4. Configure extension with API Gateway URL

### Stage Configuration

- **Stage Name**: `v1`
- **Logging**: INFO level with data trace enabled
- **Metrics**: CloudWatch metrics enabled
- **Throttling**: Configured at stage level

## Monitoring

### CloudWatch Logs

API Gateway logs all requests to CloudWatch:

- Request/response bodies
- Integration latency
- Errors and exceptions
- Throttling events

### CloudWatch Metrics

- **4XXError**: Client errors
- **5XXError**: Server errors
- **Count**: Total requests
- **IntegrationLatency**: Backend processing time
- **Latency**: Total request time

### Alarms

Recommended CloudWatch alarms:

- 4XX error rate > 5%
- 5XX error rate > 1%
- Latency > 2 seconds (p95)
- Throttle count > 100/minute

## Security

### HTTPS Only

All API Gateway endpoints enforce HTTPS:

- HTTP requests are automatically redirected
- TLS 1.2+ required

### IAM Permissions

Lambda functions require API Gateway invoke permission:

```yaml
AWS::Lambda::Permission:
  FunctionName: !Ref LambdaFunction
  Action: lambda:InvokeFunction
  Principal: apigateway.amazonaws.com
  SourceArn: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${RestApi}/*'
```

### Token Security

- JWT tokens signed by Cognito
- Tokens validated on every request
- Expired tokens automatically rejected
- Refresh tokens for session renewal

## Testing

### Manual Testing

Test endpoints using curl:

```bash
# Public endpoint (no auth)
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/v1/auth \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Authenticated endpoint
curl -X GET https://<api-id>.execute-api.<region>.amazonaws.com/v1/datapoints \
  -H "Authorization: Bearer <jwt-token>"
```

### Integration Tests

Run integration tests:

```bash
cd lambda/authorizer
pytest test_authorizer.py -v
```

## Troubleshooting

### 401 Unauthorized

- Check JWT token is valid and not expired
- Verify `Authorization` header format: `Bearer <token>`
- Confirm Cognito User Pool ARN is correct

### 403 Forbidden

- Check user role for admin endpoints
- Verify IAM permissions for Lambda invocation

### 429 Too Many Requests

- Rate limit exceeded
- Wait before retrying
- Check usage plan configuration

### 500 Internal Server Error

- Check Lambda function logs in CloudWatch
- Verify Lambda has correct IAM permissions
- Check DynamoDB table access

## Files

- `api-gateway.yaml` - Main API Gateway CloudFormation template
- `cognito-auth.yaml` - Cognito User Pool configuration
- `generate_methods.py` - Script to generate method configurations
- `api-methods-generated.yaml` - Generated method definitions
- `lambda/authorizer/handler.py` - Lambda authorizer function
- `lambda/authorizer/test_authorizer.py` - Authorizer unit tests

## References

- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- [Lambda Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
