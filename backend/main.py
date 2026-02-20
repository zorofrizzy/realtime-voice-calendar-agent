import os
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr
from dotenv import load_dotenv

# Handling timezones
from dateutil import tz

load_dotenv()

app = FastAPI(title="Calendar Tool Service", version="1.0.0")




GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
CALENDAR_ID = os.getenv("CALENDAR_ID", "primary").strip()
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "America/Los_Angeles").strip()




class CreateEventRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    title: str = Field("Meeting", min_length=1, max_length=200)
    start: datetime  # Expect ISO-8601; ideally with offset or Z
    durationMinutes: int = Field(30, ge=15, le=240)
    timezone: str = Field(default=DEFAULT_TIMEZONE, min_length=1, max_length=64)
    invitees: Optional[List[EmailStr]] = None


class CreateEventResponse(BaseModel):
    eventId: str
    htmlLink: Optional[str] = None
    summary: str
    start: str
    end: str
    calendarId: str
    requestId: str


def _require_env():
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN):
        raise HTTPException(
            status_code=500,
            detail="Server missing GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET/GOOGLE_REFRESH_TOKEN env vars.",
        )


def _get_access_token() -> str:
    _require_env()
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": GOOGLE_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    data = resp.json()
    if resp.status_code != 200 or "access_token" not in data:
        raise HTTPException(status_code=502, detail=f"Google token refresh failed: {data}")
    return data["access_token"]


def _make_request_id(payload: CreateEventRequest) -> str:
    # Simple idempotency hint; you can store/verify later if you add a DB.
    key = f"{payload.name}|{payload.title}|{payload.start.isoformat()}|{payload.durationMinutes}|{payload.timezone}|{payload.invitees or []}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@app.get("/health")
def health():
    return {"ok": True}



def normalize_start_end(start_dt: datetime, duration_minutes: int, timezone: str):
    tzinfo = tz.gettz(timezone)
    if tzinfo is None:
        raise HTTPException(status_code=400, detail=f"Invalid timezone: {timezone}")

    # If naive, assume it's already in the requested timezone.
    if start_dt.tzinfo is None:
        start_local = start_dt.replace(tzinfo=tzinfo)
    else:
        # If aware (Z/offset), convert the instant into the requested timezone.
        start_local = start_dt.astimezone(tzinfo)

    end_local = start_local + timedelta(minutes=duration_minutes)
    return start_local, end_local


@app.post("/create-event", response_model=CreateEventResponse)
def create_event(req: CreateEventRequest):
    _require_env()

    # Normalize to the user's timezone without changing minutes/seconds
    start_local, end_local = normalize_start_end(req.start, req.durationMinutes, req.timezone)

    # Reject if in the past (compare in same timezone)
    tzinfo = tz.gettz(req.timezone)
    now_local = datetime.now(tzinfo)
    if start_local < now_local:
        raise HTTPException(
            status_code=400,
            detail=f"Start time is in the past for timezone {req.timezone}. Please choose a future time.",
        )

    request_id = _make_request_id(req)
    access_token = _get_access_token()

    body = {
        "summary": req.title or "Meeting",
        "description": f"Scheduled by voice assistant for {req.name}. RequestId: {request_id}",
        "start": {"dateTime": start_local.isoformat(), "timeZone": req.timezone},
        "end": {"dateTime": end_local.isoformat(), "timeZone": req.timezone},
    }

    if req.invitees:
        body["attendees"] = [{"email": e} for e in req.invitees]

    resp = requests.post(
        f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=20,
    )

    data = resp.json()
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Google Calendar insert failed: {data}")

    return CreateEventResponse(
        eventId=data.get("id", ""),
        htmlLink=data.get("htmlLink"),
        summary=data.get("summary", req.title or "Meeting"),
        start=data.get("start", {}).get("dateTime", start_local.isoformat()),
        end=data.get("end", {}).get("dateTime", end_local.isoformat()),
        calendarId=CALENDAR_ID,
        requestId=request_id,
    )