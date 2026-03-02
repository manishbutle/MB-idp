# PowerShell script to update Lambda function code
$ErrorActionPreference = "Stop"

$REGION = "us-east-1"

Write-Host "Updating Lambda functions in region: $REGION"
Write-Host ""

# Navigate to lambda directory
Set-Location ..\lambda

# Clean up old zips
Write-Host "Cleaning up old packages..."
Remove-Item -Path "*.zip" -ErrorAction SilentlyContinue
Remove-Item -Path "temp-*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "package" -Recurse -Force -ErrorAction SilentlyContinue

# Create package directory and install dependencies
Write-Host "Installing runtime dependencies..."
New-Item -ItemType Directory -Path "package" | Out-Null
pip install -r requirements-runtime.txt -t package --upgrade --no-cache-dir | Out-Null

# Function to package Lambda
function Package-Lambda {
    param(
        [string]$Name,
        [string]$HandlerPath
    )
    
    Write-Host "Packaging $Name Lambda..."
    $tempDir = "temp-$Name"
    
    # Create temp directory
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    
    # Copy handler
    Copy-Item "$HandlerPath\handler.py" $tempDir\
    
    # Copy shared files
    Copy-Item "shared\logger_util.py" $tempDir\
    
    # Copy package dependencies
    Copy-Item "package\*" $tempDir\ -Recurse
    
    # Create zip
    $zipPath = "$Name-lambda.zip"
    Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force
    
    # Clean up temp
    Remove-Item $tempDir -Recurse -Force
    
    Write-Host "$Name Lambda packaged: $zipPath"
    return $zipPath
}

# Package all Lambdas
$authZip = Package-Lambda -Name "auth" -HandlerPath "auth"
$processZip = Package-Lambda -Name "process" -HandlerPath "process"
$dataZip = Package-Lambda -Name "data" -HandlerPath "data"
$adminZip = Package-Lambda -Name "admin" -HandlerPath "admin"
$integrationZip = Package-Lambda -Name "integration" -HandlerPath "integration"

Write-Host ""
Write-Host "Updating Lambda functions..."
Write-Host ""

# Update Auth Lambda
Write-Host "Updating Auth Lambda..."
aws lambda update-function-code `
    --function-name ai-doc-processing-auth `
    --zip-file "fileb://$authZip" `
    --region $REGION | Out-Null
Write-Host "Auth Lambda updated"

# Update Process Lambda
Write-Host "Updating Process Lambda..."
aws lambda update-function-code `
    --function-name ai-doc-processing-process `
    --zip-file "fileb://$processZip" `
    --region $REGION | Out-Null
Write-Host "Process Lambda updated"

# Update Data Lambda
Write-Host "Updating Data Lambda..."
aws lambda update-function-code `
    --function-name ai-doc-processing-data `
    --zip-file "fileb://$dataZip" `
    --region $REGION | Out-Null
Write-Host "Data Lambda updated"

# Update Admin Lambda
Write-Host "Updating Admin Lambda..."
aws lambda update-function-code `
    --function-name ai-doc-processing-admin `
    --zip-file "fileb://$adminZip" `
    --region $REGION | Out-Null
Write-Host "Admin Lambda updated"

# Update Integration Lambda
Write-Host "Updating Integration Lambda..."
aws lambda update-function-code `
    --function-name ai-doc-processing-integration `
    --zip-file "fileb://$integrationZip" `
    --region $REGION | Out-Null
Write-Host "Integration Lambda updated"

# Clean up
Write-Host ""
Write-Host "Cleaning up..."
Remove-Item -Path "*.zip" -ErrorAction SilentlyContinue
Remove-Item -Path "package" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================"
Write-Host "All Lambda functions updated successfully!"
Write-Host "========================================"

Set-Location ..\infrastructure
