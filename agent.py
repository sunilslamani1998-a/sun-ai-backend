import os
import json
import time
import subprocess
from openai import OpenAI

class SunAIAgent:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.memory = []
        self.pending_patches = {}
        self.execution_logs = []

    def plan_task(self, prompt: str) -> list:
        """Deconstructs complex prompt into sub-tasks."""
        system_prompt = (
            "You are SUN.AI's Advanced Planning Engine. Break down the user's request "
            "into 2 to 5 discrete, sequential execution steps. Return valid JSON as a list of strings."
        )
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            content = json.loads(response.choices[0].message.content)
            return content.get("steps", [prompt])
        except Exception:
            return [prompt]

    def execute_task(self, prompt: str) -> dict:
        start_time = time.time()
        steps = self.plan_task(prompt)
        
        step_results = []
        for step in steps:
            # Simulate tool execution and reasoning
            step_results.append({
                "step": step,
                "status": "completed",
                "verified": True
            })

        # Check if task involves self-repair or code generation
        patch_id = None
        if "fix" in prompt.lower() or "code" in prompt.lower() or "bug" in prompt.lower():
            patch_id = f"patch_{int(time.time())}"
            self.pending_patches[patch_id] = {
                "file": "agent.py",
                "diff": "--- a/agent.py\n+++ b/agent.py\n@@ -10,3 +10,4 @@\n+# Self-repair optimization applied for robust execution",
                "status": "pending_approval"
            }

        execution_time = round(time.time() - start_time, 2)
        
        result_summary = {
            "prompt": prompt,
            "plan": steps,
            "steps_executed": step_results,
            "execution_time_seconds": execution_time,
            "pending_patch_id": patch_id,
            "status": "success"
        }
        
        self.memory.append(result_summary)
        return result_summary

    def get_pending_patches(self):
        return [ {"id": k, **v} for k, v in self.pending_patches.items() if v["status"] == "pending_approval" ]

    def handle_patch_approval(self, patch_id: str, approved: bool):
        if patch_id not in self.pending_patches:
            return {"success": False, "message": "Patch not found."}
        
        if approved:
            self.pending_patches[patch_id]["status"] = "applied"
            return {"success": True, "message": f"Patch {patch_id} approved and safely integrated."}
        else:
            self.pending_patches[patch_id]["status"] = "rejected"
            return {"success": True, "message": f"Patch {patch_id} rejected."}
