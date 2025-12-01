from flask import Flask, render_template

app = Flask(
    __name__,
    static_folder='site_files',      # directory on disk
    static_url_path='/site_files'    # URL prefix
)

@app.route("/")
def home():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='38104', debug=True)
