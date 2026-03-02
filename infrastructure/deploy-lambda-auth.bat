@echo off
REM Deploy Lambda functions with proper role ARNs

setlocal enabledelayedexpansion

if "%AWS_REGION%"=="" (
  set REGION=us-east-1
) else (
  set REGION=%AWS_REGION%
)

echo Deploying Lambda functions to region: %REGION%
echo.

REM Get AWS Account ID
echo Getting AWS Account ID...
for /f "tokens=*" %%i in ('aws sts get-caller-identity --query Account --output text') do set ACCOUNT_ID=%%i
echo Account ID: %ACCOUNT_ID%
echo.

REM Get Role ARNs from CloudFormation stack
echo Getting IAM Role ARNs from CloudFormation...
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name ai-document-processing-iam --region %REGION% --query "Stacks[0].Outputs[?OutputKey=='AuthLambdaRoleArn'].OutputValue" --output text') do set AUTH_ROLE_ARN=%%i

echo Auth Role ARN: %AUTH_ROLE_ARN%

REM Wait for IAM roles to propagate
echo Waiting 10 seconds for IAM roles to propagate...
timeout /t 10 /nobreak >nul
echo.

REM Navigate to lambda directory
cd ..\lambda

REM Check if Lambda functions already exist and delete them if they do
echo Checking for existing Lambda functions...
aws lambda get-function --function-name ai-doc-processing-auth --region %REGION% >nul 2>&1
if %errorlevel% equ 0 (
    echo Deleting existing auth Lambda...
    aws lambda delete-function --function-name ai-doc-processing-auth --region %REGION%
    timeout /t 2 /nobreak >nul
)

echo.
echo Creating deployment packages...
echo.

REM Create deployment package for Auth Lambda
echo Packaging Auth Lambda...
cd auth
if exist ..\auth-lambda.zip del ..\auth-lambda.zip
powershell -Command "Compress-Archive -Path * -DestinationPath ..\auth-lambda.zip -Force"
cd ..

echo.
echo Deploying Lambda functions...
echo.

REM Deploy Auth Lambda
echo Deploying Auth Lambda...
aws lambda create-function ^
  --function-name ai-doc-processing-auth ^
  --runtime python3.9 ^
  --role %AUTH_ROLE_ARN% ^
  --handler handler.lambda_handler ^
  --zip-file fileb://auth-lambda.zip ^
  --timeout 30 ^
  --memory-size 256 ^
  --region %REGION% ^
  --environment "Variables={USERS_TABLE=idp_users,COGNITO_USER_POOL_ID=,COGNITO_CLIENT_ID=,SES_FROM_EMAIL=noreply@example.com}"

if %errorlevel% neq 0 (
    echo Failed to deploy Auth Lambda
    goto :error
)
echo Auth Lambda deployed successfully
echo.

echo.

echo.
echo ========================================
echo All Lambda functions deployed successfully!
echo ========================================
echo.
echo Lambda Functions:
echo - ai-doc-processing-auth

cd ..\infrastructure
goto :end

:error
echo.
echo ========================================
echo Deployment failed!
echo ========================================
cd ..\infrastructure
exit /b 1

:end
