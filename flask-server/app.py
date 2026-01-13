from flask import Flask, render_template, request
import json
import pathlib
import os
import minidb
from datetime import datetime

class Appointment(minidb.Model):
    date_received = str
    patient_name = str
    visit_type = str
    patient_email = str
    patient_phone = str
    patient_notes = str
    
DATA_DIR = './data'
BOOKING_FILE = f'{DATA_DIR}/db.json' # may God have mercy on my soul
db = minidb.Store('appointments.sqlite', debug=True)
db.register(Appointment)
required_form_data = ["name", "visitType", "patientPhone"]
if not os.path.isdir(DATA_DIR):
    os.mkdir(DATA_DIR)

app = Flask(
    __name__,
    # static_folder='site_files',
    # static_url_path='/site_files'
)


@app.route("/")
def home():
    return render_template("index.html")


# @app.route("/errore")
def result_page(msg: str = "Errore interno."):
    return render_template("error.html", err_msg=msg)


def appointify(form_data):
    return Appointment(
        patient_name = form_data.get("patientName"),
        visit_type = form_data.get("visitType"),
        patient_email = form_data.get("patientEmail"),
        patient_phone = form_data.get("patientPhone"),
        patient_notes = form_data.get("patientNotes"),
        date_received = str(datetime.now())
    )

def log_critical():
    pass

def register_appointment(booking_data: dict):
    appointment = appointify(booking_data)
    appointment.save(db)
    db.commit()
    
    
    
@app.route("/prenota", methods=["POST"])
def prenota():
    def check_too_long(obj: dict):
        return any(len(value) > 1024 for _, value in obj.items())

    def check_phone_valid(phone: str):
        """Check if phone number is valid (no invalid characters and valid length)"""
        return 10 <= len(phone) <= 15
        return all(char in "0123456789+ " for char in phone)

    def extract_data(form_data):
        return {
            "patientName": form_data.get("patientName"),
            "visitType": form_data.get("visitType"),
            "email": form_data.get("patientEmail"),
            "patientPhone": form_data.get("patientPhone"),
            "patientNotes": form_data.get("patientNotes"),
        }


    def check_data(form_data):
        for k, v in form_data.items():
            if k in required_form_data and not v:
                return f"Alcuno dati obbligatori non sono stati inseriti ({k})"
            if len(v) > 1024:
                return "Avete inserito troppi caratteri."
        if not check_phone_valid(form_data.get("patientPhone")):
            return "Il numero di telefono inserito non e' valido."
        return "OK"

    form_data = extract_data(request.form)
    if (_res := check_data(form_data)) != "OK":
        return result_page(_res)
    register_appointment(form_data)
    for app in Appointment.load(db):
        print(app)
    return result_page(
        "Richiesta ricevuta, verrete contattati al piu' presto."
    )
