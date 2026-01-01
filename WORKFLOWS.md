# LLM Council Workflows

This document describes the two main workflows in LLM Council: **Chat Deliberation** and **Code Generation**.

---

## Chat Deliberation Workflow

The chat workflow uses a 3-stage deliberation process where multiple LLMs collaboratively answer questions with anonymous peer review.

### Stage 1: Individual Responses

**Process:**
1. User submits a question
2. Question is sent in parallel to all council models (configured in `backend/config.py`)
3. Each model generates an independent response without seeing other models' answers

**Implementation:**
- Function: `stage1_collect_responses()` in `backend/council.py`
- Uses `asyncio.gather()` for parallel execution
- Graceful degradation: continues with successful responses if some models fail

**UI Display:**
- Tab view showing each model's response
- Model name displayed for transparency
- Markdown rendering for formatted output

---

### Stage 2: Anonymous Peer Review

**Process:**
1. Responses from Stage 1 are **anonymized** as "Response A", "Response B", etc.
2. Each council model receives all anonymized responses
3. Models evaluate each response individually based on:
   - Accuracy
   - Completeness
   - Clarity
   - Insight
4. Each model provides a ranking: "1. Response C, 2. Response A, 3. Response B..."

**Implementation:**
- Function: `stage2_collect_rankings()` in `backend/council.py`
- Creates `label_to_model` mapping for later de-anonymization
- Strict prompt format ensures parseable rankings
- Parser: `parse_ranking_from_text()` extracts "FINAL RANKING:" section
- Aggregation: `calculate_aggregate_rankings()` computes average positions

**Why Anonymization?**
- Prevents models from favoring responses from specific vendors
- Ensures objective evaluation based solely on content quality
- Maintains transparency by showing original model names in UI

**UI Display:**
- Tab view showing each model's evaluation text
- "Extracted Ranking" below each evaluation for validation
- Aggregate rankings table with average positions
- Explanatory text clarifying that boldface names are added client-side

---

### Stage 3: Chairman Synthesis

**Process:**
1. Chairman model receives:
   - Original user question
   - All individual responses from Stage 1
   - All peer evaluations and rankings from Stage 2
   - Aggregate ranking results
2. Chairman synthesizes a final answer that:
   - Incorporates insights from all responses
   - Weighs higher-ranked responses more heavily
   - Resolves contradictions
   - Provides a cohesive, authoritative answer

**Implementation:**
- Function: `stage3_synthesize_final()` in `backend/council.py`
- Chairman model configured separately in `backend/config.py`
- Can be same as or different from council members

**UI Display:**
- Green-tinted background (#f0fff0) to highlight final answer
- Markdown rendering
- Chairman model name displayed

---

### Chat Data Flow

```
User Question
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Anonymize responses as A, B, C...
    ↓
Stage 2: Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Calculate aggregate rankings → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context
    ↓
Return: {stage1, stage2, stage3, metadata}
    ↓
Frontend: Display in tabs with validation UI
```

---

## Code Generation Workflow

The code generation workflow uses an iterative refinement process with peer review to produce high-quality code.

### Step 1: Initial Code Generation

**Process:**
1. User provides:
   - Code specification (what the code should do)
   - Optional: programming language
   - Optional: framework
2. Specification sent in parallel to all council models
3. Each model generates initial code implementation

**Implementation:**
- API endpoint: `/api/code_conversations/{id}/generate`
- Parallel execution across distributed nodes if available
- Event: `code_generation_complete`

**Output:**
- Multiple code submissions from different models
- Each includes: code, model name, node ID, language

---

### Step 2: Code Review (First Iteration)

**Process:**
1. All code submissions are **anonymized** as "Code Submission A", "B", etc.
2. Each council model reviews all submissions
3. Reviews evaluate multiple categories:
   - **Bugs**: Correctness, edge cases, logical errors
   - **Style**: Code readability, formatting, naming conventions
   - **Performance**: Efficiency, algorithmic complexity
   - **Security**: Vulnerabilities, input validation
   - **Best Practices**: Idiomatic code, design patterns
4. Each reviewer provides:
   - Category-specific feedback for each submission
   - Overall score (0-10)
   - Final ranking of submissions

**Implementation:**
- Anonymization prevents bias toward specific models
- Structured review format ensures comprehensive evaluation
- Event: `code_review_complete`

**UI Display:**
- Expandable review cards for each reviewer
- Category-based feedback with emoji icons
- Scores and rankings visible
- Collapsible "Full Review Text" for transparency

---

### Step 3: Iterative Refinement

**Process:**
1. Each model receives:
   - Original specification
   - Their own previous code submission
   - All peer reviews (anonymous)
   - Aggregate feedback
2. Models refine their code based on feedback
3. Process repeats for configured number of iterations (default: 2)

**Implementation:**
- Event: `code_refinement_complete`
- Each iteration produces new code submissions
- Reviews are conducted after each iteration

**Benefits:**
- Incorporates collective wisdom from peer reviews
- Addresses identified bugs and issues
- Improves code quality progressively
- Models learn from each other's approaches

---

### Step 4: Test Generation

**Process:**
1. After final iteration, all models generate test suites
2. Tests cover:
   - Normal use cases
   - Edge cases
   - Error handling
   - Integration scenarios
3. Each model creates comprehensive tests for the code

**Implementation:**
- Event: `test_generation_complete`
- Tests generated in appropriate testing framework
- Language-specific test patterns

**Output:**
- Multiple test suites from different models
- Each provides different perspectives on testing

---

### Step 5: Final Synthesis

**Process:**
1. Chairman model receives:
   - Original specification
   - All code submissions from all iterations
   - All reviews and feedback
   - All generated test suites
2. Chairman synthesizes:
   - **Final Code**: Best implementation incorporating insights from all submissions
   - **Final Tests**: Comprehensive test suite combining best test cases

**Implementation:**
- Event: `code_synthesis_complete`
- Chairman considers rankings and feedback when synthesizing
- Produces production-ready code

**UI Display:**
- "Final Synthesized Code" section with syntax highlighting
- "Final Synthesized Tests" section
- Download and copy functionality
- Language detection and appropriate file extensions

---

### Code Generation Data Flow

```
User Specification + Language/Framework
    ↓
Initial Code Generation (Parallel)
    ↓
[Multiple Code Submissions]
    ↓
Anonymize as Submission A, B, C...
    ↓
Code Review Round 1 (Parallel)
    ↓
[Reviews with scores, feedback, rankings]
    ↓
Refinement Iteration 1
    ↓
[Refined Code Submissions]
    ↓
Code Review Round 2
    ↓
[Reviews with scores, feedback, rankings]
    ↓
Refinement Iteration 2 (if configured)
    ↓
[Final Refined Submissions]
    ↓
Test Generation (Parallel)
    ↓
[Multiple Test Suites]
    ↓
Chairman Synthesis
    ↓
Final Code + Final Tests
    ↓
Frontend: Display with iterations, reviews, and final result
```

---

## Key Design Principles

### 1. Anonymization
Both workflows use anonymization to prevent bias:
- **Chat**: Response labels (A, B, C) hide model identity during ranking
- **Code**: Submission labels hide model identity during review
- De-anonymization happens client-side for transparency

### 2. Parallel Execution
Performance optimization through parallelization:
- Stage 1 queries run in parallel
- Stage 2 rankings run in parallel
- Code generation runs in parallel across nodes
- Code reviews run in parallel

### 3. Graceful Degradation
System continues even if individual components fail:
- Failed model queries don't block entire workflow
- Successful responses are still processed
- Errors logged but not exposed to user unless catastrophic

### 4. Progressive Enhancement
UI updates progressively as each stage completes:
- Real-time streaming of stage completions
- Loading indicators for each stage
- Immediate display of results as they arrive

### 5. Transparency
Full visibility into the deliberation process:
- All raw outputs available via tabs
- Parsed rankings shown for validation
- Review feedback fully displayed
- Model names and node information visible

---

## Configuration

### Chat Configuration
Edit `backend/config.py`:
```python
COUNCIL_MODELS = [
    'anthropic/claude-3.5-sonnet',
    'openai/gpt-4-turbo',
    'google/gemini-pro-1.5',
    # Add more models...
]

CHAIRMAN_MODEL = 'google/gemini-pro-1.5'
```

### Code Configuration
Same model lists used for code generation. Adjust iteration count in API call:
```python
await api.generateCodeStream(
    conversation_id,
    specification,
    language,
    framework,
    2,  # Number of refinement iterations
    callback
)
```

---

## API Integration

Both workflows use OpenRouter API for model access:
- API key: Set `OPENROUTER_API_KEY` in `.env`
- Rate limiting: Handled by OpenRouter
- Cost tracking: Available via OpenRouter dashboard
- Model availability: Check OpenRouter for supported models

---

## Storage

### Conversation Storage
- Location: `data/conversations/`
- Format: JSON
- Structure: `{id, created_at, messages[]}`
- Metadata: Not persisted, returned in API responses only

### Code Conversation Storage
- Location: `data/code_conversations/`
- Format: JSON
- Structure: `{id, created_at, messages[], code_generations[]}`
- Includes: iterations, reviews, final code, tests

---

## Performance Considerations

### Chat Workflow
- **Stage 1**: ~5-15 seconds (parallel)
- **Stage 2**: ~10-20 seconds (parallel)
- **Stage 3**: ~5-10 seconds (single query)
- **Total**: ~20-45 seconds

### Code Workflow
- **Initial Generation**: ~10-20 seconds (parallel)
- **Review Round**: ~15-25 seconds (parallel)
- **Refinement**: ~10-20 seconds (parallel)
- **Per Iteration**: ~25-45 seconds
- **Test Generation**: ~10-20 seconds (parallel)
- **Synthesis**: ~15-25 seconds (single query)
- **Total** (2 iterations): ~90-180 seconds

Times vary based on:
- Model response times
- Complexity of question/specification
- Number of council members
- Network latency
