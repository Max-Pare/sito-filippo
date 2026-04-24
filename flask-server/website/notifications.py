from __future__ import annotations

import base64
from urllib import request
from urllib.error import HTTPError, URLError

from flask import current_app


def send_appointment_notification(submission) -> None:
    ntfy_url = current_app.config.get("NTFY_URL", "").strip()
    if not ntfy_url:
        return

    payload = _build_message(submission).encode("utf-8")
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Title": "Nuovo appuntamento",
        "Priority": "5",
        "User-Agent": "sito-filippo/1.0 (+https://filipporadiceosteopata.com)",
    }

    ntfy_token = current_app.config.get("NTFY_TOKEN", "").strip()
    if ntfy_token:
        headers["Authorization"] = _build_auth_header(ntfy_token)

    ntfy_request = request.Request(
        ntfy_url,
        data=payload,
        headers=headers,
        method="POST",
    )

    timeout = float(current_app.config.get("NTFY_TIMEOUT", 5))

    try:
        with request.urlopen(ntfy_request, timeout=timeout) as response:
            if response.status >= 400:
                raise RuntimeError(f"ntfy returned unexpected status {response.status}")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ntfy HTTP error {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"ntfy connection error: {exc.reason}") from exc


def _build_message(submission) -> str:
    lines = [
        "Nuova richiesta appuntamento",
        f"Nome: {submission.patient_name}",
        f"Tipo visita: {submission.visit_type}",
        f"Telefono: {submission.patient_phone}",
        f"Email: {submission.patient_email or 'non indicata'}",
        f"Note: {submission.patient_notes or 'nessuna'}",
        f"Ricevuta: {submission.created_at}",
    ]
    return "\n".join(lines)


def _build_auth_header(token_or_header: str) -> str:
    normalized = token_or_header.strip()
    lowered = normalized.lower()

    if lowered.startswith("bearer ") or lowered.startswith("basic "):
        return normalized

    if ":" in normalized:
        encoded = base64.b64encode(normalized.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"

    return f"Bearer {normalized}"
