"""
Async task state management.

For the MVP, tasks run as ``asyncio`` background tasks inside the FastAPI
process.  State is persisted to Redis so that ``GET /tasks/{id}`` works
across requests and (eventually) across processes.

When Redis is unavailable an :class:`InMemoryTaskStore` is used as a
transparent fallback for local development.

**Planned upgrade:** Replace the in-process background task execution with
Temporal workflows for production-grade durability and scaling.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task data model
# ---------------------------------------------------------------------------

@dataclass
class TaskState:
    """Represents the state of an agent task."""

    task_id: str
    status: str  # pending | running | completed | failed
    agent_name: str
    input_data: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = ""
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskState:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Redis-backed store
# ---------------------------------------------------------------------------

class TaskStore:
    """Redis-backed task state store.

    Keys are stored as ``task:{task_id}`` with a 24-hour TTL.
    An additional sorted set ``agent_tasks:{agent_name}`` indexes tasks by
    creation time for listing.
    """

    TTL_SECONDS: int = 86400  # 24 hours

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: Any = None  # redis.asyncio.Redis instance

    async def connect(self) -> None:
        """Open the Redis connection pool."""
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(
            self._redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        # Verify connectivity
        await self._redis.ping()
        logger.info("TaskStore connected to Redis at %s", self._redis_url)

    async def close(self) -> None:
        """Shut down the Redis connection pool."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("TaskStore disconnected from Redis")

    async def create_task(
        self, agent_name: str, input_data: dict[str, Any]
    ) -> TaskState:
        """Create a new task in *pending* state and persist it."""
        task = TaskState(
            task_id=str(uuid.uuid4()),
            status="pending",
            agent_name=agent_name,
            input_data=input_data,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        key = f"task:{task.task_id}"
        await self._redis.set(key, json.dumps(task.to_dict()), ex=self.TTL_SECONDS)

        # Index for listing
        index_key = f"agent_tasks:{agent_name}"
        await self._redis.zadd(index_key, {task.task_id: datetime.now(timezone.utc).timestamp()})
        await self._redis.expire(index_key, self.TTL_SECONDS)

        return task

    async def get_task(self, task_id: str) -> TaskState | None:
        """Return the current state of a task, or ``None`` if not found."""
        raw = await self._redis.get(f"task:{task_id}")
        if raw is None:
            return None
        return TaskState.from_dict(json.loads(raw))

    async def update_task(self, task_id: str, **kwargs: Any) -> None:
        """Merge *kwargs* into the stored task state."""
        key = f"task:{task_id}"
        raw = await self._redis.get(key)
        if raw is None:
            logger.warning("Attempted to update non-existent task %s", task_id)
            return

        data = json.loads(raw)
        data.update(kwargs)
        ttl = await self._redis.ttl(key)
        if ttl < 0:
            ttl = self.TTL_SECONDS
        await self._redis.set(key, json.dumps(data), ex=ttl)

    async def list_tasks(
        self, agent_name: str, limit: int = 50
    ) -> list[TaskState]:
        """Return the most recent tasks for *agent_name*."""
        index_key = f"agent_tasks:{agent_name}"
        task_ids: list[str] = await self._redis.zrevrange(index_key, 0, limit - 1)

        tasks: list[TaskState] = []
        for tid in task_ids:
            task = await self.get_task(tid)
            if task is not None:
                tasks.append(task)
        return tasks


# ---------------------------------------------------------------------------
# In-memory fallback (dev mode)
# ---------------------------------------------------------------------------

class InMemoryTaskStore:
    """In-memory fallback when Redis is unavailable.

    Implements the same public interface as :class:`TaskStore` so the rest of
    the framework is agnostic to the backing store.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._agent_index: dict[str, list[str]] = {}

    async def connect(self) -> None:
        logger.info("InMemoryTaskStore active (no Redis)")

    async def close(self) -> None:
        self._tasks.clear()
        self._agent_index.clear()

    async def create_task(
        self, agent_name: str, input_data: dict[str, Any]
    ) -> TaskState:
        task = TaskState(
            task_id=str(uuid.uuid4()),
            status="pending",
            agent_name=agent_name,
            input_data=input_data,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._tasks[task.task_id] = task
        self._agent_index.setdefault(agent_name, []).append(task.task_id)
        return task

    async def get_task(self, task_id: str) -> TaskState | None:
        return self._tasks.get(task_id)

    async def update_task(self, task_id: str, **kwargs: Any) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            logger.warning("Attempted to update non-existent task %s", task_id)
            return

        data = task.to_dict()
        data.update(kwargs)
        self._tasks[task_id] = TaskState.from_dict(data)

    async def list_tasks(
        self, agent_name: str, limit: int = 50
    ) -> list[TaskState]:
        task_ids = self._agent_index.get(agent_name, [])
        # Most recent first
        recent_ids = list(reversed(task_ids[-limit:]))
        tasks: list[TaskState] = []
        for tid in recent_ids:
            task = self._tasks.get(tid)
            if task is not None:
                tasks.append(task)
        return tasks


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

async def create_task_store(redis_url: str) -> TaskStore | InMemoryTaskStore:
    """Try to connect to Redis; fall back to in-memory if unavailable."""
    store = TaskStore(redis_url)
    try:
        await store.connect()
        return store
    except Exception as exc:
        logger.warning(
            "Redis unavailable (%s), falling back to InMemoryTaskStore", exc
        )
        fallback = InMemoryTaskStore()
        await fallback.connect()
        return fallback
