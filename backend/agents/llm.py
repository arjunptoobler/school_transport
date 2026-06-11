import json
import requests
from ..config import settings


def call_gemini(prompt: str, system_instruction: str = None, tools: list = None):
    """Call the Gemini API using standard HTTP REST requests.

    Avoids library-specific version mismatches and handles 429 rate limits
    gracefully by falling back to database outputs. Supports native function calling.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None if not tools else {"text": "", "functionCall": None}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if tools:
        payload["tools"] = [{"functionDeclarations": tools}]

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=8.0)
        if response.status_code == 200:
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            text_content = ""
            function_call = None
            for part in parts:
                if "text" in part:
                    text_content += part["text"]
                if "functionCall" in part:
                    function_call = part["functionCall"]
            
            if tools:
                return {"text": text_content.strip(), "functionCall": function_call}
            else:
                return text_content.strip()
        elif response.status_code == 429:
            print("[Gemini API Warning] Rate limit (429) hit. Gracefully falling back.")
            return None if not tools else {"text": "", "functionCall": None}
        else:
            print(f"[Gemini API Error] Status {response.status_code}: {response.text}")
            return None if not tools else {"text": "", "functionCall": None}
    except Exception as e:
        print(f"[Gemini API Exception] {e}")
        return None if not tools else {"text": "", "functionCall": None}

