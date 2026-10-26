import os
import json
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from agent import SunAIAgent

load_dotenv()

app = FastAPI(title="SUN.AI Advanced API", version="2.0.0")

# Initialize Advanced Agent
agent = SunAIAgent(api_key=os.getenv("OPENAI_API_KEY"))

class TaskRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = "default_user"

class PatchApproval(BaseModel):
    patch_id: str
    approved: bool

@app.get("/", response_class=HTMLResponse)
async def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>SUN.AI Advanced Backend Running</h1><p>index.html not found.</p>"

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SUN.AI Advanced Agent"}

@app.post("/api/agent/run")
async def run_agent_task(req: TaskRequest, background_tasks: BackgroundTasks):
    try:
        # Run advanced planning, tool execution, and verification
        result = agent.execute_task(req.prompt)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/patches")
async def get_pending_patches():
    """Retrieve pending self-repair code diffs awaiting user approval."""
    return {"patches": agent.get_pending_patches()}

@app.post("/api/agent/approve-patch")
async def approve_patch(approval: PatchApproval):
    """Safely apply or reject a self-repair code patch."""
    result = agent.handle_patch_approval(approval.patch_id, approval.approved)
    return JSONResponse(content=result)
