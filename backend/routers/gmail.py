import re
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from googleapiclient.discovery import build
from .auth import get_credentials

router = APIRouter()


def _strip(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    text = re.sub(r"[*#~`|>]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _gmail():
    return build("gmail", "v1", credentials=get_credentials())


@router.get("/fetch")
async def fetch_emails():
    try:
        svc = _gmail()
        result = svc.users().messages().list(
            userId="me", maxResults=5, labelIds=["INBOX"]
        ).execute()
        messages = result.get("messages", [])
        emails = []
        for msg in messages:
            data = svc.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in data["payload"]["headers"]}
            raw_from = headers.get("From", "Unknown")
            name_match = re.match(r"^([^<]+)", raw_from)
            sender = name_match.group(1).strip() if name_match else raw_from
            emails.append(
                {
                    "id": msg["id"],
                    "from": _strip(sender),
                    "subject": _strip(headers.get("Subject", "No Subject")),
                    "date": headers.get("Date", ""),
                    "snippet": _strip(data.get("snippet", "")),
                }
            )
        return {"emails": emails, "count": len(emails)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/read/{email_id}")
async def read_email(email_id: str):
    try:
        svc = _gmail()
        msg = svc.users().messages().get(
            userId="me", id=email_id, format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        body = ""
        payload = msg.get("payload", {})
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    raw = part["body"].get("data", "")
                    if raw:
                        body = base64.urlsafe_b64decode(raw).decode("utf-8", errors="ignore")
                        break
        else:
            raw = payload.get("body", {}).get("data", "")
            if raw:
                body = base64.urlsafe_b64decode(raw).decode("utf-8", errors="ignore")
        return {
            "id": email_id,
            "from": _strip(headers.get("From", "Unknown")),
            "subject": _strip(headers.get("Subject", "No Subject")),
            "body": _strip(body[:600]),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/delete/{email_id}")
async def delete_email(email_id: str):
    try:
        svc = _gmail()
        svc.users().messages().trash(userId="me", id=email_id).execute()
        return {"success": True, "message": "Email moved to trash"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class MoveRequest(BaseModel):
    email_id: str
    destination_folder: str


@router.post("/move")
async def move_email(req: MoveRequest):
    try:
        svc = _gmail()
        labels_resp = svc.users().labels().list(userId="me").execute()
        label_id = None
        for lbl in labels_resp.get("labels", []):
            if lbl["name"].lower() == req.destination_folder.lower():
                label_id = lbl["id"]
                break
        if not label_id:
            new_lbl = svc.users().labels().create(
                userId="me", body={"name": req.destination_folder}
            ).execute()
            label_id = new_lbl["id"]
        svc.users().messages().modify(
            userId="me",
            id=req.email_id,
            body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]},
        ).execute()
        return {"success": True, "message": f"Email moved to {req.destination_folder}"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
