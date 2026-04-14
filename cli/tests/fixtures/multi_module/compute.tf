resource "aws_instance" "app" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.large"
  subnet_id     = aws_subnet.app.id

  depends_on = [aws_vpc.prod]

  tags = {
    Name        = "app-server"
    Environment = "production"
  }
}

resource "aws_lambda_function" "processor" {
  function_name = "data-processor"
  handler       = "index.handler"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_role.arn
  filename      = "lambda.zip"

  tags = {
    Name        = "data-processor"
    Environment = "production"
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda-execution-role"

  assume_role_policy = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Action\":\"sts:AssumeRole\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Effect\":\"Allow\"}]}"

  tags = {
    Name        = "lambda-role"
    Environment = "production"
  }
}

resource "aws_dynamodb_table" "events" {
  name         = "events-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = "events-table"
    Environment = "production"
  }
}
