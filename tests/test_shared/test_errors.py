"""Tests for shared.errors module."""
from shared.errors import ProblemError

def test_problem_error_fields():
    err = ProblemError(404, "Not Found", "Resource not found")
    assert err.status == 404
    assert err.title == "Not Found"
    assert err.detail == "Resource not found"

def test_problem_error_with_errors():
    errors = [{"path": "/name", "message": "required", "code": "missing"}]
    err = ProblemError(422, "Validation Error", "Invalid input", errors=errors)
    assert len(err.errors) == 1
