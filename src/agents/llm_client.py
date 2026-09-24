# src/agents/llm_client.py
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def call_llm(prompt: str, model: str = "gemini-3.6-flash") -> str:
    """Call Gemini and return text response."""
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text.strip()


if __name__ == "__main__":
    print(call_llm("Say hello in one sentence."))