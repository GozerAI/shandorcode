# ShandorCode Reorganization Script
Write-Host "Reorganizing ShandorCode project structure..." -ForegroundColor Cyan

# Create directories
$dirs = @("src\core", "src\parsers", "src\api", "src\analyzers", "src\utils", "src\visualization", "docs", "examples", "tests")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created: $dir"
    }
}

# Move core files
if (Test-Path "analyzer.py") { Move-Item "analyzer.py" "src\core\" -Force }
if (Test-Path "models.py") { Move-Item "models.py" "src\core\" -Force }
if (Test-Path "watcher.py") { Move-Item "watcher.py" "src\core\" -Force }

# Move parser files
if (Test-Path "python_parser.py") { Move-Item "python_parser.py" "src\parsers\" -Force }
if (Test-Path "javascript_parser.py") { Move-Item "javascript_parser.py" "src\parsers\" -Force }

# Move API files
if (Test-Path "server.py") { Move-Item "server.py" "src\api\" -Force }

# Move docs
if (Test-Path "architecture.md") { Move-Item "architecture.md" "docs\" -Force }
if (Test-Path "usage.md") { Move-Item "usage.md" "docs\" -Force }

# Move examples
if (Test-Path "analyze_gozerai_project.py") { Move-Item "analyze_gozerai_project.py" "examples\" -Force }

# Move tests
if (Test-Path "test_shandorcode.py") { Move-Item "test_shandorcode.py" "tests\" -Force }
if (Test-Path "test_codegraph.py") { Move-Item "test_codegraph.py" "tests\" -Force }

# Create init files
"src", "src\core", "src\parsers", "src\api", "src\analyzers", "src\utils", "src\visualization", "tests" | ForEach-Object {
    $init = Join-Path $_ "__init__.py"
    if (-not (Test-Path $init)) {
        "" | Out-File -FilePath $init -Encoding UTF8
    }
}

# Clean up
Get-ChildItem -Recurse -Include "*.pyc", "__pycache__" | Remove-Item -Recurse -Force
if (Test-Path "mnt") { Remove-Item "mnt" -Recurse -Force }
if (Test-Path "__init__.py") { Remove-Item "__init__.py" -Force }

Write-Host "Done! Run: pip install -e .[dev]" -ForegroundColor Green
