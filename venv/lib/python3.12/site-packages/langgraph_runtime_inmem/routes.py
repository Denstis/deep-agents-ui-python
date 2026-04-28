"""Internal routes for inmem runtime (testing/debugging only)."""

import asyncio
import collections
import json
import logging
import os
import re
import sys
import time
import uuid

from langgraph_runtime_inmem.database import connect

logger = logging.getLogger(__name__)

DEPLOY_TIMEOUT_SECONDS = 900  # 15 minutes

_ALLOWED_DEPLOY_ORIGINS = {
    "https://smith.langchain.com",
    "https://dev.smith.langchain.com",
    "https://staging.smith.langchain.com",
}


def _is_allowed_deploy_origin(origin: str) -> bool:
    """Check whether *origin* is permitted to call deploy endpoints."""
    if not origin:
        return True
    if re.match(r"http://(localhost|127\.0\.0\.1)(:\d+)?$", origin):
        return True
    return origin in _ALLOWED_DEPLOY_ORIGINS


class DeployOperation:
    """Tracks a single ``langgraph deploy`` subprocess and its output."""

    __slots__ = (
        "operation_id",
        "status",
        "exit_code",
        "started_at",
        "finished_at",
        "logs",
        "status_url",
        "app_url",
        "deployment_id",
        "deploy_status",
        "_proc",
        "_reader_task",
        "_timeout_task",
        "_total_appended",
    )

    def __init__(
        self,
        proc: asyncio.subprocess.Process,
        started_at: float,
    ) -> None:
        self.operation_id: str = uuid.uuid4().hex[:12]
        self.status: str = "running"  # running | succeeded | failed
        self.exit_code: int | None = None
        self.started_at: float = started_at
        self.finished_at: float | None = None
        self.logs: collections.deque[str] = collections.deque(maxlen=2000)
        self.status_url: str | None = None
        self.app_url: str | None = None
        self.deployment_id: str | None = None
        self.deploy_status: str | None = None
        self._proc = proc
        self._reader_task: asyncio.Task | None = None
        self._timeout_task: asyncio.Task | None = None
        self._total_appended: int = 0


_current_op: DeployOperation | None = None


async def _read_subprocess(op: DeployOperation) -> None:
    """Drain subprocess stdout into the ring buffer, then record exit status.

    When the CLI is invoked with ``--json``, each line is a JSON object.
    Structured events are used to populate ``op.status_url``, ``op.app_url``,
    etc.  The human-readable ``message`` field (when present) is appended to
    the log ring buffer for the SSE stream.
    """
    try:
        assert op._proc.stdout is not None
        async for raw_line in op._proc.stdout:
            line = raw_line.decode(errors="replace").rstrip()
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                op.logs.append(line)
                op._total_appended += 1
                continue

            evt_type = event.get("event")
            msg = event.get("message", "")

            if evt_type == "status_url":
                op.status_url = event.get("url")
            elif evt_type == "result":
                op.app_url = event.get("url")
                op.deploy_status = event.get("status")
                op.deployment_id = event.get("deployment_id")
                if not op.status_url:
                    op.status_url = event.get("status_url")
            elif evt_type == "step":
                op.deployment_id = event.get("deployment_id") or op.deployment_id

            if msg:
                op.logs.append(msg)
                op._total_appended += 1

        exit_code = await op._proc.wait()
        op.exit_code = exit_code
        op.status = "succeeded" if exit_code == 0 else "failed"
    except Exception:
        op.status = "failed"
    finally:
        op.finished_at = time.time()
        if op._timeout_task and not op._timeout_task.done():
            op._timeout_task.cancel()


async def _timeout_watchdog(
    op: DeployOperation,
    timeout_seconds: float = DEPLOY_TIMEOUT_SECONDS,
) -> None:
    """Kill the subprocess if it exceeds *timeout_seconds*."""
    await asyncio.sleep(timeout_seconds)
    if op.status == "running" and op._proc and op._proc.returncode is None:
        logger.warning(
            "Deploy operation %s timed out after %ss, killing subprocess",
            op.operation_id,
            timeout_seconds,
        )
        op._proc.kill()
    else:
        logger.debug(
            "Deploy operation %s finished before timeout (status=%s)",
            op.operation_id,
            op.status,
        )


def get_internal_routes():
    from langgraph_api.config import MIGRATIONS_PATH  # noqa: PLC0415

    try:
        from langgraph_api.middleware import http_logger  # noqa: PLC0415

        http_logger.PATHS_IGNORE.add("/internal/truncate")
    except ImportError:
        pass

    if "__inmem" not in MIGRATIONS_PATH:
        # not in a testing mode.
        return []
    from langgraph_api.route import ApiRequest, ApiResponse, ApiRoute  # noqa: PLC0415
    from langgraph_api.sse import EventSourceResponse  # noqa: PLC0415

    async def truncate(request: ApiRequest):
        """Truncate all inmem data (for testing)."""
        from langgraph_api import config as api_config  # noqa: PLC0415

        if api_config.USE_CUSTOM_CHECKPOINTER:
            from langgraph_api._checkpointer._adapter import (  # noqa: PLC0415
                CHECKPOINTER_STACK,
            )

            inner = getattr(CHECKPOINTER_STACK, "inner", None)
            if inner is not None and hasattr(inner, "clear"):
                await asyncio.to_thread(inner.clear)
        else:
            from langgraph_runtime.checkpoint import Checkpointer  # noqa: PLC0415

            await asyncio.to_thread(Checkpointer().clear)
        async with connect() as conn:
            await asyncio.to_thread(conn.clear)
        return ApiResponse({"ok": True})

    async def debug_get_raw_thread(request: ApiRequest):
        """Return raw thread from store without decryption (for testing)."""
        thread_id = request.path_params["thread_id"]
        async with connect() as conn:
            for thread in conn.store["threads"]:
                if str(thread["thread_id"]) == thread_id:
                    return ApiResponse(thread)
        return ApiResponse({"error": "not found"}, status_code=404)

    # Deploy endpoints

    def _check_deploy_origin(request: ApiRequest):
        origin = request.headers.get("origin", "")
        if not _is_allowed_deploy_origin(origin):
            return ApiResponse({"error": "origin not allowed"}, status_code=403)
        return None

    def _collect_deploy_info() -> dict:
        """Gather deploy metadata (runs in a thread to avoid blocking the loop)."""
        cwd = os.getcwd()
        return {
            "default_name": re.sub(r"[^a-z0-9-]", "-", os.path.basename(cwd).lower()),
            "has_api_key": bool(
                os.environ.get("LANGSMITH_API_KEY")
                or os.environ.get("LANGCHAIN_API_KEY")
                or os.environ.get(
                    "LANGGRAPH_HOST_API_KEY"
                )  # Not in public docs: internal
            ),
            "has_config": os.path.isfile(os.path.join(cwd, "langgraph.json")),
        }

    def _serialize_operation(op: DeployOperation) -> dict:
        return {
            "operation_id": op.operation_id,
            "status": op.status,
            "exit_code": op.exit_code,
            "started_at": op.started_at,
            "finished_at": op.finished_at,
            "status_url": op.status_url,
            "app_url": op.app_url,
        }

    async def get_deploy(request: ApiRequest):
        """Return deploy metadata and current operation state (if any).

        Combines what was previously /deploy/info and /deploy/active into
        a single GET /deploy endpoint to reduce round-trips.
        """
        if err := _check_deploy_origin(request):
            return err
        info = await asyncio.to_thread(_collect_deploy_info)
        payload: dict = {**info, "current_operation": None}
        if _current_op:
            payload["current_operation"] = _serialize_operation(_current_op)
        return ApiResponse(payload)

    async def start_deploy(request: ApiRequest):
        """Start a new deploy operation."""
        global _current_op

        if err := _check_deploy_origin(request):
            return err

        if _current_op and _current_op.status == "running":
            return ApiResponse(
                {
                    "error": "Deploy already in progress",
                    "operation_id": _current_op.operation_id,
                },
                status_code=409,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}
        name = body.get("name") if isinstance(body, dict) else None

        cmd = [
            sys.executable,
            "-m",
            "langgraph_cli",
            "deploy",
            "--json",
            "--no-input",
        ]
        if name:
            cmd.extend(["--name", str(name)])

        cwd = await asyncio.to_thread(os.getcwd)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )

        op = DeployOperation(proc=proc, started_at=time.time())
        op._reader_task = asyncio.create_task(_read_subprocess(op))
        op._timeout_task = asyncio.create_task(_timeout_watchdog(op))
        _current_op = op

        return ApiResponse({"operation_id": op.operation_id, "status": op.status})

    async def stream_deploy_logs(request: ApiRequest):
        """SSE stream of deploy log lines. Replays buffered lines on reconnect."""
        if err := _check_deploy_origin(request):
            return err
        op_id = request.path_params["operation_id"]
        if not _current_op or _current_op.operation_id != op_id:
            return ApiResponse({"error": "not found"}, status_code=404)
        op = _current_op

        async def generate():
            sent_through = 0
            while True:
                snapshot = list(op.logs)
                total = op._total_appended
                deque_start = total - len(snapshot)
                skip = max(0, sent_through - deque_start)
                for line in snapshot[skip:]:
                    yield (b"log", line)
                sent_through = total

                if op.status != "running":
                    snapshot = list(op.logs)
                    total = op._total_appended
                    deque_start = total - len(snapshot)
                    skip = max(0, sent_through - deque_start)
                    for line in snapshot[skip:]:
                        yield (b"log", line)
                    event = b"done" if op.status == "succeeded" else b"error"
                    yield (event, {"exit_code": op.exit_code})
                    return

                await asyncio.sleep(0.1)

        return EventSourceResponse(generate())

    # Routes are inserted via `unshadowable_meta_routes.insert(0, route)`
    # in api/__init__.py, which reverses the order.  Put parameterised
    # paths first so they end up LAST after reversal.
    return [
        ApiRoute(
            "/deploy/{operation_id}/stream",
            stream_deploy_logs,
            methods=["GET"],
        ),
        ApiRoute("/deploy", start_deploy, methods=["POST"]),
        ApiRoute("/deploy", get_deploy, methods=["GET"]),
        ApiRoute(
            "/internal/debug/thread/{thread_id}",
            debug_get_raw_thread,
            methods=["GET"],
        ),
        ApiRoute("/internal/truncate", truncate, methods=["POST"]),
    ]
