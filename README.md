# README.md

# Local LLM Email Tone Coach (Starter)

This repository scaffolds a strictly local workflow: fetch an email thread from your provider (Gmail/Outlook/IMAP), pass the thread and your draft to a locally hosted LLM (Ollama or vLLM), receive a tonal critique plus two rewrites, and optionally create a **native draft** in your mailbox so you can send from your usual client.

## How it works

* **Gmail integration.** `runner.py` authenticates with Google via OAuth, retrieves thread contents and can create reply drafts.
* **Model interaction.** The assembled prompt (thread, draft, and goal) is sent either to a locally hosted model via an OpenAI-compatible endpoint or to OpenAI's API, and the model's critique is returned.
* **Web interface.** A small vanilla JS front-end talks to Flask endpoints to fetch threads, submit drafts/goals, and stream coaching output.
* **Mad Libs reply.** A second button analyzes the thread for the sender's needs and generates a fill‑in‑the‑blank reply addressing them.
* **Formatting cleanup.** Basic HTML tags and excessive blank lines are stripped before sending text to the model.
* **Link scrubbing.** Any `http(s)` links in the thread are reduced to their bare domains before being sent to the model.
* **Security posture.** Designed for localhost-only deployment; start with read-only mail scopes and never commit secrets.

## Quickstart (single‑user, localhost)

1. **Install a local model server.** E.g., with Ollama:

   ```bash
   ollama pull llama3.1
   ollama serve   # or run in the background
   ```

   The default OpenAI‑style endpoint is `http://127.0.0.1:11434/v1`.

2. **Create and activate a Python environment.** Install the pinned dependencies to ensure consistent versions:

   ```bash
   python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   Using a virtual environment keeps these pinned packages isolated from your system Python.

3. **Configure environment.** Copy `.env.example` ➜ `.env` and set values. At minimum:

   * `LLM_URL` (e.g., `http://127.0.0.1:11434/v1`)
   * `MODEL` (e.g., `llama3.1` or `qwen2.5:14b-instruct`)
   * To call OpenAI's hosted models instead of a local server, set `USE_OPENAI=true` and provide `OPENAI_API_KEY` (optionally `OPENAI_MODEL`).

4. **Gmail or Microsoft Graph auth (optional at first).**

  * For Gmail, place your `credentials.json` (OAuth client) next to your runner script. On first run the script logs an authorization URL instead of opening a browser. Open that link in a browser, authorize the app, and Google will display a one‑time code:

    1. Visit the printed URL and sign in.
    2. Approve the requested scopes.
    3. Copy the authorization code shown by Google.
    4. Paste the code back into the terminal when prompted.

    Use scope `gmail.readonly` until you enable draft creation.
   * For Outlook/Microsoft 365, register an app in Azure AD and set `AZURE_APP_CLIENT_ID` (device‑code flow is simplest during development).

5. **Run your app.** The starter assumes a Flask app binding to `127.0.0.1:7860`. Visit that URL to load the web UI, fetch a thread, paste a draft, and call the local LLM.

### Creating Gmail `credentials.json`

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Enable the **Gmail API** from *APIs & Services → Library*.
3. Configure the **OAuth consent screen** (External user type is sufficient for personal/testing use) and add your Gmail address as a test user.
4. Go to *APIs & Services → Credentials*, click **+ Create Credentials → OAuth client ID**, and choose **Desktop app**.
5. Download the resulting JSON file and rename it to `credentials.json`.
6. Place `credentials.json` next to `runner.py`; the first run will output a URL. Visit it in a browser, approve access, and paste the resulting code into the console to store a token locally.

> The JSON file and generated tokens contain secrets—keep them out of version control.

#### OAuth consent testing restrictions

* An unverified app left in **Testing** mode only works for email addresses added as **test users**.
* To use the app outside that pool, add your own accounts as test users in the Google Cloud console or submit the app for verification.
* Otherwise Google will block authorization with `Error 403: access_denied`.
* The best way to do this is to visit Google Auth Platform / Audience and add yourself as a test user

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
