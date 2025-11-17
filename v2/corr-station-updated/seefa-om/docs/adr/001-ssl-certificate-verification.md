# ADR-001: SSL Certificate Verification

**Status**: Accepted
**Date**: 2025-11-14
**Authors**: Claude
**Priority**: Critical (Security)

## Context

The MDSO (Multi-Domain Service Orchestrator) client was configured with `verify=False`, which bypasses SSL certificate validation. This creates a critical security vulnerability:

- **Man-in-the-Middle (MITM) Attacks**: Without certificate verification, attackers can intercept and modify traffic between the correlation engine and MDSO
- **Data Exposure**: Sensitive data (credentials, circuit information, traces) could be exposed
- **Compliance Issues**: Violates security best practices and compliance requirements (PCI-DSS, SOC 2, etc.)

### Problem Statement
```python
# BEFORE - Insecure
self._client = httpx.AsyncClient(verify=False)  # ❌ VULNERABLE
```

The hardcoded `verify=False` meant:
- No way to enable SSL verification without code changes
- Production systems exposed to MITM attacks
- No support for custom CA bundles

## Decision

**We will make SSL verification configurable with secure defaults:**

1. **Default to SSL verification enabled** (`verify_ssl=True`)
2. **Support custom CA bundles** for private Certificate Authorities
3. **Allow disabling only via explicit configuration** (with warnings)
4. **Log warnings when SSL verification is disabled**

### Implementation
```python
# AFTER - Secure by default
self._client = httpx.AsyncClient(
    verify=ssl_ca_bundle if ssl_ca_bundle else verify_ssl,
    timeout=timeout
)

if not verify_ssl:
    logger.warning(
        "MDSO client SSL verification disabled - this is insecure!",
        recommendation="Set MDSO_VERIFY_SSL=true and provide CA bundle"
    )
```

### Configuration Options
```bash
# .env
MDSO_VERIFY_SSL=true  # Default - secure
MDSO_SSL_CA_BUNDLE=/path/to/ca-bundle.crt  # Optional custom CA
```

## Consequences

### Positive
- ✅ **Security**: Prevents MITM attacks on MDSO communication
- ✅ **Compliance**: Meets security compliance requirements
- ✅ **Flexibility**: Supports custom CA bundles for private PKI
- ✅ **Visibility**: Logs warnings when verification disabled
- ✅ **Best Practices**: Secure by default, insecure opt-in

### Negative
- ⚠️ **Testing Complexity**: Local development may need CA bundles or explicit disabling
- ⚠️ **Migration**: Existing deployments with self-signed certs need configuration updates

## Alternatives Considered

### Alternative 1: Always verify, no disable option
- **Pros**: Maximum security, no way to accidentally disable
- **Cons**: Breaks local development, no flexibility for testing
- **Why not chosen**: Too rigid for development and testing scenarios

### Alternative 2: Keep verify=False by default
- **Pros**: No changes needed, backward compatible
- **Cons**: Insecure by default, violates security principles
- **Why not chosen**: Unacceptable security risk

### Alternative 3: Environment-specific defaults
- **Pros**: Secure in prod, permissive in dev
- **Cons**: Magic behavior, hard to test production configuration
- **Why not chosen**: Prefer explicit configuration over magic

## Implementation

### Phase 1: Add Configuration (✅ Complete)
- Added `verify_ssl` and `ssl_ca_bundle` parameters to `MDSOClient`
- Updated configuration with new settings
- Added logging for disabled verification

### Phase 2: Documentation (✅ Complete)
- Updated `.env.example` with SSL settings
- Added security notes in documentation
- Created `FIXES_SUMMARY.md` with migration guide

### Phase 3: Migration (In Progress)
- [ ] Update production deployments with CA bundles
- [ ] Test with real MDSO endpoints
- [ ] Monitor logs for verification warnings

## Migration Guide

### For Development
```bash
# Option 1: Use system CA bundle (recommended)
MDSO_VERIFY_SSL=true

# Option 2: Provide custom CA bundle
MDSO_VERIFY_SSL=true
MDSO_SSL_CA_BUNDLE=/path/to/mdso-ca.crt

# Option 3: Disable for local testing (NOT FOR PRODUCTION)
MDSO_VERIFY_SSL=false  # Will log warnings
```

### For Production
```bash
# Production MUST use verification
MDSO_VERIFY_SSL=true
MDSO_SSL_CA_BUNDLE=/etc/ssl/certs/mdso-ca.crt  # If custom CA
```

## Monitoring

Track SSL verification status:
```python
# Metrics to add
ssl_verification_disabled = Gauge(
    'mdso_ssl_verification_disabled',
    'Whether SSL verification is disabled (1=disabled, 0=enabled)'
)
```

## References

- [OWASP: Transport Layer Protection](https://owasp.org/www-project-proactive-controls/v3/en/c8-protect-data-everywhere)
- [NIST SP 800-52: TLS Guidelines](https://csrc.nist.gov/publications/detail/sp/800-52/rev-2/final)
- [Related Fix: FIXES_SUMMARY.md](../../FIXES_SUMMARY.md)
- [httpx SSL Configuration](https://www.python-httpx.org/advanced/#ssl-certificates)

## Status History

- **2025-11-14**: Accepted and implemented
- **Future**: Consider adding certificate pinning for extra security
