# Migration Guide: v1.0 to v2.0

## Overview

Version 2.0 adds MDSO (Multi-Domain Service Orchestrator) integration while maintaining full backward compatibility with v1.0. Existing deployments will continue to work without changes.

## What's New

- MDSO log collection and error analysis
- Circuit-based correlation (in addition to trace-based)
- Enhanced correlation with business identifiers

## Migration Steps

### 1. Update Dependencies

```bash
pip install -r requirements.txt
```

New dependencies:
- pandas
- pendulum
- configparser
- requests
- openpyxl

### 2. Update Configuration (Optional)

To enable MDSO integration, add to `.env`:

```env
MDSO_ENABLED=true
MDSO_URL=https://your-mdso-instance.com
MDSO_USER=your_username
MDSO_PASS=your_password
MDSO_COLLECTION_INTERVAL=3600
MDSO_TIME_RANGE_HOURS=3
```

### 3. Rebuild Docker Image

```bash
make build
```

### 4. Deploy

```bash
make up
```

## Backward Compatibility

✅ All v1.0 endpoints remain unchanged
✅ Existing integrations continue to work
✅ MDSO features are opt-in (disabled by default)
✅ No breaking changes to API contracts

## Testing Migration

```bash
# Test health endpoint
curl http://localhost:8080/health

# Test MDSO status (should show disabled if not configured)
curl http://localhost:8080/api/mdso/status

# Test existing correlation endpoint
curl http://localhost:8080/api/correlations
```

## Rollback

If issues occur, rollback to v1.0:

```bash
git checkout v1.0.0
make build
make up
```

## Support

For issues during migration, check:
1. Logs: `make logs`
2. Health endpoint: `GET /health`
3. MDSO status: `GET /api/mdso/status`
