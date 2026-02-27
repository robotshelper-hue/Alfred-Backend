from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from googleapiclient.discovery import build
from .auth import get_credentials

router = APIRouter()


def _drive():
    return build("drive", "v3", credentials=get_credentials())


def _docs():
    return build("docs", "v1", credentials=get_credentials())


@router.get("/folders")
async def list_folders():
    try:
        svc = _drive()
        result = svc.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            pageSize=5,
            fields="files(id, name, createdTime)",
            orderBy="createdTime desc",
        ).execute()
        folders = result.get("files", [])
        return {"folders": folders, "count": len(folders)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class CreateDocRequest(BaseModel):
    title: str
    content: str
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None


@router.post("/create-document")
async def create_document(req: CreateDocRequest):
    try:
        svc = _drive()
        folder_id = req.folder_id
        if not folder_id and req.folder_name:
            res = svc.files().list(
                q=f"mimeType='application/vnd.google-apps.folder' and name='{req.folder_name}' and trashed=false",
                fields="files(id, name)",
                pageSize=1,
            ).execute()
            found = res.get("files", [])
            if found:
                folder_id = found[0]["id"]

        metadata: dict = {
            "name": req.title,
            "mimeType": "application/vnd.google-apps.document",
        }
        if folder_id:
            metadata["parents"] = [folder_id]

        doc = svc.files().create(body=metadata, fields="id, name, webViewLink").execute()

        docs_svc = _docs()
        docs_svc.documents().batchUpdate(
            documentId=doc["id"],
            body={
                "requests": [
                    {"insertText": {"location": {"index": 1}, "text": req.content}}
                ]
            },
        ).execute()

        return {
            "success": True,
            "document": {
                "id": doc["id"],
                "name": doc["name"],
                "link": doc.get("webViewLink", ""),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/files")
async def list_files(folder_id: Optional[str] = None):
    try:
        svc = _drive()
        query = "trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        result = svc.files().list(
            q=query,
            pageSize=10,
            fields="files(id, name, mimeType, createdTime)",
        ).execute()
        files = result.get("files", [])
        return {"files": files, "count": len(files)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
