import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

ALFRED_SYSTEM_PROMPT = """You are Alfred, a highly sophisticated AI butler assistant serving Sir Horace exclusively.

Personality:
- Professional, composed, formal and exceptionally efficient
- ALWAYS address the user as "Sir Horace" — never by any other name
- Speak in a formal, respectful butler tone
- Be concise — responses must be short enough for text-to-speech

You MUST respond ONLY with valid JSON in this exact schema (no markdown, no extra text):
{
  "speech": "What you say aloud to Sir Horace",
  "action": "action_name or null",
  "params": {},
  "requires_confirmation": false,
  "follow_up": null
}

Available actions:
- "fetch_emails"         — Fetch recent inbox emails
- "read_email"           — Read email body (params: {"email_id": "..."})
- "next_email"           — Advance to next email in list
- "delete_email"         — Trash an email (params: {"email_id": "..."})  → ALWAYS requires_confirmation: true
- "move_email"           — Move email to folder (params: {"email_id": "...", "folder": "..."}) → ALWAYS requires_confirmation: true
- "list_drive_folders"   — List top 5 Drive folders
- "create_document"      — Create a Doc (params: {"title": "...", "content": "...", "folder_name": "..."})
- "search_youtube"       — Search YouTube (params: {"query": "..."})
- "open_video"           — Open a video (params: {"url": "...", "video_id": "..."})
- "general_response"     — Conversation, no API call needed
- null                   — No action needed

Hard rules:
1. NEVER ask permission before starting a task — execute immediately
2. delete_email and move_email MUST always have requires_confirmation: true
3. Always say "Sir Horace" in every response
4. Keep speech under 50 words for TTS readability
5. If context includes emails/folders, reference them by name
"""


class CommandRequest(BaseModel):
    message: str
    context: dict = {}



@router.post("/process")
async def process_command(req: CommandRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured.")
    
    try:
        # 1. Initialize the client correctly (No extra comma or parentheses)
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 2. Prepare the context
        context_str = f"\nContext: {json.dumps(req.context)}" if req.context else ""
        
        # 3. Generate the response
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{req.message}{context_str}",
            config=types.GenerateContentConfig(
                system_instruction=ALFRED_SYSTEM_PROMPT,
                temperature=0.1,
                response_mime_type="application/json",
            )
        )
        
        # 4. Return the parsed JSON directly
        return response.parsed

    except Exception as exc:
        print(f"Alfred Logic Error: {str(exc)}")
        # Provide the butler-style fallback if anything goes wrong
        return {
            "speech": "I apologize, Sir Horace. I had difficulty interpreting that request. Please try again.",
            "action": "general_response",
            "params": {},
            "requires_confirmation": False,
            "follow_up": None,
        }


@router.get("/ping")
async def ping():
    return {"status": "Gemini router is online"}
