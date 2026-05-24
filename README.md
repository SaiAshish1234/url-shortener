# short.ly — Serverless URL Shortener

![CI/CD](https://github.com/SaiAshish1234/url-shortener/actions/workflows/deploy.yml/badge.svg)

A production-grade URL shortener built on AWS serverless infrastructure with full CI/CD, Infrastructure as Code, and monitoring.

🔗 **Live Demo:** https://d1wahrswrbzjbf.cloudfront.net/index.html

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Compute | AWS Lambda (Python 3.12) |
| Database | AWS DynamoDB (on-demand) |
| API | AWS API Gateway (HTTP API) |
| Frontend | Static HTML hosted on S3 |
| CDN | AWS CloudFront |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Monitoring | CloudWatch + SNS Alerts |

---

## Architecture

```
User → CloudFront CDN → API Gateway → Lambda → DynamoDB
                              ↓
                        S3 (Frontend)
```

1. User visits the site via CloudFront
2. Pastes a long URL and clicks Shorten
3. Lambda generates a 6-character code and stores it in DynamoDB
4. Clicking the short link hits Lambda which redirects to the original URL

---

## Features

- 🔗 Shorten any URL instantly
- ↩️ 301 redirects with click tracking
- ⏰ Automatic link expiry via DynamoDB TTL
- 🌍 Global CDN via CloudFront
- 📊 CloudWatch dashboard with metrics
- 🚨 SNS email alerts on error spikes
- ✅ 14 automated tests with 95% coverage
- 🔄 Full CI/CD — every push auto-deploys

---

## Project Structure

```
url-shortener/
├── src/
│   └── handler.py              # Lambda function (Python 3.12)
├── tests/
│   └── test_handler.py         # pytest tests with moto mocks
├── frontend/
│   └── index.html              # Static frontend (deployed to S3)
├── infra/
│   ├── main.tf                 # All AWS resources in Terraform
│   ├── variables.tf
│   └── outputs.tf
├── .github/workflows/
│   └── deploy.yml              # GitHub Actions CI/CD pipeline
└── scripts/
    └── bootstrap.sh            # One-time AWS account setup
```

---

## CI/CD Pipeline

| Trigger | Action |
|---------|--------|
| Push to any branch | Run tests + lint |
| Merge to main | Deploy to production |

Pipeline steps: lint → test → build Lambda zip → terraform apply → S3 sync → CloudFront invalidation → smoke test

---

## API Reference

**POST /shorten**

```bash
curl -X POST https://85yw1disj9.execute-api.us-east-1.amazonaws.com/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Response:

```json
{
  "short_url": "https://d1wahrswrbzjbf.cloudfront.net/aB3kR9",
  "code": "aB3kR9",
  "original_url": "https://example.com"
}
```

**GET /{code}** — 301 redirect to the original URL

---

## Local Development

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Deploy infrastructure
cd infra
terraform init
terraform apply -var="alert_email=you@example.com"
```

---

## Cost

Runs entirely on AWS Free Tier — approximately **$0/month** for personal use.
