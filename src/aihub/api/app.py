"""Flask REST API (Module 7: Flask for AI deployment)."""
import hmac
import logging
import uuid

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from .. import __version__
from ..config import Settings, get_settings
from ..errors import AIHubError, ValidationError
from ..logging_conf import setup_logging
from ..services import Services
from ..tools.web import summarize_url

log = logging.getLogger(__name__)
MAX_MESSAGE_CHARS = 4000


def _json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    return data


def _required_str(data: dict, key: str, max_len: int = MAX_MESSAGE_CHARS) -> str:
    val = data.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ValidationError(f"'{key}' is required.")
    if len(val) > max_len:
        raise ValidationError(f"'{key}' is too long (max {max_len} characters).")
    return val.strip()


def create_app(settings: Settings | None = None, services: Services | None = None) -> Flask:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = settings.max_upload_mb * 1024 * 1024
    CORS(app)
    Limiter(
        get_remote_address,
        app=app,
        default_limits=[settings.rate_limit],
        storage_uri="memory://",
    )
    svc = services or Services(settings)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    @app.before_request
    def check_api_key():
        if settings.api_key and request.path.startswith("/api/"):
            supplied = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(supplied, settings.api_key):
                return jsonify(error="Invalid or missing API key."), 401

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=__version__)

    @app.post("/api/chat")
    def chat():
        data = _json_body()
        message = _required_str(data, "message")
        session_id = str(data.get("session_id") or uuid.uuid4())[:64]
        return jsonify(session_id=session_id, **svc.chat(session_id, message))

    @app.delete("/api/chat/<session_id>")
    def reset_chat(session_id):
        svc.sessions.clear(session_id)
        return jsonify(status="cleared")

    @app.post("/api/documents")
    def upload_document():
        f = request.files.get("file")
        if f is None or not f.filename:
            raise ValidationError("Attach a PDF as multipart field 'file'.")
        name = secure_filename(f.filename)
        if not name.lower().endswith(".pdf"):
            raise ValidationError("Only .pdf files are supported.")
        if f.stream.read(5) != b"%PDF-":
            raise ValidationError("File content is not a valid PDF.")
        f.stream.seek(0)
        dest = settings.upload_dir / f"{uuid.uuid4().hex}_{name}"
        f.save(dest)
        chunks = svc.kb.add_pdf(dest, name)
        return jsonify(file=name, chunks=chunks), 201

    @app.get("/api/documents")
    def list_documents():
        return jsonify(documents=svc.kb.documents())

    @app.delete("/api/documents")
    def clear_documents():
        svc.kb.clear()
        return jsonify(status="cleared")

    @app.post("/api/summarize")
    def summarize():
        url = _required_str(_json_body(), "url", 2048)
        return jsonify(summarize_url(svc.llm, url))

    @app.post("/api/sql")
    def sql():
        q = _required_str(_json_body(), "question")
        return jsonify(svc.sql().ask(q))

    @app.errorhandler(AIHubError)
    def handle_app_error(e: AIHubError):
        if e.status >= 500:
            log.exception("Server-side error")
        return jsonify(error=str(e)), e.status

    @app.errorhandler(HTTPException)
    def handle_http(e: HTTPException):
        return jsonify(error=e.description), e.code

    @app.errorhandler(Exception)
    def handle_unexpected(e: Exception):
        log.exception("Unhandled error")
        return jsonify(error="Internal server error."), 500

    return app


def app_factory() -> Flask:
    """Entry point for gunicorn:  gunicorn 'aihub.api.app:app_factory()'"""
    return create_app()
