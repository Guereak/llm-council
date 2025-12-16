# Migration Guide: OpenRouter → Ollama

This guide walks you through the changes made to replace OpenRouter with local Ollama models.

## What Changed

### 1. New File: `backend/ollama.py`
- Created a new Ollama API client that mirrors the interface of `openrouter.py`
- Uses the official `ollama` Python package instead of direct HTTP calls
- Uses the same function signatures (`query_model`, `query_models_parallel`) so the rest of the codebase works without changes
- Connects to Ollama's local API endpoint (default: `http://localhost:11434`)
- Supports custom hosts via `OLLAMA_API_URL` configuration

### 2. Updated: `backend/config.py`
- Added `OLLAMA_API_URL` configuration (defaults to `http://localhost:11434`)
- Changed `COUNCIL_MODELS` to use Ollama model names instead of OpenRouter identifiers
- Changed `CHAIRMAN_MODEL` to use an Ollama model name
- OpenRouter config kept for backward compatibility (not used)

### 3. Updated: `backend/council.py`
- Changed import from `openrouter` to `ollama`
- Updated title generation to use the first council model instead of a hardcoded OpenRouter model

## Setup Instructions

### Step 1: Install Ollama

If you haven't already, install Ollama:
- **macOS/Linux**: Visit [ollama.ai](https://ollama.ai) and download
- **Windows**: Download from [ollama.ai](https://ollama.ai)

### Step 1.5: Install Python Dependencies

The project now uses the official `ollama` Python package. Install it:

```bash
uv sync
```

This will install the `ollama` package along with other dependencies.

### Step 2: Pull Models

Pull the models you want to use in your council. Common options:

```bash
# Pull some popular models
ollama pull llama3.2
ollama pull mistral
ollama pull qwen2.5
ollama pull phi3
ollama pull gemma2
```

To see all available models: `ollama list`

### Step 3: Configure Models

Edit `backend/config.py` and update the model names to match what you've pulled:

```python
COUNCIL_MODELS = [
    "llama3.2",      # Replace with your models
    "mistral",
    "qwen2.5",
    "phi3",
]

CHAIRMAN_MODEL = "llama3.2"  # Replace with your preferred chairman
```

### Step 4: Configure Ollama URL (Optional)

If Ollama is running on a different host/port, set it in your `.env` file:

```bash
OLLAMA_API_URL=http://localhost:11434
```

Or if running on a remote server:
```bash
OLLAMA_API_URL=http://192.168.1.100:11434
```

### Step 5: Start Ollama

Make sure Ollama is running:

```bash
ollama serve
```

This starts the Ollama API server on `http://localhost:11434` (default).

### Step 6: Run the Application

The application should now work with local Ollama models! Start it as usual:

```bash
./start.sh
```

Or manually:
```bash
# Terminal 1
uv run python -m backend.main

# Terminal 2
cd frontend && npm run dev
```

## Key Differences: OpenRouter vs Ollama

| Aspect | OpenRouter | Ollama |
|--------|-----------|--------|
| **API Endpoint** | `https://openrouter.ai/api/v1/chat/completions` | `http://localhost:11434/api/chat` |
| **Model Names** | `openai/gpt-4o`, `google/gemini-2.0-flash` | `llama3.2`, `mistral`, `qwen2.5` |
| **Authentication** | API key required | None (local) |
| **Cost** | Pay per request | Free (runs locally) |
| **Speed** | Depends on provider | Depends on your hardware |
| **Privacy** | Data sent to external APIs | All processing local |

## Troubleshooting

### "Connection refused" error
- Make sure Ollama is running: `ollama serve`
- Check the `OLLAMA_API_URL` in your `.env` file matches where Ollama is running

### "Model not found" error
- The model name in `config.py` doesn't match what you've pulled
- Run `ollama list` to see available models
- Pull the model: `ollama pull <model-name>`

### Slow responses
- Local models run on your hardware, so speed depends on your CPU/GPU
- Consider using smaller/faster models for the council
- Use GPU acceleration if available (Ollama will use it automatically if configured)

## Switching Back to OpenRouter

If you want to switch back to OpenRouter:

1. In `backend/council.py`, change the import:
   ```python
   from .openrouter import query_models_parallel, query_model
   ```

2. In `backend/config.py`, restore OpenRouter model names:
   ```python
   COUNCIL_MODELS = [
       "openai/gpt-5.1",
       "google/gemini-3-pro-preview",
       # etc.
   ]
   ```

3. Make sure your `.env` has `OPENROUTER_API_KEY` set

## Advanced: Supporting Both

You could modify the code to support both OpenRouter and Ollama by:
- Adding a `PROVIDER` config option (`"ollama"` or `"openrouter"`)
- Creating a provider abstraction layer
- Conditionally importing the appropriate client

This is left as an exercise for the reader! 🚀

