"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .code_council import run_code_council, generate_initial_code, review_code_structured, refine_code, generate_tests, synthesize_final_code
from .distributed import get_distributed_client
from .config import get_enabled_nodes, get_all_council_models, get_chairman_config

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class GenerateCodeRequest(BaseModel):
    """Request to generate code."""
    specification: str
    language: Optional[str] = None
    framework: Optional[str] = None
    max_iterations: int = 2


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    nodes = get_enabled_nodes()
    return {
        "status": "ok",
        "service": "LLM Council API - Distributed",
        "nodes_configured": len(nodes),
        "models_available": len(get_all_council_models()),
    }


# =============================================================================
# CLUSTER MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/api/cluster/status")
async def get_cluster_status():
    """
    Get the current status of the distributed LLM cluster.
    
    Returns information about all nodes, their health status,
    and available models.
    """
    client = get_distributed_client()
    return client.get_cluster_status()


@app.post("/api/cluster/health-check")
async def run_cluster_health_check():
    """
    Run a health check on all configured nodes.
    
    This will ping each node and verify what models are available.
    """
    client = get_distributed_client()
    health_results = await client.check_all_nodes_health()
    
    # Convert to serializable format
    results = {}
    for name, health in health_results.items():
        results[name] = {
            "is_healthy": health.is_healthy,
            "last_check": health.last_check.isoformat() if health.last_check else None,
            "last_error": health.last_error,
            "consecutive_failures": health.consecutive_failures,
            "available_models": health.available_models,
        }
    
    healthy_count = sum(1 for h in health_results.values() if h.is_healthy)
    
    return {
        "status": "ok" if healthy_count > 0 else "degraded",
        "healthy_nodes": healthy_count,
        "total_nodes": len(health_results),
        "nodes": results,
    }


@app.get("/api/cluster/nodes")
async def list_nodes():
    """List all configured nodes with their details."""
    nodes = get_enabled_nodes()
    return {
        "nodes": [node.to_dict() for node in nodes],
        "total": len(nodes),
    }


@app.get("/api/cluster/models")
async def list_models():
    """List all available models across all nodes."""
    models = get_all_council_models()
    chairman = get_chairman_config()
    
    return {
        "council_models": models,
        "chairman": chairman,
        "total_models": len(models),
    }


class TestNodeRequest(BaseModel):
    """Request to test a specific node."""
    node_name: str
    model: Optional[str] = None
    prompt: str = "Hello! Please respond with a brief greeting."


@app.post("/api/cluster/test-node")
async def test_node(request: TestNodeRequest):
    """
    Test a specific node by sending a simple prompt.
    
    Useful for debugging and verifying node connectivity.
    """
    client = get_distributed_client()
    nodes = get_enabled_nodes()
    
    # Find the requested node
    target_node = None
    for node in nodes:
        if node.name == request.node_name:
            target_node = node
            break
    
    if target_node is None:
        raise HTTPException(status_code=404, detail=f"Node '{request.node_name}' not found")
    
    # Use specified model or first available
    model = request.model or (target_node.models[0] if target_node.models else None)
    if model is None:
        raise HTTPException(status_code=400, detail="No model specified and node has no configured models")
    
    # Query the model
    response = await client.query_model(
        model=model,
        messages=[{"role": "user", "content": request.prompt}],
        node_url=target_node.url,
    )
    
    if response is None:
        raise HTTPException(status_code=503, detail="Failed to get response from node")
    
    return {
        "node": target_node.name,
        "model": model,
        "prompt": request.prompt,
        "response": response.get("content", ""),
        "status": "ok",
    }


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.get("/api/code/conversations", response_model=List[ConversationMetadata])
async def list_code_conversations():
    """List all code conversations (metadata only)."""
    return storage.list_conversations(conversation_type="code")


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.post("/api/code/conversations", response_model=Conversation)
async def create_code_conversation(request: CreateConversationRequest):
    """Create a new code conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id, conversation_type="code")
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/api/code/conversations/{conversation_id}", response_model=Conversation)
async def get_code_conversation(conversation_id: str):
    """Get a specific code conversation with all its data."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Code conversation not found")
    if conversation.get("type") != "code":
        raise HTTPException(status_code=400, detail="Not a code conversation")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# =============================================================================
# CODE CONVERSATION ENDPOINTS
# =============================================================================

@app.post("/api/code/conversations/{conversation_id}/generate")
async def generate_code(conversation_id: str, request: GenerateCodeRequest):
    """
    Generate code with iterative refinement.
    Returns the complete code generation result.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Code conversation not found")
    if conversation.get("type") != "code":
        raise HTTPException(status_code=400, detail="Not a code conversation")

    # Add specification
    storage.add_code_specification(
        conversation_id,
        request.specification,
        request.language,
        request.framework
    )

    # Generate title if first message
    if len(conversation["messages"]) == 0:
        title = await generate_conversation_title(request.specification)
        storage.update_conversation_title(conversation_id, title)

    # Run code council
    result = await run_code_council(
        request.specification,
        request.language,
        request.framework,
        request.max_iterations
    )

    # Save code generation
    storage.add_code_generation(
        conversation_id,
        request.specification,
        result["iterations"],
        result["final_code"],
        result["final_tests"],
        result["tests"],
        result["metadata"]
    )

    return result


@app.post("/api/code/conversations/{conversation_id}/generate/stream")
async def generate_code_stream(conversation_id: str, request: GenerateCodeRequest):
    """
    Generate code with iterative refinement (streamed).
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Code conversation not found")
    if conversation.get("type") != "code":
        raise HTTPException(status_code=400, detail="Not a code conversation")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add specification
            storage.add_code_specification(
                conversation_id,
                request.specification,
                request.language,
                request.framework
            )

            # Start title generation in parallel
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.specification))

            # Stage 1: Initial code generation
            yield f"data: {json.dumps({'type': 'code_generation_start'})}\n\n"
            code_submissions = await generate_initial_code(
                request.specification,
                request.language,
                request.framework
            )
            yield f"data: {json.dumps({'type': 'code_generation_complete', 'data': code_submissions})}\n\n"

            if not code_submissions:
                yield f"data: {json.dumps({'type': 'error', 'message': 'All models failed to generate code'})}\n\n"
                return

            current_submissions = code_submissions
            iterations = [{
                "iteration": 0,
                "code_submissions": code_submissions.copy(),
                "reviews": []
            }]

            # Iterative refinement
            for iteration_num in range(1, request.max_iterations + 1):
                # Review current submissions
                yield f"data: {json.dumps({'type': 'code_review_start', 'iteration': iteration_num})}\n\n"
                reviews = await review_code_structured(current_submissions, request.specification)
                yield f"data: {json.dumps({'type': 'code_review_complete', 'iteration': iteration_num, 'data': reviews})}\n\n"

                # Store reviews
                iterations[-1]["reviews"] = reviews

                # Refine code
                yield f"data: {json.dumps({'type': 'code_refinement_start', 'iteration': iteration_num})}\n\n"
                refined_submissions = []
                for submission in current_submissions:
                    refined = await refine_code(submission, reviews, request.specification, iteration_num)
                    refined_submissions.append(refined)
                
                current_submissions = refined_submissions
                yield f"data: {json.dumps({'type': 'code_refinement_complete', 'iteration': iteration_num, 'data': refined_submissions})}\n\n"

                # Store iteration
                iterations.append({
                    "iteration": iteration_num,
                    "code_submissions": current_submissions.copy(),
                    "reviews": []
                })

            # Final review
            yield f"data: {json.dumps({'type': 'code_review_start', 'iteration': 'final'})}\n\n"
            final_reviews = await review_code_structured(current_submissions, request.specification)
            iterations[-1]["reviews"] = final_reviews
            yield f"data: {json.dumps({'type': 'code_review_complete', 'iteration': 'final', 'data': final_reviews})}\n\n"

            # Generate tests
            yield f"data: {json.dumps({'type': 'test_generation_start'})}\n\n"
            best_code = current_submissions[0]["code"]
            tests = await generate_tests(best_code, request.specification, request.language)
            yield f"data: {json.dumps({'type': 'test_generation_complete', 'data': tests})}\n\n"

            # Synthesize final code
            yield f"data: {json.dumps({'type': 'code_synthesis_start'})}\n\n"
            final_result = await synthesize_final_code(
                current_submissions,
                final_reviews,
                tests,
                request.specification
            )
            yield f"data: {json.dumps({'type': 'code_synthesis_complete', 'data': final_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete code generation
            storage.add_code_generation(
                conversation_id,
                request.specification,
                iterations,
                final_result["code"],
                final_result["tests"],
                tests,
                {
                    "language": request.language,
                    "framework": request.framework,
                    "total_iterations": len(iterations),
                }
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
