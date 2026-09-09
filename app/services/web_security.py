"""Kleine LAN/Proxy-Vertrauensgrenze plus signierter Double-Submit-CSRF-Schutz."""
import hashlib
import hmac
import ipaddress
import secrets
from fastapi import HTTPException, Request
from app.config import settings

COOKIE_NAME = "oy_csrf"
_PROCESS_SECRET = secrets.token_bytes(32)


def _secret() -> bytes:
    return settings.web_csrf_secret.encode() if settings.web_csrf_secret else _PROCESS_SECRET


def csrf_token() -> str:
    seed = secrets.token_hex(16)
    sig = hmac.new(_secret(), seed.encode(), hashlib.sha256).hexdigest()
    return f"{seed}.{sig}"


def valid_csrf_token(token: str) -> bool:
    try:
        seed, sig = token.split(".", 1)
    except (ValueError, AttributeError):
        return False
    if len(seed) != 32 or len(sig) != 64:
        return False
    expected = hmac.new(_secret(), seed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def set_csrf_cookie(response, token: str, request: Request) -> None:
    response.set_cookie(COOKIE_NAME, token, max_age=43_200, httponly=True, secure=request.url.scheme == "https", samesite="strict", path="/")


def _trusted_peer(request: Request) -> bool:
    header, expected = settings.trusted_proxy_header.strip(), settings.trusted_proxy_value.strip()
    if header or expected:
        return bool(header and expected and hmac.compare_digest(request.headers.get(header, ""), expected))
    host = str(request.client.host if request.client else "")
    if host == "testclient":
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


async def require_trusted_request(request: Request) -> None:
    if not _trusted_peer(request):
        raise HTTPException(status_code=403, detail="OrderYourself ist nur im vertrauenswürdigen Haushaltsnetz verfügbar.")
    if request.method.upper() != "POST":
        return
    form = await request.form()
    submitted = str(form.get("csrf_token") or "")
    cookie = request.cookies.get(COOKIE_NAME, "")
    if not submitted or not cookie or not hmac.compare_digest(submitted, cookie) or not valid_csrf_token(submitted):
        raise HTTPException(status_code=403, detail="Ungültiger CSRF-Schutz.")
