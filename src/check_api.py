import os
import google.generativeai as genai
from dotenv import load_dotenv

def check_api():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] GOOGLE_API_KEY not found in environment variables or .env file.")
        return

    print(f"[*] Found API Key: {api_key[:5]}...{api_key[-5:]}")
    genai.configure(api_key=api_key)

    print("[*] Listing available models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"   - {m.name}")
        
        print("\n[*] Testing generation with gemini-2.0-flash-exp (fastest check)...")
        try:
             # Fallback to a generally available model if specific 2.0/3.0 not found
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("Hello, this is a test.")
            print(f"[*] Response received: {response.text.strip()}")
            print("[SUCCESS] API is working correctly.")
        except Exception as e:
            print(f"[!] Generation failed: {e}")

    except Exception as e:
        print(f"[!] Failed to list models: {e}")

if __name__ == "__main__":
    check_api()
