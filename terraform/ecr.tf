# ---------------------------------------------------------------------------
# ECR repositories for Lambdas with heavy dependencies
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "refresh" {
  name                 = "${local.prefix}-refresh"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "query" {
  name                 = "${local.prefix}-query"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# Lifecycle policies — keep only the last 3 images to save storage
resource "aws_ecr_lifecycle_policy" "refresh" {
  repository = aws_ecr_repository.refresh.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 3 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "query" {
  repository = aws_ecr_repository.query.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 3 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}
