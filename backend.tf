data "aws_caller_identity" "current" {}

resource "aws_security_group" "vpcendpoints-sg" {
 name        = "vpcendpoints-sg"
 description = "Allow HTTPS to vpc cidr"
 vpc_id      = var.vpcid

ingress {
   from_port   = 443
   to_port     = 443
   protocol    = "tcp"
   cidr_blocks = [var.vpc_cidr]
 }
}

resource "aws_vpc_endpoint" "ssm" {
  vpc_id       = var.vpcid
  service_name = "com.amazonaws.${var.region}.ssm"
  security_group_ids = [
    aws_security_group.vpcendpoints-sg.id,
  ]
  vpc_endpoint_type = "Interface"
  private_dns_enabled = true
  subnet_ids = [var.subnet_ids[0], var.subnet_ids[1], var.subnet_ids[2]]
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = var.vpcid
  service_name = "com.amazonaws.${var.region}.dynamodb"
}


resource "aws_kms_key" "ssm-kms" {
  description             = "kms key for ssm"
  enable_key_rotation     = true
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "ssm-kms-policy"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_key" "dynamodb-kms" {
  description             = "kms key for dynamodb"
  enable_key_rotation     = true
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "dynamodb-kms-policy"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_key" "s3-kms" {
  description             = "kms key for s3"
  enable_key_rotation     = true
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "s3-kms-policy"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
}

resource "aws_s3_bucket" "state_bucket" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_public_access_block" "state_bucket_access" {
  bucket = aws_s3_bucket.state_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "state_bucket_versioning" {
  bucket = aws_s3_bucket.state_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state_bucket_encryption" {
  bucket = aws_s3_bucket.state_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3-kms.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  deletion_protection_enabled = true
  server_side_encryption {
    enabled = true
    kms_key_arn = aws_kms_key.dynamodb-kms.arn
  }  

  attribute {
    name = "LockID"
    type = "S"
  }
}

resource "aws_ssm_parameter" "owmapikey" {
  name  = "/owm/owmapikey"
  type  = "SecureString"
  value = var.api_key
  key_id = aws_kms_key.ssm-kms.arn
}

