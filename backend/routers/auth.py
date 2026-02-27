import os
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secrets.json")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
TOKEN_FILE = "tokens.json"

token_store: dict = {}


def _get_flow() -> Flow:
    if os.path.exists(CLIENT_SECRETS_FILE):
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
        )
    else:
        client_config = {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        }
        flow = Flow.from_client_config(
            client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI
        )
    return flow


def get_credentials() -> Credentials:
    if "credentials" not in token_store:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                token_store["credentials"] = json.load(f)
        else:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated with Google. Please visit /auth/login.",
            )
    data = token_store["credentials"]
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id") or os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=data.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=data.get("scopes", SCOPES),
    )
    return creds


@router.get("/login")
async def login():
    flow = _get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(code: str, state: str = None):
    try:
        flow = _get_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        }
        token_store["credentials"] = token_data
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)
        return RedirectResponse(url=f"{FRONTEND_URL}?auth=success")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/status")
async def auth_status():
    if "credentials" in token_store:
        return {"authenticated": True}
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            token_store["credentials"] = json.load(f)
        return {"authenticated": True}
    return {"authenticated": False}


@router.post("/logout")
async def logout():
    token_store.clear()
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    return {"message": "Logged out successfully"}
