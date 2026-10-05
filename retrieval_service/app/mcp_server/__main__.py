"""Run the MCP server standalone.

    python -m app.mcp_server                      # stdio (Claude Desktop / Claude Code)
    python -m app.mcp_server --transport http     # Streamable HTTP on :5556/mcp

Run from the retrieval_service folder. In normal deployments the MCP endpoint is
served by the main API instead (`uvicorn app.main:app` -> http://host:5555/mcp).
"""
import argparse
import logging
import sys

from app.core.logging_setup import setup_logging


def main():
    parser = argparse.ArgumentParser(description="Legal retrieval MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5556)
    args = parser.parse_args()

    setup_logging()
    if args.transport == "stdio":
        # stdout carries the MCP protocol: keep log output on stderr only.
        loggers = [logging.getLogger()] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        for handler in {h for lg in loggers for h in lg.handlers}:
            if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
                handler.setStream(sys.stderr)

    from app.mcp_server.server import mcp, streamable_http_app

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn

        uvicorn.run(streamable_http_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
