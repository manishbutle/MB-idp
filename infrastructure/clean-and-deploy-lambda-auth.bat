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

echo Auth Role ARN: %AUTH_ROLE_ARN%
echo.

REM Navigate to lambda directory
cd ..\lambda

REM Clean up old packages
echo Cleaning up old packages...
if exist auth-lambda.zip del auth-lambda.zip
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
