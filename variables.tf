variable region {
  type        = string
  default     = "us-east-1"
  description = "AWS Deployment Region"
}

variable bucket_name {
  type        = string
  description = "State backup table"
}

variable table_name {
  type        = string
  description = "State locking table name"
}

variable owm_table_name {
  type        = string
  description = "dynamodb table for OWM"
}

variable vpcid {
  type        = string
  description = "VPC id"
}

variable subnet_ids {
  type        = list
  description = "subnet ids"
  default     = ["subnet-053a1d9fcb6712ef9", "subnet-0bef46b57d4fbd986", "subnet-0c35cffe4d7fb771c"] 
}

variable vpc_cidr {
  type        = string
  description = "vpc_cidr"
}

variable api_key {
  type        = string
  sensitive    = true
}

variable s3_prefix {
  type        = string
  description = "s3 managed prefix list"
}

variable dynamodb_prefix {
  type        = string
  description = "dynamodb prefix list"
}














