"""ASGI entry point: ``uvicorn app.main:app --app-dir backend``.

Configuration is validated when this module is imported, so a missing or
placeholder setting stops startup with a readable error.
"""
from app.factory import create_app

app = create_app()
