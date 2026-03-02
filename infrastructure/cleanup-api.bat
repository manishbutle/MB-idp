@echo off
REM Cleanup failed API Gateway stack

setlocal

if "%AWS_REGION%"=="" (
  set REGION=us-east-1
) else (
  set REGION=%AWS_REGION%
)

set STACK_NAME=ai-document-processing-api

echo Deleting API Gateway stack: %STACK_NAME%
echo Region: %REGION%
echo.

aws cloudformation delete-stack ^
  --stack-name %STACK_NAME% ^
  --region %REGION%

echo.
echo Waiting for stack deletion to complete...
echo This may take a few minutes...
echo.

aws cloudformation wait stack-delete-complete ^
  --stack-name %STACK_NAME% ^
  --region %REGION%

echo.
echo Stack deleted successfully!
echo You can now run deploy.bat to redeploy.
