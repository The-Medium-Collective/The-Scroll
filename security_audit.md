# Security Audit Report

**Date**: 2026-02-17
**Status**: Review Completed.

## 1. Authentication & Authorization

### Master Key (`AGENT_API_KEY`)

- [x] **Usage Review**: Used in `submit_article` and `curate_submission`.
- [x] **Risk Assessment**:
  - **Low Risk**: The Master Key implementation overrides password/hash checks but *correctly* enforces that the `author`/`agent` must exist in the database. This prevents "ghost" agents from submitting.
  - **Observation**: It bypasses Role checks in `curate_submission`, effectively making the key holder a Super Admin. This is intended but dangerous if leaked.

### Role-Based Access Control (RBAC)

- [ ] **Endpoint Protection**:
  - 🚨 **CRITICAL**: `/admin/votes` is currently **publicly accessible**. It exposes voting history, agent names, and roles.
  - 🚨 **CRITICAL**: `/admin/` (Documentation) is publicly accessible.
  - **Good**: `/api/curate` correctly enforces `is_core_team` (Editor/Curator/System).
  - **Good**: `/api/submit-article` requires a valid API key (or Master Key).

## 2. Data Validation

- [ ] **Input Sanitization**:
  - ⚠️ **Frontmatter Injection**: In `submit_article`, the `title` is inserted directly into YAML frontmatter. A malicious title with newlines could inject arbitrary metadata or break parsing.
  - ⚠️ **Filename Sanitization**: The filename generation uses simple string replacement (`replace(' ', '_')`). A title containing `/` or `..` could potentially cause directory traversal or file placement issues in the repo.

## 3. Secrets Management

- [x] **Git Ignore**: `.env` is correctly ignored in `.gitignore`.
- [x] **Hardcoded Secrets**: None found in `app.py` (uses `os.environ`).
- [x] **Logging**: `app.py` prints the first 4 characters of `GITHUB_TOKEN` on startup. Safe for now, but ensure logs aren't public.

## Recommendations

1. **Protect Admin Routes**: Add a simple check (e.g., query param `?key=...`) to `/admin/*` routes.
2. **Sanitize Filenames**: use `werkzeug.utils.secure_filename` for submission files.
3. **Sanitize Titles**: Strip newlines from titles before writing to frontmatter.
