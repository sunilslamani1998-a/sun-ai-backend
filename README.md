# SUN.AI Advanced

SUN.AI Advanced is a FastAPI personal assistant backend using Gemini, SQLite-backed memory and feedback, and a static dashboard.

## Requirements
- Python 3.11+
- Gemini API key for live chat
- Git; Render account for deployment

## Local setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
