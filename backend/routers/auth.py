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
        'scope': "openid email profile https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/youtube.readonly",
        'token_endpoint_auth_method': 'client_secret_post',
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

# Change from "/auth/callback" to just "/callback" 
# because main.py already adds the first "/auth"
@router.get("/callback") 
async def auth_callback(request: Request):
    try:
        # 1. Exchange the code for a token
        token = await oauth.google.authorize_access_token(request)
        
        # 2. SAVE the token so Alfred stays logged in
        with open(TOKEN_FILE, "w") as f:
            json.dump(token, f)

        # 3. Get user info (optional, for Alfred to know your name)
        user = token.get('userinfo')
        
        # 4. Redirect home
        return RedirectResponse(url="https://alfred.robotshelper.com/dashboard")

    except Exception as e:
        print(f"Detailed OAuth Error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

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

def get_credentials():
    import os
    import json
    from google.oauth2.credentials import Credentials
    
    TOKEN_FILE = "tokens.json"
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            # This turns the saved file back into a "Google ID Card"
            return Credentials(
                token=data.get("access_token"), # Authlib uses 'access_token'
                refresh_token=data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
            )
    return None
