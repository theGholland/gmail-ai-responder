```text
repo/
├─ README.md
├─ LICENSE
├─ .gitignore
├─ requirements.txt
├─ .env.example
├─ Dockerfile
└─ .github/
   └─ workflows/
      └─ ci.yml
├─ CONTRIBUTING.md
└─ SECURITY.md
```

---

# README.md

# Local LLM Email Tone Coach (Starter)

This repository scaffolds a strictly local workflow: fetch an email thread from your provider (Gmail/Outlook/IMAP), pass the thread and your draft to a locally hosted LLM (Ollama or vLLM), receive a tonal critique plus two rewrites, and optionally create a **native draft** in your mailbox so you can send from your usual client.

## Quickstart (single‑user, localhost)

1. **Install a local model server.** E.g., with Ollama:

   ```bash
   ollama pull llama3.1
   ollama serve   # or run in the background
   ```

   The default OpenAI‑style endpoint is `http://127.0.0.1:11434/v1`.

2. **Create and activate a Python environment.**

   ```bash
   python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment.** Copy `.env.example` ➜ `.env` and set values. At minimum:

   * `LLM_BASE_URL` (e.g., `http://127.0.0.1:11434/v1`)
   * `LLM_MODEL` (e.g., `llama3.1` or `qwen2.5:14b-instruct`)

4. **Gmail or Microsoft Graph auth (optional at first).**

   * For Gmail, place your `credentials.json` (OAuth client) next to your runner script; first run will open a browser to consent. Use scope `gmail.readonly` until you enable draft creation.
   * For Outlook/Microsoft 365, register an app in Azure AD and set `AZURE_APP_CLIENT_ID` (device‑code flow is simplest during development).

5. **Run your app.** The starter assumes a Flask app binding to `127.0.0.1:7860`. Visit that URL to fetch a thread, paste a draft, and call the local LLM.

## Security model

* Keep the LLM server and the Flask app bound to **loopback only** (`127.0.0.1`).
* Begin with **read‑only** mail scopes; add draft‑creation scopes after you trust the flow.
* Never commit secrets: `.env`, OAuth tokens, and `credentials.json` are already ignored by `.gitignore`.

## Extending

* Add a minimal browser extension that passes the current thread/conversation ID to `http://127.0.0.1:7860/open?conv=<ID>`.
* Add a second provider module using Microsoft Graph; the interface is parallel to Gmail: fetch conversation by `conversationId`, then create a draft reply.

## License

MIT — see `LICENSE`.

---

# LICENSE

MIT License

Copyright (c) 2025 Galen Holland

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

# .gitignore

# Python

**pycache**/
\*.py\[cod]
\*.pyo
\*.pyd
*.so
.build/
.venv/
.env
.env.*
\*.env

# VS Code & PyCharm

.vscode/
.idea/

# OS junk

.DS\_Store
Thumbs.db

# Credentials & tokens

credentials.json
token.json
\*.pickle
\*.db

# Logs & cache

\*.log
\*.sqlite3
.cache/

# Node (if you add a tiny extension or UI build)

node\_modules/

# Docker

\*.tar

---

# requirements.txt

# App

flask>=3.0
python-dotenv>=1.0
openai>=1.40

# Gmail

google-api-python-client>=2.130
google-auth-httplib2>=0.2
google-auth-oauthlib>=1.2

# Microsoft Graph

msal>=1.28
requests>=2.32

# IMAP (generic + Proton Bridge)

imapclient>=3.0
beautifulsoup4>=4.12

# Dev tools (optional but useful)

black>=24.3
flake8>=7.0

---

# .env.example

# Flask app

FLASK\_HOST=127.0.0.1
FLASK\_PORT=7860

# Local LLM endpoint

LLM\_BASE\_URL=[http://127.0.0.1:11434/v1](http://127.0.0.1:11434/v1)
LLM\_MODEL=llama3.1

# Gmail OAuth scopes: start read‑only; upgrade to modify for drafts

GOOGLE\_SCOPES=[https://www.googleapis.com/auth/gmail.readonly](https://www.googleapis.com/auth/gmail.readonly)

# Microsoft Graph

AZURE\_TENANT=common
AZURE\_APP\_CLIENT\_ID=
MS\_GRAPH\_SCOPES=Mail.Read

# IMAP (optional; e.g., Proton Mail Bridge on localhost)

IMAP\_HOST=127.0.0.1
IMAP\_PORT=1143
IMAP\_USER=
IMAP\_PASS=

---

# Dockerfile

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1&#x20;
PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends&#x20;
ca-certificates && rm -rf /var/lib/apt/lists/\*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD \["python", "app.py"]

---

# .github/workflows/ci.yml

name: ci
on:
push:
branches: \[ main, master ]
pull\_request:
branches: \[ main, master ]

jobs:
lint:
runs-on: ubuntu-latest
steps:
\- uses: actions/checkout\@v4
\- uses: actions/setup-python\@v5
with:
python-version: '3.11'
\- name: Install deps
run: |
python -m pip install --upgrade pip
pip install -r requirements.txt
\- name: Black (check)
run: black --check .
\- name: Flake8
run: flake8 .

---

# CONTRIBUTING.md

Thank you for considering a contribution. This project’s value comes from clear, auditable local behavior and minimal dependencies.

## Development setup

1. Create a virtual environment and install dependencies with `pip install -r requirements.txt`.
2. Run a local LLM server (Ollama or vLLM) bound to `127.0.0.1`.
3. Copy `.env.example` to `.env` and set `LLM_BASE_URL` and `LLM_MODEL`.
4. Launch the Flask app (e.g., `python app.py`) and visit `http://127.0.0.1:7860`.

## Style

* Format with `black` and keep imports minimal.
* Prefer pure functions for provider adapters (Gmail/Graph/IMAP) so behavior is easy to reason about.
* Avoid writing raw email bodies to disk; pass them in memory.

## Pull requests

* Keep each PR focused: one feature or fix.
* Include a short rationale describing the user journey (“what the user clicks, what happens”).
* If you change scopes or network exposure, explain the security impact in your PR description.

---

# SECURITY.md

## Supported versions

The repository is provided as‑is under MIT. Security posture assumes **localhost‑only** usage by default.

## Reporting a vulnerability

Please open a private disclosure by emailing `<your-security-contact@example.com>` with a minimal, reproducible description. Do not include real email content or credentials in reports.

## Hardening guidance

* Keep all servers bound to `127.0.0.1`; if multi‑user access is required, place the app behind a reverse proxy that enforces TLS and authentication or keep it on a VPN.
* Use read‑only mail scopes until you intentionally add draft creation.
* Never commit secrets. Ensure `.env`, tokens, and OAuth client secrets remain untracked.
