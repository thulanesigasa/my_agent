# Deployment status

The application provides a local, single-host foundation. Follow [README.md](README.md) for native/Docker startup and [RUNBOOK.md](RUNBOOK.md) for backup and recovery.

Public deployment is a later operational task. Before hosting publicly, complete the operator authentication design, secure HTTPS/reverse-proxy access, Google app publishing/verification requirements, credential storage for the deployment environment, spending limits and operator recovery procedures. Phase 2 provides local authorisation, contact eligibility, native OIDC validation and provider reconciliation controls. A production environment flag or a successful `/health` response is not evidence that these are complete.

Persist the entire shared data directory. API and worker must use the same local filesystem volume and only one scheduler owner. The local workflow store does not support multiple application hosts sharing SQLite over a network filesystem.

Existing GitHub deployment workflows may build container images and call a configured deployment hook on merges to main. Runtime credentials are configured by the operator, not committed to the repository.
