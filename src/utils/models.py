import os
import openai
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_available_models(provider: str) -> list[str]:
    """
    Returns a list of available model names for the given provider.
    Falls back to a default list if fetching fails or is not supported.
    """
    provider = provider.lower()
    
    try:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key: return ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            client = openai.OpenAI(api_key=api_key)
            models = client.models.list()
            # Filter for likely chat models to reduce noise
            return sorted([m.id for m in models.data if "gpt" in m.id])

        elif provider == "anthropic":
            # Anthropic doesn't have a public "list models" endpoint in the same way, 
            # or it requires strict versioning. We'll return the known stable ones.
            return [
                "claude-3-5-sonnet-20240620",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]

        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key: return ["gemini-1.5-pro", "gemini-1.5-flash"]
            client = genai.Client(api_key=api_key)
            models = client.models.list()
            # Filter for generateContent support
            return sorted([m.name.replace("models/", "") for m in models if m.supported_actions and "generateContent" in m.supported_actions])

        elif provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key: return ["deepseek-chat", "deepseek-coder"]
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            models = client.models.list()
            return sorted([m.id for m in models.data])

        elif provider == "openrouter":
            # OpenRouter has a lot of models. Fetching can be slow.
            # We can try to fetch, but falling back to a curated list is often safer for UI responsiveness
            # unless we implement caching. Let's try fetching.
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key: return ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5"]
            
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            models = client.models.list()
            # OpenRouter IDs are like "vendor/model-name"
            return sorted([m.id for m in models.data])

    except Exception as e:
        print(f"Error fetching models for {provider}: {e}")
        # Fallbacks
        if provider == "openai": return ["gpt-4o", "gpt-4-turbo"]
        if provider == "anthropic": return ["claude-3-opus-20240229"]
        if provider == "gemini": return ["gemini-1.5-pro"]
        if provider == "deepseek": return ["deepseek-chat"]
        if provider == "openrouter": return ["openai/gpt-4o"]
    
    return ["default-model"]
