"""Slice 17: the local web app's HTTP API, over the same functions as the MCP server.

Every endpoint calls rb_errata/tools.py, exactly what the MCP tools call, so
the browser and Claude Desktop cannot disagree. A ToolError becomes a 400
with its message (the fix is in the message, as for the MCP tools); anything
else is a 500 that names no internals.

Bound to 127.0.0.1 only (`make app`): responses carry Riot's rule text from
the local database and PDFs, which stays on this machine. The built front end
(app/dist) is served from the same address, so one command runs everything.

    GET  /api/versions
    GET  /api/rule?ref=core@1.4:419.4.a
    GET  /api/changed?from=1.3&to=1.4[&ref=...][&limit=20]
    POST /api/search   {"question", "as_of"?, "k"?}
    POST /api/ask      {"question", "as_of"?}
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from rb_errata import tools

DIST = Path("app/dist")
log = logging.getLogger("rb_errata.app")
Handler = Callable[[Request], Awaitable[Any]]


def _json(handler: Handler) -> Callable[[Request], Awaitable[Response]]:
    """Run a handler; ToolError -> 400 with its message, anything else -> 500."""

    async def wrapped(request: Request) -> Response:
        try:
            return JSONResponse(await handler(request))
        except ToolError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        except ValueError as e:  # malformed JSON body or a non-integer k
            return JSONResponse({"error": f"bad request: {e}"}, status_code=400)
        except Exception:
            log.exception("unexpected error in %s", request.url.path)
            return JSONResponse({"error": "unexpected server error; see the terminal"},
                                status_code=500)  # fmt: skip

    return wrapped


def build(backend: tools.AgentBackend | None = None) -> Starlette:
    """The app. `backend` is injectable so tests run without Postgres or Ollama."""
    be = backend or tools.AgentBackend()

    async def versions(_: Request) -> Any:
        return tools.list_versions()

    async def rule(request: Request) -> Any:
        return await run_in_threadpool(tools.get_rule, request.query_params.get("ref", ""))

    async def changed(request: Request) -> Any:
        q = request.query_params
        return await run_in_threadpool(
            tools.what_changed, q.get("from", ""), q.get("to", ""), q.get("ref") or None,
            int(q.get("limit", "20")),
        )  # fmt: skip

    async def search(request: Request) -> Any:
        body = await request.json()
        return await run_in_threadpool(
            tools.search_rules, str(body.get("question", "")), body.get("as_of") or None,
            int(body.get("k", 5)), be.search,
        )  # fmt: skip

    async def ask(request: Request) -> Any:
        body = await request.json()
        return await run_in_threadpool(
            tools.ask, str(body.get("question", "")), body.get("as_of") or None, be.ask
        )

    routes: list[Any] = [
        Route("/api/versions", _json(versions)),
        Route("/api/rule", _json(rule)),
        Route("/api/changed", _json(changed)),
        Route("/api/search", _json(search), methods=["POST"]),
        Route("/api/ask", _json(ask), methods=["POST"]),
    ]
    if DIST.exists():
        routes.append(Mount("/", StaticFiles(directory=DIST, html=True)))
    return Starlette(routes=routes)


def main(port: int = 8765) -> None:
    import uvicorn

    if not DIST.exists():
        print("app/dist not built yet: run `make app-build` (the API still works)")
    print(f"rb_errata local app: http://localhost:{port}  (Ctrl+C to stop)")
    uvicorn.run(build(), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
