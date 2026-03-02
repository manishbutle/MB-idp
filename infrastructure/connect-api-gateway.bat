@echo off
REM Connect API Gateway to Lambda functions

setlocal enabledelayedexpansion

if "%AWS_REGION%"=="" (
  set REGION=us-east-1
) else (
  set REGION=%AWS_REGION%
)

echo Connecting API Gateway to Lambda functions...
echo Region: %REGION%
echo.

REM Get Lambda function ARNs
echo Getting Lambda function ARNs...
for /f "tokens=*" %%i in ('aws lambda get-function --function-name ai-doc-processing-auth --region %REGION% --query "Configuration.FunctionArn" --output text') do set AUTH_ARN=%%i
for /f "tokens=*" %%i in ('aws lambda get-function --function-name ai-doc-processing-process --region %REGION% --query "Configuration.FunctionArn" --output text') do set PROCESS_ARN=%%i
for /f "tokens=*" %%i in ('aws lambda get-function --function-name ai-doc-processing-data --region %REGION% --query "Configuration.FunctionArn" --output text') do set DATA_ARN=%%i
for /f "tokens=*" %%i in ('aws lambda get-function --function-name ai-doc-processing-admin --region %REGION% --query "Configuration.FunctionArn" --output text') do set ADMIN_ARN=%%i
for /f "tokens=*" %%i in ('aws lambda get-function --function-name ai-doc-processing-integration --region %REGION% --query "Configuration.FunctionArn" --output text') do set INTEGRATION_ARN=%%i

echo Auth Lambda ARN: %AUTH_ARN%
echo Process Lambda ARN: %PROCESS_ARN%
echo Data Lambda ARN: %DATA_ARN%
echo Admin Lambda ARN: %ADMIN_ARN%
echo Integration Lambda ARN: %INTEGRATION_ARN%
echo.

REM Delete old API Gateway stack if it exists
echo Checking for existing API Gateway stack...
aws cloudformation describe-stacks --stack-name ai-document-processing-api --region %REGION% >nul 2>&1
if %errorlevel% equ 0 (
    echo Deleting old API Gateway stack...
    aws cloudformation delete-stack --stack-name ai-document-processing-api --region %REGION%
    echo Waiting for stack deletion...
    aws cloudformation wait stack-delete-complete --stack-name ai-document-processing-api --region %REGION%
    echo Old stack deleted
    echo.
)

REM Deploy new API Gateway with Lambda integration
echo Deploying API Gateway with Lambda integration...
aws cloudformation deploy ^
  --template-file api-gateway-with-lambda.yaml ^
  --stack-name ai-document-processing-api ^
  --region %REGION% ^
  --parameter-overrides ^
    AuthLambdaArn=%AUTH_ARN% ^
    ProcessLambdaArn=%PROCESS_ARN% ^
    DataLambdaArn=%DATA_ARN% ^
    AdminLambdaArn=%ADMIN_ARN% ^
    IntegrationLambdaArn=%INTEGRATION_ARN% ^
  --no-fail-on-empty-changeset

if %errorlevel% neq 0 (
    echo Failed to deploy API Gateway
    exit /b 1
)

echo.
echo ========================================
echo API Gateway connected successfully!
echo ========================================
echo.
echo Getting API Gateway URL...
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name ai-document-processing-api --region %REGION% --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" --output text') do set API_URL=%%i

echo.
echo API Gateway URL: %API_URL%
echo.
echo Update this URL in your extension's api-client.js file:
echo   const API_BASE_URL = '%API_URL%';
echo.
