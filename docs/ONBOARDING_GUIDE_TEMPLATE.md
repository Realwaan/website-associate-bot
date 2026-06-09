# Developer Onboarding Guide Template

This document provides a template for getting new developers setup with local environment configuration, dependencies, and execution targets for the **Website Associate Bot**.

---

## 🛠️ Prerequisites & Local System Tools

To support the bot's features (such as PDF brief scanning and LaTeX math rendering), the following system runtimes must be installed and added to your system `PATH`:

### 1. LaTeX Compiler (For Math Rendering)
Required to compile `.tex` equations to PDF assets.
*   **Windows:** Install MiKTeX via Scoop `scoop install miktex` or Chocolaty `choco install miktex`.
*   **macOS:** Install MacTeX via Homebrew `brew install mactex`.
*   **Linux:** Install via Apt `sudo apt-get install texlive-latex-base texlive-latex-extra`.

### 2. ImageMagick / pdftoppm (For Image Conversion)
Required to convert PDF pages and LaTeX-compiled PDF equations to PNG images.
*   **ImageMagick Installation:**
    *   **Windows:** `choco install imagemagick`
    *   **macOS:** `brew install imagemagick`
    *   **Linux:** `sudo apt-get install imagemagick`
*   **Poppler Utilities (pdftoppm):** Recommended for faster page-by-page PDF scanning conversions.

### 3. Tesseract OCR (Optional, for PDF Scanning)
Used as an OCR fallback when reading scanned/image-only PDFs.
*   Make sure to configure the `TESSERACT_CMD` environment variable pointing to your tesseract binary if it is not in the system's default PATH.

---

## 🐍 Python Environment Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd website-associate-bot
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## ⚙️ Environment Variables Config (`.env`)

Create a `.env` file at the project root based on `.env.example`:

```bash
# Discord Credentials
DISCORD_TOKEN=your_bot_token_here

# Database URL (Supabase/PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# GitHub Integration
GITHUB_TOKEN=your_personal_access_token_here
```

---

## 🚀 Running the Bot Locally

1.  **Run Database Migrations:**
    Database tables and initial migrations are run automatically on startup via `init_db()`. Alternatively, run migrations standalone:
    ```bash
    python scripts/migrate_db.py
    ```

2.  **Start the Bot:**
    ```bash
    python main.py
    ```

3.  **Invite Bot to Discord Server:**
    Generate an invite link in the Discord Developer Portal with:
    *   **Scopes:** `bot`, `applications.commands`
    *   **Permissions:** Manage Channels, Manage Threads, Send Messages, Embed Links, Manage Roles.
