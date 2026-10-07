"""The MCP server, the product surface (slice 15, A41).

Claude Desktop starts this as a subprocess and talks JSON-RPC over its stdin
and stdout. It opens no network port, so no rule text leaves the machine.
stdout belongs to the protocol: nothing here may print to it, which is why
the SDK's logging goes to stderr.

The tools are thin: rb_errata/tools.py holds every rule and its tests.

    uv run python -m rb_errata.server
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from rb_errata import tools

INSTRUCTIONS = (
    "Riftbound Core Rules, by version and date. Rules change between versions and "
    "numbers shift, so always pass the date the question is about as as_of (today if "
    "it is about now). Cite rules by the ref each passage carries, like core@1.4:419.4.a. "
    "A passage with newer_version_exists true is from an older version: say so."
)
# httpx logs every Ollama request at INFO, one line per search on stderr:
# 224 lines in the first `make mcp-check`. Warnings and errors still show.
logging.getLogger("httpx").setLevel(logging.WARNING)
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

server = MCPServer("rb-errata", instructions=INSTRUCTIONS)
_backend = tools.Backend()


@server.tool(annotations=READ_ONLY)
def search_rules(question: str, as_of: str | None = None, k: int = 5) -> dict[str, Any]:
    """Find the Core Rules passages that answer a question, as of a date.

    Only rules in force on as_of are searched, so an outdated version never
    appears. as_of is YYYY-MM-DD and defaults to today; dates before the first
    datable version are refused. k is how many passages to return (1 to 20).
    """
    return tools.search_rules(question, as_of, k, _backend.search)


@server.tool(annotations=READ_ONLY)
def get_rule(ref: str) -> dict[str, Any]:
    """The text of one rule in one version, with the dates that version was in force.

    ref is document, version and number, like core@1.4:419.4.a. The first call
    for a version reads its PDF and takes several seconds.
    """
    return tools.get_rule(ref)


@server.tool(annotations=READ_ONLY)
def list_versions() -> dict[str, Any]:
    """Every Core Rules version, when it took effect, and whether it is searchable."""
    return tools.list_versions()


@server.tool(annotations=READ_ONLY)
def what_changed(
    from_version: str, to_version: str, ref: str | None = None, limit: int = 20
) -> dict[str, Any]:
    """What changed in the Core Rules between two versions.

    With ref (a rule in either version, like core@1.4:419.4.a): that rule's
    counterpart in the other version and whether it changed, was renumbered,
    added or removed. Rules are matched by wording, never by number. Without
    ref: the changed rules, meaning-flipping wording first, up to limit, plus
    the refs of added and removed rules. The first call reads two PDFs and
    takes several seconds.
    """
    return tools.what_changed(from_version, to_version, ref, limit)


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
