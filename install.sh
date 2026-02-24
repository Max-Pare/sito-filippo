#!/bin/bash
sudo apt update -y && sudo apt install python3 -y
python3 -m venv .venv
source .venv/bin/activate
.vev/bin/python3 -m pip install -r ./flask-server/requirements.txt
