import google.generativeai as genai
from ..config import settings


def call_gemini(prompt: str, system_instruction: str = None) -> str:
    """Call the Gemini API using google-generativeai client.

    Returns None if key is missing or if the API call fails, allowing
    agents to fall back to structured database lookups safely.
    """
    if not settings.GEMINI_API_KEY:
        return None
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction,
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini API Call Exception] {e}")
        return None
