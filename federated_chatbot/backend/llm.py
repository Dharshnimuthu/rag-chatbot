import requests
import os

OLLAMA_API = os.getenv("OLLAMA_API", "http://localhost:11434/api/generate")

def generate_with_phi3(prompt: str, max_tokens: int = 250):
    payload = {
        "model": "phi3",
        "prompt": prompt,
        "stream": False,
        "max_tokens": max_tokens
    }

    try:
        resp = requests.post(OLLAMA_API, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response") or data.get("text") or ""
    except Exception as e:
        return f"[LLM ERROR] {e}"
