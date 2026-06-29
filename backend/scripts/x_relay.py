import json
import os
import subprocess
from urllib.parse import urlencode, urlparse, urlunparse

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


ALLOWED_HOSTS = set(["x.com", "twitter.com", "api.twitter.com", "abs.twimg.com"])
RELAY_TOKEN = os.getenv("X_RELAY_TOKEN", "")
UPSTREAM_PROXY = os.getenv("X_RELAY_UPSTREAM_PROXY", "http://127.0.0.1:7890")
UPSTREAM_PROXY_AUTH = os.getenv("X_RELAY_UPSTREAM_PROXY_AUTH", "")
COOKIE_JAR = os.getenv("X_RELAY_COOKIE_JAR", "/tmp/x-relay-cookies.txt")
CURL_BIN = os.getenv("X_RELAY_CURL_BIN", "curl")

app = FastAPI(title="X Relay")


class FetchRequest(BaseModel):
    method: str = "GET"
    url: str
    params: dict = Field(default_factory=dict)
    headers: dict = Field(default_factory=dict)
    json_body: dict = None
    response_type: str = "json"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "upstream_proxy": _redact_proxy_url(UPSTREAM_PROXY),
        "upstream_proxy_auth": "configured" if UPSTREAM_PROXY_AUTH else "none",
        "cookie_jar": COOKIE_JAR,
    }


@app.post("/fetch")
def fetch(payload: FetchRequest, x_relay_token: str = Header(default=None)):
    if RELAY_TOKEN and x_relay_token != RELAY_TOKEN:
        raise HTTPException(status_code=401, detail="invalid relay token")

    method = payload.method.upper()
    if method not in ("GET", "POST"):
        raise HTTPException(status_code=400, detail="method is not allowed")

    parsed = urlparse(payload.url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise HTTPException(status_code=400, detail="target host is not allowed")

    target_url = _with_params(payload.url, payload.params)
    args = [
        CURL_BIN,
        "-sS",
        "--max-time",
        "35",
        "--connect-timeout",
        "10",
        "-b",
        COOKIE_JAR,
        "-c",
        COOKIE_JAR,
        "-x",
        UPSTREAM_PROXY,
        "-A",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "-H",
        "accept: */*",
        "-H",
        "accept-language: en-US,en;q=0.9",
        "-H",
        "origin: https://x.com",
        "-H",
        "referer: https://x.com/",
        "-w",
        "\n%{http_code}",
    ]
    if UPSTREAM_PROXY_AUTH:
        args.extend(["--proxy-user", UPSTREAM_PROXY_AUTH])

    for key, value in _filter_headers(payload.headers).items():
        args.extend(["-H", "%s: %s" % (key, value)])

    if method == "POST":
        args.extend(["-X", "POST", "-H", "content-type: application/json"])
        args.extend(["--data-binary", json.dumps(payload.json_body or {}, separators=(",", ":"))])

    args.append(target_url)

    try:
        completed = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=40,
        )
    except OSError as exc:
        raise HTTPException(status_code=502, detail="curl execution failed: %s" % exc)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="upstream request timed out")

    if completed.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail="curl failed: %s" % (completed.stderr.strip() or completed.returncode),
        )

    body, status_code = _split_curl_output(completed.stdout)
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=body[:1000])

    if payload.response_type == "text":
        return {"status_code": status_code, "text": body}

    try:
        return json.loads(body)
    except ValueError:
        raise HTTPException(status_code=502, detail="upstream response is not json: %s" % body[:300])


def _with_params(url, params):
    if not params:
        return url
    parsed = urlparse(url)
    existing = parsed.query
    extra = urlencode(params)
    query = existing + "&" + extra if existing else extra
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))


def _split_curl_output(output):
    if "\n" not in output:
        raise HTTPException(status_code=502, detail="curl output missing status code")
    body, status = output.rsplit("\n", 1)
    try:
        return body, int(status)
    except ValueError:
        raise HTTPException(status_code=502, detail="curl output invalid status code: %s" % status)


def _filter_headers(headers):
    allowed = set(
        [
            "authorization",
            "x-guest-token",
            "x-twitter-active-user",
            "x-twitter-client-language",
            "x-csrf-token",
        ]
    )
    return {str(key).lower(): str(value) for key, value in headers.items() if str(key).lower() in allowed}


def _redact_proxy_url(url):
    parsed = urlparse(url)
    if not parsed.username and not parsed.password:
        return url
    hostname = parsed.hostname or ""
    if parsed.port:
        hostname = "%s:%s" % (hostname, parsed.port)
    if parsed.scheme:
        return "%s://***:***@%s" % (parsed.scheme, hostname)
    return "***:***@%s" % hostname
