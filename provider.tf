terraform {
  required_version = ">= 1.3"
  backend "s3" {
    bucket = "tf-state-owm"
    region = "us-east-1"
    dynamodb_table = "tf-state-locks-owm"
    key = "global/owmtfstate/terraform.tfstate"
    encrypt = true
  }
  
  
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "5.59.0"
    }
  }
}

provider "aws" {
  region = var.region
}
