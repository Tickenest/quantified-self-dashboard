# deploy_query.ps1
# Builds and deploys the query Lambda container image to ECR

param(
    [string]$Environment = "demo"
)

$PROFILE = "quantified-self-dashboard-dev"
$REGION = "us-east-1"
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text --profile $PROFILE)
$FUNCTION_NAME = "qsd-$Environment-query"
$ECR_REPO = "qsd-$Environment-query"
$ECR_REGISTRY = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
$ECR_URI = "$ECR_REGISTRY/$ECR_REPO"
$IMAGE_TAG = "latest"

Write-Host "Deploying query Lambda for environment: $Environment" -ForegroundColor Cyan

# Docker build
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker build --platform linux/amd64 --provenance=false -t "$ECR_REPO`:$IMAGE_TAG" ./backend/query
if ($LASTEXITCODE -ne 0) { Write-Host "Docker build failed" -ForegroundColor Red; exit 1 }

# ECR login
Write-Host "Logging in to ECR..." -ForegroundColor Yellow
$ECR_PASSWORD = aws ecr get-login-password --region $REGION --profile $PROFILE
docker login --username AWS --password $ECR_PASSWORD $ECR_REGISTRY
if ($LASTEXITCODE -ne 0) { Write-Host "ECR login failed" -ForegroundColor Red; exit 1 }

# Tag and push
Write-Host "Tagging and pushing image..." -ForegroundColor Yellow
docker tag "$ECR_REPO`:$IMAGE_TAG" "$ECR_URI`:$IMAGE_TAG"
docker push "$ECR_URI`:$IMAGE_TAG"
if ($LASTEXITCODE -ne 0) { Write-Host "Docker push failed" -ForegroundColor Red; exit 1 }

# Update Lambda
Write-Host "Updating Lambda function..." -ForegroundColor Yellow
aws lambda update-function-code `
    --function-name $FUNCTION_NAME `
    --image-uri "$ECR_URI`:$IMAGE_TAG" `
    --region $REGION `
    --profile $PROFILE | Out-Null

aws lambda wait function-updated `
    --function-name $FUNCTION_NAME `
    --region $REGION `
    --profile $PROFILE

Write-Host "Query Lambda deployed successfully." -ForegroundColor Green
