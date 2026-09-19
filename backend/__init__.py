from __future__ import annotations

from pathlib import Path

from flask import Flask
from flask_cors import CORS

from backend.config import get_config
from backend.database import init_db
from backend.routes import bp
from backend.auth import auth_bp, init_login
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf


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
    init_login(app)
    # CSRF protection for forms
    csrf = CSRFProtect()
    csrf.init_app(app)
    # make csrf_token available in templates
    app.jinja_env.globals["csrf_token"] = generate_csrf
    app.register_blueprint(bp)
    # Exempt JSON/API endpoints from CSRF (client-side JS posts)
    for rule in app.url_map.iter_rules():
        try:
            if rule.rule.startswith("/api/"):
                view = app.view_functions.get(rule.endpoint)
                if view:
                    csrf.exempt(view)
        except Exception:
            # ignore any url_map inspection errors
            pass
    app.register_blueprint(auth_bp)
    return app
