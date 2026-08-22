from flask import Flask, request, jsonify
from threading import Thread
import logging
import os
import hmac
import time
from collections import defaultdict, deque
from wsgiref.simple_server import make_server
from typing import Callable

# Suppress Flask default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask('')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB payload limit

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
    return response

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"ok": False, "message": "Payload too large. Maximum size is 10MB."}), 413

@app.errorhandler(500)
def internal_server_error(error):
    logger.error("Internal server error: %s", error)
    return jsonify({"ok": False, "message": "An internal server error occurred."}), 500

_github_webhook_handler: Callable[[bytes, dict], tuple[int, str]] | None = None
_capstone_ticket_handler: Callable[[dict], tuple[int, dict]] | None = None
_capstone_ready_checker: Callable[[], bool] | None = None
_capstone_request_times: dict[str, deque[float]] = defaultdict(deque)
CAPSTONE_RATE_LIMIT = int(os.getenv('CAPSTONE_API_RATE_LIMIT', '30'))
CAPSTONE_RATE_WINDOW_SECONDS = 60

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


@app.route('/ready', methods=['GET', 'HEAD'], strict_slashes=False)
def ready():
    """Report whether the Discord client is connected and ready."""
    is_ready = _capstone_ready_checker() if _capstone_ready_checker else False
    if not is_ready:
        return jsonify({"ok": False, "ready": False, "message": "Discord bot is not ready"}), 503
    return jsonify({"ok": True, "ready": True}), 200


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


@app.route('/api/capstone/tickets', methods=['POST'])
def capstone_ticket():
    """Create a ticket thread for CapStoneFlow using the bot's Discord session."""
    configured_secret = os.getenv('CAPSTONE_API_SECRET', '')
    supplied_secret = request.headers.get('X-Capstone-API-Key', '')
    if not configured_secret or not hmac.compare_digest(supplied_secret, configured_secret):
        return jsonify({"ok": False, "message": "Unauthorized"}), 401

    now = time.monotonic()
    request_times = _capstone_request_times[request.remote_addr or 'unknown']
    while request_times and now - request_times[0] >= CAPSTONE_RATE_WINDOW_SECONDS:
        request_times.popleft()
    if len(request_times) >= CAPSTONE_RATE_LIMIT:
        return jsonify({"ok": False, "message": "Too many requests"}), 429, {
            'Retry-After': str(CAPSTONE_RATE_WINDOW_SECONDS)
        }
    request_times.append(now)

    if _capstone_ticket_handler is None:
        return jsonify({"ok": False, "message": "Ticket handler is not configured"}), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "message": "A JSON object is required"}), 400

    try:
        status_code, result = _capstone_ticket_handler(payload)
        return jsonify(result), status_code
    except Exception as exc:
        logger.exception("CapStoneFlow ticket request failed")
        return jsonify({"ok": False, "message": "Ticket request failed"}), 500


def set_github_webhook_handler(handler: Callable[[bytes, dict], tuple[int, str]]) -> None:
    """Set callback used by /webhook/github endpoint."""
    global _github_webhook_handler
    _github_webhook_handler = handler


def set_capstone_ticket_handler(handler: Callable[[dict], tuple[int, dict]]) -> None:
    """Set the callback used by the CapStoneFlow ticket API."""
    global _capstone_ticket_handler
    _capstone_ticket_handler = handler


def set_capstone_ready_checker(checker: Callable[[], bool]) -> None:
    """Set the readiness callback used by /ready."""
    global _capstone_ready_checker
    _capstone_ready_checker = checker

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
