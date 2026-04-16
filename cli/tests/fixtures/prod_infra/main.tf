provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "prod" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name        = "vpc-prod"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.prod.id
  tags = {
    Name        = "main-igw"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_subnet" "public_1a" {
  vpc_id                  = aws_vpc.prod.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
  tags = {
    Name        = "public-1a"
    Tier        = "public"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_subnet" "private_1a" {
  vpc_id            = aws_vpc.prod.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1a"
  tags = {
    Name        = "private-1a"
    Tier        = "private"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_eip" "nat" {
  tags = {
    Name        = "nat-eip"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_nat_gateway" "az1" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_1a.id
  tags = {
    Name        = "az1"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_lb" "main" {
  name               = "main"
  internal           = false
  load_balancer_type = "application"
  subnets            = [aws_subnet.public_1a.id]
  tags = {
    Name        = "main"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_security_group" "web_sg" {
  name        = "web-sg"
  description = "Web tier security group"
  vpc_id      = aws_vpc.prod.id

  ingress {
    from_port   = 0
    to_port     = 65535
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
    Name        = "web-sg"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_instance" "web_1" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  subnet_id     = aws_subnet.private_1a.id

  vpc_security_group_ids = [aws_security_group.web_sg.id]

  root_block_device {
    encrypted = true
  }

  tags = {
    Name        = "web-1"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_instance" "web_2" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  subnet_id     = aws_subnet.private_1a.id

  vpc_security_group_ids = [aws_security_group.web_sg.id]

  root_block_device {
    encrypted = true
  }

  tags = {
    Name = "web-2"
  }
}

resource "aws_iam_role" "web_role" {
  name = "web-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  tags = {
    Name        = "web-role"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

resource "aws_s3_bucket" "app_data" {
  bucket = "app-data-bucket"
  tags = {
    Name        = "app-data"
    Environment = "prod"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}
