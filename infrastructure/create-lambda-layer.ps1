# PowerShell script to create Lambda layer with Python dependencies
$ErrorActionPreference = "Stop"

$REGION = "us-east-1"
$LAYER_NAME = "ai-doc-processing-dependencies"
$S3_BUCKET = "ai-doc-processing-lambda-layers-$((Get-Date).Ticks)"

Write-Host "Creating Lambda Layer for Python dependencies"
Write-Host "Region: $REGION"
Write-Host ""

# Navigate to lambda directory
Set-Location ..\lambda

# Clean up old layer files
Write-Host "Cleaning up old layer files..."
Remove-Item -Path "layer" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "lambda-layer.zip" -ErrorAction SilentlyContinue

# Create layer directory structure
Write-Host "Creating layer directory structure..."
New-Item -ItemType Directory -Path "layer\python" -Force | Out-Null

# Install dependencies to layer
Write-Host "Installing Python dependencies to layer..."
pip install -r requirements-runtime.txt -t layer\python --upgrade --no-cache-dir

# Create layer zip
Write-Host "Creating layer zip file..."
Set-Location layer
Compress-Archive -Path python -DestinationPath ..\lambda-layer.zip -Force
Set-Location ..

Write-Host "Layer zip created: lambda-layer.zip"
Write-Host ""

# Create S3 bucket for layer storage
Write-Host "Creating S3 bucket for layer storage..."
try {
    aws s3 mb "s3://$S3_BUCKET" --region $REGION 2>&1 | Out-Null
    Write-Host "S3 bucket created: $S3_BUCKET"
} catch {
    Write-Host "Note: Bucket creation failed (may already exist or name taken)"
    # Try with a different bucket name
    $S3_BUCKET = "ai-doc-processing-layers-$(Get-Random -Maximum 99999)"
    aws s3 mb "s3://$S3_BUCKET" --region $REGION
    Write-Host "S3 bucket created: $S3_BUCKET"
}

# Upload layer to S3
Write-Host "Uploading layer to S3..."
aws s3 cp lambda-layer.zip "s3://$S3_BUCKET/lambda-layer.zip" --region $REGION
Write-Host "Layer uploaded to S3"
Write-Host ""

# Publish Lambda layer
Write-Host "Publishing Lambda layer..."
$layerOutput = aws lambda publish-layer-version `
    --layer-name $LAYER_NAME `
    --description "Python dependencies for AI Document Processing" `
    --content "S3Bucket=$S3_BUCKET,S3Key=lambda-layer.zip" `
    --compatible-runtimes python3.9 python3.10 python3.11 python3.12 `
    --region $REGION | ConvertFrom-Json

$LAYER_ARN = $layerOutput.LayerVersionArn
Write-Host "Layer published: $LAYER_ARN"
Write-Host ""

# Attach layer to all Lambda functions
Write-Host "Attaching layer to Lambda functions..."

$functions = @(
    "ai-doc-processing-auth",
    "ai-doc-processing-process",
    "ai-doc-processing-data",
    "ai-doc-processing-admin",
    "ai-doc-processing-integration"
)

foreach ($function in $functions) {
    Write-Host "Updating $function..."
    aws lambda update-function-configuration `
        --function-name $function `
        --layers $LAYER_ARN `
        --region $REGION | Out-Null
    Write-Host "$function updated"
}

Write-Host ""
Write-Host "Waiting for Lambda functions to update..."
Start-Sleep -Seconds 10

# Now redeploy Lambda functions with minimal packages (only handler and shared files)
Write-Host ""
Write-Host "Redeploying Lambda functions with minimal packages..."
Write-Host ""

# Clean up old packages
Remove-Item -Path "*.zip" -ErrorAction SilentlyContinue
Remove-Item -Path "temp-*" -Recurse -Force -ErrorAction SilentlyContinue

# Function to package Lambda without dependencies
function Package-MinimalLambda {
    param(
        [string]$Name,
        [string]$HandlerPath
    )
    
    Write-Host "Packaging $Name Lambda (minimal)..."
    $tempDir = "temp-$Name"
    
    # Create temp directory
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    
    # Copy handler
    Copy-Item "$HandlerPath\handler.py" $tempDir\
    
    # Copy shared files
    Copy-Item "shared\logger_util.py" $tempDir\
    
    # Create zip (no dependencies - they're in the layer)
    $zipPath = "$Name-lambda.zip"
    Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force
    
    # Clean up temp
    Remove-Item $tempDir -Recurse -Force
    
    Write-Host "$Name Lambda packaged: $zipPath"
    return $zipPath
}

# Package all Lambdas (minimal - no dependencies)
$authZip = Package-MinimalLambda -Name "auth" -HandlerPath "auth"
$processZip = Package-MinimalLambda -Name "process" -HandlerPath "process"
$dataZip = Package-MinimalLambda -Name "data" -HandlerPath "data"
$adminZip = Package-MinimalLambda -Name "admin" -HandlerPath "admin"
$integrationZip = Package-MinimalLambda -Name "integration" -HandlerPath "integration"

Write-Host ""
Write-Host "Updating Lambda function code..."
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
Remove-Item -Path "layer" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================"
Write-Host "Lambda Layer created and attached successfully!"
Write-Host "========================================"
Write-Host ""
Write-Host "Layer ARN: $LAYER_ARN"
Write-Host "S3 Bucket: $S3_BUCKET"
Write-Host ""
Write-Host "All Lambda functions now use the shared layer."
Write-Host "Deployment packages are now much smaller and faster to update."

Set-Location ..\infrastructure
