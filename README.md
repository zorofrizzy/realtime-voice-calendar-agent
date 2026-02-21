# Real-Time Voice Scheduling Agent

Real-time AI voice assistant that schedules a Google Calendar event.

## Deployment:
- **Frontend (Vercel):**
     - https://realtime-voice-calendar-agent-verce.vercel.app/
- **Voice Agent (Vapi Hosted Link):**
   - https://vapi.ai?demo=true&shareKey=2aaf3172-f599-44b9-9702-69579ca67b39&assistantId=5a234ade-36a9-4f0b-98bf-b00bedc5417b
- **Backend (Render):**
   - https://realtime-voice-calendar-agent.onrender.com


## How to Test
1. Open the Vercel frontend link above.
2. Click Start Voice Assistant.
3. Allow microphone access when prompted.
4. Say:

```“Schedule a meeting tomorrow at 5 PM titled Project Sync.”```

5. Provide your name when asked.
6. Confirm the final details.
7. The assistant will create a real Google Calendar event.
8. Open the demo calendar (if provided) to verify the event was created.

## What the Agent Does
The assistant:
1. Initiates the conversation.
2. Asks for:
   - User's name
   - Preferred Date and Time
   - Optional Meeting Title
3. Confirms all details verbally.
4. Calls a backend tool to create a real Google Calendar event.
5. Confirms a successful scheduling.

## Calendar Integration
The backend integrates directly with the Google Calendar API.
- OAuth 2.0 is used to obtain a refresh token.
- The refresh token is securely stored as an environment variable.
- On each scheduling request:
   1. The backend refreshes the access token.
   2. Constructs a properly formatted ISO-8601 datetime (with timezone offset).
   3.  Creates the event via ```events.insert```.
   4. Returns the event ID and metadata to the voice agent.

A dedicated demo calendar is used for verification.

## Local Installation

### Backend 
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install requirements.txt.

```bash
pip install -r requirements.txt

```
Run the backend app
```
uvicorn main:app --reload
```

Environment variables required:

- ```GOOGLE_CLIENT_ID```
- ```GOOGLE_CLIENT_SECRET```
- ```GOOGLE_REFRESH_TOKEN```
- ```CALENDAR_ID```
- ```DEFAULT_TIMEZONE```

### Frontend 
The frontend is a static HTML page and can be opened directly or served via:
```
cd frontend
npx serve .
```
## Tech Stack:
- Python
- FastAPI
- Vapi AI
- Google Calendar API
- Grok 4 Reasoning 
- Render (Backend Hosting)
- Vercel (Frontend Hosting)

## Demo
Loom video Demo:
https://www.loom.com/share/3701eb4b5f864b3894b7b853dcbbba86

