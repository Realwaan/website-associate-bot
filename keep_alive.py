from flask import Flask
from threading import Thread
import logging
import os
from wsgiref.simple_server import make_server

# Suppress Flask default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run(host: str = "0.0.0.0", port: int = 8080):
    """Run a tiny WSGI server for health checks without Flask dev-server noise."""
    try:
        with make_server(host, port, app) as server:
            logger.info("Keep-alive server started on %s:%s", host, port)
            server.serve_forever()
    except OSError as e:
        logger.warning("Keep-alive server not started on %s:%s (%s)", host, port, e)

def keep_alive():
    """Starts the Flask server in a separate thread."""
    host = os.getenv("KEEP_ALIVE_HOST", "0.0.0.0")
    port = int(os.getenv("KEEP_ALIVE_PORT", "8080"))
    t = Thread(target=run, args=(host, port), daemon=True)
    t.start()
