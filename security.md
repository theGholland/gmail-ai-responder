# SECURITY.md

## Supported versions

The repository is provided as‑is under MIT. Security posture assumes **localhost‑only** usage by default.

## Reporting a vulnerability

Please open a private disclosure by emailing `<your-security-contact@example.com>` with a minimal, reproducible description. Do not include real email content or credentials in reports.

## Hardening guidance

* Keep all servers bound to `127.0.0.1`; if multi‑user access is required, place the app behind a reverse proxy that enforces TLS and authentication or keep it on a VPN.
* Use read‑only mail scopes until you intentionally add draft creation.
* Never commit secrets. Ensure `.env`, tokens, and OAuth client secrets remain untracked.
