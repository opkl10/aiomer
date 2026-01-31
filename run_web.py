#!/usr/bin/env python3
"""Run the Aiomer AI web application.

Usage:
    python run_web.py [--host HOST] [--port PORT] [--reload]

Example:
    python run_web.py
    python run_web.py --host 0.0.0.0 --port 8080
    python run_web.py --reload  # Development mode with auto-reload
"""

import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run Aiomer AI Web Application")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    print(f"""
    ╔═══════════════════════════════════════════════╗
    ║           Aiomer AI - Web Server              ║
    ╠═══════════════════════════════════════════════╣
    ║  Running on: http://{args.host}:{args.port:<5}              ║
    ║  Press Ctrl+C to stop                         ║
    ╚═══════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "src.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
