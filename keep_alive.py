from flask import Flask
from threading import Thread
import logging

# Suppress Flask default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Starts the Flask server in a separate thread."""
    t = Thread(target=run)
    t.start()
