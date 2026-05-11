from flask import Flask, request, jsonify
from threading import Thread
import logging
import os
from wsgiref.simple_server import make_server
from typing import Callable

# Suppress Flask default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask('')
_github_webhook_handler: Callable[[bytes, dict], tuple[int, str]] | None = None

@app.route('/', methods=['GET', 'POST', 'HEAD', 'OPTIONS'], strict_slashes=False)
def home():
    # If GitHub is (mis)configured to post to the root URL, accept and forward it.
    if request.method == 'POST':
        gh_event = request.headers.get('X-GitHub-Event') or request.headers.get('X-Github-Event')
        gh_delivery = request.headers.get('X-GitHub-Delivery') or request.headers.get('X-Github-Delivery')
        if gh_event and gh_delivery:
            if _github_webhook_handler is None:
                return jsonify({"ok": False, "message": "Webhook handler is not configured"}), 503
            raw_body = request.get_data(cache=False, as_text=False)
            headers = {k: v for k, v in request.headers.items()}
            status_code, message = _github_webhook_handler(raw_body, headers)
            return jsonify({"ok": status_code < 400, "message": message}), status_code

        return jsonify({
            "ok": True,
            "message": "Service is alive. For GitHub webhooks use /webhook/github",
        }), 202

    if request.method == 'OPTIONS':
        return jsonify({"ok": True, "message": "ok"}), 200

    return "Bot is alive!"


@app.route('/health', methods=['GET', 'HEAD'], strict_slashes=False)
def health():
    return "ok", 200


@app.route('/webhook/github', methods=['GET', 'POST', 'HEAD', 'OPTIONS'], strict_slashes=False)
@app.route('/webhook/github/', methods=['GET', 'POST', 'HEAD', 'OPTIONS'], strict_slashes=False)
def github_webhook():
    """Receive GitHub webhook events and hand off to bot-level handler."""
    if request.method in {'GET', 'HEAD'}:
        return jsonify({"ok": True, "message": "GitHub webhook endpoint is ready. Send POST events."}), 200
    if request.method == 'OPTIONS':
        return jsonify({"ok": True, "message": "ok"}), 200

    if _github_webhook_handler is None:
        return jsonify({"ok": False, "message": "Webhook handler is not configured"}), 503

    raw_body = request.get_data(cache=False, as_text=False)
    headers = {k: v for k, v in request.headers.items()}
    status_code, message = _github_webhook_handler(raw_body, headers)
    return jsonify({"ok": status_code < 400, "message": message}), status_code


def set_github_webhook_handler(handler: Callable[[bytes, dict], tuple[int, str]]) -> None:
    """Set callback used by /webhook/github endpoint."""
    global _github_webhook_handler
    _github_webhook_handler = handler

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
    # Render sets PORT dynamically for web services.
    port = int(os.getenv("PORT") or os.getenv("KEEP_ALIVE_PORT", "8080"))
    t = Thread(target=run, args=(host, port), daemon=True)
    t.start()
