from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict

from backend.app.core.research_store import ResearchStore

logger = logging.getLogger("core.job_manager")


class BackgroundJobManager:
    def __init__(self, store: ResearchStore):
        self.store = store
        self._tasks: dict[str, asyncio.Task] = {}

    async def submit(
        self,
        *,
        job_type: str,
        payload: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Dict[str, Any] | Awaitable[Dict[str, Any]]],
        run_async: bool = True,
    ) -> Dict[str, Any]:
        job = self.store.create_job(job_type=job_type, payload=payload)
        if run_async:
            task = asyncio.create_task(self._run_job(job["id"], payload, handler))
            self._tasks[job["id"]] = task
            return self.store.get_record("jobs", job["id"]) or job
        await self._run_job(job["id"], payload, handler)
        return self.store.get_record("jobs", job["id"]) or job

    async def _run_job(
        self,
        job_id: str,
        payload: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Dict[str, Any] | Awaitable[Dict[str, Any]]],
    ):
        self.store.update_job(job_id, status="running")
        try:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                result = await result
            else:
                result = await asyncio.to_thread(lambda: result)
            self.store.update_job(job_id, status="completed", result=result)
        except Exception as exc:
            self.store.update_job(job_id, status="failed", result={"error": str(exc)})
            logger.exception("Background job %s failed: %s", job_id, exc)
        finally:
            self._tasks.pop(job_id, None)
