"""Entrypoint used by PyInstaller for the bundled CyberTriage API."""

import os

import uvicorn
from app.main import app


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("CYBERTRIAGE_HOST", "127.0.0.1"),
        port=int(os.getenv("CYBERTRIAGE_PORT", "8000")),
        log_level="warning",
    )
