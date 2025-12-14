# Deploying MDSO Instrumentation to Remote Server

## Overview

This guide walks you through deploying the OTel instrumentation code to your remote MDSO server for testing.

## Prerequisites

- **Remote MDSO Server**: Access to the MDSO server (likely 159.56.4.37 based on your configs)
- **SSH Access**: SSH keys configured for password-less login
- **Docker**: Docker installed and running on the remote server
- **Meta Server**: The correlation station running on 159.56.4.94:55681

## What Gets Deployed

### 1. Grafana Alloy Collector (Container)
- Collects logs from `/var/log/ciena/` and `/bp2/log/`
- Collects traces from instrumented products
- Sends everything to Meta server (159.56.4.94:55681)

### 2. OTel Instrumentation Python Code
- `otel_instrumentation/` module with mixin classes
- Gets copied into MDSO product directories
- Adds tracing to products like ServiceMapper

## Deployment Steps

### Step 1: Prepare Deployment Package

```bash
cd /home/user/correlation-station/seefa-om/mdso-alloy

# Create deployment tarball
./create-deployment-package.sh
```

This creates `mdso-instrumentation-deploy.tar.gz` containing:
- Alloy configuration (`config.alloy`)
- Docker Compose file
- Deployment scripts
- OTel instrumentation Python code
- Verification scripts

### Step 2: Deploy to Remote Server

```bash
# Set your remote server IP
export MDSO_SERVER="159.56.4.37"
export MDSO_USER="bpadmin"

# Deploy the package
./deploy-to-remote.sh $MDSO_SERVER
```

This will:
1. Copy the deployment package to the remote server
2. Extract it to `~/alloy-agent/`
3. Verify prerequisites (Docker, network, log directories)

### Step 3: Deploy Alloy Collector on Remote Server

```bash
# SSH to remote server
ssh ${MDSO_USER}@${MDSO_SERVER}

# Navigate to deployment directory
cd ~/alloy-agent

# Deploy Alloy container
./deploy-container.sh
```

This starts the Alloy collector which:
- Tails MDSO log files
- Listens for OTLP traces (ports 4317/4318)
- Exports everything to Meta server

### Step 4: Deploy OTel Instrumentation to MDSO Products

**Option A: Direct Copy (For Testing)**

```bash
# On remote server
cd ~/alloy-agent

# Copy instrumentation to a product directory
# Replace with actual product path on your server
PRODUCT_DIR="/opt/ciena/bp2/bpso-sensor-templates/scripts"

# Copy the instrumentation module
sudo cp -r mdso-instrumentation/otel_instrumentation $PRODUCT_DIR/

# Verify
ls -la $PRODUCT_DIR/otel_instrumentation/
```

**Option B: Integrate into Product Docker Image (Production)**

Create a Dockerfile that includes the instrumentation:

```dockerfile
FROM your-mdso-product-base:latest

# Copy OTel instrumentation
COPY mdso-instrumentation/otel_instrumentation /app/scripts/otel_instrumentation/

# Install dependencies
RUN pip install -r /app/scripts/otel_instrumentation/requirements.txt

# Set environment variables
ENV OTEL_ENABLED=true
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
ENV MDSO_ENV=dev

# Rest of your Dockerfile...
```

### Step 5: Modify Product Code

**For ServiceMapper (Example)**

Edit the product file (e.g., `serviceMapper/common.py`):

```python
# Add imports at top
from otel_instrumentation.otel_mixin import OTelMixin
from otel_instrumentation.feature_flags import is_otel_enabled

# Modify class to inherit from mixin
class Common(CommonPlan, OTelMixin):

    def run(self):
        """Override run() to add OTel root span"""
        if is_otel_enabled():
            self.__init_otel__()
            with self.create_root_span():
                return super().run()
        else:
            return super().run()
```

### Step 6: Set Environment Variables

On the MDSO server, set these environment variables before running products:

```bash
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export MDSO_ENV=dev
export OTEL_TRACE_EXPORT_MODE=file  # For isolated containers
export OTEL_TRACE_FILE_PATH=/opt/ciena/bp2/alloy-collector/traces.ndjson
```

**For Docker Containers:**

Add to `docker-compose.yml` or container environment:

```yaml
environment:
  - OTEL_ENABLED=true
  - OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318
  - MDSO_ENV=dev
```

### Step 7: Verify Deployment

On the MDSO server:

```bash
cd ~/alloy-agent

# Verify Alloy is running
docker ps | grep alloy-mdso

# Check Alloy logs
docker logs alloy-mdso --tail 50

# Verify it's collecting logs
docker logs alloy-mdso | grep "Tailing"

# Verify connectivity to Meta
curl -v http://159.56.4.94:55681/v1/logs
```

On the Meta server (159.56.4.94):

```bash
# Check OTel Gateway received data
docker-compose logs --tail 100 otel-gateway | grep mdso

# Check correlation engine
docker-compose logs --tail 100 correlation-engine | grep mdso

# Query Loki for MDSO logs
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso"}' \
  --data-urlencode 'limit=10' | jq
```

## Testing the Instrumentation

### Test 1: Execute an MDSO Product

Trigger a ServiceMapper or other instrumented product to run. For example:
- Create a circuit order
- Modify a service
- Run a product manually

### Test 2: Check for Traces in Tempo

On Meta server (or via Grafana):

```bash
# Query Tempo for traces
curl -G 'http://localhost:9000/api/search' \
  --data-urlencode 'q={service.name="mdso.common"}'
```

Or in Grafana:
1. Go to Explore
2. Select Tempo datasource
3. Search for: `{service.name="mdso.common"}`

### Test 3: Verify Log Correlation

In Grafana Loki:
1. Find logs with `{service="mdso"}`
2. Verify they have `trace_id` attributes
3. Click on a trace_id to jump to the trace

## Troubleshooting

### Alloy Not Collecting Logs

```bash
# Check Alloy logs for errors
docker logs alloy-mdso | grep -i error

# Verify log files exist and have content
ls -lh /var/log/ciena/blueplanet.log
tail -f /var/log/ciena/blueplanet.log

# Check file permissions
docker exec alloy-mdso ls -la /var/log/ciena/
```

### Traces Not Appearing

```bash
# Check if OTel is enabled in the product
# In product logs, look for "OTel initialized"

# Verify environment variables are set
docker exec <product-container> env | grep OTEL

# Check if traces are being exported
docker logs alloy-mdso | grep -i trace

# For file-based export, check the trace file
cat /opt/ciena/bp2/alloy-collector/traces.ndjson
```

### Network Connectivity Issues

```bash
# From MDSO server, test Meta connectivity
curl -v http://159.56.4.94:55681/v1/logs

# Check firewall rules
sudo iptables -L | grep 55681

# Test OTLP endpoint from container
docker exec alloy-mdso curl http://159.56.4.94:55681/v1/traces
```

### Import Errors in Products

```python
# If you get: ModuleNotFoundError: No module named 'otel_instrumentation'

# Check if the module was copied
ls -la /path/to/product/scripts/otel_instrumentation/

# Verify Python path includes the scripts directory
python -c "import sys; print('\\n'.join(sys.path))"

# Install dependencies
pip install -r otel_instrumentation/requirements.txt
```

## Monitoring Deployment

### Alloy Health Check

```bash
# Check Alloy is running
curl http://<mdso-server>:12345/-/ready

# View Alloy UI
# Open browser to: http://<mdso-server>:12345
```

### Data Flow Verification

```mermaid
MDSO Products → OTel Traces → Alloy (4318) → Meta (55681) → Tempo
             ↓
           Logs → Alloy (file tail) → Meta (55681) → Loki
```

Check each hop:
1. ✅ Product generates traces
2. ✅ Alloy receives traces (check logs)
3. ✅ Meta Gateway receives traces (check gateway logs)
4. ✅ Tempo stores traces (query Tempo)

## Rolling Back

If you need to rollback:

```bash
# On MDSO server
cd ~/alloy-agent

# Stop Alloy
docker-compose down

# Remove instrumentation from products
sudo rm -rf /opt/ciena/bp2/*/scripts/otel_instrumentation/

# Revert product code changes
git checkout <product-file>
```

## Next Steps After Deployment

1. **Validate**: Run test circuits and verify traces appear
2. **Monitor**: Watch for errors in Alloy/Gateway logs
3. **Tune**: Adjust sampling rates if needed
4. **Expand**: Add instrumentation to more products
5. **Document**: Record any MDSO-specific deployment notes

## Additional Resources

- **Deployment Guide**: `DEPLOYMENT-GUIDE-ENHANCED.md`
- **Testing Guide**: `TESTING-GUIDE-ENHANCED.md`
- **Implementation Guide**: `mdso-instrumentation/IMPLEMENTATION_GUIDE.md`
- **Quick Start**: `QUICK-START.md`
