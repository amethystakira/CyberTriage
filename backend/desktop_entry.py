"""Entrypoint used by PyInstaller for the bundled CyberTriage API."""

import os

import uvicorn


def main():
    # Set this before importing the FastAPI module: importing it initializes the DB.
    os.environ["CYBERTRIAGE_SEED_DEMO_DATA"] = "0"
    from app.main import app

    uvicorn.run(
        app,
        host=os.getenv("CYBERTRIAGE_HOST", "127.0.0.1"),
        port=int(os.getenv("CYBERTRIAGE_PORT", "8000")),
        log_level="warning",
    )


if __name__ == "__main__":
    main()
