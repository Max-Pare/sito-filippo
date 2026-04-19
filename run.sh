#!/bin/bash
cd ~/sito-filippo/
source .venv/bin/activate
cd flask-server
python app.py >> ~/osteo.log
