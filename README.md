
# SUN.AI Advanced

SUN.AI Advanced is a FastAPI-powered personal AI assistant backend using Google Gemini for text generation and real-time voice interaction, SQLite-backed memory, user feedback, learning records, and a static dashboard.

## Features

- Gemini-powered AI chat.
- Gemini Live API integration for real-time voice interaction.
- SQLite-backed persistent assistant memory.
- User feedback and learning records.
- Response verification.
- Code improvement proposal management.
- Bearer-token authentication for protected API endpoints.
- Static dashboard.
- FastAPI documentation.

## Requirements

- Python 3.11+
- Google Gemini API key.
- Git.
- Render account (for cloud deployment).

## Local setup

### 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd sun-ai-backend
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Windows:

```bash
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Edit `.env` and configure:

```env
APP_NAME=SUN.AI Advanced
APP_ENV=development
DEBUG=false

SUNAI_API_TOKEN=your_secure_api_token
GEMINI_API_KEY=your_gemini_api_key

GEMINI_MODEL=gemini-3.8-flash
GEMINI_LIVE_MODEL=gemini-3.8-live
GEMINI_LIVE_VOICE=Kore

TAVILY_API_KEY=

DATABASE_PATH=./data/sunai.db
SESSION_SECRET=your_secure_session_secret
```

Never commit `.env` or expose API keys and authentication tokens.

### 5. Start the backend

```bash
uvicorn main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

## API endpoints

### Health

```http
GET /health
```

### AI chat

```http
POST /api/chat
Authorization: Bearer YOUR_SUNAI_API_TOKEN
Content-Type: application/json
```

Request:

```json
{
  "prompt": "Hello Bittu"
}
```

### Memory

```http
POST   /api/memory
GET    /api/memory
GET    /api/memory/search
DELETE /api/memory/{memory_id}
DELETE /api/memory
```

### Feedback

```http
POST /api/feedback
GET  /api/feedback
```

### Learning

```http
POST /api/learning
GET  /api/learning
```

### Improvement proposals

```http
POST  /api/improvements/propose
GET   /api/improvements
PATCH /api/improvements/{proposal_id}
```

### Live voice

```http
POST /api/live/ticket
WS   /ws/live?ticket=YOUR_SHORT_LIVED_TICKET
```

The Live API uses a short-lived, one-time ticket obtained through the authenticated ticket endpoint.

## Running tests

Run the test suite:

```bash
pytest -v
```

## Render deployment

Configure the following environment variables in Render:

```env
APP_ENV=production
DEBUG=false

SUNAI_API_TOKEN=your_secure_api_token
GEMINI_API_KEY=your_gemini_api_key

GEMINI_MODEL=gemini-3.8-flash
GEMINI_LIVE_MODEL=gemini-3.8-live
GEMINI_LIVE_VOICE=Kore

DATABASE_PATH=./data/sunai.db
SESSION_SECRET=your_secure_session_secret
```

Recommended start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Ensure persistent disk storage is configured if SQLite data must survive service restarts or redeployments.

## Security notes

- Keep API keys and tokens private.
- Use HTTPS in production.
- Protect authenticated endpoints.
- Validate WebSocket connections and origins.
- Require confirmation for sensitive or destructive assistant actions.
- Review and test proposed code changes before applying them.

## Project status

SUN.AI Advanced is under incremental development.

New capabilities should preserve existing approved functionality and architecture. Features must be tested before being described as fully integrated or production-ready.
