
provider "aws" {
  region = "ap-south-1"
}

terraform {
  required_version = ">= 1.0"
}

variable "instance_type" {
  description = "EC2 instance type for the application"
  type        = string
  default     = "t3.micro"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

resource "aws_instance" "app" {
  ami           = "ami-0123456789abcdef0"
  instance_type = var.instance_type

  tags = {
    Name        = "costsentinel-app"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

output "instance_type" {
  value = aws_instance.app.instance_type
}
