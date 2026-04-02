"""
FastAPI application factory -- **the most important file in the framework**.

``create_app(agent_name)`` returns a fully-wired :class:`FastAPI` instance
with:

* ``GET  /health``         -- public, no auth
* ``POST /tasks``          -- create a task (sync or async mode)
* ``GET  /tasks/{task_id}`` -- retrieve task status / result

Everything an agent service needs to expose a production HTTP API is handled
here.  Individual agents only need to provide their ``agent.agent`` module
(via ``create_agent``) and a Pydantic output type.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
import logging
import re
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from shared.action_executor import execute_action as default_execute_action
from shared.approval_workflow import ApprovalWorkflow, ApprovalWorkflowError, TaskStoreApprovalStore
from shared.auth import require_auth
from shared.config import Settings, load_agent_config
from shared.errors import ProblemError, problem_error_handler, validation_error_handler
from shared.worker import create_task_store

logger = logging.getLogger(__name__)
_DYNAMIC_AGENT_BASE = "_agent2_dynamic_agents"
_AGENT_NAME_SANITIZER_RE = re.compile(r"[^a-zA-Z0-9_]")
_DIGIT_PATTERN_RE = re.compile(r"^\^\\d\{(\d+)\}\$$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_mock_result(agent_module: Any, input_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate a mock result that conforms to the agent's output_type schema.

    When no ``OPENROUTER_API_KEY`` is set the framework returns a synthetic
    response so that the API can be exercised during development without
    hitting a real LLM.
    """
    try:
        custom_mock = getattr(agent_module, "mock_result", None)
        if callable(custom_mock):
            result = custom_mock(dict(input_data or {}))
            if isinstance(result, dict):
                return result

        output_type = getattr(agent_module, "output_type", None)
        if output_type is None:
            # Try to get it from the agent object itself
            agent_obj = getattr(agent_module, "agent", None)
            if agent_obj is not None:
                output_type = getattr(agent_obj, "output_type", None)

        if output_type is not None:
            schema = output_type.model_json_schema()
            return _schema_to_example(schema)
    except Exception as exc:
        logger.debug("Could not generate mock from schema: %s", exc)

    return {"mock": True, "message": "No OPENROUTER_API_KEY configured. This is a mock response."}


def _schema_to_example(schema: dict[str, Any]) -> dict[str, Any]:
    """Walk a JSON Schema and produce an example value for each field."""
    result: dict[str, Any] = {}
    properties = schema.get("properties", {})
    defs = schema.get("$defs", {})

    for field_name, field_schema in properties.items():
        result[field_name] = _example_for_field(field_schema, defs, field_name=field_name)

    return result


def _example_for_field(
    field_schema: dict[str, Any],
    defs: dict[str, Any],
    *,
    field_name: str | None = None,
) -> Any:
    """Return an example value matching *field_schema*."""
    # Handle $ref
    if "$ref" in field_schema:
        ref_path = field_schema["$ref"]  # e.g. "#/$defs/Foo"
        ref_name = ref_path.rsplit("/", 1)[-1]
        if ref_name in defs:
            return _schema_to_example(defs[ref_name])
        return {}

    if "const" in field_schema:
        return field_schema["const"]

    # Handle anyOf (optional fields in Pydantic v2)
    if "anyOf" in field_schema:
        for variant in field_schema["anyOf"]:
            if variant.get("type") != "null":
                return _example_for_field(variant, defs, field_name=field_name)
        return None

    if "oneOf" in field_schema:
        for variant in field_schema["oneOf"]:
            if variant.get("type") != "null":
                return _example_for_field(variant, defs, field_name=field_name)
        return None

    field_type = field_schema.get("type", "string")
    normalized_name = (field_name or field_schema.get("title", "")).lower()

    if field_type == "string":
        if "enum" in field_schema:
            return field_schema["enum"][0]
        pattern = field_schema.get("pattern")
        if isinstance(pattern, str):
            digit_pattern = _DIGIT_PATTERN_RE.fullmatch(pattern)
            if digit_pattern:
                digit_count = int(digit_pattern.group(1))
                if digit_count == 4 and "date" in normalized_name:
                    return "1502"
                if digit_count == 8 and "date" in normalized_name:
                    return "20260215"
                return "1" * digit_count

        string_examples = {
            "title": "Example title",
            "summary": "Example summary",
            "language": "en",
            "message": "Example message",
            "email": "user@example.com",
            "subject": "Example subject",
            "question": "Example question",
            "answer": "Example answer",
            "status": "completed",
            "description": "Example description",
        }
        for key, value in string_examples.items():
            if key in normalized_name:
                return value
        return field_schema.get("default", "example")
    elif field_type == "integer":
        return field_schema.get("default", 0)
    elif field_type == "number":
        return field_schema.get("default", 0.0)
    elif field_type == "boolean":
        return field_schema.get("default", False)
    elif field_type == "array":
        items = field_schema.get("items", {})
        return [_example_for_field(items, defs)]
    elif field_type == "object":
        if "properties" in field_schema:
            return _schema_to_example(field_schema)
        return {}
    elif field_type == "null":
        return None
    else:
        return None


def _is_provider_auth_error(exc: Exception) -> bool:
    """Return True when a provider rejected the configured credentials."""
    message = str(exc).lower()
    auth_markers = (
        "status_code: 401",
        "invalid api key",
        "unauthorized",
        "authentication",
        "user not found",
    )
    return any(marker in message for marker in auth_markers)


async def _call_after_run_hook(
    agent_module: Any,
    hook_input: dict[str, Any],
    output_dict: dict[str, Any],
    *,
    message_history: Any = None,
) -> dict[str, Any]:
    """Execute ``after_run`` if available and keep outputs persistence-safe."""
    finalized_output = dict(output_dict)
    if "_message_history" not in finalized_output:
        finalized_output["_message_history"] = message_history if message_history is not None else []

    after_run = getattr(agent_module, "after_run", None)
    if callable(after_run):
        try:
            await after_run(hook_input, finalized_output)
        except Exception as exc:
            logger.warning(
                "Agent '%s' after_run hook failed: %s",
                getattr(agent_module, "__name__", "unknown"),
                exc,
            )
    return finalized_output


def _sanitize_agent_module_segment(agent_name: str) -> str:
    return _AGENT_NAME_SANITIZER_RE.sub("_", agent_name)


def _ensure_dynamic_agent_namespace(agent_dir: Path, package_name: str) -> None:
    if _DYNAMIC_AGENT_BASE not in sys.modules:
        base_module = importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec(_DYNAMIC_AGENT_BASE, loader=None, is_package=True)
        )
        base_module.__path__ = []  # type: ignore[attr-defined]
        sys.modules[_DYNAMIC_AGENT_BASE] = base_module

    if package_name in sys.modules:
        return

    init_file = agent_dir / "__init__.py"
    if init_file.exists():
        spec = importlib.util.spec_from_file_location(
            package_name,
            init_file,
            submodule_search_locations=[str(agent_dir)],
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create package spec for '{package_name}'.")
        module = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = module
        spec.loader.exec_module(module)
    else:
        module = importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec(package_name, loader=None, is_package=True)
        )
        module.__path__ = [str(agent_dir)]  # type: ignore[attr-defined]
        sys.modules[package_name] = module


def _load_source_agent_module(agent_name: str) -> Any:
    agent_dir = Path(__file__).resolve().parent.parent / "agents" / agent_name
    agent_file = agent_dir / "agent.py"
    if not agent_file.exists():
        raise ModuleNotFoundError(f"No source-layout agent module found for '{agent_name}'.")

    package_name = f"{_DYNAMIC_AGENT_BASE}.{_sanitize_agent_module_segment(agent_name)}"
    _ensure_dynamic_agent_namespace(agent_dir, package_name)

    module_name = f"{package_name}.agent"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, agent_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load source-layout agent module for '{agent_name}'.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_agent_module(agent_name: str) -> Any:
    import_paths = ["agent.agent"]
    for path in import_paths:
        try:
            return importlib.import_module(path)
        except (ModuleNotFoundError, ImportError):
            continue

    try:
        return _load_source_agent_module(agent_name)
    except (ModuleNotFoundError, ImportError) as exc:
        raise ProblemError(
            status=500,
            title="Agent Module Error",
            detail=(
                f"Could not import agent module for '{agent_name}'. "
                "Tried Docker layout 'agent.agent' and source layout "
                f"'agents/{agent_name}/agent.py'. Ensure the module and its dependencies are importable."
            ),
        ) from exc


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

def _make_lifespan(agent_name: str):
    """Build the ASGI lifespan context manager for this app."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # --- Startup ---
        settings = Settings.from_env()
        app.state.settings = settings
        app.state.agent_name = agent_name

        config = load_agent_config(agent_name)
        app.state.agent_config = config

        # Connect task store (Redis with in-memory fallback)
        task_store = await create_task_store(settings.redis_url)
        app.state.task_store = task_store

        logger.info(
            "Agent '%s' started on port %d (model=%s, llm_key=%s, langfuse=%s)",
            agent_name,
            config.port,
            config.model or settings.default_model,
            "yes" if settings.has_llm_key else "NO (mock mode)",
            "yes" if settings.has_langfuse else "no",
        )

        yield

        # --- Shutdown ---
        await task_store.close()
        logger.info("Agent '%s' shut down", agent_name)

    return lifespan


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(agent_name: str) -> FastAPI:
    """Create a complete FastAPI application for an agent service.

    Parameters
    ----------
    agent_name:
        The agent directory name under ``agents/``.  Used to load
        ``config.yaml`` and dynamically import ``agent.agent``.
    """

    config = load_agent_config(agent_name)

    app = FastAPI(
        title=f"Agent2: {agent_name}",
        description=config.description or f"API for the {agent_name} agent",
        version="0.1.0",
        lifespan=_make_lifespan(agent_name),
    )

    # -- Error handlers ------------------------------------------------------
    app.add_exception_handler(ProblemError, problem_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

    # -- Routes --------------------------------------------------------------

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, Any]:
        """Public health-check endpoint. No authentication required."""
        return {
            "status": "ok",
            "agent": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.post("/tasks", tags=["tasks"], status_code=200)
    async def create_task(
        request: Request,
        mode: str = Query("sync", pattern="^(sync|async)$"),
        _token: str = Depends(require_auth),
    ) -> JSONResponse:
        """Create and execute an agent task.

        Query Parameters
        ----------------
        mode : str
            ``sync`` (default) -- run inline, return result with 200.
            ``async`` -- queue task, return 202 with ``task_id``.

        Request Body
        ------------
        JSON object with an ``input`` key containing arbitrary data::

            {"input": {"question": "What is the meaning of life?"}}
        """
        try:
            body = await request.json()
        except Exception:
            raise ProblemError(
                status=400,
                title="Bad Request",
                detail="Request body must be valid JSON.",
            )

        if not isinstance(body, dict):
            raise ProblemError(
                status=422,
                title="Unprocessable Entity",
                detail="Request body must be a JSON object, not an array or primitive.",
            )

        input_data = body.get("input", {})
        if not isinstance(input_data, dict):
            raise ProblemError(
                status=422,
                title="Unprocessable Entity",
                detail="The 'input' field must be a JSON object, not an array or primitive.",
            )

        settings: Settings = request.app.state.settings
        task_store = request.app.state.task_store

        if mode == "async":
            return await _handle_async(
                request, agent_name, input_data, settings, task_store
            )
        else:
            return await _handle_sync(
                request, agent_name, input_data, settings
            )

    @app.get("/tasks/{task_id}", tags=["tasks"])
    async def get_task(
        request: Request,
        task_id: str,
        _token: str = Depends(require_auth),
    ) -> JSONResponse:
        """Retrieve the status and result of a previously created task."""
        task_store = request.app.state.task_store
        task = await task_store.get_task(task_id)

        if task is None:
            raise ProblemError(
                status=404,
                title="Not Found",
                detail=f"Task '{task_id}' not found or has expired",
            )

        return JSONResponse(
            status_code=200,
            content=task.to_dict(),
        )

    @app.post("/tasks/{task_id}/actions/execute", tags=["tasks"])
    async def execute_pending_action(
        request: Request,
        task_id: str,
        _token: str = Depends(require_auth),
    ) -> JSONResponse:
        """Execute a pending action for a task result."""
        try:
            body = await request.json()
        except Exception:
            raise ProblemError(
                status=400,
                title="Bad Request",
                detail="Request body must be valid JSON.",
            )

        if not isinstance(body, dict):
            raise ProblemError(
                status=422,
                title="Unprocessable Entity",
                detail="Request body must be a JSON object, not an array or primitive.",
            )

        action = body.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ProblemError(
                status=422,
                title="Unprocessable Entity",
                detail="The 'action' field is required and must be a non-empty string.",
            )

        params = body.get("params")
        if params is not None and not isinstance(params, dict):
            raise ProblemError(
                status=422,
                title="Unprocessable Entity",
                detail="The optional 'params' field must be a JSON object.",
            )

        raw_index = body.get("index")
        if raw_index is not None and not isinstance(raw_index, int):
            raise ProblemError(
                status=422,
                title="Unprocessable Entity",
                detail="The optional 'index' field must be an integer.",
            )

        try:
            agent_module = _load_agent_module(agent_name)
            action_executor = getattr(agent_module, "execute_action", None)
            workflow = ApprovalWorkflow(
                store=TaskStoreApprovalStore(request.app.state.task_store),
                action_executor=action_executor if callable(action_executor) else default_execute_action,
            )
            result = await workflow.execute_pending_action(
                task_id,
                action=action.strip(),
                params=params,
                index=raw_index,
            )
        except ApprovalWorkflowError as exc:
            raise ProblemError(status=exc.status, title=exc.title, detail=exc.detail) from exc

        return JSONResponse(status_code=200, content=result)

    return app


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

async def _load_and_run_agent(
    agent_name: str,
    input_data: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    """Dynamically load the agent module and run it.

    The agent module is expected to live at ``agent.agent`` (i.e. the
    ``agent/`` package inside the agent's Docker context or sys.path).

    The module must expose an ``agent`` attribute (a PydanticAI Agent
    instance).
    """
    agent_module = _load_agent_module(agent_name)

    message_history = None
    raw_history = input_data.pop("message_history", None)
    if raw_history:
        try:
            from shared.message_history import deserialize_messages

            message_history = deserialize_messages(raw_history)
            logger.info(
                "Loaded message_history with %d messages for agent '%s'",
                len(message_history),
                agent_name,
            )
        except Exception as exc:
            logger.warning("Failed to deserialize message_history for agent '%s': %s", agent_name, exc)

    hook_input = dict(input_data)
    if raw_history is not None:
        hook_input["message_history"] = raw_history

    before_run = getattr(agent_module, "before_run", None)
    if callable(before_run):
        try:
            prepared = before_run(dict(hook_input))
            if isinstance(prepared, dict):
                input_data = prepared
                hook_input = dict(prepared)
        except Exception as exc:
            logger.error("Agent '%s' before_run hook failed: %s", agent_name, exc)
            raise ProblemError(
                status=500,
                title="Agent Precondition Failed",
                detail=str(exc),
            ) from exc

    # -- Mock mode when no LLM key is present --------------------------------
    if not settings.has_llm_key:
        logger.info("No OPENROUTER_API_KEY set; returning mock result")
        return await _call_after_run_hook(
            agent_module,
            hook_input,
            _generate_mock_result(agent_module, hook_input),
            message_history=raw_history if message_history is not None else [],
        )

    # -- Run the agent -------------------------------------------------------
    agent_obj = getattr(agent_module, "agent", None)
    if agent_obj is None:
        raise ProblemError(
            status=500,
            title="Agent Module Error",
            detail="The 'agent.agent' module must expose an 'agent' attribute "
            "(a PydanticAI Agent instance).",
        )

    run_instructions = None
    if callable(before_run):
        run_instructions = input_data.pop("_instructions", None)
    else:
        input_data.pop("_instructions", None)

    input_str = json.dumps(input_data)
    try:
        run_kwargs: dict[str, Any] = {"message_history": message_history}
        if run_instructions is not None:
            run_kwargs["instructions"] = run_instructions
        result = await agent_obj.run(input_str, **run_kwargs)
    except Exception as exc:
        if _is_provider_auth_error(exc):
            logger.warning(
                "Agent '%s' provider auth failed; returning mock result instead of 500. Error: %s",
                agent_name,
                exc,
            )
            mock_result = _generate_mock_result(agent_module, hook_input)
            mock_result["_mock_reason"] = "provider_auth_failed"
            mock_result["_mock_error"] = str(exc)
            return await _call_after_run_hook(
                agent_module,
                hook_input,
                mock_result,
                message_history=raw_history if message_history is not None else [],
            )
        raise

    # result.output is a Pydantic model -- serialise to dict
    output = result.output
    if hasattr(output, "model_dump"):
        output_dict = output.model_dump(mode="json")
    elif isinstance(output, dict):
        output_dict = output
    else:
        output_dict = {"result": str(output)}

    try:
        from shared.message_history import serialize_messages

        output_dict["_message_history"] = serialize_messages(result.all_messages())
    except Exception as exc:
        logger.warning("Failed to serialize message_history: %s", exc)

    return await _call_after_run_hook(agent_module, hook_input, output_dict)


async def _handle_sync(
    request: Request,
    agent_name: str,
    input_data: dict[str, Any],
    settings: Settings,
) -> JSONResponse:
    """Execute the agent synchronously and return the result."""
    try:
        result = await _load_and_run_agent(agent_name, input_data, settings)
    except ProblemError:
        raise
    except Exception as exc:
        logger.exception("Agent '%s' failed during sync execution", agent_name)
        raise ProblemError(
            status=500,
            title="Agent Execution Error",
            detail=str(exc),
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "completed",
            "agent": agent_name,
            "input": input_data,
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    )


async def _handle_async(
    request: Request,
    agent_name: str,
    input_data: dict[str, Any],
    settings: Settings,
    task_store: Any,
) -> JSONResponse:
    """Create a background task and return immediately with a task ID."""
    task = await task_store.create_task(agent_name, input_data)

    # NOTE: Tasks are not durable -- a process restart will lose pending tasks.
    # This is acceptable for MVP. Upgrade path: Temporal workflows (see docs/deployment.md).
    bg_task = asyncio.create_task(
        _run_task_background(task.task_id, agent_name, input_data, settings, task_store),
        name=f"agent-task-{task.task_id}",
    )
    # Suppress "exception was never retrieved" -- errors are already stored in task_store
    bg_task.add_done_callback(lambda t: None)

    return JSONResponse(
        status_code=202,
        content={
            "task_id": task.task_id,
            "status": "pending",
            "agent": agent_name,
            "created_at": task.created_at,
        },
    )


async def _run_task_background(
    task_id: str,
    agent_name: str,
    input_data: dict[str, Any],
    settings: Settings,
    task_store: Any,
) -> None:
    """Execute the agent in the background and update the task store."""
    try:
        await task_store.update_task(task_id, status="running")

        result = await _load_and_run_agent(agent_name, input_data, settings)

        await task_store.update_task(
            task_id,
            status="completed",
            result=result,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("Background task %s completed", task_id)

    except Exception as exc:
        logger.exception("Background task %s failed", task_id)
        await task_store.update_task(
            task_id,
            status="failed",
            error=str(exc),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
