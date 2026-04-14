# InfraCanvas Demo Infrastructure
# A realistic 15-resource AWS project for screenshots and demos

# --- Networking ---

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "demo-vpc"
    Environment = "production"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "demo-public-subnet"
    Tier = "public"
  }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "demo-private-subnet"
    Tier = "private"
  }
}

# --- Load Balancer ---

resource "aws_alb" "web" {
  name               = "demo-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = [aws_subnet.public.id]
  security_groups    = [aws_security_group.alb.id]

  tags = {
    Name = "demo-alb"
  }
}

# --- Security Groups ---

resource "aws_security_group" "alb" {
  name        = "demo-alb-sg"
  description = "Allow HTTP/HTTPS inbound"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "demo-alb-sg"
  }
}

resource "aws_security_group" "app" {
  name        = "demo-app-sg"
  description = "Allow traffic from ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "demo-app-sg"
  }
}

# --- Compute ---

resource "aws_instance" "app_1" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.medium"
  subnet_id              = aws_subnet.private.id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  root_block_device {
    encrypted   = true
    volume_size = 50
    volume_type = "gp3"
  }

  tags = {
    Name = "demo-app-1"
  }
}

resource "aws_instance" "app_2" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.medium"
  subnet_id              = aws_subnet.private.id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  root_block_device {
    encrypted   = true
    volume_size = 50
    volume_type = "gp3"
  }

  tags = {
    Name = "demo-app-2"
  }
}

# --- Database ---

resource "aws_db_instance" "main" {
  identifier              = "demo-postgres"
  engine                  = "postgres"
  engine_version          = "15.4"
  instance_class          = "db.t3.medium"
  allocated_storage       = 100
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.db.arn
  publicly_accessible     = false
  vpc_security_group_ids  = [aws_security_group.app.id]
  db_subnet_group_name    = "demo-db-subnet-group"
  backup_retention_period = 7

  tags = {
    Name = "demo-postgres"
  }
}

# --- Storage ---

resource "aws_s3_bucket" "assets" {
  bucket = "demo-app-assets-2024"

  tags = {
    Name = "demo-assets"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.db.arn
    }
  }
}

# --- Encryption ---

resource "aws_kms_key" "db" {
  description             = "KMS key for database and S3 encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "demo-encryption-key"
  }
}

# --- IAM ---

resource "aws_iam_role" "app" {
  name = "demo-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "demo-app-role"
  }
}

resource "aws_iam_instance_profile" "app" {
  name = "demo-app-profile"
  role = aws_iam_role.app.name
}

# --- Lambda (no VPC — regional service) ---

resource "aws_lambda_function" "processor" {
  function_name = "demo-event-processor"
  runtime       = "python3.12"
  handler       = "handler.main"
  role          = aws_iam_role.app.arn
  filename      = "lambda.zip"
  memory_size   = 256
  timeout       = 30

  tags = {
    Name = "demo-processor"
  }
}

# --- Monitoring ---

resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/ec2/demo-app"
  retention_in_days = 30

  tags = {
    Name = "demo-app-logs"
  }
}
