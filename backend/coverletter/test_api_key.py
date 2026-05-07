"""
Simple script to test if your API key is valid
"""
import sys
import os

def test_gemini_key(api_key):
    """Test Gemini API key"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        response = model.generate_content("Say 'Hello'")
        print("✅ Gemini API Key is VALID!")
        print(f"Response: {response.text[:50]}")
        return True
    except Exception as e:
        print(f"❌ Gemini API Key is INVALID")
        print(f"Error: {str(e)[:200]}")
        return False

def test_groq_key(api_key):
    """Test Groq API key"""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say 'Hello'"}],
            max_tokens=10
        )
        print("✅ Groq API Key is VALID!")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ Groq API Key is INVALID")
        print(f"Error: {str(e)[:200]}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_api_key.py <provider> <api_key>")
        print("Example: python test_api_key.py gemini AIza...")
        print("Example: python test_api_key.py groq gsk_...")
        sys.exit(1)
    
    provider = sys.argv[1].lower()
    api_key = sys.argv[2]
    
    print(f"\nTesting {provider.upper()} API key...")
    print(f"Key length: {len(api_key)} characters")
    print(f"Key starts with: {api_key[:4]}...")
    print("-" * 50)
    
    if provider == "gemini":
        test_gemini_key(api_key)
    elif provider == "groq":
        test_groq_key(api_key)
    else:
        print(f"Unknown provider: {provider}")
        print("Use 'gemini' or 'groq'")

if __name__ == "__main__":
    main()


