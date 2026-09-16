from __future__ import annotations

from pathlib import Path

from flask import Flask
from flask_cors import CORS

from backend.config import get_config
from backend.database import init_db
from backend.routes import bp


def create_app() -> Flask:
    config = get_config()
    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "frontend" / "templates"),
        static_folder=str(base_dir / "frontend" / "static"),
    )
    app.config.from_object(config)
    CORS(app)
    init_db(config.DATABASE_PATH)
    app.register_blueprint(bp)
    return app
