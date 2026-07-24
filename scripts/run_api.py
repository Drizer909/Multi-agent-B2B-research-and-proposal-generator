"""
Launch the B2B Proposal Generator API server.
"""

import sys
from pathlib import Path
import os
import argparse
import uvicorn

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    default_port = int(os.environ.get("PORT", 8000))
    parser = argparse.ArgumentParser(description="B2B Proposal Generator API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=default_port, help="Port")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()

    print("\n" + "🌐" * 30)
    print("  B2B PROPOSAL GENERATOR — API Server")
    print("🌐" * 30)

    # Auto-reload should be OFF in production (e.g., inside Docker or on Render)
    # to prevent WatchFiles from restarting the app when ChromaDB/SQLite files are written.
    env_reload = os.environ.get("RELOAD", "false").lower() == "true"
    should_reload = env_reload if not args.no_reload else False

    uvicorn.run(
        "src.api.app:app",
        host=args.host,
        port=args.port,
        reload=should_reload,
    )

if __name__ == "__main__":
    main()
