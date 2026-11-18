"""Flask REST API for the paddle finder.

Run it locally::

    flask --app paddle_finder.api run --debug

Configuration comes from environment variables:

* ``DATABASE_URL``  -- e.g. ``postgresql://paddle:paddle@localhost:5432/paddles``
  (defaults to a SQLite file in ``backend/instance/``)
* ``AUTO_SEED``     -- ``1`` (default) loads the CSV when the table is empty;
  with ``0``, seed first with ``python -m paddle_finder.data.seed``
* ``FRONTEND_DIST`` -- optional path to the built React app to serve at ``/``
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

from flask import Flask, abort, send_from_directory

from ..core.config import DEFAULT_DATA_FILE
from ..data.etl import load_clean_frame
from ..data.schema import count_paddles, create_schema, make_engine, seed
from .errors import register_error_handlers
from .routes import bp
from .state import EXTENSION_KEY, load_state


def create_app(config: Optional[Mapping[str, Any]] = None) -> Flask:
    """Application factory.

    Args:
        config (Mapping[str, Any] | None): Settings that override the
            environment, e.g. ``{"DATABASE_URL": "sqlite:///test.db"}`` in tests.

    Returns:
        Flask: The configured application, with its data loaded.
    """
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.from_mapping(
        DATABASE_URL=os.environ.get("DATABASE_URL")
        or "sqlite:///" + os.path.join(app.instance_path, "paddles.db"),
        DATA_FILE=DEFAULT_DATA_FILE,
        AUTO_SEED=os.environ.get("AUTO_SEED", "1") != "0",
        FRONTEND_DIST=os.environ.get("FRONTEND_DIST", ""),
    )
    if config:
        app.config.update(config)
    app.json.sort_keys = False

    engine = make_engine(app.config["DATABASE_URL"])
    create_schema(engine)
    if app.config["AUTO_SEED"] and count_paddles(engine) == 0:
        seed(engine, load_clean_frame(app.config["DATA_FILE"]))
    app.extensions[EXTENSION_KEY] = load_state(engine)

    app.register_blueprint(bp)
    register_error_handlers(app)
    if app.config["FRONTEND_DIST"]:
        serve_frontend(app, app.config["FRONTEND_DIST"])
    return app


def serve_frontend(app: Flask, dist: str) -> None:
    """Serve the built React app, falling back to ``index.html`` for client routes.

    Args:
        app (Flask): The application.
        dist (str): Folder containing ``index.html`` and ``assets/``.
    """
    dist = os.path.abspath(dist)

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path: str):
        if path.startswith("api/"):
            abort(404)
        if path and os.path.isfile(os.path.join(dist, path)):
            return send_from_directory(dist, path)
        return send_from_directory(dist, "index.html")
