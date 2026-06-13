output "instance_public_ip" {
  value = aws_instance.platform.public_ip
}

output "artifact_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}

