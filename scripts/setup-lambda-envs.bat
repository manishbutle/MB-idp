@echo off
REM Setup Python virtual environments for all Lambda functions (Windows)

setlocal enabledelayedexpansion

set LAMBDA_DIRS=auth process data admin integration

for %%d in (%LAMBDA_DIRS%) do (
  echo Setting up Lambda function: %%d
  cd lambda\%%d
  
  REM Create virtual environment
  python -m venv venv
  
  REM Activate and install dependencies
  call venv\Scripts\activate.bat
  pip install --upgrade pip
  pip install -r requirements.txt
  call deactivate
  
  cd ..\..
  echo ✓ %%d setup complete
)

echo All Lambda environments setup complete!
