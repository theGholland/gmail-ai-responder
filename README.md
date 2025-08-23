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
