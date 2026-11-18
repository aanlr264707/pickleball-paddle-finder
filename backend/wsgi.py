"""WSGI entry point for production servers: ``gunicorn wsgi:app``."""

from paddle_finder.api import create_app

app = create_app()
