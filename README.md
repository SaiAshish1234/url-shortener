# short.ly — Serverless URL Shortener

A production-grade URL shortener built on AWS serverless infrastructure with full CI/CD, IaC, and monitoring.

**Stack:** Lambda · API Gateway · DynamoDB · S3 · CloudFront · Terraform · GitHub Actions · CloudWatch

---

## Project Structure

```
url-shortener/
├── src/
│   ├── handler.py          # Lambda function (Python 3.12)
│   └── requirements.txt
├── tests/
│   └── test_handler.py     # pytest tests with moto mocks
├── frontend/
│   └── index.html          # Static frontend (deployed to S3)
├── infra/
│   ├── main.tf             # All AWS resources in Terraform
│   ├── variables.tf
│   └── outputs.tf
├── scripts/
│   └── bootstrap.sh        # One-time AWS account setup
├── .github/workflows/
│   └── deploy.yml          # GitHub Actions CI/CD
├── requirements-dev.txt
└── pytest.ini
```

---

## Quick Start

### 1. Prerequisites

```bash
# Install tools
brew install awscli terraform          # macOS
# or: apt install awscli + terraform   # Ubuntu

pip install -r requirements-dev.txt   # Python dev dependencies
```

### 2. Configure AWS CLI

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, region (us-east-1), output (json)
```

You need an IAM user with these permissions: `AmazonDynamoDBFullAccess`, `AWSLambda_FullAccess`, `AmazonAPIGatewayAdministrator`, `AmazonS3FullAccess`, `CloudFrontFullAccess`, `IAMFullAccess`, `CloudWatchFullAccess`, `AmazonSNSFullAccess`.

### 3. Bootstrap AWS (one time only)

```bash
bash scripts/bootstrap.sh
```

This creates:
- S3 bucket for Terraform remote state
- DynamoDB table for state locking
- Patches `infra/main.tf` with your bucket name

### 4. Run tests locally

```bash
pytest
```

### 5. Deploy with Terraform

```bash
cd infra
terraform init
terraform plan -var="alert_email=you@example.com"
terraform apply -var="alert_email=you@example.com"
```

Note the outputs — you'll need `cloudfront_url` and `frontend_bucket`.

### 6. Deploy the frontend

```bash
# Replace YOUR_API_URL with the api_endpoint output from terraform
sed -i 's|YOUR_API_GATEWAY_URL|https://your-api-id.execute-api.us-east-1.amazonaws.com|' frontend/index.html

BUCKET=$(cd infra && terraform output -raw frontend_bucket)
aws s3 sync frontend/ s3://$BUCKET --delete

CF_ID=$(cd infra && terraform output -raw cloudfront_distribution_id)
aws cloudfront create-invalidation --distribution-id $CF_ID --paths "/*"
```

Your site is live at the `cloudfront_url` output!

---

## CI/CD Setup

### GitHub Secrets required

Go to your repo → **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `ALERT_EMAIL` | Email for CloudWatch alerts |

### GitHub Environments

Create two environments in **Settings → Environments**:
- `staging` — no protection rules needed
- `production` — add "Required reviewers" for manual approval gate

### How the pipeline works

| Trigger | What happens |
|---------|-------------|
| Push to any branch | Tests + lint run |
| Open PR to main | Deploy to staging → smoke test |
| Merge to main | Deploy to production → smoke test → git tag |

---

## API Reference

### POST /shorten

```bash
curl -X POST https://your-api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/url"}'
```

Response:
```json
{
  "short_url": "https://xyz.cloudfront.net/aB3kR9",
  "code": "aB3kR9",
  "original_url": "https://example.com/very/long/url"
}
```

### GET /{code}

```bash
curl -L https://your-api/aB3kR9
# → 301 redirect to original URL
```

---

## Monitoring

- **Dashboard:** AWS Console → CloudWatch → Dashboards → `urlshortener-prod-dashboard`
- **Alarms:** Fires SNS email when Lambda errors exceed 5 in a 2-minute window
- **Logs:** CloudWatch Logs → `/aws/lambda/urlshortener-prod-shortener`

Useful Log Insights query (top redirected codes):
```
fields @timestamp, code, url
| filter action = "redirect"
| stats count() as hits by code
| sort hits desc
| limit 20
```

---

## Cost estimate (AWS Free Tier)

| Service | Free tier | Typical personal usage |
|---------|-----------|----------------------|
| Lambda | 1M req/month | ~$0 |
| DynamoDB | 25 GB storage | ~$0 |
| API Gateway | 1M calls/month | ~$0 |
| S3 | 5 GB storage | ~$0 |
| CloudFront | 1 TB transfer | ~$0 |

**Total: ~$0/month** for personal use within free tier limits.

---

## Extending the project

- **Custom domain** — Add Route53 hosted zone + ACM certificate in `infra/main.tf`
- **Click analytics** — DynamoDB hits counter is already tracked; add a `/stats/{code}` endpoint
- **Rate limiting** — Add API Gateway usage plan with throttling
- **Link preview** — Fetch Open Graph tags for URLs and store in DynamoDB
- **Password-protected links** — Add `password_hash` field + Lambda check
