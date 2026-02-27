import os
from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from .auth import get_credentials

router = APIRouter()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


def _youtube():
    if YOUTUBE_API_KEY:
        return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    return build("youtube", "v3", credentials=get_credentials())


@router.get("/search")
async def search_youtube(query: str, max_results: int = 5):
    try:
        svc = _youtube()
        result = svc.search().list(
            part="snippet",
            q=query,
            maxResults=max_results,
            type="video",
            order="relevance",
        ).execute()
        videos = []
        for item in result.get("items", []):
            vid_id = item["id"]["videoId"]
            videos.append(
                {
                    "id": vid_id,
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "description": item["snippet"]["description"][:120],
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "thumbnail": item["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
                }
            )
        return {"videos": videos, "count": len(videos)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
