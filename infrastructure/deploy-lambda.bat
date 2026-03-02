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
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name ai-document-processing-iam --region %REGION% --query "Stacks[0].Outputs[?OutputKey=='ProcessLambdaRoleArn'].OutputValue" --output text') do set PROCESS_ROLE_ARN=%%i
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name ai-document-processing-iam --region %REGION% --query "Stacks[0].Outputs[?OutputKey=='DataLambdaRoleArn'].OutputValue" --output text') do set DATA_ROLE_ARN=%%i
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name ai-document-processing-iam --region %REGION% --query "Stacks[0].Outputs[?OutputKey=='AdminLambdaRoleArn'].OutputValue" --output text') do set ADMIN_ROLE_ARN=%%i
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name ai-document-processing-iam --region %REGION% --query "Stacks[0].Outputs[?OutputKey=='IntegrationLambdaRoleArn'].OutputValue" --output text') do set INTEGRATION_ROLE_ARN=%%i

echo Auth Role ARN: %AUTH_ROLE_ARN%
echo Process Role ARN: %PROCESS_ROLE_ARN%
echo Data Role ARN: %DATA_ROLE_ARN%
echo Admin Role ARN: %ADMIN_ROLE_ARN%
echo Integration Role ARN: %INTEGRATION_ROLE_ARN%
echo.

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

aws lambda get-function --function-name ai-doc-processing-process --region %REGION% >nul 2>&1
if %errorlevel% equ 0 (
    echo Deleting existing process Lambda...
    aws lambda delete-function --function-name ai-doc-processing-process --region %REGION%
    timeout /t 2 /nobreak >nul
)

aws lambda get-function --function-name ai-doc-processing-data --region %REGION% >nul 2>&1
if %errorlevel% equ 0 (
    echo Deleting existing data Lambda...
    aws lambda delete-function --function-name ai-doc-processing-data --region %REGION%
    timeout /t 2 /nobreak >nul
)

aws lambda get-function --function-name ai-doc-processing-admin --region %REGION% >nul 2>&1
if %errorlevel% equ 0 (
    echo Deleting existing admin Lambda...
    aws lambda delete-function --function-name ai-doc-processing-admin --region %REGION%
    timeout /t 2 /nobreak >nul
)

aws lambda get-function --function-name ai-doc-processing-integration --region %REGION% >nul 2>&1
if %errorlevel% equ 0 (
    echo Deleting existing integration Lambda...
    aws lambda delete-function --function-name ai-doc-processing-integration --region %REGION%
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

REM Create deployment package for Process Lambda
echo Packaging Process Lambda...
cd process
if exist ..\process-lambda.zip del ..\process-lambda.zip
powershell -Command "Compress-Archive -Path * -DestinationPath ..\process-lambda.zip -Force"
cd ..

REM Create deployment package for Data Lambda
echo Packaging Data Lambda...
cd data
if exist ..\data-lambda.zip del ..\data-lambda.zip
powershell -Command "Compress-Archive -Path * -DestinationPath ..\data-lambda.zip -Force"
cd ..

REM Create deployment package for Admin Lambda
echo Packaging Admin Lambda...
cd admin
if exist ..\admin-lambda.zip del ..\admin-lambda.zip
powershell -Command "Compress-Archive -Path * -DestinationPath ..\admin-lambda.zip -Force"
cd ..

REM Create deployment package for Integration Lambda
echo Packaging Integration Lambda...
cd integration
if exist ..\integration-lambda.zip del ..\integration-lambda.zip
powershell -Command "Compress-Archive -Path * -DestinationPath ..\integration-lambda.zip -Force"
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

REM Deploy Process Lambda
echo Deploying Process Lambda...
aws lambda create-function ^
  --function-name ai-doc-processing-process ^
  --runtime python3.9 ^
  --role %PROCESS_ROLE_ARN% ^
  --handler handler.lambda_handler ^
  --zip-file fileb://process-lambda.zip ^
  --timeout 300 ^
  --memory-size 512 ^
  --region %REGION%

if %errorlevel% neq 0 (
    echo Failed to deploy Process Lambda
    goto :error
)
echo Process Lambda deployed successfully
echo.

REM Deploy Data Lambda
echo Deploying Data Lambda...
aws lambda create-function ^
  --function-name ai-doc-processing-data ^
  --runtime python3.9 ^
  --role %DATA_ROLE_ARN% ^
  --handler handler.lambda_handler ^
  --zip-file fileb://data-lambda.zip ^
  --timeout 30 ^
  --memory-size 256 ^
  --region %REGION% ^
  --environment "Variables={USERS_TABLE=idp_users,DATAPOINTS_TABLE=idp_datapoints,HISTORY_TABLE=idp_history,TRANSACTIONS_TABLE=idp_transactions}"

if %errorlevel% neq 0 (
    echo Failed to deploy Data Lambda
    goto :error
)
echo Data Lambda deployed successfully
echo.

REM Deploy Admin Lambda
echo Deploying Admin Lambda...
aws lambda create-function ^
  --function-name ai-doc-processing-admin ^
  --runtime python3.9 ^
  --role %ADMIN_ROLE_ARN% ^
  --handler handler.lambda_handler ^
  --zip-file fileb://admin-lambda.zip ^
  --timeout 30 ^
  --memory-size 256 ^
  --region %REGION% ^
  --environment "Variables={USERS_TABLE=idp_users,ROLES_TABLE=idp_roles,TRANSACTIONS_TABLE=idp_transactions}"

if %errorlevel% neq 0 (
    echo Failed to deploy Admin Lambda
    goto :error
)
echo Admin Lambda deployed successfully
echo.

REM Deploy Integration Lambda
echo Deploying Integration Lambda...
aws lambda create-function ^
  --function-name ai-doc-processing-integration ^
  --runtime python3.9 ^
  --role %INTEGRATION_ROLE_ARN% ^
  --handler handler.lambda_handler ^
  --zip-file fileb://integration-lambda.zip ^
  --timeout 60 ^
  --memory-size 256 ^
  --region %REGION%

if %errorlevel% neq 0 (
    echo Failed to deploy Integration Lambda
    goto :error
)
echo Integration Lambda deployed successfully
echo.

echo.
echo ========================================
echo All Lambda functions deployed successfully!
echo ========================================
echo.
echo Lambda Functions:
echo - ai-doc-processing-auth
echo - ai-doc-processing-process
echo - ai-doc-processing-data
echo - ai-doc-processing-admin
echo - ai-doc-processing-integration
echo.

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
