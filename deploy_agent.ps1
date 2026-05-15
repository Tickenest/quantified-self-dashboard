# deploy_agent.ps1
# Zips and deploys the agent Lambda function

param(
    [string]$Environment = "demo"
)

$PROFILE = "quantified-self-dashboard-dev"
$REGION = "us-east-1"
$FUNCTION_NAME = "qsd-$Environment-agent"
$ZIP_FILE = "agent.zip"
$SOURCE_FILE = "./backend/agent/lambda_agent.py"

Write-Host "Deploying agent Lambda for environment: $Environment" -ForegroundColor Cyan

# Zip the Lambda file
Write-Host "Zipping Lambda function..." -ForegroundColor Yellow
if (Test-Path $ZIP_FILE) { Remove-Item $ZIP_FILE }
Compress-Archive -Path $SOURCE_FILE -DestinationPath $ZIP_FILE
if ($LASTEXITCODE -ne 0) { Write-Host "Zip failed" -ForegroundColor Red; exit 1 }

# Update Lambda
Write-Host "Updating Lambda function..." -ForegroundColor Yellow
aws lambda update-function-code `
    --function-name $FUNCTION_NAME `
    --zip-file "fileb://$ZIP_FILE" `
    --region $REGION `
    --profile $PROFILE | Out-Null

aws lambda wait function-updated `
    --function-name $FUNCTION_NAME `
    --region $REGION `
    --profile $PROFILE

# Clean up zip
Remove-Item $ZIP_FILE

Write-Host "Agent Lambda deployed successfully." -ForegroundColor Green
