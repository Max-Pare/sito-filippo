from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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

    def test_valid_booking_is_saved(self) -> None:
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

        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT patient_name, visit_type, patient_email, patient_phone
                FROM appointments
                """
            ).fetchone()

        self.assertEqual(row, ("Mario Rossi", "prima-visita", "mario@example.com", "+39 345 850 8870"))

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


if __name__ == "__main__":
    unittest.main()
