import os
import json # Added for saving tokens
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError

router = APIRouter()

# --- Configuration ---
TOKEN_FILE = "tokens.json" # Added this definition
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://alfred.robotshelper.com")

# --- Initialize OAuth Engine ---
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': "openid email profile https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/youtube.readonly"
    }
)

@router.get("/login")
async def login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return await oauth.google.authorize_redirect(
        request, 
        redirect_uri,
        access_type="offline",
        prompt="consent",
        code_challenge_method="S256"
    )

@router.get("/callback")
async def callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        # We save the token to a file so Alfred has his "ID card" for Gmail/Drive
        with open(TOKEN_FILE, "w") as f:
            json.dump(token, f)
        return RedirectResponse(url=f"{FRONTEND_URL}?auth=success")
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def auth_status():
    # If the token file exists, Alfred is logged in!
    if os.path.exists(TOKEN_FILE):
        return {"authenticated": True}
    return {"authenticated": False}

@router.post("/logout")
async def logout():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    return {"message": "Logged out successfully"}
