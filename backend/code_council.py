"""Code-specific LLM Council orchestration with iterative refinement."""

import json
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from .distributed import get_distributed_client
from .config import get_all_council_models, get_chairman_config, CHAIRMAN_MODEL


async def generate_initial_code(
    specification: str,
    language: Optional[str] = None,
    framework: Optional[str] = None
) -> List[Dict[str, Any]]:
    """ Stage 1: Generate initial code from specification """
    language_part = f"Programming Language: {language}\n" if language else ""
    framework_part = f"Framework/Library: {framework}\n" if framework else ""
    
    code_prompt = f"""You are an expert software developer. Generate clean, well-structured code based on the following specification.

{language_part}{framework_part}
Specification:
{specification}

Requirements:
- Write production-ready code
- Include proper error handling
- Add comments where appropriate
- Follow best practices for the language
- Make the code maintainable and readable

Provide ONLY the code without any explanations or markdown formatting. Start directly with the code."""

    messages = [{"role": "user", "content": code_prompt}]
    
    # Get client and query the models
    client = get_distributed_client()
    models_config = get_all_council_models()
    
    responses = await client.query_models_parallel(models_config, messages)
    
    # Results formatting
    code_results = []
    for model, response in responses.items():
        if response is not None:
            code_content = response.get('content', '').strip()
            code_content = re.sub(r'^```[\w]*\n', '', code_content, flags=re.MULTILINE)
            code_content = re.sub(r'\n```$', '', code_content, flags=re.MULTILINE)
            code_content = code_content.strip()
            
            code_results.append({
                "model": model,
                "code": code_content,
                "node": response.get('node', 'unknown'),
                "iteration": 0,
            })
    
    return code_results


async def review_code_structured(
    code_submissions: List[Dict[str, Any]],
    specification: str
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """ Stage 2: Each model reviews code with structured feedback """
    # Create anonymized labels for code submissions
    labels = [chr(65 + i) for i in range(len(code_submissions))]  # A, B, C, ...

    # Create label to model mapping for deobfuscation
    label_to_model = {
        label: submission['model']
        for label, submission in zip(labels, code_submissions)
    }

    # Build code review prompt
    code_texts = "\n\n".join([
        f"Code Submission {label}:\n```\n{submission['code']}\n```"
        for label, submission in zip(labels, code_submissions)
    ])
    
    review_prompt = f"""You are a senior code reviewer. Review the following code submissions against the original specification.

Original Specification:
{specification}

Code Submissions:
{code_texts}

For each code submission, provide structured feedback in the following categories:

1. **Bugs**: Actual errors, logic issues, or potential runtime problems
2. **Style**: Code formatting, naming conventions, consistency
3. **Performance**: Optimization opportunities, efficiency concerns
4. **Security**: Vulnerabilities, unsafe practices, security risks
5. **Best Practices**: Design patterns, maintainability, code organization

Format your response as follows for EACH submission:

Code Submission X:
- Bugs: [list any bugs or issues]
- Style: [style feedback]
- Performance: [performance feedback]
- Security: [security feedback]
- Best Practices: [best practices feedback]
- Overall Score: [1-10 rating]

Then provide a ranking at the end:

FINAL RANKING:
1. Code Submission X
2. Code Submission Y
3. Code Submission Z"""

    messages = [{"role": "user", "content": review_prompt}]
    
    # Get reviews from all council models
    client = get_distributed_client()
    models_config = get_all_council_models()
    
    responses = await client.query_models_parallel(models_config, messages)
    
    # Parse reviews
    review_results = []
    for model, response in responses.items():
        if response is not None:
            review_text = response.get('content', '')
            parsed_review = parse_structured_review(review_text, labels)
            
            review_results.append({
                "model": model,
                "review_text": review_text,
                "parsed_review": parsed_review,
                "node": response.get('node', 'unknown'),
            })

    return review_results, label_to_model

# TODO
def parse_structured_review(review_text: str, labels: List[str]) -> Dict[str, Any]:
    """ Parse structured review from LLM response """
    parsed = {
        "submissions": {},
        "ranking": []
    }
    
    # Extract reviews for each submission
    for label in labels:
        submission_key = f"Code Submission {label}"
        if submission_key in review_text:
            pattern = rf"{re.escape(submission_key)}:(.*?)(?=Code Submission [A-Z]|FINAL RANKING:|$)"
            match = re.search(pattern, review_text, re.DOTALL)
            if match:
                submission_review = match.group(1).strip()
                
                # Extract categories
                categories = {}
                for category in ["Bugs", "Style", "Performance", "Security", "Best Practices"]:
                    pattern = rf"{category}:\s*(.*?)(?=\n-|$)"
                    cat_match = re.search(pattern, submission_review, re.DOTALL)
                    if cat_match:
                        categories[category.lower()] = cat_match.group(1).strip()
                
                # Extract overall score
                score_match = re.search(r"Overall Score:\s*(\d+)", submission_review)
                score = int(score_match.group(1)) if score_match else None
                
                parsed["submissions"][label] = {
                    "categories": categories,
                    "score": score,
                    "full_text": submission_review
                }
    
    # Extract ranking
    if "FINAL RANKING:" in review_text:
        ranking_section = review_text.split("FINAL RANKING:")[1]
        ranking_matches = re.findall(r'Code Submission ([A-Z])', ranking_section)
        parsed["ranking"] = ranking_matches
    
    return parsed


async def refine_code(
    code_submission: Dict[str, Any],
    reviews: List[Dict[str, Any]],
    specification: str,
    iteration: int
) -> Dict[str, Any]:
    """
    Refine code based on review feedback.
    
    Args:
        code_submission: Original code submission
        reviews: List of review feedback
        specification: Original specification
        iteration: Current iteration number
    
    Returns:
        Refined code submission dict
    """
    # Collect all feedback for this submission
    feedback_summary = []
    for review in reviews:
        parsed = review.get("parsed_review", {})
        submission_label = None
        
        # Find which label corresponds to this submission
        for label, submission_data in parsed.get("submissions", {}).items():
            feedback_summary.append({
                "reviewer": review["model"],
                "categories": submission_data.get("categories", {}),
                "score": submission_data.get("score"),
            })
            break
    
    # Build refinement prompt
    feedback_text = "\n\n".join([
        f"Reviewer: {fb['reviewer']}\n"
        f"Score: {fb['score']}\n"
        f"Feedback:\n" + "\n".join([f"- {k}: {v}" for k, v in fb['categories'].items()])
        for fb in feedback_summary[:3]  # Limit to top 3 reviews
    ])
    
    refinement_prompt = f"""You are refining code based on peer review feedback.

Original Specification:
{specification}

Original Code:
```{code_submission['code']}
```

Review Feedback (Iteration {iteration}):
{feedback_text}

Refine the code to address the feedback while maintaining the original functionality. Prioritize:
1. Fixing bugs and errors
2. Improving code style and readability
3. Addressing security concerns
4. Optimizing performance where appropriate
5. Following best practices

Provide ONLY the refined code without explanations or markdown formatting."""

    messages = [{"role": "user", "content": refinement_prompt}]
    
    # Use the same model that generated the original code
    client = get_distributed_client()
    response = await client.query_model(
        model=code_submission['model'],
        messages=messages,
        node_url=None
    )
    
    if response is None:
        return code_submission  # Return original if refinement fails
    
    refined_code = response.get('content', '').strip()
    # Remove markdown code blocks if present
    refined_code = re.sub(r'^```[\w]*\n', '', refined_code, flags=re.MULTILINE)
    refined_code = re.sub(r'\n```$', '', refined_code, flags=re.MULTILINE)
    refined_code = refined_code.strip()
    
    return {
        **code_submission,
        "code": refined_code,
        "iteration": iteration,
    }


async def generate_tests(
    final_code: str,
    specification: str,
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate unit tests for the final code.
    
    Args:
        final_code: The final refined code
        specification: Original specification
        language: Programming language
    
    Returns:
        List of test code dicts from different models
    """
    language_part = f"Programming Language: {language}\n" if language else ""
    
    test_prompt = f"""You are a test engineer. Generate comprehensive unit tests for the following code.

{language_part}
Original Specification:
{specification}

Code to Test:
```{final_code}
```

Requirements:
- Write comprehensive unit tests
- Cover edge cases and error scenarios
- Use appropriate testing framework for the language
- Include both positive and negative test cases
- Make tests clear and maintainable

Provide ONLY the test code without explanations or markdown formatting."""

    messages = [{"role": "user", "content": test_prompt}]
    
    # Get tests from all council models
    client = get_distributed_client()
    models_config = get_all_council_models()
    
    responses = await client.query_models_parallel(models_config, messages)
    
    # Format results
    test_results = []
    for model, response in responses.items():
        if response is not None:
            test_code = response.get('content', '').strip()
            # Remove markdown code blocks if present
            test_code = re.sub(r'^```[\w]*\n', '', test_code, flags=re.MULTILINE)
            test_code = re.sub(r'\n```$', '', test_code, flags=re.MULTILINE)
            test_code = test_code.strip()
            
            test_results.append({
                "model": model,
                "test_code": test_code,
                "node": response.get('node', 'unknown'),
            })
    
    return test_results


async def synthesize_final_code(
    code_submissions: List[Dict[str, Any]],
    reviews: List[Dict[str, Any]],
    tests: List[Dict[str, Any]],
    specification: str
) -> Dict[str, Any]:
    """
    Chairman synthesizes final code and tests.
    
    Args:
        code_submissions: All code submissions (final iterations)
        reviews: All review feedback
        tests: Generated test code
        specification: Original specification
    
    Returns:
        Final synthesized code and tests
    """
    # Build synthesis prompt
    code_texts = "\n\n".join([
        f"Code from {sub['model']}:\n```\n{sub['code']}\n```"
        for sub in code_submissions
    ])
    
    test_texts = "\n\n".join([
        f"Tests from {test['model']}:\n```\n{test['test_code']}\n```"
        for test in tests
    ])
    
    synthesis_prompt = f"""You are the Chairman of the Code Council. Synthesize the best code and tests from multiple submissions.

Original Specification:
{specification}

Code Submissions:
{code_texts}

Test Submissions:
{test_texts}

Your task:
1. Synthesize the best code by combining the strongest aspects of each submission
2. Integrate the best test cases into a comprehensive test suite
3. Ensure the final code is production-ready, well-tested, and follows best practices

Provide your response in the following format:

FINAL CODE:
[the synthesized code]

FINAL TESTS:
[the synthesized test suite]

Do not include markdown code blocks, just the code directly."""

    messages = [{"role": "user", "content": synthesis_prompt}]
    
    # Query chairman
    client = get_distributed_client()
    response = await client.query_chairman(messages)
    
    if response is None:
        # Fallback: use best code submission
        return {
            "code": code_submissions[0]["code"] if code_submissions else "",
            "tests": tests[0]["test_code"] if tests else "",
            "model": CHAIRMAN_MODEL,
            "node": "error"
        }
    
    synthesis_text = response.get('content', '')
    
    # Parse final code and tests
    final_code = ""
    final_tests = ""
    
    if "FINAL CODE:" in synthesis_text:
        parts = synthesis_text.split("FINAL CODE:")
        if len(parts) > 1:
            rest = parts[1]
            if "FINAL TESTS:" in rest:
                final_code = rest.split("FINAL TESTS:")[0].strip()
                final_tests = rest.split("FINAL TESTS:")[1].strip()
            else:
                final_code = rest.strip()
    
    # Clean up code blocks
    final_code = re.sub(r'^```[\w]*\n', '', final_code, flags=re.MULTILINE)
    final_code = re.sub(r'\n```$', '', final_code, flags=re.MULTILINE)
    final_code = final_code.strip()
    
    final_tests = re.sub(r'^```[\w]*\n', '', final_tests, flags=re.MULTILINE)
    final_tests = re.sub(r'\n```$', '', final_tests, flags=re.MULTILINE)
    final_tests = final_tests.strip()
    
    return {
        "code": final_code,
        "tests": final_tests,
        "model": response.get('model', CHAIRMAN_MODEL),
        "node": response.get('node', 'unknown')
    }


async def run_code_council(
    specification: str,
    language: Optional[str] = None,
    framework: Optional[str] = None,
    max_iterations: int = 2
) -> Dict[str, Any]:
    """
    Run the complete iterative code council process.
    
    Args:
        specification: Code requirements/specification
        language: Programming language (optional)
        framework: Framework/library (optional)
        max_iterations: Maximum refinement iterations
    
    Returns:
        Complete code council results
    """
    # Stage 1: Initial code generation
    code_submissions = await generate_initial_code(specification, language, framework)
    
    if not code_submissions:
        return {
            "error": "All models failed to generate code",
            "iterations": [],
            "final_code": None,
            "tests": []
        }
    
    iterations = [{
        "iteration": 0,
        "code_submissions": code_submissions.copy(),
        "reviews": []
    }]
    
    current_submissions = code_submissions
    
    # Iterative refinement
    for iteration_num in range(1, max_iterations + 1):
        # Review current submissions
        reviews, label_to_model = await review_code_structured(current_submissions, specification)

        # Store reviews and label mapping
        iterations[-1]["reviews"] = reviews
        iterations[-1]["label_to_model"] = label_to_model
        
        # Refine each submission
        refined_submissions = []
        for submission in current_submissions:
            refined = await refine_code(submission, reviews, specification, iteration_num)
            refined_submissions.append(refined)
        
        current_submissions = refined_submissions
        
        # Store iteration
        iterations.append({
            "iteration": iteration_num,
            "code_submissions": current_submissions.copy(),
            "reviews": []
        })
    
    # Final review
    final_reviews, final_label_to_model = await review_code_structured(current_submissions, specification)
    iterations[-1]["reviews"] = final_reviews
    iterations[-1]["label_to_model"] = final_label_to_model
    
    # Generate tests
    # Use best submission (first one for now, could be improved with ranking)
    best_code = current_submissions[0]["code"]
    tests = await generate_tests(best_code, specification, language)
    
    # Synthesize final code
    final_result = await synthesize_final_code(
        current_submissions,
        final_reviews,
        tests,
        specification
    )
    
    return {
        "iterations": iterations,
        "final_code": final_result["code"],
        "final_tests": final_result["tests"],
        "tests": tests,
        "metadata": {
            "language": language,
            "framework": framework,
            "total_iterations": len(iterations),
        }
    }

