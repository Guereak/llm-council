"""Configuration for the LLM Council."""

import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMNode:
    """Represents a remote LLM node in the distributed council."""
    name: str                          # Human-readable node name
    host: str                          # Hostname or IP address
    port: int = 8080                   # Node server port (default: 8080)
    models: List[str] = field(default_factory=list)  # Models available on this node
    is_chairman: bool = False          # Whether this node hosts the chairman model
    chairman_model: Optional[str] = None  # Specific model to use as chairman (if is_chairman)
    enabled: bool = True               # Whether this node is active
    timeout: float = 120.0             # Request timeout for this node
    api_key: Optional[str] = None      # API key for node authentication (optional)
    
    @property
    def url(self) -> str:
        """Get the full URL for this node."""
        return f"http://{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "models": self.models,
            "is_chairman": self.is_chairman,
            "chairman_model": self.chairman_model,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "api_key": self.api_key,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMNode":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            host=data["host"],
            port=data.get("port", 8080),
            models=data.get("models", []),
            is_chairman=data.get("is_chairman", False),
            chairman_model=data.get("chairman_model"),
            enabled=data.get("enabled", True),
            timeout=data.get("timeout", 120.0),
            api_key=data.get("api_key"),
        )


# =============================================================================
# DISTRIBUTED NODE CONFIGURATION
# =============================================================================
# 
# Configure your LLM council nodes here. Each node represents a machine
# running Ollama with one or more models.
#
# For a single-machine setup, just configure one node with localhost.
# For distributed setup, add multiple nodes with their network addresses.
#
# Example distributed setup:
#   - Node 1 (192.168.1.10): llama3.2, gemma2
#   - Node 2 (192.168.1.11): mistral, phi3  
#   - Node 3 (192.168.1.12): qwen2.5 (Chairman)
#
# =============================================================================

# Load nodes from environment variable (JSON) or use defaults
_nodes_json = os.getenv("LLM_COUNCIL_NODES")

if _nodes_json:
    # Parse nodes from environment variable
    try:
        _nodes_data = json.loads(_nodes_json)
        COUNCIL_NODES: List[LLMNode] = [LLMNode.from_dict(n) for n in _nodes_data]
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse LLM_COUNCIL_NODES: {e}")
        COUNCIL_NODES = []
else:
    # Default configuration - single localhost node
    # Changes made via API will only persist for the current session
    COUNCIL_NODES: List[LLMNode] = [
        LLMNode(
            name="local",
            host="localhost",
            port=8080,  # node_server.py default port
            models=["gemma3:4b", "mistral"],
            is_chairman=True,
            chairman_model="mistral",
            enabled=True,
        ),
        LLMNode(
            name="Gabin",
            host="10.1.181.9",
            port=8080,
            models=["gemma3:1b"],
            is_chairman=False,
            enabled=True,
        ),
        LLMNode(
            name="Nathan",
            host="10.1.184.150",
            port=8080,
            models=["llama3.2:1b"],
            enabled=True,
        ),
    ]


def get_all_nodes() -> List[LLMNode]:
    """
    Get all nodes (for CRUD operations).
    Returns the in-memory list of nodes.
    """
    return COUNCIL_NODES


def get_enabled_nodes() -> List[LLMNode]:
    """Get all enabled nodes."""
    return [node for node in COUNCIL_NODES if node.enabled]


def add_node(node: LLMNode) -> None:
    """
    Add a node to the in-memory list.
    Changes are only valid for the current session.
    """
    global COUNCIL_NODES
    # Check if node with same name exists
    if any(n.name == node.name for n in COUNCIL_NODES):
        raise ValueError(f"Node with name '{node.name}' already exists")
    COUNCIL_NODES.append(node)


def update_node(node_name: str, updated_node: LLMNode) -> None:
    """
    Update a node in the in-memory list.
    Changes are only valid for the current session.
    """
    global COUNCIL_NODES
    # Find the node to update
    node_index = None
    for i, n in enumerate(COUNCIL_NODES):
        if n.name == node_name:
            node_index = i
            break
    
    if node_index is None:
        raise ValueError(f"Node '{node_name}' not found")
    
    # Check for name conflicts if name is being changed
    if updated_node.name != node_name:
        if any(n.name == updated_node.name for n in COUNCIL_NODES):
            raise ValueError(f"Node with name '{updated_node.name}' already exists")
    
    COUNCIL_NODES[node_index] = updated_node


def remove_node(node_name: str) -> None:
    """
    Remove a node from the in-memory list.
    Changes are only valid for the current session.
    """
    global COUNCIL_NODES
    original_len = len(COUNCIL_NODES)
    COUNCIL_NODES = [n for n in COUNCIL_NODES if n.name != node_name]
    
    if len(COUNCIL_NODES) == original_len:
        raise ValueError(f"Node '{node_name}' not found")


def get_node(node_name: str) -> Optional[LLMNode]:
    """Get a specific node by name."""
    for node in COUNCIL_NODES:
        if node.name == node_name:
            return node
    return None


def get_all_council_models() -> List[Dict[str, Any]]:
    """
    Get all council models across all enabled nodes.
    
    Returns:
        List of dicts with 'model', 'node_name', 'node_url' keys
    """
    models = []
    for node in get_enabled_nodes():
        for model in node.models:
            models.append({
                "model": model,
                "node_name": node.name,
                "node_url": node.url,
                "timeout": node.timeout,
            })
    return models


def get_chairman_config() -> Optional[Dict[str, Any]]:
    """
    Get the chairman model configuration.
    
    Returns:
        Dict with 'model', 'node_name', 'node_url' keys, or None if no chairman configured
    """
    for node in get_enabled_nodes():
        if node.is_chairman and node.chairman_model:
            return {
                "model": node.chairman_model,
                "node_name": node.name,
                "node_url": node.url,
                "timeout": node.timeout,
            }
    
    # Fallback: use first model from first node as chairman
    models = get_all_council_models()
    if models:
        return models[0]
    
    return None


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================
# These are kept for backward compatibility with non-distributed code

# Build COUNCIL_MODELS list from all nodes
COUNCIL_MODELS = [m["model"] for m in get_all_council_models()]

# Get chairman model
_chairman = get_chairman_config()
CHAIRMAN_MODEL = _chairman["model"] if _chairman else "mistral"

# Data directory for conversation storage
DATA_DIR = "data/conversations"


# =============================================================================
# DISTRIBUTED SETTINGS
# =============================================================================

# Health check interval (seconds) - how often to check node availability
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))

# Maximum retries for failed requests
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

# Retry delay (seconds)
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))

# Enable verbose logging for distributed operations
DISTRIBUTED_DEBUG = os.getenv("DISTRIBUTED_DEBUG", "false").lower() == "true"
