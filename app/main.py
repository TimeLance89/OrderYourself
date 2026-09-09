"""FastAPI-Einstiegspunkt für OrderYourself."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.db import engine, init_db
from app.routers import dashboard, household, recipes, shopping
from app.services import web_security

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="OrderYourself", version="2.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request, call_next):
    cookie_token = request.cookies.get(web_security.COOKIE_NAME, "")
    token = cookie_token if web_security.valid_csrf_token(cookie_token) else web_security.csrf_token()
    request.state.csrf_token = token
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if request.method.upper() == "GET" and "text/html" in response.headers.get("content-type", ""):
        web_security.set_csrf_cookie(response, token, request)
    return response


@app.get("/health/live", include_in_schema=False)
def health_live(): return {"status": "alive"}


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    try:
        with engine.connect() as connection: connection.exec_driver_sql("SELECT 1")
        return {"status": "ready"}
    except Exception as exc:
        return JSONResponse({"status": "not-ready", "error": type(exc).__name__}, status_code=503)


app.mount("/static", StaticFiles(directory=str(BASE_DIR.parent / "static")), name="static")
trusted = [Depends(web_security.require_trusted_request)]
app.include_router(dashboard.router, dependencies=trusted)
app.include_router(household.router, dependencies=trusted)
app.include_router(recipes.router, dependencies=trusted)
app.include_router(shopping.router, dependencies=trusted)
