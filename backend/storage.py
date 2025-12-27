"""JSON-based storage for conversations."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_conversation_path(conversation_id: str) -> str:
    """Get the file path for a conversation."""
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


def create_conversation(conversation_id: str, conversation_type: str = "chat") -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation
        conversation_type: Type of conversation ("chat" or "code")

    Returns:
        New conversation dict
    """
    ensure_data_dir()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "type": conversation_type,
        "messages": []
    }
    
    if conversation_type == "code":
        conversation["code_generations"] = []

    # Save to file
    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict to save
    """
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def list_conversations(conversation_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Args:
        conversation_type: Optional filter by type ("chat" or "code")

    Returns:
        List of conversation metadata dicts
    """
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                conv_type = data.get("type", "chat")
                
                # Filter by type if specified
                if conversation_type and conv_type != conversation_type:
                    continue
                
                # Return metadata only
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "title": data.get("title", "New Conversation"),
                    "type": conv_type,
                    "message_count": len(data.get("messages", [])),
                    "code_generation_count": len(data.get("code_generations", []))
                })

    # Sort by creation time, newest first
    conversations.sort(key=lambda x: x["created_at"], reverse=True)

    return conversations


def add_user_message(conversation_id: str, content: str):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "user",
        "content": content
    })

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any]
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    })

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(conversation)


# =============================================================================
# CODE CONVERSATION FUNCTIONS
# =============================================================================

def add_code_specification(conversation_id: str, specification: str, language: Optional[str] = None, framework: Optional[str] = None):
    """
    Add a code specification to a code conversation.

    Args:
        conversation_id: Conversation identifier
        specification: Code requirements/specification
        language: Programming language (optional)
        framework: Framework/library (optional)
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    
    if conversation.get("type") != "code":
        raise ValueError(f"Conversation {conversation_id} is not a code conversation")

    conversation["messages"].append({
        "role": "user",
        "content": specification,
        "specification": specification,
        "language": language,
        "framework": framework
    })

    save_conversation(conversation)


def add_code_generation(
    conversation_id: str,
    specification: str,
    iterations: List[Dict[str, Any]],
    final_code: str,
    final_tests: str,
    tests: List[Dict[str, Any]],
    metadata: Dict[str, Any]
):
    """
    Add a code generation result to a code conversation.

    Args:
        conversation_id: Conversation identifier
        specification: Original specification
        iterations: List of iteration data
        final_code: Final synthesized code
        final_tests: Final synthesized tests
        tests: List of test submissions
        metadata: Metadata (language, framework, etc.)
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    
    if conversation.get("type") != "code":
        raise ValueError(f"Conversation {conversation_id} is not a code conversation")

    code_generation = {
        "specification": specification,
        "created_at": datetime.utcnow().isoformat(),
        "iterations": iterations,
        "final_code": final_code,
        "final_tests": final_tests,
        "tests": tests,
        "metadata": metadata
    }
    
    if "code_generations" not in conversation:
        conversation["code_generations"] = []
    
    conversation["code_generations"].append(code_generation)
    
    # Also add as assistant message for consistency
    conversation["messages"].append({
        "role": "assistant",
        "type": "code_generation",
        "code_generation": code_generation
    })

    save_conversation(conversation)
