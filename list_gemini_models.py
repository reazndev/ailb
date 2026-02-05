from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found.")
    exit()

client = genai.Client(api_key=api_key)

print("Listing available Gemini models...")
try:
    for m in client.models.list():
        if m.supported_actions and 'generateContent' in m.supported_actions:
            print(f"- {m.name.replace('models/', '')}")
except Exception as e:
    print(f"Error: {e}")
