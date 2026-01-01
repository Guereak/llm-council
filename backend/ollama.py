"""Ollama API client for making LLM requests to local models using the official Ollama Python package."""

import ollama
from typing import List, Dict, Any, Optional
from .config import OLLAMA_API_URL


def _get_ollama_client():
    """
    Get an Ollama client instance, configured with custom host if needed.
    
    The ollama package supports custom hosts via the Client constructor.
    If OLLAMA_API_URL is set to a non-default value, we extract the host:port
    and create a custom client.
    
    Returns:
        Ollama client instance
    """
    # Default is localhost:11434, so only create custom client if URL differs
    if OLLAMA_API_URL != "http://localhost:11434":
        # Extract host from URL (e.g., "http://localhost:11434" -> "localhost:11434")
        from urllib.parse import urlparse
        
        parsed = urlparse(OLLAMA_API_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 11434
        
        # Create client with custom host
        # The ollama.Client accepts host as a string like "hostname:port"
        return ollama.Client(host=f"{host}:{port}")
    
    # Use default client (localhost:11434)
    # The ollama package uses module-level functions by default, but Client() 
    # without args also works for the default host
    return ollama.Client()


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via Ollama API using the official Python package.

    Args:
        model: Ollama model name (e.g., "llama3.2", "mistral", "qwen2.5")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds (not directly supported by ollama package)

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    try:
        # Get the configured Ollama client
        client = _get_ollama_client()
        
        # Use ollama.chat() for synchronous calls, wrap in asyncio for async compatibility
        import asyncio
        
        # Run the blocking client.chat() call in a thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat(
                model=model,
                messages=messages,
                options={
                    # You can add Ollama-specific options here if needed
                    # e.g., 'temperature': 0.7, 'num_predict': 512
                }
            )
        )

        message = response.get('message', {})

        return {
            'content': message.get('content', ''),
            'reasoning_details': None  # Ollama doesn't provide reasoning details
        }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of Ollama model names
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model name to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}

