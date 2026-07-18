from __future__ import annotations

import re
import sqlite3
import sys
import tempfile
import unittest
from base64 import b64encode
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import website
from website import notifications
from website import create_app


class AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database_path = Path(self.temp_dir.name) / "appointments.sqlite"
        app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": str(self.database_path),
                "SQLITE_JOURNAL_MODE": "DELETE",
                "APPOINTMENTS_ADMIN_USERNAME": "admin",
                "APPOINTMENTS_ADMIN_PASSWORD": "secret",
            }
        )
        self.client = app.test_client()

    def tearDown(self) -> None:
        self.client = None
        self.temp_dir.cleanup()

    def test_home_page_loads(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Prenota la Tua Visita", response.data)
        self.assertIn(b'id="contatti"', response.data)
        self.assertIn(b'navbar-toggler', response.data)
        self.assertIn(b"/assets/", response.data)

    def test_rendered_static_assets_are_versioned_and_cacheable(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        asset_urls = set(re.findall(rb'["\'](/assets/[^"\']+)["\']', response.data))
        self.assertGreater(len(asset_urls), 0)

        for asset_url in asset_urls:
            asset_response = self.client.get(asset_url.decode("utf-8"))
            try:
                self.assertEqual(asset_response.status_code, 200, asset_url)
                self.assertEqual(
                    asset_response.headers["Cache-Control"],
                    "public, max-age=31536000, immutable",
                )
                self.assertEqual(
                    asset_response.headers["CDN-Cache-Control"],
                    "public, max-age=31536000, immutable",
                )
            finally:
                asset_response.close()

    def test_font_css_is_self_hosted(self) -> None:
        font_css = Path(__file__).resolve().parents[1] / "static" / "site-assets" / "google-fonts.css"
        css_text = font_css.read_text(encoding="utf-8")

        self.assertNotIn("https://fonts.gstatic.com", css_text)
        self.assertIn("../webfonts/inter-latin.woff2", css_text)
        self.assertIn("../webfonts/playfair-display-latin.woff2", css_text)

    def test_robots_txt_is_served(self) -> None:
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"].split(";")[0], "text/plain")
        self.assertIn(b"User-agent: *", response.data)

    def test_valid_booking_is_saved(self) -> None:
        with mock.patch.object(website, "send_appointment_notification") as notify_mock:
            response = self.client.post(
                "/prenota",
                data={
                    "visitType": "prima-visita",
                    "patientName": "Mario Rossi",
                    "patientPhone": "+39 345 850 8870",
                    "patientEmail": "mario@example.com",
                    "patientNotes": "Dolore cervicale da due settimane.",
                    "website": "",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Richiesta ricevuta", response.data)
        notify_mock.assert_called_once()

        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT patient_name, visit_type, patient_email, patient_phone
                FROM appointments
                """
            ).fetchone()

        self.assertEqual(row, ("Mario Rossi", "prima-visita", "mario@example.com", "+39 345 850 8870"))

    def test_notification_failure_does_not_break_booking(self) -> None:
        with mock.patch.object(
            website,
            "send_appointment_notification",
            side_effect=RuntimeError("ntfy offline"),
        ) as notify_mock:
            response = self.client.post(
                "/prenota",
                data={
                    "visitType": "prima-visita",
                    "patientName": "Mario Rossi",
                    "patientPhone": "+39 345 850 8870",
                    "patientEmail": "mario@example.com",
                    "patientNotes": "",
                    "website": "",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Richiesta ricevuta", response.data)
        notify_mock.assert_called_once()

    def test_ntfy_auth_header_accepts_prefixed_and_raw_tokens(self) -> None:
        self.assertEqual(
            notifications._build_auth_header("tk_exampletoken"),
            "Bearer tk_exampletoken",
        )
        self.assertEqual(
            notifications._build_auth_header("Bearer tk_exampletoken"),
            "Bearer tk_exampletoken",
        )
        self.assertEqual(
            notifications._build_auth_header("Basic dGVzdA=="),
            "Basic dGVzdA==",
        )

    def test_invalid_phone_is_rejected(self) -> None:
        response = self.client.post(
            "/prenota",
            data={
                "visitType": "prima-visita",
                "patientName": "Mario Rossi",
                "patientPhone": "abc",
                "patientEmail": "",
                "patientNotes": "",
                "website": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Numero di telefono non valido", response.data)

    def test_admin_appointments_requires_basic_auth(self) -> None:
        response = self.client.get("/admin/appuntamenti")

        self.assertEqual(response.status_code, 401)
        self.assertIn("Basic", response.headers["WWW-Authenticate"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_admin_appointments_rejects_bad_basic_auth(self) -> None:
        response = self.client.get(
            "/admin/appuntamenti",
            headers={"Authorization": self._basic_auth_header("admin", "wrong")},
        )

        self.assertEqual(response.status_code, 401)

    def test_admin_appointments_lists_saved_bookings(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.executemany(
                """
                INSERT INTO appointments (
                    created_at,
                    patient_name,
                    visit_type,
                    patient_email,
                    patient_phone,
                    patient_notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        "2026-05-19T09:00:00+02:00",
                        "Mario Rossi",
                        "prima-visita",
                        "mario@example.com",
                        "+39 345 850 8870",
                        "Dolore cervicale.",
                    ),
                    (
                        "2026-05-20T10:30:00+02:00",
                        "Luisa Bianchi",
                        "controllo",
                        "",
                        "+39 340 123 4567",
                        "",
                    ),
                ),
            )

        response = self.client.get(
            "/admin/appuntamenti",
            headers={"Authorization": self._basic_auth_header("admin", "secret")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn(b"Appuntamenti", response.data)
        self.assertIn(b"2 richieste salvate", response.data)
        self.assertIn(b"Luisa Bianchi", response.data)
        self.assertIn(b"Mario Rossi", response.data)
        self.assertLess(response.data.index(b"Luisa Bianchi"), response.data.index(b"Mario Rossi"))

    @staticmethod
    def _basic_auth_header(username: str, password: str) -> str:
        token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"


if __name__ == "__main__":
    unittest.main()
