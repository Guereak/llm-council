import ollama
from typing import List, Dict, Any, Optional
from .config import OLLAMA_API_URL
import asyncio


def _get_ollama_client():
    """ Get an Ollama client instance """    
    return ollama.Client()


async def query_model(
    model_name: str,
    messages: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    try:
        client = _get_ollama_client()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat(
                model=model_name,
                messages=messages
            )
        )

        message = response.get('message', {})

        return {
            'content': message.get('content', ''),
        }

    except Exception as e:
        print(f"Error querying model {model_name}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """ Query multiple models in parallel """

    tasks = [query_model(model, messages) for model in models]

    responses = await asyncio.gather(*tasks)

    # Map models to responses
    return {model: response for model, response in zip(models, responses)}

