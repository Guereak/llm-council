"""
Distributed LLM Client for multi-node LLM Council.

This module handles communication with multiple remote Ollama instances
running on different machines, enabling a distributed LLM council.
"""

import asyncio
import ollama
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .config import (
    LLMNode,
    get_enabled_nodes,
    get_all_council_models,
    get_chairman_config,
    MAX_RETRIES,
    RETRY_DELAY,
    DISTRIBUTED_DEBUG,
)


@dataclass
class NodeHealth:
    """Tracks the health status of a node."""
    node_name: str
    is_healthy: bool = True
    last_check: datetime = field(default_factory=datetime.now)
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    available_models: List[str] = field(default_factory=list)


class DistributedLLMClient:
    """
    Client for querying LLMs across multiple distributed nodes.
    
    Features:
    - Automatic node discovery and health monitoring
    - Parallel queries to multiple nodes
    - Automatic failover and retries
    - Model-to-node routing
    """
    
    def __init__(self):
        self._node_health: Dict[str, NodeHealth] = {}
        self._ollama_clients: Dict[str, ollama.Client] = {}
        self._initialized = False
    
    def _get_client_for_node(self, node: LLMNode) -> ollama.Client:
        """Get or create an Ollama client for a specific node."""
        if node.name not in self._ollama_clients:
            # Parse the URL to get host:port format
            parsed = urlparse(node.url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 11434
            
            # Create client with the node's host
            self._ollama_clients[node.name] = ollama.Client(host=f"{host}:{port}")
            
            if DISTRIBUTED_DEBUG:
                print(f"[Distributed] Created client for node '{node.name}' at {host}:{port}")
        
        return self._ollama_clients[node.name]
    
    async def check_node_health(self, node: LLMNode) -> NodeHealth:
        """
        Check if a node is healthy and what models it has available.
        
        Args:
            node: The node to check
            
        Returns:
            NodeHealth object with current status
        """
        health = self._node_health.get(node.name, NodeHealth(node_name=node.name))
        
        try:
            client = self._get_client_for_node(node)
            
            # Run the blocking list() call in a thread pool
            loop = asyncio.get_event_loop()
            models_response = await loop.run_in_executor(
                None,
                lambda: client.list()
            )
            
            # Extract model names
            available_models = []
            if isinstance(models_response, dict) and 'models' in models_response:
                available_models = [m.get('name', '').split(':')[0] for m in models_response['models']]
            
            health.is_healthy = True
            health.last_check = datetime.now()
            health.last_error = None
            health.consecutive_failures = 0
            health.available_models = available_models
            
            if DISTRIBUTED_DEBUG:
                print(f"[Distributed] Node '{node.name}' is healthy. Models: {available_models}")
                
        except Exception as e:
            health.is_healthy = False
            health.last_check = datetime.now()
            health.last_error = str(e)
            health.consecutive_failures += 1
            
            if DISTRIBUTED_DEBUG:
                print(f"[Distributed] Node '{node.name}' health check failed: {e}")
        
        self._node_health[node.name] = health
        return health
    
    async def check_all_nodes_health(self) -> Dict[str, NodeHealth]:
        """Check health of all enabled nodes in parallel."""
        nodes = get_enabled_nodes()
        
        # Check all nodes in parallel
        tasks = [self.check_node_health(node) for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update health dict
        for node, result in zip(nodes, results):
            if isinstance(result, Exception):
                self._node_health[node.name] = NodeHealth(
                    node_name=node.name,
                    is_healthy=False,
                    last_error=str(result),
                    consecutive_failures=1,
                )
            elif isinstance(result, NodeHealth):
                self._node_health[node.name] = result
        
        return self._node_health.copy()
    
    def get_healthy_nodes(self) -> List[LLMNode]:
        """Get list of currently healthy nodes."""
        healthy = []
        for node in get_enabled_nodes():
            health = self._node_health.get(node.name)
            if health is None or health.is_healthy:
                healthy.append(node)
        return healthy
    
    def find_node_for_model(self, model: str) -> Optional[Tuple[LLMNode, ollama.Client]]:
        """
        Find a healthy node that can serve the specified model.
        
        Args:
            model: The model name to find
            
        Returns:
            Tuple of (node, client) or None if no node found
        """
        # First try to find from configured nodes
        for node in get_enabled_nodes():
            # Check if model is in the node's configured models
            # Handle model names with and without tags (e.g., "llama3.2" vs "llama3.2:latest")
            model_base = model.split(':')[0]
            node_models_base = [m.split(':')[0] for m in node.models]
            
            if model in node.models or model_base in node_models_base:
                health = self._node_health.get(node.name)
                if health is None or health.is_healthy:
                    return (node, self._get_client_for_node(node))
        
        # If not found in config, try any healthy node (model might be there)
        for node in self.get_healthy_nodes():
            health = self._node_health.get(node.name)
            if health and model.split(':')[0] in [m.split(':')[0] for m in health.available_models]:
                return (node, self._get_client_for_node(node))
        
        return None
    
    async def query_model(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0,
        node_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Query a specific model, automatically routing to the correct node.
        
        Args:
            model: Model name to query
            messages: List of message dicts with 'role' and 'content'
            timeout: Request timeout in seconds
            node_url: Optional specific node URL to use (overrides auto-routing)
            
        Returns:
            Response dict with 'content' key, or None if failed
        """
        # Find the appropriate node and client
        if node_url:
            # Use specific node
            parsed = urlparse(node_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 11434
            client = ollama.Client(host=f"{host}:{port}")
            node_name = node_url
        else:
            # Auto-route to appropriate node
            result = self.find_node_for_model(model)
            if result is None:
                print(f"[Distributed] No healthy node found for model '{model}'")
                return None
            node, client = result
            node_name = node.name
            timeout = node.timeout
        
        # Try with retries
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                if DISTRIBUTED_DEBUG:
                    print(f"[Distributed] Querying model '{model}' on node '{node_name}' (attempt {attempt + 1})")
                
                # Run the blocking chat() call in a thread pool
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.chat(
                        model=model,
                        messages=messages,
                        options={}
                    )
                )
                
                message = response.get('message', {})
                
                if DISTRIBUTED_DEBUG:
                    content_preview = message.get('content', '')[:100]
                    print(f"[Distributed] Got response from '{model}': {content_preview}...")
                
                return {
                    'content': message.get('content', ''),
                    'reasoning_details': None,
                    'node': node_name,
                    'model': model,
                }
                
            except Exception as e:
                last_error = e
                print(f"[Distributed] Error querying '{model}' on '{node_name}': {e}")
                
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
        
        # All retries failed
        print(f"[Distributed] All retries failed for model '{model}': {last_error}")
        return None
    
    async def query_models_parallel(
        self,
        models_config: List[Dict[str, Any]],
        messages: List[Dict[str, str]],
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Query multiple models in parallel across distributed nodes.
        
        Args:
            models_config: List of dicts with 'model', 'node_url', 'timeout' keys
            messages: List of message dicts to send to each model
            
        Returns:
            Dict mapping model name to response dict (or None if failed)
        """
        async def query_with_config(config: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
            model = config["model"]
            node_url = config.get("node_url")
            timeout = config.get("timeout", 120.0)
            
            result = await self.query_model(
                model=model,
                messages=messages,
                timeout=timeout,
                node_url=node_url,
            )
            return (model, result)
        
        # Create tasks for all models
        tasks = [query_with_config(config) for config in models_config]
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build response dict
        responses = {}
        for result in results:
            if isinstance(result, tuple):
                model, response = result
                responses[model] = response
            elif isinstance(result, Exception):
                print(f"[Distributed] Query task failed with exception: {result}")
        
        return responses
    
    async def query_chairman(
        self,
        messages: List[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        """
        Query the designated chairman model.
        
        Args:
            messages: List of message dicts
            
        Returns:
            Response dict or None if failed
        """
        chairman_config = get_chairman_config()
        
        if chairman_config is None:
            print("[Distributed] No chairman configured!")
            return None
        
        return await self.query_model(
            model=chairman_config["model"],
            messages=messages,
            timeout=chairman_config.get("timeout", 120.0),
            node_url=chairman_config.get("node_url"),
        )
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Get the current status of the distributed cluster.
        
        Returns:
            Dict with cluster status information
        """
        nodes = get_enabled_nodes()
        healthy_count = len(self.get_healthy_nodes())
        
        node_statuses = []
        for node in nodes:
            health = self._node_health.get(node.name, NodeHealth(node_name=node.name))
            node_statuses.append({
                "name": node.name,
                "url": node.url,
                "is_healthy": health.is_healthy,
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "last_error": health.last_error,
                "configured_models": node.models,
                "available_models": health.available_models,
                "is_chairman": node.is_chairman,
                "chairman_model": node.chairman_model,
            })
        
        chairman_config = get_chairman_config()
        
        return {
            "total_nodes": len(nodes),
            "healthy_nodes": healthy_count,
            "nodes": node_statuses,
            "chairman": chairman_config,
            "all_models": get_all_council_models(),
        }


# Global singleton instance
_distributed_client: Optional[DistributedLLMClient] = None


def get_distributed_client() -> DistributedLLMClient:
    """Get the global distributed client instance."""
    global _distributed_client
    if _distributed_client is None:
        _distributed_client = DistributedLLMClient()
    return _distributed_client


# =============================================================================
# Convenience functions matching the interface of ollama.py
# =============================================================================

async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a model via the distributed client.
    
    This function matches the signature of ollama.query_model for compatibility.
    """
    client = get_distributed_client()
    return await client.query_model(model, messages, timeout)


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel via the distributed client.
    
    This function matches the signature of ollama.query_models_parallel for compatibility.
    """
    client = get_distributed_client()
    
    # Build config from model names
    models_config = get_all_council_models()
    
    # Filter to only requested models
    filtered_config = [c for c in models_config if c["model"] in models]
    
    # Add any models not in config (will use auto-routing)
    configured_models = {c["model"] for c in filtered_config}
    for model in models:
        if model not in configured_models:
            filtered_config.append({"model": model, "timeout": 120.0})
    
    return await client.query_models_parallel(filtered_config, messages)

