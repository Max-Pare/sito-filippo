from flask import Flask, render_template, request

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
    data_obj = {
        'name'         : data['patientName'],
        'visitType'    : data['visitType'],
        'email'        : data['patientEmail'],
        'patientPhone' : data['patientPhone'],
        'patientNotes' : data['patientNotes']
        
    }
    print(data_obj)
    return data_obj


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='38104', debug=True)
