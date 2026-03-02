@echo off
REM Clean and deploy Lambda functions without test dependencies

setlocal enabledelayedexpansion

if "%AWS_REGION%"=="" (
  set REGION=us-east-1
) else (
  set REGION=%AWS_REGION%
)

echo Cleaning and deploying Lambda functions to region: %REGION%
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

REM Navigate to lambda directory
cd ..\lambda

REM Clean up old packages
echo Cleaning up old packages...
if exist auth-lambda.zip del auth-lambda.zip
if exist process-lambda.zip del process-lambda.zip
if exist data-lambda.zip del data-lambda.zip
if exist admin-lambda.zip del admin-lambda.zip
if exist integration-lambda.zip del integration-lambda.zip
if exist package rmdir /s /q package
echo.

REM Create clean package directory
mkdir package
cd package

REM Install runtime dependencies only
echo Installing runtime dependencies...
pip install -r ..\requirements-runtime.txt -t . --upgrade --no-cache-dir
echo.

REM Function to create clean Lambda package
cd ..

echo Creating clean Lambda packages...
echo.

REM Auth Lambda
echo Packaging Auth Lambda...
if exist temp-auth rmdir /s /q temp-auth
mkdir temp-auth
xcopy /Y auth\handler.py temp-auth\
xcopy /Y shared\*.py temp-auth\
xcopy /E /I /Y package\* temp-auth\
cd temp-auth
powershell -Command "Compress-Archive -Path * -DestinationPath ..\auth-lambda.zip -Force"
cd ..
rmdir /s /q temp-auth
echo Auth Lambda packaged

REM Process Lambda
echo Packaging Process Lambda...
if exist temp-process rmdir /s /q temp-process
mkdir temp-process
xcopy /Y process\handler.py temp-process\
xcopy /Y shared\*.py temp-process\
xcopy /E /I /Y package\* temp-process\
cd temp-process
powershell -Command "Compress-Archive -Path * -DestinationPath ..\process-lambda.zip -Force"
cd ..
rmdir /s /q temp-process
echo Process Lambda packaged

REM Data Lambda
echo Packaging Data Lambda...
if exist temp-data rmdir /s /q temp-data
mkdir temp-data
xcopy /Y data\handler.py temp-data\
xcopy /Y shared\*.py temp-data\
xcopy /E /I /Y package\* temp-data\
cd temp-data
powershell -Command "Compress-Archive -Path * -DestinationPath ..\data-lambda.zip -Force"
cd ..
rmdir /s /q temp-data
echo Data Lambda packaged

REM Admin Lambda
echo Packaging Admin Lambda...
if exist temp-admin rmdir /s /q temp-admin
mkdir temp-admin
xcopy /Y admin\handler.py temp-admin\
xcopy /Y shared\*.py temp-admin\
xcopy /E /I /Y package\* temp-admin\
cd temp-admin
powershell -Command "Compress-Archive -Path * -DestinationPath ..\admin-lambda.zip -Force"
cd ..
rmdir /s /q temp-admin
echo Admin Lambda packaged

REM Integration Lambda
echo Packaging Integration Lambda...
if exist temp-integration rmdir /s /q temp-integration
mkdir temp-integration
xcopy /Y integration\handler.py temp-integration\
xcopy /Y shared\*.py temp-integration\
xcopy /E /I /Y package\* temp-integration\
cd temp-integration
powershell -Command "Compress-Archive -Path * -DestinationPath ..\integration-lambda.zip -Force"
cd ..
rmdir /s /q temp-integration
echo Integration Lambda packaged

echo.
echo Updating Lambda functions...
echo.

REM Update Auth Lambda
echo Updating Auth Lambda...
aws lambda update-function-code ^
  --function-name ai-doc-processing-auth ^
  --zip-file fileb://auth-lambda.zip ^
  --region %REGION%

if %errorlevel% neq 0 (
    echo Failed to update Auth Lambda
    goto :error
)
echo Auth Lambda updated successfully
echo.

REM Update Process Lambda
echo Updating Process Lambda...
aws lambda update-function-code ^
  --function-name ai-doc-processing-process ^
  --zip-file fileb://process-lambda.zip ^
  --region %REGION%

if %errorlevel% neq 0 (
    echo Failed to update Process Lambda
    goto :error
)
echo Process Lambda updated successfully
echo.

REM Update Data Lambda
echo Updating Data Lambda...
aws lambda update-function-code ^
  --function-name ai-doc-processing-data ^
  --zip-file fileb://data-lambda.zip ^
  --region %REGION%

if %errorlevel% neq 0 (
    echo Failed to update Data Lambda
    goto :error
)
echo Data Lambda updated successfully
echo.

REM Update Admin Lambda
echo Updating Admin Lambda...
aws lambda update-function-code ^
  --function-name ai-doc-processing-admin ^
  --zip-file fileb://admin-lambda.zip ^
  --region %REGION%

if %errorlevel% neq 0 (
    echo Failed to update Admin Lambda
    goto :error
)
echo Admin Lambda updated successfully
echo.

REM Update Integration Lambda
echo Updating Integration Lambda...
aws lambda update-function-code ^
  --function-name ai-doc-processing-integration ^
  --zip-file fileb://integration-lambda.zip ^
  --region %REGION%

if %errorlevel% neq 0 (
    echo Failed to update Integration Lambda
    goto :error
)
echo Integration Lambda updated successfully
echo.

REM Clean up
echo Cleaning up temporary files...
rmdir /s /q package
echo.

echo ========================================
echo All Lambda functions updated successfully!
echo ========================================
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
