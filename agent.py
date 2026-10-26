from google import genai
from google.genai import types
import os

# Initialize the Gemini client. It automatically picks up GEMINI_API_KEY from your Render environment variables.
client = genai.Client()

async def ask_ai(prompt: str) -> str:
    """
    Sends the prompt to Gemini 3.8 Flash using native async execution, 
    custom system instructions, and advanced configuration settings.
    """
    try:
        # Using the native asynchronous client call for maximum FastAPI performance
        response = await client.aio.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are SUN.AI, an elite, highly intelligent, and precise AI assistant "
                    "embedded in a custom cloud-hosted backend. Provide clear, direct, "
                    "and brilliantly structured answers."
                ),
                temperature=0.7,
                max_output_tokens=2048,
            ),
        )
        return response.text
    except Exception as e:
        raise RuntimeError(f"Advanced AI provider request failed: {str(e)}")
