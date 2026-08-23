from flask import Flask, request, jsonify
from threading import Thread, Lock
import logging
import os
import hmac
import time
from collections import defaultdict, deque
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
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
_capstone_status_handler: Callable[[dict], tuple[int, dict]] | None = None
_capstone_ready_checker: Callable[[], bool] | None = None
_capstone_request_times: dict[str, deque[float]] = defaultdict(deque)
_rate_limit_lock = Lock()
CAPSTONE_RATE_LIMIT = int(os.getenv('CAPSTONE_API_RATE_LIMIT', '30'))
CAPSTONE_RATE_WINDOW_SECONDS = 60
# Render (and most PaaS load balancers) terminate TLS in front of the app, so
# request.remote_addr is the balancer's IP for every client.  Trust the
# X-Forwarded-For chain only when the direct peer is a private/balancer
# address; otherwise keep the peer IP so a spoofed header from the public
# internet cannot rotate the rate-limit identity.
_TRUST_PROXY_HEADERS = os.getenv('CAPSTONE_TRUST_PROXY_HEADERS', 'true').lower() == 'true'

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


def _capstone_request_metadata() -> dict:
    """Read bounded tracing metadata supplied by the server-side website bridge."""
    return {
        "idempotency_key": (request.headers.get("X-Idempotency-Key") or "").strip()[:200],
        "correlation_id": (request.headers.get("X-Correlation-ID") or "").strip()[:200],
    }


def _client_ip_for_rate_limit() -> str:
    """Resolve the caller identity used for rate limiting.

    Behind Render's load balancer, request.remote_addr is the balancer IP for
    every caller, which would collapse "per-IP" limiting into one shared global
    budget.  When the direct peer is a private address (i.e. a trusted proxy),
    use the leftmost X-Forwarded-For entry instead.  When the peer is public,
    ignore forwarded headers entirely so external clients cannot spoof their
    rate-limit identity.
    """
    peer = request.remote_addr or 'unknown'
    if not _TRUST_PROXY_HEADERS:
        return peer

    private_peer = peer.startswith(('10.', '192.168.', '127.')) or peer == '::1' or (
        peer.startswith('172.') and peer.split('.')[1].isdigit() and 16 <= int(peer.split('.')[1]) <= 31
    )
    if not private_peer:
        return peer

    forwarded = request.headers.get('X-Forwarded-For', '')
    first_hop = forwarded.split(',')[0].strip() if forwarded else ''
    return first_hop or peer


def _authorize_capstone_request() -> tuple[bool, int | None]:
    """Authenticate the website bridge and apply a small per-caller rate limit."""
    configured_secret = os.getenv('CAPSTONE_API_SECRET', '')
    supplied_secret = request.headers.get('X-Capstone-API-Key', '')
    if not configured_secret or not hmac.compare_digest(supplied_secret, configured_secret):
        return False, 401

    now = time.monotonic()
    client_ip = _client_ip_for_rate_limit()
    with _rate_limit_lock:
        # Evict identities idle for more than two windows so the table cannot
        # grow unboundedly under many distinct source addresses.
        if len(_capstone_request_times) > 256:
            stale = [
                ip for ip, times in _capstone_request_times.items()
                if not times or now - times[-1] >= CAPSTONE_RATE_WINDOW_SECONDS * 2
            ]
            for ip in stale:
                del _capstone_request_times[ip]

        request_times = _capstone_request_times[client_ip]
        while request_times and now - request_times[0] >= CAPSTONE_RATE_WINDOW_SECONDS:
            request_times.popleft()
        if len(request_times) >= CAPSTONE_RATE_LIMIT:
            return False, 429
        request_times.append(now)
    return True, None


def _run_capstone_handler(handler: Callable[[dict], tuple[int, dict]] | None):
    authorized, error_status = _authorize_capstone_request()
    if not authorized:
        if error_status == 429:
            return jsonify({"ok": False, "message": "Too many requests"}), 429, {
                'Retry-After': str(CAPSTONE_RATE_WINDOW_SECONDS)
            }
        return jsonify({"ok": False, "message": "Unauthorized"}), 401

    if handler is None:
        return jsonify({"ok": False, "message": "Ticket handler is not configured"}), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "message": "A JSON object is required"}), 400

    metadata = _capstone_request_metadata()
    payload["__integration"] = metadata
    if not metadata["idempotency_key"]:
        return jsonify({"ok": False, "message": "X-Idempotency-Key is required"}), 400
    if not metadata["correlation_id"]:
        return jsonify({"ok": False, "message": "X-Correlation-ID is required"}), 400

    try:
        status_code, result = handler(payload)
        return jsonify(result), status_code
    except RuntimeError:
        # Log full detail server-side; return a generic message to the caller
        # so dependency internals (pool sizes, DSN fragments) never leak.
        logger.exception("CapStoneFlow integration dependency failed")
        return jsonify({"ok": False, "message": "Database or Discord dependency unavailable"}), 503
    except Exception:
        logger.exception("CapStoneFlow integration request failed")
        return jsonify({"ok": False, "message": "Integration request failed"}), 500


@app.route('/api/capstone/tickets', methods=['POST'])
def capstone_ticket():
    """Create a ticket thread for CapStoneFlow using the bot's Discord session."""
    return _run_capstone_handler(_capstone_ticket_handler)


@app.route('/api/capstone/tickets/status', methods=['POST'])
def capstone_ticket_status():
    """Mirror a website state transition onto its Discord ticket thread."""
    return _run_capstone_handler(_capstone_status_handler)


def set_github_webhook_handler(handler: Callable[[bytes, dict], tuple[int, str]]) -> None:
    """Set callback used by /webhook/github endpoint."""
    global _github_webhook_handler
    _github_webhook_handler = handler


def set_capstone_ticket_handler(handler: Callable[[dict], tuple[int, dict]]) -> None:
    """Set the callback used by the CapStoneFlow ticket API."""
    global _capstone_ticket_handler
    _capstone_ticket_handler = handler


def set_capstone_status_handler(handler: Callable[[dict], tuple[int, dict]]) -> None:
    """Set the callback used by the CapStoneFlow ticket status API."""
    global _capstone_status_handler
    _capstone_status_handler = handler


def set_capstone_ready_checker(checker: Callable[[], bool]) -> None:
    """Set the readiness callback used by /ready."""
    global _capstone_ready_checker
    _capstone_ready_checker = checker

class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Handle each request on its own thread.

    The stock wsgiref server is single-threaded: one slow Discord round-trip
    (up to ~20s) would block /health and /ready, letting Render's health check
    fail and restart the container mid-processing.  All handler dependencies
    are thread-safe: the DB layer uses a ThreadedConnectionPool, cache.py is
    locked, and Discord work is dispatched via run_coroutine_threadsafe onto
    the bot's single event loop.
    """
    daemon_threads = True


class _QuietRequestHandler(WSGIRequestHandler):
    """Suppress per-request access logs; errors still surface via logging."""

    def log_message(self, format: str, *args) -> None:
        pass


def run(host: str = "0.0.0.0", port: int = 8080):
    """Run a threaded WSGI server for health checks and the bridge API."""
    try:
        with make_server(
            host,
            port,
            app,
            server_class=_ThreadingWSGIServer,
            handler_class=_QuietRequestHandler,
        ) as server:
            logger.info("Keep-alive server started on %s:%s (threaded)", host, port)
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
