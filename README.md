# SUN.AI Advanced

A modular FastAPI AI assistant starter project.

## Features in this starter

- AI chat through an OpenAI-compatible API
- SQLite persistent memory
- User feedback collection
- Basic result verification
- Code-improvement proposals
- Python syntax checking
- Bearer-token API authentication
- Health check endpoint
- Render deployment configuration

## Requirements

Python 3.11 or newer.

## Local setup

1. Install dependencies:

   pip install -r requirements.txt

2. Copy `.env.example` to `.env`.

3. Set a strong `SUNAI_API_TOKEN` and a valid AI provider API key.

4. Load environment variables from `.env` using your preferred
   environment manager, or set them in your shell.

5. Start the server:

   uvicorn main:app --reload

6. Open http://127.0.0.1:8000

## Authentication

Send the token with API requests:

Authorization: Bearer YOUR_SUNAI_API_TOKEN

Do not put the token in a public frontend, GitHub repository,
URL, or browser local storage.

## Endpoints

- GET /health
- POST /api/chat
- POST /api/memory
- GET /api/memory
- DELETE /api/memory/{memory_id}
- POST /api/feedback
- GET /api/learning
- POST /api/improvements/propose
- GET /api/improvements

## Testing

Install pytest and run:

pip install pytest
pytest -q

## Limitations

Feedback storage is not model training.
Memory search is keyword-based.
Result verification is basic.
Code proposals are not automatically applied.
The syntax checker does not execute untrusted code.
Web research, voice, video generation, and specialist
HVAC/Revit workflows require additional integrations.

SQLite is suitable for development and small deployments.
Use PostgreSQL and durable storage for a multi-user production
deployment. Configure backups, monitoring, and access controls.

Do not deploy publicly until authentication, authorization,
error handling, and security testing have been reviewed.
