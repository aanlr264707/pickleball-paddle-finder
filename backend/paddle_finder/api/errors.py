"""JSON error responses.

Every error leaves the API in the same shape::

    {"error": {"status": 400, "message": "...", "field": "preferences[0].importance"}}
"""

from __future__ import annotations

from typing import Optional

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """An error the client can fix (bad input, unknown id...).

    Attributes:
        status (int): HTTP status code.
        message (str): Human-readable explanation.
        field (str | None): The request field that caused it, if any.
    """

    def __init__(self, message: str, status: int = 400, field: Optional[str] = None):
        """Create the error.

        Args:
            message (str): Human-readable explanation.
            status (int): HTTP status code. Defaults to 400.
            field (str | None): The request field that caused it.
        """
        super().__init__(message)
        self.status = status
        self.message = message
        self.field = field


def error_body(status: int, message: str, field: Optional[str] = None) -> dict:
    """Build the JSON body for an error.

    Args:
        status (int): HTTP status code.
        message (str): Human-readable explanation.
        field (str | None): The request field that caused it.

    Returns:
        dict: ``{"error": {...}}``.
    """
    error = {"status": status, "message": message}
    if field is not None:
        error["field"] = field
    return {"error": error}


def register_error_handlers(app: Flask) -> None:
    """Make every error (ours, Flask's and unexpected ones) answer in JSON.

    Args:
        app (Flask): The application.
    """

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify(error_body(error.status, error.message, error.field)), error.status

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify(error_body(error.code or 500, error.description or error.name)), error.code

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        app.logger.exception("Unhandled error", exc_info=error)
        return jsonify(error_body(500, "Internal server error")), 500
