terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "enterprise-ai-review-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda to write to DynamoDB and CloudWatch
resource "aws_iam_role_policy" "lambda_policy" {
  name = "enterprise-ai-review-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.reviews_table.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# DynamoDB Table for storing reviews
resource "aws_dynamodb_table" "reviews_table" {
  name           = "enterprise-ai-reviews"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "review_id"
  
  attribute {
    name = "review_id"
    type = "S"
  }

  ttl {
    attribute_name = "expiration"
    enabled        = true
  }

  tags = {
    Name        = "enterprise-ai-reviews"
    Environment = "production"
  }
}

# Lambda Layer for dependencies
resource "aws_lambda_layer_version" "dependencies" {
  filename   = "lambda_layer.zip"
  layer_name = "enterprise-ai-dependencies"

  source_code_hash = filebase64sha256("lambda_layer.zip")

  compatible_runtimes = ["python3.11"]
}

# Lambda Function
resource "aws_lambda_function" "review_agent" {
  filename      = "lambda_function.zip"
  function_name = "enterprise-ai-review-agent"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      OPENAI_API_KEY = var.openai_api_key
      DYNAMODB_TABLE = aws_dynamodb_table.reviews_table.name
    }
  }

  source_code_hash = filebase64sha256("lambda_function.zip")

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_lambda_layer_version.dependencies
  ]
}

# API Gateway
resource "aws_apigatewayv2_api" "review_api" {
  name          = "enterprise-ai-review-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET"]
    allow_headers = ["*"]
  }
}

# API Gateway Integration
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.review_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.review_agent.invoke_arn

  payload_format_version = "2.0"
}

# API Gateway Route
resource "aws_apigatewayv2_route" "review_route" {
  api_id    = aws_apigatewayv2_api.review_api.id
  route_key = "POST /review"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "production" {
  api_id      = aws_apigatewayv2_api.review_api.id
  name        = "prod"
  auto_deploy = true

  depends_on = [aws_apigatewayv2_route.review_route]
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.review_agent.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.review_api.execution_arn}/*/*"
}
