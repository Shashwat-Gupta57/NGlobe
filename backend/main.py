"""NetworkGlobe — Application entry point.

Loads configuration, initializes logging, creates the FastAPI app,
and starts the Uvicorn server with the full startup orchestration.
"""

from __future__ import annotations

import multiprocessing
import sys
from pathlib import Path

# Ensure the project root is on PYTHONPATH for imports
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    import uvicorn
except ImportError:
    print("ERROR: Missing dependencies (uvicorn not found).")
    print("Are you running within the virtual environment?")
    print("Run: .venv\\Scripts\\activate (Windows) or source .venv/bin/activate (Mac/Linux)")
    print("Then try: python main.py")
    sys.exit(1)

from backend.api.app import create_app
from backend.config import load_config
from backend.utils.logging import get_logger, setup_logging


def main() -> None:
    """Application entry point."""
    # Required for PyInstaller on Windows
    multiprocessing.freeze_support()

    # Load centralized configuration
    config = load_config()

    # Initialize structured logging
    setup_logging(config.logging)
    logger = get_logger("networkglobe")

    logger.info(
        "networkglobe_starting",
        version="0.2.0",
        server_host=config.server.host,
        server_port=config.server.port,
        proxy_port=config.proxy.listen_port,
    )

    # Create FastAPI application
    app = create_app(config)

    # Start Uvicorn
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
