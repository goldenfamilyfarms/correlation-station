# Finding MDSO Products - Quick Reference

**Quick guide to locate MDSO scriptplan products for OTel instrumentation**

---

## Where to Look

### 1. MDSO Server (Primary Location)

```bash
# SSH to MDSO server
ssh user@159.56.4.37  # Or your MDSO server IP

# Search for common_plan.py
find /opt -name "common_plan.py" 2>/dev/null
find /opt -name "*common_plan*" 2>/dev/null

# Search for product directories
find /opt -type d -name "*serviceMapper*" 2>/dev/null
find /opt -type d -name "*fabricator*" 2>/dev/null
find /opt -type d -name "*configmodeler*" 2>/dev/null

# Search for scripts directory
find /opt -type d -name "scripts" 2>/dev/null | grep -i mdso
find /opt -type d -path "*/scripts/*" 2>/dev/null

# Check common locations
ls -la /opt/mdso-dev/
ls -la /opt/charter/
ls -la /opt/sensor-templates/
ls -la /opt/model-definitions/
```

### 2. This Repository

```bash
# Search for archive or hidden directories
find . -name ".archive" -type d
find . -name "*archive*" -type d
find . -name "*mdso-dev*" -type d

# Check if products are in a submodule
git submodule status
cat .gitmodules 2>/dev/null
```

### 3. Separate Repository

Check for:
- `mdso-dev` repository
- `charter-sensor-templates` repository
- `model-definitions` repository
- Internal GitLab/GitHub MDSO repos

### 4. Container/Deployment Location

```bash
# Check Docker containers
docker ps | grep mdso
docker exec <container> find / -name "common_plan.py" 2>/dev/null

# Check Kubernetes deployments
kubectl get pods | grep mdso
kubectl exec <pod> -- find / -name "common_plan.py" 2>/dev/null
```

---

## What to Look For

### File Structure (Expected)

```
/path/to/products/
├── common_plan.py              # Base class
├── serviceMapper/
│   └── common.py              # ServiceMapper product
├── fabricator/
│   └── common.py              # Fabricator product
├── configmodeler/
│   └── common.py              # ConfigModeler product
├── deviceconfiguration/
│   └── common.py              # Device config product
└── networkservice/
    └── common.py              # Network service product
```

### Key Files to Find

1. **common_plan.py** - Base class with logging setup
2. **Product common.py files** - Individual product implementations
3. **requirements.txt** - Python dependencies
4. **Deployment scripts** - How products are deployed

---

## Once Found

1. **Document Location**
   - Update `PRODUCT_LOCATION_ANALYSIS.md` with actual paths
   - Note deployment process
   - Document access requirements

2. **Deploy OTel Classes**
   ```bash
   # Copy OTel instrumentation
   cp -r seefa-om/mdso-alloy/mdso-instrumentation/otel_instrumentation/ \
        /path/to/products/otel_instrumentation/
   ```

3. **Follow Implementation Guide**
   - See `IMPLEMENTATION_GUIDE.md`
   - Add mixin to products
   - Test integration

---

## Contact Points

If products cannot be found:

1. **MDSO Team** - Ask for product code location
2. **DevOps Team** - Check deployment documentation
3. **Platform Team** - Verify MDSO server access
4. **Architecture Team** - Understand product execution model

---

## Alternative: Instrument at Integration Points

If products cannot be modified directly, instrument where they're called:

1. **Sense Apps** - Add OTel to MDSO API calls
2. **MDSO Client** - Instrument HTTP client
3. **Log Parsing** - Extract correlation from logs

See `PRODUCT_LOCATION_ANALYSIS.md` for details.

