variable "az_count" {
  description = "Number of AZs"
  default     = 3
}

variable "cidr_block" {
  description = "VPC CIDR"
  default     = "10.0.0.0/16"
}

resource "aws_vpc" "this" {
  cidr_block = var.cidr_block
}

resource "aws_subnet" "public" {
  count      = var.az_count
  vpc_id     = aws_vpc.this.id
  cidr_block = cidrsubnet(var.cidr_block, 8, count.index)
}

output "vpc_id" {
  value = aws_vpc.this.id
}
