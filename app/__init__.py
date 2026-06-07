from flask import Flask
from flask_cors import CORS
from .config import Config

_CORS_ORIGINS = [
    "https://api.universidad.localhost",
    "http://localhost",
    r"http://localhost:\d+",
    "null",  # file:// pages
]


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app, origins=_CORS_ORIGINS, supports_credentials=True)

    from .routes.users import users_bp
    app.register_blueprint(users_bp)

    from werkzeug.exceptions import HTTPException
    from app.utils.errors import problem_details, internal_server_error

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Map standard Flask HTTP exceptions (404, 400, etc.) to RFC 9457 Problem Details"""
        return problem_details(
            status=e.code,
            title=e.name,
            detail=e.description
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """Map unhandled system exceptions to 500 Internal Server Error Problem Details"""
        app.logger.error(f"Unhandled Exception: {str(e)}", exc_info=True)
        return internal_server_error(detail=str(e))

    @app.route("/health")
    def health_check():
        return {"status": "ok", "service": "user"}, 200

    return app
