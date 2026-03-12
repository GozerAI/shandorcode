# ShandorCode Hostinger Deployment - Windows Helper Script
# Run this from Windows PowerShell

$VPS_IP = "72.61.76.32"
$VPS_USER = "root"
$DOMAIN = "shandor.gozerai.com"

Write-Host "ShandorCode - Hostinger VPS Deployment Helper" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "VPS IP: $VPS_IP" -ForegroundColor Yellow
Write-Host "Domain: $DOMAIN" -ForegroundColor Yellow
Write-Host ""

function Show-Menu {
    Write-Host "What would you like to do?" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Test SSH connection"
    Write-Host "2. Upload setup script"
    Write-Host "3. Upload ShandorCode files"
    Write-Host "4. SSH to VPS"
    Write-Host "5. Check deployment status"
    Write-Host "6. View logs"
    Write-Host "7. Test DNS resolution"
    Write-Host "8. Full deployment (all steps)"
    Write-Host "0. Exit"
    Write-Host ""
}

function Test-SSH {
    Write-Host "Testing SSH connection..." -ForegroundColor Cyan
    ssh -o ConnectTimeout=5 ${VPS_USER}@${VPS_IP} "echo 'SSH connection successful!'"
}

function Upload-SetupScript {
    Write-Host "Uploading setup script..." -ForegroundColor Cyan
    scp .\hostinger-setup.sh ${VPS_USER}@${VPS_IP}:/tmp/setup.sh
    Write-Host "Upload complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Now run on VPS:" -ForegroundColor Yellow
    Write-Host "  ssh root@$VPS_IP" -ForegroundColor White
    Write-Host "  chmod +x /tmp/setup.sh" -ForegroundColor White
    Write-Host "  /tmp/setup.sh" -ForegroundColor White
}

function Upload-Files {
    Write-Host "Creating archive..." -ForegroundColor Cyan
    
    # Create archive (requires tar on Windows)
    if (Get-Command tar -ErrorAction SilentlyContinue) {
        tar -czf shandorcode.tar.gz ../src ../deployment ../pyproject.toml ../LICENSE.txt ../README.md
        Write-Host "Archive created" -ForegroundColor Green
        
        Write-Host "Uploading to VPS..." -ForegroundColor Cyan
        scp shandorcode.tar.gz ${VPS_USER}@${VPS_IP}:/opt/shandorcode/
        
        Write-Host "Upload complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Now extract on VPS:" -ForegroundColor Yellow
        Write-Host "  ssh root@$VPS_IP" -ForegroundColor White
        Write-Host "  cd /opt/shandorcode" -ForegroundColor White
        Write-Host "  tar -xzf shandorcode.tar.gz" -ForegroundColor White
        
        # Cleanup
        Remove-Item shandorcode.tar.gz
    } else {
        Write-Host "tar command not found. Using individual file upload..." -ForegroundColor Red
        Write-Host "Uploading files..." -ForegroundColor Cyan
        scp -r ..\src ..\deployment ..\pyproject.toml ..\LICENSE.txt ..\README.md ${VPS_USER}@${VPS_IP}:/opt/shandorcode/
        Write-Host "Upload complete!" -ForegroundColor Green
    }
}

function Connect-VPS {
    Write-Host "Connecting to VPS..." -ForegroundColor Cyan
    ssh ${VPS_USER}@${VPS_IP}
}

function Check-Status {
    Write-Host "Checking deployment status..." -ForegroundColor Cyan
    ssh ${VPS_USER}@${VPS_IP} "cd /opt/shandorcode/deployment; docker-compose ps"
}

function View-Logs {
    Write-Host "Viewing logs (Ctrl+C to exit)..." -ForegroundColor Cyan
    ssh ${VPS_USER}@${VPS_IP} "cd /opt/shandorcode/deployment; docker-compose logs -f shandorcode"
}

function Test-DNS {
    Write-Host "Testing DNS resolution..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Resolving $DOMAIN..." -ForegroundColor Yellow
    nslookup $DOMAIN
    Write-Host ""
    Write-Host "Expected IP: $VPS_IP" -ForegroundColor Yellow
}

function Full-Deployment {
    Write-Host "Starting full deployment..." -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Step 1: Testing SSH..." -ForegroundColor Yellow
    Test-SSH
    Write-Host ""
    
    Write-Host "Step 2: Uploading setup script..." -ForegroundColor Yellow
    Upload-SetupScript
    Write-Host ""
    
    Write-Host "Please run the setup script on VPS first!" -ForegroundColor Red
    Write-Host "Then come back and select option 3 to upload ShandorCode files." -ForegroundColor Yellow
}

# Main loop
do {
    Show-Menu
    $choice = Read-Host "Enter your choice (0-8)"
    Write-Host ""
    
    switch ($choice) {
        "1" { Test-SSH }
        "2" { Upload-SetupScript }
        "3" { Upload-Files }
        "4" { Connect-VPS }
        "5" { Check-Status }
        "6" { View-Logs }
        "7" { Test-DNS }
        "8" { Full-Deployment }
        "0" { 
            Write-Host "Goodbye!" -ForegroundColor Green
            exit 
        }
        default { Write-Host "Invalid choice. Please try again." -ForegroundColor Red }
    }
    
    Write-Host ""
    Write-Host "Press any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Clear-Host
    
} while ($choice -ne "0")
