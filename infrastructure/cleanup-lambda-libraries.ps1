# PowerShell script to clean up Python libraries from Lambda folders
$ErrorActionPreference = "Stop"

Write-Host "Cleaning up Python libraries from Lambda folders..."
Write-Host ""

# Navigate to lambda directory
Set-Location ..\lambda

# List of Lambda function directories
$lambdaDirs = @("auth", "process", "data", "admin", "integration")

# List of files/folders to keep (handler and shared files)
$keepFiles = @("handler.py", "test_*.py", "__init__.py")

foreach ($dir in $lambdaDirs) {
    Write-Host "Cleaning $dir folder..."
    
    if (Test-Path $dir) {
        # Get all items in the directory
        $items = Get-ChildItem -Path $dir -Force
        
        foreach ($item in $items) {
            $shouldKeep = $false
            
            # Check if it's a file we want to keep
            foreach ($keepPattern in $keepFiles) {
                if ($item.Name -like $keepPattern) {
                    $shouldKeep = $true
                    break
                }
            }
            
            # Delete if not in keep list
            if (-not $shouldKeep) {
                Write-Host "  Removing: $($item.Name)"
                Remove-Item -Path $item.FullName -Recurse -Force
            }
        }
    }
    
    Write-Host "$dir cleaned"
    Write-Host ""
}

# Clean up root lambda directory (keep only essential files and folders)
Write-Host "Cleaning root lambda directory..."

$rootKeepDirs = @("auth", "process", "data", "admin", "integration", "shared", "authorizer")
$rootKeepFiles = @("requirements.txt", "requirements-runtime.txt", "README.md")

$rootItems = Get-ChildItem -Path . -Force | Where-Object { $_.Name -notlike ".*" }

foreach ($item in $rootItems) {
    $shouldKeep = $false
    
    # Check if it's a directory we want to keep
    if ($item.PSIsContainer) {
        if ($rootKeepDirs -contains $item.Name) {
            $shouldKeep = $true
        }
    } else {
        # Check if it's a file we want to keep
        if ($rootKeepFiles -contains $item.Name) {
            $shouldKeep = $true
        }
    }
    
    # Delete if not in keep list
    if (-not $shouldKeep) {
        Write-Host "  Removing: $($item.Name)"
        Remove-Item -Path $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "Cleanup completed successfully!"
Write-Host "========================================"
Write-Host ""
Write-Host "All Python libraries have been removed from Lambda folders."
Write-Host "Only handler code and test files remain."
Write-Host "Dependencies are now provided by the Lambda layer."

Set-Location ..\infrastructure
