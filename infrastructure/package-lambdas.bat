@echo off
REM Package Lambda functions with shared dependencies

echo Packaging Lambda functions with shared code...
echo.

cd ..\lambda

REM Create a temporary directory for packaging
if exist temp-package rmdir /s /q temp-package
mkdir temp-package

REM Function to package a Lambda
:package_lambda
setlocal
set LAMBDA_NAME=%1
echo Packaging %LAMBDA_NAME% Lambda...

REM Copy Lambda-specific files
xcopy /E /I /Y %LAMBDA_NAME% temp-package\%LAMBDA_NAME%

REM Copy shared folder into the package
xcopy /E /I /Y shared temp-package\%LAMBDA_NAME%\shared

REM Create ZIP file
cd temp-package\%LAMBDA_NAME%
if exist ..\..\%LAMBDA_NAME%-lambda.zip del ..\..\%LAMBDA_NAME%-lambda.zip
powershell -Command "Compress-Archive -Path * -DestinationPath ..\..\%LAMBDA_NAME%-lambda.zip -Force"
cd ..\..

REM Clean up temp directory for this Lambda
rmdir /s /q temp-package\%LAMBDA_NAME%

echo %LAMBDA_NAME% Lambda packaged successfully
echo.
endlocal
goto :eof

REM Package each Lambda function
call :package_lambda auth
call :package_lambda process
call :package_lambda data
call :package_lambda admin
call :package_lambda integration

REM Clean up temp directory
rmdir /s /q temp-package

echo.
echo All Lambda functions packaged successfully!
echo.
echo Created packages:
echo - auth-lambda.zip
echo - process-lambda.zip
echo - data-lambda.zip
echo - admin-lambda.zip
echo - integration-lambda.zip
echo.

cd ..\infrastructure
