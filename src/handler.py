import json
import boto3
import string
import random
import os
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ["TABLE_NAME"]
BASE_URL = os.environ["BASE_URL"]
TTL_DAYS = int(os.environ.get("TTL_DAYS", "365"))

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def generate_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def cors_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def respond(status_code: int, body: dict) -> dict:
    logger.info(json.dumps({"status": status_code, "body": body}))
    return {
        "statusCode": status_code,
        "headers": cors_headers(),
        "body": json.dumps(body),
    }


def shorten_url(url: str) -> dict:
    if not url or not url.startswith(("http://", "https://")):
        return respond(400, {"error": "Invalid URL. Must start with http:// or https://"})

    # Retry on collision (extremely rare but good practice)
    for _ in range(3):
        code = generate_code()
        ttl = int(time.time()) + TTL_DAYS * 86400

        table.put_item(
            Item={
                "code": code,
                "url": url,
                "created_at": int(time.time()),
                "ttl": ttl,
                "hits": 0,
            },
            ConditionExpression="attribute_not_exists(code)",
        )
        logger.info(json.dumps({"action": "shorten", "code": code, "url": url}))
        return respond(200, {
            "short_url": f"{BASE_URL}/{code}",
            "code": code,
            "original_url": url,
        })

    return respond(500, {"error": "Failed to generate unique code. Try again."})


def redirect(code: str) -> dict:
    result = table.get_item(Key={"code": code})
    item = result.get("Item")

    if not item:
        logger.warning(json.dumps({"action": "redirect", "code": code, "result": "not_found"}))
        return respond(404, {"error": f"Short code '{code}' not found"})

    # Increment hit counter asynchronously (best-effort)
    try:
        table.update_item(
            Key={"code": code},
            UpdateExpression="ADD hits :inc",
            ExpressionAttributeValues={":inc": 1},
        )
    except Exception:
        pass

    logger.info(json.dumps({"action": "redirect", "code": code, "url": item["url"]}))
    return {
        "statusCode": 301,
        "headers": {
            **cors_headers(),
            "Location": item["url"],
            "Cache-Control": "no-cache",
        },
        "body": "",
    }


def lambda_handler(event: dict, context) -> dict:
    logger.info(json.dumps({"event": event}))

    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method", "").upper()
    path = event.get("rawPath", "/")

    # CORS preflight
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": cors_headers(), "body": ""}

    # POST /shorten — create a short URL
    if method == "POST" and path == "/shorten":
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return respond(400, {"error": "Invalid JSON body"})
        return shorten_url(body.get("url", "").strip())

    # GET /{code} — redirect
    if method == "GET" and len(path) > 1:
        code = path.lstrip("/")
        if code and code != "favicon.ico":
            return redirect(code)

    return respond(404, {"error": "Not found"})
