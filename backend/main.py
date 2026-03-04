import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware # Added this
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from routers import auth, gmail, drive, youtube, gemini

app = FastAPI(title="Alfred Voice Agent API", version="1.0.0")

# STEP 1: Add Session Middleware FIRST (Innermost layer)
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SECRET_KEY", "Alfred_Security_2026_Key"),
    same_site="none",   # Required for cross-site cookie tracking in 2026
    https_only=True     # Must be True for "same_site=none" to work
)

# STEP 2: Add CORS Middleware LAST (Outermost layer)
# This ensures CORS headers are added even if a session error occurs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://alfred.robotshelper.com", 
        "http://localhost:5173"
    ],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(gmail.router, prefix="/gmail", tags=["Gmail"])
app.include_router(drive.router, prefix="/drive", tags=["Google Drive"])
app.include_router(youtube.router, prefix="/youtube", tags=["YouTube"])
app.include_router(gemini.router, prefix="/gemini", tags=["Gemini AI"])


@app.get("/")
async def root():
    return {"status": "online", "message": "Alfred is at your service, Sir Horace."}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
