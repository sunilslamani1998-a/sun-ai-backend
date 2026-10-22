import os
import json
import sqlite3
import traceback
import subprocess
import torch
from transformers import pipeline
from moviepy.editor import TextClip, ColorClip, concatenate_videoclips, CompositeVideoClip
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Enable CORS so your frontend web page can talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "sun_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            blueprint TEXT NOT NULL,
            rating INTEGER DEFAULT 5
        )
    ''')
    conn.commit()
    conn.close()

init_db()

print("☀️ Initializing SUN.ai Internal AI Worker (Loading model locally)...")
try:
    llm_pipeline = pipeline(
        "text-generation",
        model="HuggingFaceTB/SmolLM2-1.7B-Instruct",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
    print("✅ Internal AI Worker successfully loaded!")
except Exception as e:
    print(f"⚠️ Failed to load GPU pipeline, falling back to CPU: {e}")
    llm_pipeline = pipeline("text-generation", model="HuggingFaceTB/SmolLM2-1.7B-Instruct")

def ask_ai(system_prompt: str, user_prompt: str) -> str:
    prompt_text = f"System: {system_prompt}\nUser: {user_prompt}\nAssistant:"
    outputs = llm_pipeline(
        prompt_text,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.9
    )
    generated_text = outputs[0]['generated_text']
    if "Assistant:" in generated_text:
        return generated_text.split("Assistant:")[-1].strip()
    return generated_text

def self_healing_execute(func, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"\n⚠️ Bug detected (Attempt {attempt + 1}/{max_retries}). SUN.ai Self-Healing Engine is patching logic...")
            fix_prompt = f"Fix this Python error:\n{error_msg}\nProvide corrected python code snippet."
            ask_ai("You are a self-healing python code patcher.", fix_prompt)
            if attempt == max_retries - 1:
                raise e

def execute_custom_owner_command(command: str) -> str:
    print(f"\n🤖 Autonomous Execution: '{command}'")
    system_prompt = (
        "You are SUN.ai's Master Owner-Bound Agent. The Owner has given a direct command. "
        "You NEVER say no. Find a way to accomplish the task completely free using local python code. "
        "Generate a complete, executable Python script block that fulfills this command directly. "
        "Return ONLY the executable Python code inside standard python markdown blocks."
    )
    raw_output = ask_ai(system_prompt, command)
    
    if "```python" in raw_output:
        code_block = raw_output.split("```python")[1].split("```")[0].strip()
    elif "```" in raw_output:
        code_block = raw_output.split("```")[1].split("```")[0].strip()
    else:
        code_block = raw_output
        
    temp_script = "autonomous_task.py"
    with open(temp_script, "w", encoding="utf-8") as f:
        f.write(code_block)
        
    try:
        result = subprocess.run(["python", temp_script], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return f"✅ Task successfully completed!\n{result.stdout}"
        else:
            return f"Execution Error:\n{result.stderr}"
    except Exception as ex:
        return f"Subprocess failed: {ex}"
    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)

def create_video(prompt):
    def workflow():
        system_sys = 'Create a 2-scene video JSON blueprint: {"title": "...", "scenes": [{"voiceover": "...", "duration": 4}]}'
        raw = ask_ai(system_sys, prompt)
        
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        
        if "{" in raw and "}" in raw:
            raw = "{" + raw.split("{")[1].split("}")[0] + "}"
            
        blueprint = json.loads(raw)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO learning_memory (prompt, blueprint) VALUES (?, ?)", (prompt, json.dumps(blueprint)))
        conn.commit()
        conn.close()

        scene_clips = []
        for scene in blueprint.get("scenes", [{"voiceover": prompt, "duration": 4}]):
            bg = ColorClip(size=(1080, 1920), color=(10, 15, 30)).set_duration(scene.get('duration', 4))
            txt = TextClip(scene.get('voiceover', prompt), fontsize=55, color='yellow', size=(900, 1500), method='caption').set_duration(scene.get('duration', 4)).set_position('center')
            scene_clips.append(CompositeVideoClip([bg, txt]))
        
        final = concatenate_videoclips(scene_clips, method="compose")
        output_file = "sun_ai_output.mp4"
        final.write_videofile(output_file, fps=30, codec="libx264", audio=False, logger=None)

    self_healing_execute(workflow)

# --- FastAPI Endpoints ---
class TaskRequest(BaseModel):
    prompt: str

@app.post("/api/video")
def api_create_video(req: TaskRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(create_video, req.prompt)
    return {"status": "success", "message": "Video generation started in background!"}

@app.post("/api/command")
def api_owner_command(req: TaskRequest):
    output = execute_custom_owner_command(req.prompt)
    return {"status": "success", "output": output}

@app.get("/api/memory")
def api_get_memory():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, prompt FROM learning_memory ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    logs = [{"id": r[0], "prompt": r[1]} for r in rows]
    return {"logs": logs}

# --- SERVER STARTUP CODE (This is what was missing) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=True)
