provider "aws" {
  region = "us-east-1"
}

module "vpc" {
  source     = "../../modules/vpc"
  az_count   = 3
  cidr_block = "10.0.0.0/16"
}

module "broken" {
  source = "../../modules/broken"
}

data "aws_caller_identity" "current" {}
