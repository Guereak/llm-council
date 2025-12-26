"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# Ollama API URL
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")

# Council members - list of Ollama model names
COUNCIL_MODELS = [
    "qwen3:4b",
    "gemma3:4b",
]
    
# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "mistral"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
