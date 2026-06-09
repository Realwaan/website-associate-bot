# API Documentation Template

This document provides a template for documenting the Slash Commands and Webhook Endpoints exposed by the **Website Associate Bot**.

---

## 🧭 Slash Commands Reference

### `/command-name`
*   **Description:** Short 1-sentence summary of what this command does.
*   **Required Roles:** `Developer` | `QA` | `Project Manager` | `Server Admin` | `Anyone`
*   **Channel Scope:** `Anywhere` | `Thread-only` | `Text-channel only`
*   **Parameters:**

| Parameter | Type | Required | Description | Default / Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `param_1` | `String` | Yes | Description of parameter 1. | e.g. Folder name |
| `param_2` | `Integer` | No | Description of parameter 2. | Min: 1, Max: 100 |

*   **Behavior and Execution Flow:**
    1. Steps bot takes to process the command.
    2. Side-effects (database writes, notifications sent).
    3. Error scenarios and fallback behavior.

*   **Example Response:**
    > 📝 **Embed Title**
    > Description of the response...
    > *   **Field 1:** Value
    > *   **Field 2:** Value

---

## 🌐 HTTP Webhook Endpoints

### `POST /webhook/github`
*   **Description:** Receives event payloads (such as `push` or `pull_request` events) from GitHub.
*   **Auth Mechanism:** `X-Hub-Signature-256` signature verification using configured `GITHUB_WEBHOOK_SECRET`.
*   **Request Headers:**

| Header Name | Required | Description / Value |
| :--- | :--- | :--- |
| `X-GitHub-Event` | Yes | The type of GitHub event (e.g. `push`). |
| `X-GitHub-Delivery` | Yes | Unique delivery UUID for idempotency check. |
| `X-Hub-Signature-256` | Yes | HMAC hex digest signature for payload validation. |

*   **Request Payload (JSON):**
    ```json
    {
      "ref": "refs/heads/main",
      "repository": {
        "name": "example-repo",
        "owner": {
          "login": "example-owner"
        }
      },
      "commits": [
        {
          "id": "commit-sha-here",
          "message": "Commit message title",
          "author": { "name": "Author Name" }
        }
      ]
    }
    ```

*   **Response Codes:**
    *   `202 Accepted`: Webhook accepted and queued for processing.
    *   `400 Bad Request`: Missing signature headers or malformed JSON.
    *   `401 Unauthorized`: Invalid webhook signature match.
    *   `503 Service Unavailable`: Bot loop not ready or webhook queue full.

---

## 🏥 Health Check Endpoints

### `GET /health`
*   **Description:** Simple health check endpoint used by Render or uptime checkers to verify server status.
*   **Auth Mechanism:** None (Public)
*   **Response Code:** `200 OK`
*   **Response Body:** `ok`
