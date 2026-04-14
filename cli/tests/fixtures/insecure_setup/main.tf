provider "aws" {
  region = "us-west-2"
}

resource "aws_s3_bucket" "public_data" {
  bucket = "my-public-data-bucket"
  acl    = "public-read"
}

resource "aws_s3_bucket" "logs" {
  bucket = "my-log-bucket"
}

resource "aws_security_group" "open_sg" {
  name = "open-sg"

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "exposed_db" {
  identifier           = "exposed-db"
  engine               = "mysql"
  instance_class       = "db.t3.medium"
  allocated_storage    = 20
  publicly_accessible  = true
}

resource "aws_instance" "untagged_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
}

resource "aws_kms_key" "no_rotation" {
  description = "KMS key without rotation"
}

resource "aws_iam_policy" "admin_policy" {
  name   = "admin-policy"
  policy = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"*\",\"Resource\":\"*\"}]}"
}
