resource "aws_vpc" "empty" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_s3_bucket" "minimal" {
  bucket = "minimal-bucket"
}
