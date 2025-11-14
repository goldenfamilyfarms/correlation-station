# Archive

This directory contains deprecated code that has been removed from the active codebase but preserved for historical reference.

## Contents

### `sense-apps/beorn/beorn_app/middleware.py`
### `sense-apps/palantir/palantir_app/middleware.py`

**Archived:** November 14, 2025
**Reason:** Resource-intensive `LoggingWSGIMiddleware` that caused machine crashes

These files contained the original WSGI middleware used for request logging in Beorn and Palantir.
They were replaced with lightweight OpenTelemetry instrumentation in commit `0a18df6`.

**Replacement:** `sense-apps/common/otel_utils.py` provides the same functionality with:
- Lower resource overhead
- Better trace context propagation
- Integration with the correlation-station observability stack
- No performance issues or crashes

**Related Commits:**
- `0a18df6` - "sense instrumentation and gitlab ci cd configs" (removed middleware)
- Earlier commits that introduced the middleware

---

## Note

Files in this archive are not maintained and should not be used in production.
They are kept solely for reference purposes.
