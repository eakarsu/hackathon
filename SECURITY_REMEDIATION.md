# Security remediation status

This prototype now uses normal TLS certificate verification for Python HTTP clients. If an internal certificate authority is required, configure `AI_CA_BUNDLE`, `REQUESTS_CA_BUNDLE`, or `SSL_CERT_FILE`; do not disable verification.

Credential literals were removed from the tracked launch scripts and backend defaults. Configure them through an untracked `.env` copied from `.env.example`. Because earlier values remain in Git history, the credential owner must revoke or rotate them and decide whether repository history must be rewritten.

The backend is local-only by default, uses an explicit CORS allowlist, constrains request-supplied data paths to `DATA_ROOT`, limits request sizes, and disables the destructive HTTP database reset and simulated task-execution endpoint. The launcher no longer kills unrelated processes.

Production use still needs an owner-approved authentication and authorization model, durable storage and migrations, audit and retention rules, dependency review, secret management, and deployment-specific TLS/CORS configuration. The current code is a prototype, not an autonomous task executor.
