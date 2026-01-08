from flask import Flask, render_template, request, abort
import mysql.connector

app = Flask(
    __name__,
    #static_folder='site_files',
    #static_url_path='/site_files'
)


@app.route("/")
def home():
    return render_template('index.html')

@app.route("/errore")
def error_page(msg:str="Errore interno."):
    return render_template('error.html', err_msg=msg)

required_form_data = ['name', 'visitType', 'patientPhone']

@app.route('/prenota', methods=['POST'])
def prenota():

    def check_too_long(obj:dict):
        return any(len(value) > 1024 for _, value in obj.items())

    def check_phone_valid(phone:str):
        '''Check if phone number is valid (no invalid characters and valid length)'''
        return all(char in '0123456789+ ' for char in phone) and 10 <= len(phone) <= 15
    
    def extract_data(form_data):
        # We do this to make sure that if a bad actor sends a larger object than
        # expected we can just pull out the necessary data and discard the rest
        return {
            'name'         : form_data.get('patientName'),
            'visitType'    : form_data.get('visitType'),
            'email'        : form_data.get('patientEmail'),
            'patientPhone' : form_data.get('patientPhone'),
            'patientNotes' : form_data.get('patientNotes')
        }
    cleaned_data = extract_data(request.form)
    print(cleaned_data)
    for k, v in cleaned_data.items():
        if k in required_form_data and not v:
            return error_page(f'Alcuno dati obbligatori non sono stati inseriti ({k})')
    if check_too_long(cleaned_data):
        return error_page('Errore: avete inserito troppi caratteri.')
    if not check_phone_valid(cleaned_data.get('patientPhone')): return error_page('Il numero di telefono inserito non e\' valido.')
    return f"<h1>Richiesta ricevuta, verrete contattati al piu' presto.</h1>"


# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port='38104', debug=True)
