"""
Code Review Agent — analyzes code for bugs, security, style, and quality.

Demonstrates: structured output with quality scoring and actionable findings.
"""
from shared.runtime import create_agent
from .schemas import CodeReviewResult
from . import tools

agent = create_agent(
    name="code-review",
    output_type=CodeReviewResult,
    instructions=(
        "You are an expert code reviewer. Given a code snippet or diff, "
        "analyze it for bugs, security vulnerabilities, performance issues, "
        "style problems, and maintainability concerns. "
        "Use detect_language to identify the language. "
        "Use check_complexity to assess structural complexity. "
        "Be constructive — highlight strengths alongside issues. "
        "Set approve=true only if there are no error or critical findings."
    ),
)


@agent.tool_plain
def count_lines(code: str) -> int:
    """Count the number of lines in the submitted code."""
    return tools.count_lines(code)


@agent.tool_plain
def detect_language(code: str) -> str:
    """Detect the programming language of the code."""
    return tools.detect_language(code)


@agent.tool_plain
def check_complexity(code: str) -> dict:
    """Analyze code complexity — nesting depth, branch count, overall rating."""
    return tools.check_complexity(code)
