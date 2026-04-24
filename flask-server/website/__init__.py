from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from flask import Flask, current_app, render_template, request, url_for
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

from .notifications import send_appointment_notification
from .storage import init_storage, save_appointment

BASE_DIR = Path(__file__).resolve().parent.parent
ALLOWED_VISIT_TYPES = {"prima-visita", "controllo"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+() /\-]+$")


class ValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AppointmentSubmission:
    patient_name: str
    visit_type: str
    patient_email: str
    patient_phone: str
    patient_notes: str
    created_at: str


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv(BASE_DIR / ".env", override=False)

    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config.from_mapping(
        DATABASE_PATH=str(BASE_DIR / "data" / "appointments.sqlite"),
        CONTACT_EMAIL=os.getenv("CONTACT_EMAIL", ""),
        MAX_CONTENT_LENGTH=16 * 1024,
        SQLITE_JOURNAL_MODE=os.getenv("SQLITE_JOURNAL_MODE", "WAL"),
        NTFY_URL=os.getenv(
            "NTFY_URL",
            "https://ntfy.filipporadiceosteopata.com/Appuntamenti",
        ),
        NTFY_TOKEN=os.getenv("NTFY_TOKEN", ""),
        NTFY_TIMEOUT=float(os.getenv("NTFY_TIMEOUT", "5")),
    )
    if test_config:
        app.config.update(test_config)

    _configure_logging()
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    init_storage(app)
    _register_routes(app)
    _register_response_hooks(app)
    return app


def _configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _register_routes(app: Flask) -> None:
    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/privacy")
    def privacy_policy():
        return render_template(
            "privacy.html",
            contact_email=app.config["CONTACT_EMAIL"],
        )

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}, 200

    @app.post("/prenota")
    def book_visit():
        try:
            submission = _validate_submission(request.form)
            save_appointment(submission)
        except ValidationError as exc:
            current_app.logger.info("Rejected appointment request: %s", exc)
            return _message_page(
                title="Richiesta non valida",
                message=str(exc),
                status_code=400,
            )
        except Exception:
            current_app.logger.exception("Failed to save appointment")
            return _message_page(
                title="Errore interno",
                message="Errore interno. Riprovare tra poco o contattare via WhatsApp.",
                status_code=500,
            )

        try:
            send_appointment_notification(submission)
        except Exception:
            current_app.logger.warning(
                "Appointment saved but ntfy notification failed",
                exc_info=True,
            )

        current_app.logger.info("Appointment request saved for %s", submission.patient_name)
        return _message_page(
            title="Richiesta ricevuta",
            message="Richiesta ricevuta, verrete contattati al piu' presto.",
            status_code=200,
        )

    @app.errorhandler(413)
    def request_too_large(_error):
        return _message_page(
            title="Richiesta troppo grande",
            message="Dati inviati troppo grandi. Ridurre testo e riprovare.",
            status_code=413,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return _message_page(
            title="Pagina non trovata",
            message="Pagina richiesta non esiste.",
            status_code=404,
        )

    @app.errorhandler(500)
    def internal_error(_error):
        return _message_page(
            title="Errore interno",
            message="Errore interno. Riprovare tra poco.",
            status_code=500,
        )


def _register_response_hooks(app: Flask) -> None:
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("Content-Security-Policy", _content_security_policy())
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


def _content_security_policy() -> str:
    return "; ".join(
        (
            "default-src 'self'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "img-src 'self' data:",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "font-src 'self' data:",
            "connect-src 'self'",
        )
    )


def _message_page(title: str, message: str, status_code: int) -> tuple[str, int]:
    return (
        render_template(
            "message.html",
            page_title=title,
            message=message,
            home_url=url_for("home"),
        ),
        status_code,
    )


def _validate_submission(form_data) -> AppointmentSubmission:
    if _clean_text(form_data.get("website"), max_length=255):
        raise ValidationError("Richiesta non valida.")

    visit_type = _clean_text(form_data.get("visitType"), max_length=40, required=True)
    if visit_type not in ALLOWED_VISIT_TYPES:
        raise ValidationError("Tipo di visita non valido.")

    patient_name = _clean_text(form_data.get("patientName"), max_length=120, required=True)
    patient_phone = _clean_text(form_data.get("patientPhone"), max_length=32, required=True)
    patient_email = _clean_text(form_data.get("patientEmail"), max_length=254)
    patient_notes = _clean_text(form_data.get("patientNotes"), max_length=2000)

    if not PHONE_RE.fullmatch(patient_phone):
        raise ValidationError("Numero di telefono non valido.")

    digits_only = "".join(char for char in patient_phone if char.isdigit())
    if len(digits_only) < 8 or len(digits_only) > 15:
        raise ValidationError("Numero di telefono non valido.")

    if patient_email and not EMAIL_RE.fullmatch(patient_email):
        raise ValidationError("Email non valida.")

    return AppointmentSubmission(
        patient_name=patient_name,
        visit_type=visit_type,
        patient_email=patient_email,
        patient_phone=patient_phone,
        patient_notes=patient_notes,
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )


def _clean_text(value: str | None, *, max_length: int, required: bool = False) -> str:
    cleaned = (value or "").strip()
    if required and not cleaned:
        raise ValidationError("Compilare tutti i campi obbligatori.")
    if len(cleaned) > max_length:
        raise ValidationError("Uno o piu' campi superano lunghezza consentita.")
    if any(ord(char) < 32 and char not in "\r\n\t" for char in cleaned):
        raise ValidationError("Sono presenti caratteri non validi.")
    return cleaned
