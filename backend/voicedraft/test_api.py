import google.generativeai as genai
import sys

print("=== Gemini API Test ===\n")

# Get API key from command line
if len(sys.argv) < 2:
    print("Usage: python test_api.py YOUR_API_KEY")
    print("\nOr copy your API key from the Rung Account page and run:")
    print("  python test_api.py <paste-key-here>")
    exit(1)

api_key = sys.argv[1].strip()

if not api_key:
    print("ERROR: No API key provided!")
    exit(1)

print(f"API key length: {len(api_key)} characters\n")

# Configure API
genai.configure(api_key=api_key)

# Test 1: List available models
print("--- Test 1: Listing available models ---")
try:
    models = list(genai.list_models())
    print(f"Found {len(models)} models:")
    for m in models[:10]:  # Show first 10
        if 'generateContent' in m.supported_generation_methods:
            print(f"  ✓ {m.name}")
    print()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}\n")

# Test 2: Try different model names
test_models = [
    "models/gemini-1.5-flash",
    "models/gemini-1.5-pro",
    "gemini-1.5-flash",
    "models/gemini-pro",
    "gemini-pro"
]

for model_name in test_models:
    print(f"--- Test: {model_name} ---")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello, this works!'")
        print(f"✓ SUCCESS! Response: {response.text[:100]}")
        print(f"\n🎉 WORKING MODEL: {model_name}\n")
        break
    except Exception as e:
        print(f"✗ FAILED: {type(e).__name__}: {str(e)[:200]}")
    print()

print("\n=== Test Complete ===")

