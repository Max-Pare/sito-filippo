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

@app.route('/prenota', methods=['POST'])
def prenota():

    def check_too_long(obj:dict):
        return len(value) > 1024

    def check_phone_valid(phone:str):
        '''Check if phone number is valid (no invalid characters and valid length)'''
        return all(char in '0123456789+ ' for char in phone) and 10 <= len(phone) <= 15
    
    def extract_data(form_data):
        # We do this to make sure that if a bad actor sends a larger object than
        # expected we can just pull out the necessary data and discard the rest
        return {
            'name'         : data.get('patientName'),
            'visitType'    : data.get('visitType'),
            'email'        : data.get('patientEmail'),
            'patientPhone' : data.get('patientPhone'),
            'patientNotes' : data.get('patientNotes')
            }
    return error_page('Errore !!!')
    try:
        data = request.form
    except ValueError as e:
        print('Received invalid/empty form data.')
        return error_page('I dati inseriti non sono validi, riprovare.')
    return extract_data(data)
    return f"<h1>Richiesta ricevuta, verrete contattati al piu' presto.</h1><div></div><p>{data_obj}</p>"


# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port='38104', debug=True)
