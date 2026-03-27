# MDSO Instrumentation Deployment - Quick Reference

## Overview

You have OTel instrumentation code that adds tracing to MDSO products. This guide shows you how to deploy it to your remote MDSO server for testing.

## What This Is Different From

The document you mentioned about "Building MDSO Solutions" with DID tools (Docker Image Directory) is for deploying **Ciena Blue Planet MDSO solutions** (like Resource Adapters, Service Templates, etc.) using their traditional deployment process.

**What you're actually deploying** is your **custom instrumentation code** that adds observability to existing MDSO products. This is a simpler process:

1. Deploy Alloy collector (to collect logs/traces)
2. Deploy Python instrumentation code (to products)
3. Modify products to use the instrumentation

## One-Command Deployment

```bash
cd /home/user/correlation-station/seefa-om/mdso-alloy

# Deploy to your MDSO server (replace with actual IP)
./deploy-to-remote.sh 159.56.4.37 bpadmin
```

This will:
- Create a deployment package
- Copy it to your remote server
- Extract and set it up
- Run prerequisite checks

## Then On Remote Server

```bash
# SSH to MDSO server
ssh bpadmin@159.56.4.37

# Navigate to deployment
cd ~/alloy-agent/mdso-instrumentation-deploy

# Deploy Alloy container (collects logs/traces)
./deploy-container.sh

# Verify it's working
./verify-deployment.sh
```

## Deploying to a Specific MDSO Product

On the remote server:

```bash
# Integrate with a product (e.g., ServiceMapper)
cd ~/alloy-agent/mdso-instrumentation-deploy

./integrate-product.sh /opt/ciena/bp2/your-product/scripts YourProductClass
```

This copies the instrumentation code and creates example files.

## Key Differences from DID Deployment

| DID Tools (Solutions) | Your Deployment (Instrumentation) |
|----------------------|-----------------------------------|
| Deploys MDSO solutions (RAs, templates) | Deploys instrumentation code |
| Uses solmaker, did-save, did-push | Uses scp/rsync + docker-compose |
| Managed by Solution Manager (solman) | Managed by Alloy container |
| Requires building Docker images | Just copies Python files |
| Complex multi-step process | Simple 3-step deployment |

## The Complete Picture

```
Your Dev Machine
    ↓ (./deploy-to-remote.sh)
MDSO Server (159.56.4.37)
    ├─ Alloy Container (collects logs/traces)
    │   └─ Sends to → Meta Server (159.56.4.94:55681)
    └─ MDSO Products (with instrumentation)
        ├─ Generate traces
        └─ Send to Alloy → Meta → Tempo/Loki
```

## Files You Created

- `DEPLOY_TO_REMOTE.md` - Detailed deployment guide
- `create-deployment-package.sh` - Creates tarball for deployment
- `deploy-to-remote.sh` - One-command deployment to remote
- `integrate-product.sh` - Integrates OTel into products
- `deploy-container.sh` - Deploys Alloy (already exists)
- `verify-deployment.sh` - Verifies deployment (already exists)

## Testing After Deployment

1. **Check Alloy is collecting logs:**
   ```bash
   ssh bpadmin@159.56.4.37
   docker logs alloy-mdso --tail 50
   ```

2. **Run an MDSO product** (one with instrumentation)

3. **Check Meta server for traces:**
   ```bash
   ssh user@159.56.4.94
   docker-compose logs otel-gateway | grep mdso
   ```

4. **View in Grafana:**
   - Go to http://159.56.4.94:3000 (or wherever Grafana is)
   - Explore → Tempo
   - Search: `{service.name="mdso.yourproduct"}`

## Troubleshooting

### "Can't reach Meta server"
```bash
# On MDSO server, test connectivity
curl http://159.56.4.94:55681/v1/logs
```

### "OTel not initialized in product"
```bash
# Check environment variables are set
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export MDSO_ENV=dev
```

### "No traces appearing"
```bash
# Wait 10-15 seconds (batch export delay)
# Check if product is actually instrumented (look for "OTel initialized" in logs)
# Verify Alloy is receiving: docker logs alloy-mdso | grep -i trace
```

## When to Use DID Tools vs Your Scripts

**Use DID Tools** when deploying:
- Ciena Blue Planet solutions (bp-ra-adva, bp-ra-jnpr, etc.)
- Solution images built with `make solution`
- Products managed by Solution Manager (solman)

**Use Your Scripts** when deploying:
- Your OTel instrumentation code
- Alloy collector for log/trace collection
- Custom observability additions to MDSO

## Quick Commands Reference

```bash
# Create deployment package
./create-deployment-package.sh

# Deploy to remote
./deploy-to-remote.sh <server-ip> <username>

# On remote: Deploy Alloy
./deploy-container.sh

# On remote: Integrate with product
./integrate-product.sh <product-dir> <class-name>

# On remote: Verify
./verify-deployment.sh
docker logs alloy-mdso
curl http://159.56.4.94:55681/v1/logs
```

## Next Steps After Successful Deployment

1. ✅ Alloy collecting logs from MDSO server
2. ✅ Instrumentation code deployed to products
3. ⏳ Modify product code to use OTelMixin
4. ⏳ Test with real circuits
5. ⏳ Verify traces in Tempo
6. ⏳ Build correlation dashboard in Grafana
