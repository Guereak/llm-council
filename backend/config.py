"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key (kept for backward compatibility, not used with Ollama)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Ollama API URL (default: http://localhost:11434)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")

# Council members - list of Ollama model names
# Common models: llama3.2, mistral, qwen2.5, phi3, gemma2, etc.
# Run `ollama list` to see available models on your system
COUNCIL_MODELS = [
    "mistral",
    "qwen3:4b",
    "gemma3:4b",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "mistral"

# OpenRouter API endpoint (kept for backward compatibility)
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
