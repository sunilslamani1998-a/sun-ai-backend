# SUN.AI Advanced

An advanced, reliable AI agent featuring multi-step task planning, long-term memory, automated verification, and a secure self-repair approval dashboard.

## Deployment on Render
1. Create a new **Web Service** on Render connected to your GitHub repository.
2. Use the provided `render.yaml` or manual settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Add your environment variables (`OPENAI_API_KEY`).
