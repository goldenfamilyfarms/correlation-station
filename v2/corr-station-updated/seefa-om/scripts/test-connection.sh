#!/usr/bin/env bash
set -euo pipefail

# ===========================
# CONFIG: targets & hostnames
# ===========================
SERVER_124_IP="${SERVER_124_IP:-159.56.4.94}"

# If you have DNS names for services on Server-124, set them here (or via env).
# Leave blank to skip; the script will still test the raw IP.
TEMPO_HOST="${TEMPO_HOST:-}"        # e.g. tempo.dev.chtrse.com
LOKI_HOST="${LOKI_HOST:-}"          # e.g. loki.dev.chtrse.com
PROM_HOST="${PROM_HOST:-}"          # e.g. prometheus.dev.chtrse.com
GRAFANA_HOST="${GRAFANA_HOST:-}"    # e.g. grafana.dev.chtrse.com
OTLP_HOST="${OTLP_HOST:-}"          # e.g. otlp.dev.chtrse.com (if you terminate OTLP behind a name)

# Ports to test on Server-124
PORTS=(4317 4318 3100 3200 9090 3000)

# Public endpoints to validate internet egress
PUBLIC_SITES=("grafana.com" "github.com" "google.com")

# Alloy download URL (just a proof-of-download; no install)
ALLOY_URL="${ALLOY_URL:-https://github.com/grafana/alloy/releases/latest/download/alloy-linux-amd64}"

# Where to log
OUT="/tmp/connectivity_report.txt"
: > "$OUT"

log() { echo -e "[$(date '+%F %T')] $*" | tee -a "$OUT"; }
hr()  { printf -- '%.0s-' {1..92} | tee -a "$OUT"; echo | tee -a "$OUT"; }

need_cmd() {
  local cmd="$1" pkg="${2:-$1}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "Installing missing dependency: $cmd"
    if command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y "$pkg" >>"$OUT" 2>&1 || true
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y "$pkg" >>"$OUT" 2>&1 || true
    fi
  fi
}

hr
log "MDSO Dev Server → Connectivity Diagnostics"
log "Target Server-124 IP: $SERVER_124_IP"
log "Hostnames (if set): TEMPO='${TEMPO_HOST:-<unset>}' LOKI='${LOKI_HOST:-<unset>}' PROM='${PROM_HOST:-<unset>}' GRAFANA='${GRAFANA_HOST:-<unset>}' OTLP='${OTLP_HOST:-<unset>}'"
hr

# ------------------------
# Environment & networking
# ------------------------
log "Step 0: Environment, routes, DNS, VPN-ish hints"
log "User: $(whoami)"
log "Hostname: $(hostname -f || hostname)"
log "Kernel: $(uname -srmo)"
log "Proxy env: http_proxy='${http_proxy:-<unset>}' https_proxy='${https_proxy:-<unset>}' no_proxy='${no_proxy:-<unset>}'"
ip a       >>"$OUT" 2>&1 || true
ip route   >>"$OUT" 2>&1 || true
# Heuristic VPN hint: presence of tun/tap/wg interfaces
ip -o link show | awk -F': ' '{print $2}' | grep -E '^(tun|tap|wg)' >>"$OUT" 2>&1 || true

need_cmd nslookup bind-utils
for site in "${PUBLIC_SITES[@]}"; do
  log "DNS lookup: $site"
  nslookup "$site" >>"$OUT" 2>&1 || log "  ⚠️ DNS lookup FAILED for $site"
done

# ------------------------
# ICMP reachability checks
# ------------------------
need_cmd ping iputils
log "Step 1: Ping checks"
ping -c 4 -W 2 "$SERVER_124_IP" >>"$OUT" 2>&1 || log "  ⚠️ Ping to $SERVER_124_IP FAILED (ICMP may be blocked)"
ping -c 4 -W 2 "google.com"    >>"$OUT" 2>&1 || log "  ⚠️ Ping to google.com FAILED (ICMP may be blocked)"
hr

# ------------------------
# TCP reachability to Server-124
# ------------------------
need_cmd nc nmap-ncat
log "Step 2: TCP port checks to Server-124 ($SERVER_124_IP)"
for p in "${PORTS[@]}"; do
  if nc -zv "$SERVER_124_IP" "$p" >>"$OUT" 2>&1; then
    log "  ✅ $SERVER_124_IP:$p reachable"
  else
    log "  ❌ $SERVER_124_IP:$p closed/filtered or service down"
  fi
done
hr

# ------------------------
# Hostname-specific tests
# ------------------------
# --- Step 3: Hostname-specific resolution & TCP checks (safe when unset) ---
log "Step 3: Hostname-specific resolution & TCP checks"
declare -A NAME2PORTS
[[ -n "${TEMPO_HOST:-}"   ]] && NAME2PORTS["$TEMPO_HOST"]="3200"
[[ -n "${LOKI_HOST:-}"    ]] && NAME2PORTS["$LOKI_HOST"]="3100"
[[ -n "${PROM_HOST:-}"    ]] && NAME2PORTS["$PROM_HOST"]="9090"
[[ -n "${GRAFANA_HOST:-}" ]] && NAME2PORTS["$GRAFANA_HOST"]="3000"
[[ -n "${OTLP_HOST:-}"    ]] && NAME2PORTS["$OTLP_HOST"]="4317 4318"

for name in "${!NAME2PORTS[@]}"; do
  log "Testing hostname: $name"
  nslookup "$name" >>"$OUT" 2>&1 || log "  ⚠️ DNS lookup FAILED for $name"
  for p in ${NAME2PORTS[$name]}; do
    if nc -zv "$name" "$p" >>"$OUT" 2>&1; then
      log "    ✅ $name:$p reachable"
    else
      log "    ❌ $name:$p closed/filtered or not listening"
    fi
  done
done
hr


# ------------------------
# Proxy diagnostics & curl tests
# ------------------------
need_cmd curl curl
log "Step 4: Proxy diagnostics & web egress"
# With proxy (if set)
if [[ -n "${https_proxy:-}" || -n "${http_proxy:-}" ]]; then
  for site in "${PUBLIC_SITES[@]}"; do
    log "  Curl (WITH proxy) HEAD https://$site"
    HTTPS_PROXY="$https_proxy" HTTP_PROXY="$http_proxy" NO_PROXY="$no_proxy" \
      curl -I -L --max-time 12 "https://$site" >>"$OUT" 2>&1 || log "    ⚠️ Curl with proxy FAILED for $site"
  done
fi
# Without proxy
for site in "${PUBLIC_SITES[@]}"; do
  log "  Curl (NO proxy) HEAD https://$site"
  HTTPS_PROXY= HTTP_PROXY= NO_PROXY= \
    curl -I -L --max-time 12 "https://$site" >>"$OUT" 2>&1 || log "    ⚠️ Curl without proxy FAILED for $site"
done
hr

# ------------------------
# Download test (no install)
# ------------------------
log "Step 5: Download test (Alloy binary) → /tmp"
cd /tmp || exit 1
if HTTPS_PROXY="${https_proxy:-}" HTTP_PROXY="${http_proxy:-}" NO_PROXY="${no_proxy:-}" \
   curl -L --fail --max-time 45 -o alloy-linux-amd64 "$ALLOY_URL" >>"$OUT" 2>&1; then
  SZ=$(stat -c%s /tmp/alloy-linux-amd64 2>/dev/null || echo "?")
  log "  ✅ Downloaded alloy-linux-amd64 (size: $SZ bytes)"
else
  log "  ❌ Download FAILED from $ALLOY_URL"
fi
hr

# ------------------------
# Traceroute & nmap (optional deeper look)
# ------------------------
need_cmd traceroute traceroute
log "Step 6: Traceroute to Server-124"
traceroute -n "$SERVER_124_IP" >>"$OUT" 2>&1 || log "  ⚠️ Traceroute FAILED"

need_cmd nmap nmap
log "Step 7: nmap scan of key ports on Server-124"
nmap -Pn -p "$(IFS=,; echo "${PORTS[*]}")" "$SERVER_124_IP" >>"$OUT" 2>&1 || log "  ⚠️ nmap FAILED"
hr

# ------------------------
# Local firewall diagnostics (iptables / nftables)
# ------------------------
log "Step 8: Local firewall diagnostics (iptables/nftables)"
# iptables (legacy or nft backend)
if command -v iptables >/dev/null 2>&1; then
  {
    echo "---- iptables -S (rules) ----"
    sudo iptables -S
    echo "---- iptables -L -n -v (counters) ----"
    sudo iptables -L -n -v
    echo "---- iptables-save ----"
    sudo iptables-save
  } >>"$OUT" 2>&1 || true
else
  log "  (iptables not present)"
fi

# nftables ruleset
if command -v nft >/dev/null 2>&1; then
  {
    echo "---- nft list ruleset ----"
    sudo nft list ruleset
  } >>"$OUT" 2>&1 || true
else
  log "  (nft not present)"
fi

# Quick policy hints
IN_POLICY=$(sudo iptables -S 2>/dev/null | awk '/^-P INPUT/ {print $3}' || true)
OUT_POLICY=$(sudo iptables -S 2>/dev/null | awk '/^-P OUTPUT/ {print $3}' || true)
FW_NOTE="INPUT policy=${IN_POLICY:-?}, OUTPUT policy=${OUT_POLICY:-?}"
log "  Firewall chain policies: $FW_NOTE"
hr

# ------------------------
# Summary
# ------------------------
log "SUMMARY"
# Ports summary
for p in "${PORTS[@]}"; do
  if grep -q "✅ $SERVER_124_IP:$p reachable" "$OUT"; then
    echo "  ✅ $SERVER_124_IP:$p reachable" | tee -a "$OUT"
  else
    echo "  ❌ $SERVER_124_IP:$p NOT reachable" | tee -a "$OUT"
  fi
done

# Hostname summary
for name in "${!NAME2PORTS[@]}"; do
  [[ -z "$name" ]] && continue
  for p in ${NAME2PORTS[$name]}; do
    if grep -q "✅ $name:$p reachable" "$OUT"; then
      echo "  ✅ $name:$p reachable" | tee -a "$OUT"
    else
      echo "  ❌ $name:$p NOT reachable" | tee -a "$OUT"
    fi
  done
done

log "Report saved to $OUT"
echo
echo "Tip: set hostnames via env, e.g.:"
echo "  TEMPO_HOST=tempo.dev.chtrse.com LOKI_HOST=loki.dev.chtrse.com GRAFANA_HOST=grafana.dev.chtrse.com \\"
echo "  PROM_HOST=prom.dev.chtrse.com OTLP_HOST=otlp.dev.chtrse.com ./connectivity-extended.sh"
