import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

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
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=ALFRED_SYSTEM_PROMPT,
        )
        context_str = f"\nContext: {json.dumps(req.context)}" if req.context else ""
        raw = model.generate_content(
            f"{req.message}{context_str}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1, # Lower temperature = more stable JSON
                max_output_tokens=400,
                response_mime_type="application/json", # <--- ADD THIS LINE
            ),
        )
        text = raw.text.strip()
        # Strip markdown fences if present
        for fence in ("```json", "```"):
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {
            "speech": "I apologise, Sir Horace. I had difficulty interpreting that request. Please try again.",
            "action": "general_response",
            "params": {},
            "requires_confirmation": False,
            "follow_up": None,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/ping")
async def ping():
    return {"status": "Gemini router is online"}
