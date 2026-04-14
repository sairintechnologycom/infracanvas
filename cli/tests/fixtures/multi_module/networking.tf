resource "aws_vpc" "prod" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name        = "prod-vpc"
    Environment = "production"
  }
}

resource "aws_subnet" "app" {
  vpc_id     = aws_vpc.prod.id
  cidr_block = "10.0.10.0/24"

  tags = {
    Name        = "app-subnet"
    Environment = "production"
  }
}

variable "environment" {
  description = "Deployment environment"
  default     = "production"
}

output "vpc_id" {
  value = aws_vpc.prod.id
}
