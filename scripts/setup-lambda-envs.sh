#!/bin/bash
# Setup Python virtual environments for all Lambda functions

set -e

LAMBDA_DIRS=("auth" "process" "data" "admin" "integration")

for dir in "${LAMBDA_DIRS[@]}"; do
  echo "Setting up Lambda function: $dir"
  cd "lambda/$dir"
  
  # Create virtual environment
  python -m venv venv
  
  # Activate and install dependencies
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  deactivate
  
  cd ../..
  echo "✓ $dir setup complete"
done

echo "All Lambda environments setup complete!"
