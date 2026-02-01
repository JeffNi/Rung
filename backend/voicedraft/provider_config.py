# Provider configuration for AI models

# Model mappings for each provider
PROVIDER_MODELS = {
    "gemini": "models/gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile"  # Primary model
}

# Fallback models for when primary hits quota
FALLBACK_MODELS = {
    "groq": ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]  # Faster models with separate quotas
}

def get_model_for_provider(provider: str) -> str:
    """Get the default model for a provider"""
    return PROVIDER_MODELS.get(provider.lower(), PROVIDER_MODELS["gemini"])

def get_fallback_models(provider: str) -> list:
    """Get fallback models for a provider"""
    return FALLBACK_MODELS.get(provider.lower(), [])

