import json
import os
import pytest
import boto3
from moto import mock_aws

# Set env vars before importing handler
os.environ["TABLE_NAME"] = "test-urls"
os.environ["BASE_URL"] = "https://short.example.com"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"


def make_event(method, path, body=None):
    return {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "body": json.dumps(body) if body else None,
    }


@pytest.fixture
def dynamodb_table():
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="test-urls",
            KeySchema=[{"AttributeName": "code", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "code", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield


# ── POST /shorten ─────────────────────────────────────────────────────────────

class TestShorten:
    def test_valid_https_url(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("POST", "/shorten", {"url": "https://example.com"})
        result = lambda_handler(event, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "short_url" in body
        assert body["short_url"].startswith("https://short.example.com/")
        assert len(body["code"]) == 6
        assert body["original_url"] == "https://example.com"

    def test_valid_http_url(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("POST", "/shorten", {"url": "http://example.com/path?q=1"})
        result = lambda_handler(event, {})
        assert result["statusCode"] == 200

    def test_invalid_url_no_scheme(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("POST", "/shorten", {"url": "example.com"})
        result = lambda_handler(event, {})
        assert result["statusCode"] == 400
        assert "error" in json.loads(result["body"])

    def test_empty_url(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("POST", "/shorten", {"url": ""})
        result = lambda_handler(event, {})
        assert result["statusCode"] == 400

    def test_missing_url_field(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("POST", "/shorten", {})
        result = lambda_handler(event, {})
        assert result["statusCode"] == 400

    def test_invalid_json_body(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("POST", "/shorten")
        event["body"] = "not-json"
        result = lambda_handler(event, {})
        assert result["statusCode"] == 400

    def test_cors_headers_present(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("POST", "/shorten", {"url": "https://example.com"})
        result = lambda_handler(event, {})
        assert "Access-Control-Allow-Origin" in result["headers"]
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_unique_codes_generated(self, dynamodb_table):
        from src.handler import lambda_handler
        codes = set()
        for _ in range(10):
            event = make_event("POST", "/shorten", {"url": "https://example.com"})
            result = lambda_handler(event, {})
            body = json.loads(result["body"])
            codes.add(body["code"])
        assert len(codes) == 10


# ── GET /{code} ───────────────────────────────────────────────────────────────

class TestRedirect:
    def _shorten(self, url):
        from src.handler import lambda_handler
        event = make_event("POST", "/shorten", {"url": url})
        result = lambda_handler(event, {})
        return json.loads(result["body"])["code"]

    def test_valid_redirect(self, dynamodb_table):
        from src.handler import lambda_handler
        code = self._shorten("https://google.com")
        event = make_event("GET", f"/{code}")
        result = lambda_handler(event, {})
        assert result["statusCode"] == 301
        assert result["headers"]["Location"] == "https://google.com"

    def test_unknown_code(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("GET", "/xxxxxx")
        result = lambda_handler(event, {})
        assert result["statusCode"] == 404

    def test_hit_counter_increments(self, dynamodb_table):
        import boto3
        from src.handler import lambda_handler
        code = self._shorten("https://example.com")
        for _ in range(3):
            lambda_handler(make_event("GET", f"/{code}"), {})
        table = boto3.resource(
            "dynamodb", region_name="us-east-1"
        ).Table("test-urls")
        item = table.get_item(Key={"code": code})["Item"]
        assert int(item["hits"]) == 3


# ── Misc ──────────────────────────────────────────────────────────────────────

class TestMisc:
    def test_options_preflight(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("OPTIONS", "/shorten")
        result = lambda_handler(event, {})
        assert result["statusCode"] == 204

    def test_unknown_route(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("GET", "/")
        result = lambda_handler(event, {})
        assert result["statusCode"] == 404

    def test_favicon_ignored(self, dynamodb_table):
        from src.handler import lambda_handler
        event = make_event("GET", "/favicon.ico")
        result = lambda_handler(event, {})
        assert result["statusCode"] == 404
