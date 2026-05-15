# deploy_frontend.ps1
# Builds and deploys the React frontend to S3

param(
    [string]$Environment = "demo"
)

$PROFILE = "quantified-self-dashboard-dev"
$REGION = "us-east-1"
$BUCKET_NAME = "qsd-$Environment-frontend"

Write-Host "Deploying frontend for environment: $Environment" -ForegroundColor Cyan

# Build React app
Write-Host "Building React app..." -ForegroundColor Yellow
Set-Location ./frontend
if ($Environment -eq "personal") {
    npm run build:personal
} else {
    npm run build:demo
}
if ($LASTEXITCODE -ne 0) { Write-Host "React build failed" -ForegroundColor Red; Set-Location ..; exit 1 }
Set-Location ..

# Sync to S3
Write-Host "Syncing to S3..." -ForegroundColor Yellow
aws s3 sync ./frontend/build "s3://$BUCKET_NAME" `
    --delete `
    --region $REGION `
    --profile $PROFILE

if ($LASTEXITCODE -ne 0) { Write-Host "S3 sync failed" -ForegroundColor Red; exit 1 }

# Get website URL
$WEBSITE_URL = "http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
Write-Host "Frontend deployed successfully." -ForegroundColor Green
Write-Host "URL: $WEBSITE_URL" -ForegroundColor Cyan
