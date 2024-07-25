/*Create IAM Role for lambda. Lambda has read/write permissions to dynamodb and read only access to SSM.
Role also has VPC access for Lambda Execution which has permissions for logging and monitoring of lambda function */
resource "aws_iam_role" "owmlambdarole" {
  name = "owm_lambda_role"
  managed_policy_arns = ["arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess", 
                         "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"]
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
  inline_policy {
    name = "owm_lambda_policy"

    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Sid      = "KmsSsm"
          Action   = ["kms:Decrypt"]
          Effect   = "Allow"
          Resource = [aws_kms_key.ssm-kms.arn]
        },
        {
          Sid      = "KmsDynamodb"
          Action   = ["kms:Decrypt", "kms:Encrypt"]
          Effect   = "Allow"
          Resource = [aws_kms_key.dynamodb-kms.arn]
        },
        {
          Sid      = "DynamodbAccess"
          Action   = ["dynamodb:BatchGetItem",
                      "dynamodb:BatchWriteItem",
                      "dynamodb:ConditionCheckItem",
                      "dynamodb:PutItem",
                      "dynamodb:DescribeTable",
                      "dynamodb:DeleteItem",
                      "dynamodb:GetItem",
                      "dynamodb:Scan",
                      "dynamodb:Query",
                      "dynamodb:UpdateItem"]
          Effect   = "Allow"
          Resource = [aws_dynamodb_table.owm_table.arn]
        }
      ]
    })
  }
}

# Create OpenWeatherMap Dynamodb table and encrypt the table with Customer Managed KMS Key.
resource "aws_dynamodb_table" "owm_table" {
  name         = var.owm_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "TimeId"
  deletion_protection_enabled = true
  server_side_encryption {
    enabled = true
    kms_key_arn = aws_kms_key.dynamodb-kms.arn
  }  

  attribute {
    name = "TimeId"
    type = "S"
  }
}

# Create HTTP type API Gateway
resource "aws_apigatewayv2_api" "weatherapigateway" {
  name          = "nycweatherapigateway"
  protocol_type = "HTTP"
}

# Create api gateway stage and enable api gateway logging
resource "aws_apigatewayv2_stage" "test" {
  api_id = aws_apigatewayv2_api.weatherapigateway.id
  name        = "test"
  auto_deploy = true
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.nycweatherapi.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      }
    )
  }
}

# Create api gateway integration that points to OpenWeatherMap Lambda.
resource "aws_apigatewayv2_integration" "api_gw_integration" {
  api_id                    = aws_apigatewayv2_api.weatherapigateway.id
  integration_type          = "AWS_PROXY"
  description               = "nyc weather integration"
  integration_method        = "POST"
  integration_uri           = aws_lambda_function.owm_lambda_func.invoke_arn
  payload_format_version    = "2.0"
}

# Create api gateway route for HTTP GET
resource "aws_apigatewayv2_route" "api_gw_route" {
  api_id    = aws_apigatewayv2_api.weatherapigateway.id
  route_key = "GET /getWeatherNyc"
  target = "integrations/${aws_apigatewayv2_integration.api_gw_integration.id}"
}

# Create api gateway log group.
resource "aws_cloudwatch_log_group" "nycweatherapi" {
  name = "/aws/apigateway/${aws_apigatewayv2_api.weatherapigateway.name}"
}

# Grant API Gateway access to invoke OpenWeatherMap lambda function
resource "aws_lambda_permission" "lambda_permission" {
  statement_id  = "APIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.owm_lambda_func.function_name
  principal     = "apigateway.amazonaws.com"

  # The /* part allows invocation from any stage, method and resource path
  # within API Gateway.
  source_arn = "${aws_apigatewayv2_api.weatherapigateway.execution_arn}/*"
}

# Create OpenWeatherMap lambda that is VPC bound. 
resource "aws_lambda_function" "owm_lambda_func" {
filename      = "${path.module}/src/owmLambda.zip"
function_name = "owmLambda"
role          = aws_iam_role.owmlambdarole.arn
handler       = "owmLambda.lambda_handler"
runtime       = "python3.12"
timeout       = 300
vpc_config {
    security_group_ids = [aws_security_group.owm-lambda-sg.id]
    subnet_ids = [var.subnet_ids[0], var.subnet_ids[1], var.subnet_ids[2]]
}
environment {
    variables = {
        dynamodb_table_name = aws_dynamodb_table.owm_table.name
        region              = var.region
    }
}
}

# Create security group for OpenWeatherMap Lambda
resource "aws_security_group" "owm-lambda-sg" {
 name        = "owm-lambda-sg"
 description = "Allow HTTPS to internet"
 vpc_id      = var.vpcid

egress {
   from_port   = 443
   to_port     = 443
   protocol    = "tcp"
   cidr_blocks = ["0.0.0.0/0"]
 }

 egress {
   from_port   = 443
   to_port     = 443
   protocol    = "tcp"
   prefix_list_ids = [var.s3_prefix, var.dynamodb_prefix]
 }
}

