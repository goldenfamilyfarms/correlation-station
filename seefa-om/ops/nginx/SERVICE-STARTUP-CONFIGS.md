# **Service Startup Configuration Guide**

This document provides the **required startup flags** for all backend services to work correctly behind NGINX reverse proxy.

---

## **🔷 PROMETHEUS**

### **Issue**
Prometheus fails at `http://austx-mdso-logs-02.chtrse.com/prometheus` but works at `159.56.4.94:9090`.

### **Root Cause**
Prometheus doesn't know it's behind a reverse proxy at `/prometheus/` path.

### **Fix**
Start Prometheus with these flags:

```bash
prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.console.libraries=/usr/share/prometheus/console_libraries \
  --web.console.templates=/usr/share/prometheus/consoles \
  --web.external-url=http://austx-mdso-logs-02.chtrse.com/prometheus \
  --web.route-prefix=/
```

**Key Flags:**
- `--web.external-url=/prometheus` - Tells Prometheus its public URL
- `--web.route-prefix=/` - Internal routing still uses `/` (NGINX adds the prefix)

### **Docker Compose**
```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--web.console.libraries=/usr/share/prometheus/console_libraries'
    - '--web.console.templates=/usr/share/prometheus/consoles'
    - '--web.external-url=http://austx-mdso-logs-02.chtrse.com/prometheus'
    - '--web.route-prefix=/'
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus-data:/prometheus
```

### **Verification**
```bash
# Test direct access
curl http://localhost:9090/graph

# Test through NGINX
curl http://austx-mdso-logs-02.chtrse.com/prometheus/graph

# Should both return Prometheus UI HTML
```

---

## **🔷 PYROSCOPE**

### **Issue**
App list returns HTML 404.

### **Root Cause**
Pyroscope doesn't know it's behind a reverse proxy at `/pyroscope/` path.

### **Fix**
Start Pyroscope with base-url flag:

```bash
pyroscope server \
  -base-url=/pyroscope \
  -config=/etc/pyroscope/config.yml
```

**Key Flag:**
- `-base-url=/pyroscope` - Tells Pyroscope its base path

### **Docker Compose**
```yaml
pyroscope:
  image: grafana/pyroscope:latest
  container_name: pyroscope
  command:
    - 'server'
    - '-base-url=/pyroscope'
    - '-config=/etc/pyroscope/config.yml'
  ports:
    - "4040:4040"
  volumes:
    - ./pyroscope-config.yml:/etc/pyroscope/config.yml
    - pyroscope-data:/var/lib/pyroscope
```

### **Verification**
```bash
# Test direct access
curl http://localhost:4040/

# Test through NGINX
curl http://austx-mdso-logs-02.chtrse.com/pyroscope/

# Both should return Pyroscope UI HTML
```

---

## **🔷 CORRELATION ENGINE**

### **Issue**
`/openapi.json` returns 404.

### **Root Cause**
Already fixed in code! FastAPI has `root_path="/correlation-engine"` configured correctly.

### **Current Config (Correct)**
```python
# seefa-om/correlation-engine/app/main.py:173
app = FastAPI(
    title="SEEFA Observability - Correlation Engine",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/correlation-engine",  # ✅ Correct
    docs_url="/docs",                  # ✅ Correct
    redoc_url="/redoc",                # ✅ Correct
    openapi_url="/openapi.json",       # ✅ Correct
)
```

### **Uvicorn Startup**
```bash
# If running with uvicorn directly:
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8080 \
  --root-path /correlation-engine
```

### **Docker Compose**
```yaml
correlation-engine:
  build: ./correlation-engine
  container_name: correlation-engine
  ports:
    - "8080:8080"
  environment:
    - ROOT_PATH=/correlation-engine
  command: >
    uvicorn app.main:app
    --host 0.0.0.0
    --port 8080
    --root-path /correlation-engine
```

### **Verification**
```bash
# Test OpenAPI JSON
curl http://austx-mdso-logs-02.chtrse.com/correlation-engine/openapi.json

# Test Swagger UI
curl http://austx-mdso-logs-02.chtrse.com/correlation-engine/docs

# Test ReDoc
curl http://austx-mdso-logs-02.chtrse.com/correlation-engine/redoc

# All should return valid responses
```

---

## **🔷 ARDA (SENSE App)**

### **Issue**
Returns **502 Bad Gateway** at `http://austx-mdso-logs-02.chtrse.com/arda`.

### **Root Cause**
One of the following:
1. **ARDA service not running**
2. **ARDA not listening on port 5001**
3. **ARDA listening on 127.0.0.1 instead of 0.0.0.0**
4. **ARDA crashed/stuck**

### **Troubleshooting Steps**

#### **1. Check if ARDA is running**
```bash
# Check if ARDA container/process is running
docker ps | grep arda
# OR
ps aux | grep arda
```

#### **2. Check if port 5001 is listening**
```bash
# Check what's listening on port 5001
sudo netstat -tulpn | grep 5001
# OR
sudo lsof -i :5001
```

#### **3. Test direct access**
```bash
# Test ARDA directly (bypass NGINX)
curl http://localhost:5001/

# If this fails with "Connection refused", ARDA isn't running
# If this works but NGINX fails, it's an NGINX config issue
```

#### **4. Check ARDA logs**
```bash
# Docker logs
docker logs arda

# System logs
journalctl -u arda -f

# Look for:
# - Port binding errors
# - Crashes
# - "Address already in use"
```

#### **5. Verify ARDA is binding to 0.0.0.0**
ARDA must listen on `0.0.0.0:5001` (all interfaces), not `127.0.0.1:5001` (localhost only).

**Flask/FastAPI:**
```python
# Correct
app.run(host="0.0.0.0", port=5001)

# Wrong (won't work with Docker/NGINX)
app.run(host="127.0.0.1", port=5001)
```

**Gunicorn:**
```bash
# Correct
gunicorn app:app --bind 0.0.0.0:5001

# Wrong
gunicorn app:app --bind 127.0.0.1:5001
```

### **Fix**
Update ARDA startup to bind to all interfaces:

```yaml
# Docker Compose
arda:
  build: ./sense-apps/arda
  container_name: arda
  ports:
    - "5001:5001"
  environment:
    - HOST=0.0.0.0
    - PORT=5001
  command: >
    gunicorn app.main:app
    --bind 0.0.0.0:5001
    --workers 4
    --timeout 300
```

---

## **🔷 NGINX RELOAD**

After making NGINX changes, reload the configuration:

```bash
# Test configuration syntax
sudo nginx -t

# Reload (no downtime)
sudo nginx -s reload

# OR restart (if reload doesn't work)
sudo systemctl restart nginx
```

---

## **🔷 VERIFICATION CHECKLIST**

Run these commands to verify all services are accessible:

```bash
#!/bin/bash
# Service verification script

echo "Testing services through NGINX reverse proxy..."

# Prometheus
echo -n "Prometheus: "
curl -s -o /dev/null -w "%{http_code}" http://austx-mdso-logs-02.chtrse.com/prometheus/graph

# Pyroscope
echo -n "Pyroscope: "
curl -s -o /dev/null -w "%{http_code}" http://austx-mdso-logs-02.chtrse.com/pyroscope/

# Correlation Engine - Health
echo -n "Correlation Engine Health: "
curl -s -o /dev/null -w "%{http_code}" http://austx-mdso-logs-02.chtrse.com/correlation-engine/health

# Correlation Engine - OpenAPI
echo -n "Correlation Engine OpenAPI: "
curl -s -o /dev/null -w "%{http_code}" http://austx-mdso-logs-02.chtrse.com/correlation-engine/openapi.json

# Correlation Engine - Docs
echo -n "Correlation Engine Docs: "
curl -s -o /dev/null -w "%{http_code}" http://austx-mdso-logs-02.chtrse.com/correlation-engine/docs

# ARDA
echo -n "ARDA: "
curl -s -o /dev/null -w "%{http_code}" http://austx-mdso-logs-02.chtrse.com/arda/

# BEORN
echo -n "BEORN: "
curl -s -o /dev/null -w "%{http_code}" http://austx-mdso-logs-02.chtrse.com/beorn/

# PALANTIR
echo -n "PALANTIR: "
curl -s -o /dev/null -w "%{http_code}" http://austx-mdso-logs-02.chtrse.com/palantir/

echo ""
echo "Expected: 200 for all services"
echo "502/503: Service not running or not accessible"
echo "404: Service running but endpoint doesn't exist"
```

Save as `test-services.sh` and run:
```bash
chmod +x test-services.sh
./test-services.sh
```

---

## **🔷 SUMMARY**

| **Service** | **Required Flag** | **Why** |
|-------------|-------------------|---------|
| **Prometheus** | `--web.external-url=/prometheus` | Tells Prometheus its public URL path |
| **Pyroscope** | `-base-url=/pyroscope` | Tells Pyroscope its base path |
| **Correlation Engine** | `--root-path /correlation-engine` | FastAPI needs to know its mount point |
| **ARDA/BEORN/PALANTIR** | `--bind 0.0.0.0:PORT` | Must listen on all interfaces, not just localhost |

---

## **🔷 NEXT STEPS**

1. **Apply NGINX fixes**: Copy `nginx-routing-fixes.conf` to production
2. **Update service startup configs**: Add required flags to docker-compose/systemd
3. **Reload NGINX**: `sudo nginx -s reload`
4. **Restart services**: With new startup flags
5. **Verify**: Run test script to confirm all endpoints work
