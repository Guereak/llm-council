#!/usr/bin/env python3
"""
LLM Council Node Server

This script provides a lightweight wrapper around Ollama for remote LLM nodes.
Run this on each machine that will participate in the distributed LLM council.

Features:
- Exposes Ollama models over the network
- Provides node metadata and health endpoints
- Optional authentication (via API key)
- Automatic model discovery

Usage:
    # Basic usage (uses Ollama defaults)
    python node_server.py

    # Custom port
    python node_server.py --port 8080

    # With authentication
    python node_server.py --api-key your-secret-key

    # Specify models to advertise
    python node_server.py --models llama3.2 mistral

Environment Variables:
    NODE_NAME: Human-readable name for this node (default: hostname)
    NODE_PORT: Port to run the server on (default: 8080)
    NODE_API_KEY: API key for authentication (optional)
    OLLAMA_HOST: Ollama host URL (default: http://localhost:11434)
"""

import argparse
import os
import socket
from typing import List, Dict, Any, Optional
from datetime import datetime

import ollama
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


# =============================================================================
# Configuration
# =============================================================================

NODE_NAME = os.getenv("NODE_NAME", socket.gethostname())
NODE_PORT = int(os.getenv("NODE_PORT", "8080"))
NODE_API_KEY = os.getenv("NODE_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Parse Ollama host for the client
from urllib.parse import urlparse
parsed = urlparse(OLLAMA_HOST)
ollama_client = ollama.Client(host=f"{parsed.hostname}:{parsed.port or 11434}")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title=f"LLM Council Node: {NODE_NAME}",
    description="A node in the distributed LLM Council network",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Authentication
# =============================================================================

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if authentication is enabled."""
    if NODE_API_KEY and x_api_key != NODE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


# =============================================================================
# Models
# =============================================================================

class ChatMessage(BaseModel):
    """A chat message."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request to chat with a model."""
    model: str
    messages: List[ChatMessage]
    options: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response from a chat request."""
    model: str
    message: ChatMessage
    node: str
    done: bool


class NodeInfo(BaseModel):
    """Information about this node."""
    name: str
    host: str
    port: int
    models: List[str]
    ollama_host: str
    uptime: str
    authenticated: bool


# =============================================================================
# State
# =============================================================================

_start_time = datetime.now()
_advertised_models: List[str] = []


def set_advertised_models(models: List[str]):
    """Set the list of models this node advertises."""
    global _advertised_models
    _advertised_models = models


def get_uptime() -> str:
    """Get the node uptime as a human-readable string."""
    delta = datetime.now() - _start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "node": NODE_NAME,
        "service": "LLM Council Node",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    try:
        # Check Ollama connectivity
        response = ollama_client.list()
        ollama_status = "ok"
        # Handle both old dict format and new object format from Ollama library
        if hasattr(response, 'models'):
            available_models = [m.model.split(':')[0] for m in response.models]
        else:
            available_models = [m.get('name', '').split(':')[0] for m in response.get('models', [])]
    except Exception as e:
        ollama_status = f"error: {e}"
        available_models = []

    return {
        "status": "ok" if ollama_status == "ok" else "degraded",
        "node": NODE_NAME,
        "ollama_status": ollama_status,
        "available_models": available_models,
        "advertised_models": _advertised_models or available_models,
        "uptime": get_uptime(),
    }


@app.get("/info", response_model=NodeInfo)
async def get_info():
    """Get information about this node."""
    try:
        models = ollama_client.list()
        available_models = [m.get('name', '').split(':')[0] for m in models.get('models', [])]
    except Exception:
        available_models = []
    
    return NodeInfo(
        name=NODE_NAME,
        host=socket.gethostname(),
        port=NODE_PORT,
        models=_advertised_models or available_models,
        ollama_host=OLLAMA_HOST,
        uptime=get_uptime(),
        authenticated=NODE_API_KEY is not None,
    )


@app.get("/models")
async def list_models():
    """List available models on this node."""
    try:
        models = ollama_client.list()
        available_models = []
        for m in models.get('models', []):
            available_models.append({
                "name": m.get('name', ''),
                "size": m.get('size', 0),
                "modified_at": m.get('modified_at', ''),
            })
        return {
            "models": available_models,
            "advertised": _advertised_models,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to list models: {e}")


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest):
    """
    Chat with a model on this node.
    
    This endpoint mirrors the Ollama chat API but adds node information.
    """
    try:
        # Convert messages to dict format
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        # Call Ollama
        response = ollama_client.chat(
            model=request.model,
            messages=messages,
            options=request.options or {},
        )
        
        message = response.get('message', {})
        
        return ChatResponse(
            model=request.model,
            message=ChatMessage(
                role=message.get('role', 'assistant'),
                content=message.get('content', ''),
            ),
            node=NODE_NAME,
            done=response.get('done', True),
        )
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Chat failed: {e}")


@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate(request: Dict[str, Any]):
    """
    Generate text with a model (non-chat completion).
    
    Accepts the same format as Ollama's generate endpoint.
    """
    try:
        model = request.get('model')
        prompt = request.get('prompt')
        
        if not model or not prompt:
            raise HTTPException(status_code=400, detail="'model' and 'prompt' are required")
        
        response = ollama_client.generate(
            model=model,
            prompt=prompt,
            options=request.get('options', {}),
        )
        
        return {
            "model": model,
            "response": response.get('response', ''),
            "node": NODE_NAME,
            "done": response.get('done', True),
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Generate failed: {e}")


# =============================================================================
# Main
# =============================================================================

def main():
    # Update globals
    global NODE_NAME, NODE_PORT, NODE_API_KEY

    parser = argparse.ArgumentParser(description="LLM Council Node Server")
    parser.add_argument("--port", type=int, default=NODE_PORT, help="Port to run on")
    parser.add_argument("--name", type=str, default=NODE_NAME, help="Node name")
    parser.add_argument("--api-key", type=str, default=NODE_API_KEY, help="API key for auth")
    parser.add_argument("--models", nargs="+", help="Models to advertise")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")

    args = parser.parse_args()
    NODE_NAME = args.name
    NODE_PORT = args.port
    NODE_API_KEY = args.api_key
    
    if args.models:
        set_advertised_models(args.models)
    
    print(f"🚀 Starting LLM Council Node: {NODE_NAME}")
    print(f"   Port: {args.port}")
    print(f"   Ollama: {OLLAMA_HOST}")
    print(f"   Auth: {'enabled' if args.api_key else 'disabled'}")
    if args.models:
        print(f"   Models: {', '.join(args.models)}")
    print()
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

