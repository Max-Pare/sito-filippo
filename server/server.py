from flask import Flask, render_template, request

form_char_limit_default = 96
form_char_limit_notes = 1024

app = Flask(
    __name__,
    static_folder='site_files',
    static_url_path='/site_files'
)

@app.route("/")
def home():
    return render_template('index.html')

@app.route('/prenota', methods=['POST'])
def prenota():
    data = request.form
    
    def check_too_long(obj:dict):
        char_limit = form_char_limit_default
        for key, value in obj.items():
            if key is 'patientNotes':
                char_limit = form_char_limit_notes
            if len(value) > char_limit:
                return True
    
    data_obj = {
        'name'         : data['patientName'],
        'visitType'    : data['visitType'],
        'email'        : data['patientEmail'],
        'patientPhone' : data['patientPhone'],
        'patientNotes' : data['patientNotes']
    }
    del data
    if check_too_long(data_obj): return "Uno dei dati inseriti e' troppo lungo, perfavore usa meno caratteri."
    if len(data_obj.get(patientPhone)) > 13 or any(char not in '+1234567890' for char in data_obj.get(patientPhone)):
        return "Numero di telefono non valido."
    
    return f"<h1>Richiesta ricevuta, verrete contattati al piu' presto.</h1><div></div><p>{data_obj}</p>"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='38104', debug=True)
