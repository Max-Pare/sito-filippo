from flask import Flask, render_template, request
import os
import minidb
from datetime import datetime, tzinfo, timedelta

class TZ1(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=1)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self,dt):
        return "+01:00"

    def  __repr__(self):
        return f"{self.__class__.__name__}()"

class Appointment(minidb.Model):
    date_received = str
    patient_name = str
    visit_type = str
    patient_email = str
    patient_phone = str
    patient_notes = str

def app_to_str(_app: Appointment):
    return f'Tipo: {_app.visit_type}, Nome paziente: {_app.patient_name}, Tel.: {_app.patient_phone}, Email: {_app.patient_phone}, Note: {_app.patient_notes}, Data ricevuta: {_app.date_received}'
    
DATA_DIR = './data'
db = minidb.Store('appointments.sqlite', debug=True)
db.register(Appointment)
required_form_data = ["name", "visitType", "patientPhone"]
TIMEZONE = TZ1()
if not os.path.isdir(DATA_DIR):
    os.mkdir(DATA_DIR)

app = Flask(
    __name__,
    # static_folder='site_files',
    # static_url_path='/site_files'
)

def clean_html(string):
    newstr = string
    for char in '<>/':
        newstr = newstr.replace(char, ' ')
    return newstr

@app.route("/debug")
def get_db():
    entry_list = []
    entry_list = [f'<h4><li class="hero-title mb-4">{clean_html(app_to_str(_app))}</li></h4>' for _app in Appointment.load(db)]
    entry_list.insert(0,'<ol>')
    entry_list.append('</ol>')
    elem = '\n'.join(entry_list)
    return elem

@app.route("/")
def home():
    return render_template("index.html")


# @app.route("/errore")
def result_page(msg: str = "Errore interno."):
    return render_template("error.html", err_msg=msg)


def appointify(form_data):
    try: 
        return Appointment(
            patient_name = form_data.get("patientName"),
            visit_type = form_data.get("visitType"),
            patient_email = form_data.get("patientEmail"),
            patient_phone = form_data.get("patientPhone"),
            patient_notes = form_data.get("patientNotes"),
            date_received = str(datetime.now(tz=TIMEZONE).strftime(r'%m-%d-%y %H:%M:%S'))
        )
    except Exception as e:
        raise(e)
        log(f'Error while creating appointment: {str(e)}', 'CRITICAL')
        return 'ERR'
        

def log(message, logtype:str = 'INFO'):
    msg = f'({datetime.now()})[{logtype}] {message}\n'
    print(msg)
    if not os.path.exists(f'{DATA_DIR}/error.log'):
        open(f'{DATA_DIR}/error.log', 'w').close()
    with open(f'{DATA_DIR}/error.log', 'a') as file:
        file.write(msg)


def register_appointment(booking_data: dict):
    appointment = appointify(booking_data)
    if appointment == 'ERR': return 'ERR'
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
                log(f'User omitted required data ({k})', 'WARN')
                return f"Alcuno dati obbligatori non sono stati inseriti ({k})"
            if len(v) > 1024:
                log(f'User inserted too many characters ({len(v)})', 'WARN')
                return "Avete inserito troppi caratteri."
        if not check_phone_valid(form_data.get("patientPhone")):
            log(f'User inserted invalid phone number ({form_data.get("patientPhone")})', 'WARN')
            return "Il numero di telefono inserito non e' valido."
        return "OK"

    form_data = extract_data(request.form)
    if (_res := check_data(form_data)) != "OK":
        return result_page(_res)
    if register_appointment(form_data) == 'ERR': return result_page()
    for app in Appointment.load(db):
        print(app)
    log('Registered appointment.')
    return result_page(
        "Richiesta ricevuta, verrete contattati al piu' presto."
    )
