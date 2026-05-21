"""
Cursiv Board — FastAPI backend.

Routes:
  GET  /             health check
  GET  /api/posts    public feed (no auth)
  POST /api/register register a new user
  POST /api/login    get a JWT
  GET  /api/me       current user info (requires auth)
  POST /api/blast    post a synthesis (requires auth)
  DELETE /api/post/{id}  delete own post (requires auth)

Deploy to Railway:  railway up
Set env var:        CURSIV_BOARD_SECRET=<random 32 chars>
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

try:
    from cursiv_v215.web.db   import init_db, create_user, get_user_by_username, get_user_by_id, create_post, get_posts, delete_post, count_posts_today, get_user_by_device_id
    from cursiv_v215.web.auth import hash_password, verify_password, create_token, decode_token
except ImportError:
    from db   import init_db, create_user, get_user_by_username, get_user_by_id, create_post, get_posts, delete_post, count_posts_today, get_user_by_device_id
    from auth import hash_password, verify_password, create_token, decode_token

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Cursiv Board API", docs_url=None, redoc_url=None)

# Allow the static board.html on any origin to call the API
_ALLOWED_ORIGINS = os.environ.get(
    "CURSIV_BOARD_ORIGINS",
    "https://cursiv.winklers-llc.com,https://api.cursiv.winklers-llc.com,http://localhost:5500,http://127.0.0.1:5500"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    init_db()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _require_auth(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(authorization[7:])
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    return user


# ── Models ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def _clean_username(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 2 or len(v) > 24:
            raise ValueError("Username must be 2–24 characters")
        if not v.replace("_","").replace("-","").isalnum():
            raise ValueError("Username: letters, numbers, _ and - only")
        return v

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class BlastRequest(BaseModel):
    text: str
    source: str = "broadcast"   # "council" or "broadcast"

    @field_validator("text")
    @classmethod
    def _clean_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Text cannot be empty")
        return v[:2000]

    @field_validator("source")
    @classmethod
    def _clean_source(cls, v: str) -> str:
        return v if v in ("council", "broadcast") else "broadcast"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "cursiv-board"}


@app.get("/api/posts")
def feed():
    return {"posts": get_posts(limit=200)}


@app.post("/api/register", status_code=201)
def register(body: RegisterRequest, x_cursiv_device: str | None = Header(None)):
    if get_user_by_username(body.username):
        raise HTTPException(409, "Username already taken")
    if x_cursiv_device and get_user_by_device_id(x_cursiv_device):
        raise HTTPException(409, "An account already exists for this installation")
    create_user(body.username, hash_password(body.password), device_id=x_cursiv_device)
    return {"ok": True}


@app.post("/api/login")
def login(body: LoginRequest):
    user = get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["pw_hash"]):
        raise HTTPException(401, "Invalid username or password")
    token = create_token(user["id"], user["username"])
    return {"token": token, "username": user["username"]}


@app.get("/api/me")
def me(authorization: str | None = Header(None)):
    user = _require_auth(authorization)
    return {"id": user["id"], "username": user["username"]}


@app.post("/api/blast", status_code=201)
def blast(
    body: BlastRequest,
    authorization:  str | None = Header(None),
    x_cursiv_cli:   str | None = Header(None),
):
    user = _require_auth(authorization)
    if body.source == "council" and not x_cursiv_cli:
        raise HTTPException(403, "Council posts must come from the Cursiv CLI")
    if count_posts_today(user["id"]) >= 4:
        raise HTTPException(429, "Daily limit reached — 4 posts per day max")
    post = create_post(user["id"], user["username"], body.text, body.source)
    return post


@app.delete("/api/post/{post_id}")
def remove_post(post_id: str, authorization: str | None = Header(None)):
    user = _require_auth(authorization)
    if not delete_post(post_id, user["id"]):
        raise HTTPException(404, "Post not found or not yours")
    return {"ok": True}
