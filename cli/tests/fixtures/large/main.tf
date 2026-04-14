provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = { Name = "main-vpc", Environment = "production" }
}

resource "aws_vpc" "secondary" {
  cidr_block = "10.1.0.0/16"
  tags = { Name = "secondary-vpc", Environment = "staging" }
}

resource "aws_subnet" "public_1" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  tags = { Name = "public-1", Environment = "production" }
}

resource "aws_subnet" "public_2" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.2.0/24"
  tags = { Name = "public-2", Environment = "production" }
}

resource "aws_subnet" "private_1" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.3.0/24"
  tags = { Name = "private-1", Environment = "production" }
}

resource "aws_subnet" "private_2" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.4.0/24"
  tags = { Name = "private-2", Environment = "production" }
}

resource "aws_subnet" "staging_1" {
  vpc_id     = aws_vpc.secondary.id
  cidr_block = "10.1.1.0/24"
  tags = { Name = "staging-1", Environment = "staging" }
}

resource "aws_subnet" "staging_2" {
  vpc_id     = aws_vpc.secondary.id
  cidr_block = "10.1.2.0/24"
  tags = { Name = "staging-2", Environment = "staging" }
}

resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "web-sg", Environment = "production" }
}

resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
  tags = { Name = "app-sg", Environment = "production" }
}

resource "aws_security_group" "db" {
  name   = "db-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
  tags = { Name = "db-sg", Environment = "production" }
}

resource "aws_security_group" "staging" {
  name   = "staging-sg"
  vpc_id = aws_vpc.secondary.id
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "staging-sg", Environment = "staging" }
}

resource "aws_instance" "web_1" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  subnet_id     = aws_subnet.public_1.id
  tags = { Name = "web-1", Environment = "production" }
}

resource "aws_instance" "web_2" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  subnet_id     = aws_subnet.public_2.id
  tags = { Name = "web-2", Environment = "production" }
}

resource "aws_instance" "app_1" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.large"
  subnet_id     = aws_subnet.private_1.id
  tags = { Name = "app-1", Environment = "production" }
}

resource "aws_instance" "app_2" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.large"
  subnet_id     = aws_subnet.private_1.id
  tags = { Name = "app-2", Environment = "production" }
}

resource "aws_instance" "app_3" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.large"
  subnet_id     = aws_subnet.private_2.id
  tags = { Name = "app-3", Environment = "production" }
}

resource "aws_instance" "worker_1" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.xlarge"
  subnet_id     = aws_subnet.private_2.id
  tags = { Name = "worker-1", Environment = "production" }
}

resource "aws_instance" "worker_2" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.xlarge"
  subnet_id     = aws_subnet.private_1.id
  tags = { Name = "worker-2", Environment = "production" }
}

resource "aws_instance" "bastion" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.public_1.id
  tags = { Name = "bastion", Environment = "production" }
}

resource "aws_instance" "staging_1" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.small"
  subnet_id     = aws_subnet.staging_1.id
  tags = { Name = "staging-1", Environment = "staging" }
}

resource "aws_instance" "staging_2" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.small"
  subnet_id     = aws_subnet.staging_2.id
  tags = { Name = "staging-2", Environment = "staging" }
}

resource "aws_s3_bucket" "assets" {
  bucket = "prod-assets"
  tags = { Name = "prod-assets", Environment = "production" }
}

resource "aws_s3_bucket" "logs" {
  bucket = "prod-logs"
  tags = { Name = "prod-logs", Environment = "production" }
}

resource "aws_s3_bucket" "backups" {
  bucket = "prod-backups"
  tags = { Name = "prod-backups", Environment = "production" }
}

resource "aws_s3_bucket" "data_lake" {
  bucket = "data-lake"
  tags = { Name = "data-lake", Environment = "production" }
}

resource "aws_s3_bucket" "staging_bucket" {
  bucket = "staging-assets"
  tags = { Name = "staging-assets", Environment = "staging" }
}

resource "aws_db_instance" "primary" {
  identifier        = "primary-db"
  engine            = "postgres"
  instance_class    = "db.r5.large"
  allocated_storage = 100
  storage_encrypted = true
  tags = { Name = "primary-db", Environment = "production" }
}

resource "aws_db_instance" "replica" {
  identifier        = "replica-db"
  engine            = "postgres"
  instance_class    = "db.r5.large"
  allocated_storage = 100
  storage_encrypted = true
  tags = { Name = "replica-db", Environment = "production" }
}

resource "aws_db_instance" "staging_db" {
  identifier        = "staging-db"
  engine            = "postgres"
  instance_class    = "db.t3.medium"
  allocated_storage = 20
  tags = { Name = "staging-db", Environment = "staging" }
}

resource "aws_iam_role" "app_role" {
  name               = "app-role"
  assume_role_policy = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Action\":\"sts:AssumeRole\",\"Principal\":{\"Service\":\"ec2.amazonaws.com\"},\"Effect\":\"Allow\"}]}"
  tags = { Name = "app-role", Environment = "production" }
}

resource "aws_iam_role" "lambda_role" {
  name               = "lambda-role"
  assume_role_policy = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Action\":\"sts:AssumeRole\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Effect\":\"Allow\"}]}"
  tags = { Name = "lambda-role", Environment = "production" }
}

resource "aws_iam_policy" "app_policy" {
  name   = "app-policy"
  policy = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\"],\"Resource\":\"arn:aws:s3:::prod-assets/*\"}]}"
  tags = { Name = "app-policy", Environment = "production" }
}

resource "aws_lambda_function" "api_handler" {
  function_name = "api-handler"
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  role          = aws_iam_role.lambda_role.arn
  filename      = "lambda.zip"
  tags = { Name = "api-handler", Environment = "production" }
}

resource "aws_lambda_function" "event_processor" {
  function_name = "event-processor"
  handler       = "handler.main"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_role.arn
  filename      = "processor.zip"
  tags = { Name = "event-processor", Environment = "production" }
}

resource "aws_lambda_function" "cron_job" {
  function_name = "cron-job"
  handler       = "cron.handler"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_role.arn
  filename      = "cron.zip"
  tags = { Name = "cron-job", Environment = "production" }
}

resource "aws_alb" "main" {
  name               = "main-alb"
  internal           = false
  load_balancer_type = "application"
  tags = { Name = "main-alb", Environment = "production" }
}

resource "aws_alb" "internal" {
  name               = "internal-alb"
  internal           = true
  load_balancer_type = "application"
  tags = { Name = "internal-alb", Environment = "production" }
}

resource "aws_kms_key" "main" {
  description         = "Main encryption key"
  enable_key_rotation = true
  tags = { Name = "main-kms", Environment = "production" }
}

resource "aws_kms_key" "data" {
  description         = "Data encryption key"
  enable_key_rotation = true
  tags = { Name = "data-kms", Environment = "production" }
}

resource "aws_dynamodb_table" "sessions" {
  name         = "sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  attribute {
    name = "session_id"
    type = "S"
  }
  tags = { Name = "sessions", Environment = "production" }
}

resource "aws_dynamodb_table" "events" {
  name         = "events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"
  attribute {
    name = "event_id"
    type = "S"
  }
  tags = { Name = "events", Environment = "production" }
}

resource "aws_dynamodb_table" "cache" {
  name         = "cache"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cache_key"
  attribute {
    name = "cache_key"
    type = "S"
  }
  tags = { Name = "cache", Environment = "production" }
}

resource "aws_cloudfront_distribution" "cdn" {
  enabled = true

  origin {
    domain_name = "prod-assets.s3.amazonaws.com"
    origin_id   = "s3-assets"
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-assets"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = { Name = "cdn", Environment = "production" }
}

resource "aws_instance" "monitor" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  subnet_id     = aws_subnet.private_1.id
  tags = { Name = "monitor", Environment = "production" }
}

resource "aws_instance" "ci_runner" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.xlarge"
  subnet_id     = aws_subnet.private_2.id
  tags = { Name = "ci-runner", Environment = "production" }
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "terraform-state"
  tags = { Name = "terraform-state", Environment = "production" }
}

resource "aws_iam_role" "ci_role" {
  name               = "ci-role"
  assume_role_policy = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Action\":\"sts:AssumeRole\",\"Principal\":{\"Service\":\"ec2.amazonaws.com\"},\"Effect\":\"Allow\"}]}"
  tags = { Name = "ci-role", Environment = "production" }
}

resource "aws_subnet" "db_1" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.5.0/24"
  tags = { Name = "db-1", Environment = "production" }
}

resource "aws_subnet" "db_2" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.6.0/24"
  tags = { Name = "db-2", Environment = "production" }
}
