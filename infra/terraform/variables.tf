variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "artifact_bucket_name" {
  type = string
}

variable "allowed_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

variable "instance_type" {
  type    = string
  default = "t3.large"
}

variable "ami_id" {
  type = string
}

variable "repo_url" {
  type = string
}

