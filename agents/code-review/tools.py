"""Domain tools for the code review agent."""
from __future__ import annotations


def count_lines(code: str) -> int:
    """Count the number of lines in the code."""
    return len(code.strip().splitlines())


def detect_language(code: str) -> str:
    """Detect the programming language from code content."""
    indicators = {
        "python": ["def ", "import ", "class ", "self.", "print("],
        "javascript": ["const ", "let ", "function ", "=>", "console.log"],
        "typescript": ["interface ", ": string", ": number", "const ", "=>"],
        "go": ["func ", "package ", "fmt.", "err != nil"],
        "rust": ["fn ", "let mut ", "impl ", "pub fn", "::"],
    }
    scores: dict[str, int] = {}
    for lang, markers in indicators.items():
        scores[lang] = sum(1 for m in markers if m in code)
    if not scores or max(scores.values()) == 0:
        return "unknown"
    return max(scores, key=lambda k: scores[k])


def check_complexity(code: str) -> dict:
    """Estimate code complexity based on nesting and branching."""
    lines = code.splitlines()
    max_indent = 0
    branch_count = 0
    branch_keywords = {"if ", "elif ", "else:", "for ", "while ", "match ", "case ", "try:", "except "}
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        max_indent = max(max_indent, indent)
        if any(stripped.startswith(kw) for kw in branch_keywords):
            branch_count += 1
    return {
        "max_nesting_depth": max_indent // 4,
        "branch_count": branch_count,
        "complexity": "low" if branch_count < 5 else "medium" if branch_count < 15 else "high",
    }
