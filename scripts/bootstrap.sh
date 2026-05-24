#!/usr/bin/env bash
# bootstrap.sh — One-time AWS setup before first terraform apply
# Run: bash scripts/bootstrap.sh
set -euo pipefail

echo "🚀 URL Shortener — AWS Bootstrap"
echo "=================================="

# ── Config ────────────────────────────────────────────────────────────────────
REGION="${AWS_REGION:-us-east-1}"
BUCKET_NAME="urlshortener-tfstate-$(aws sts get-caller-identity --query Account --output text)"
LOCK_TABLE="terraform-locks"

echo ""
echo "→ Region:       $REGION"
echo "→ State bucket: $BUCKET_NAME"
echo "→ Lock table:   $LOCK_TABLE"
echo ""

# ── 1. Create S3 bucket for Terraform state ───────────────────────────────────
echo "1/4  Creating S3 state bucket..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
  echo "     ✓ Bucket already exists"
else
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION"
  fi
  echo "     ✓ Bucket created: $BUCKET_NAME"
fi

aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
echo "     ✓ Versioning + encryption enabled"

# ── 2. Create DynamoDB table for state locking ────────────────────────────────
echo "2/4  Creating DynamoDB lock table..."
if aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$REGION" 2>/dev/null; then
  echo "     ✓ Lock table already exists"
else
  aws dynamodb create-table \
    --table-name "$LOCK_TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION"
  echo "     ✓ Lock table created"
fi

# ── 3. Update Terraform backend config ───────────────────────────────────────
echo "3/4  Patching infra/main.tf with your state bucket..."
sed -i.bak \
  "s|your-tfstate-bucket-name|$BUCKET_NAME|g" \
  infra/main.tf
# Uncomment the backend block
sed -i.bak \
  's|  # backend "s3"|  backend "s3"|; s|  #   bucket|    bucket|; s|  #   key|    key|; s|  #   region|    region|; s|  #   dynamodb_table|    dynamodb_table|' \
  infra/main.tf
rm -f infra/main.tf.bak
echo "     ✓ Backend configured"

# ── 4. Print GitHub Secrets needed ───────────────────────────────────────────
echo "4/4  Done! Add these GitHub Secrets to your repo:"
echo ""
echo "     Go to: Settings → Secrets and variables → Actions"
echo ""
echo "     AWS_ACCESS_KEY_ID      = (your IAM user access key)"
echo "     AWS_SECRET_ACCESS_KEY  = (your IAM user secret key)"
echo "     ALERT_EMAIL            = (your email for CloudWatch alerts)"
echo ""
echo "✅  Bootstrap complete. Now run:"
echo "    cd infra && terraform init && terraform apply"
