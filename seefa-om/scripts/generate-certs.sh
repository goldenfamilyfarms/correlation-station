#!/bin/bash
#
# Generate mTLS Certificates for Alloy → Gateway
# Creates self-signed CA and client/server certificates
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}mTLS Certificate Generation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
CERTS_DIR="certs"
DAYS_VALID=365

# Create certs directory
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# ============================================
# Generate CA (Certificate Authority)
# ============================================
echo -e "${YELLOW}Generating CA certificate...${NC}"

openssl genrsa -out ca.key 4096

openssl req -new -x509 -days $DAYS_VALID -key ca.key -out ca.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=Observability-CA"

echo -e "${GREEN}✓ CA certificate created${NC}"
echo ""

# ============================================
# Generate Server Certificate (Gateway)
# ============================================
echo -e "${YELLOW}Generating server certificate for Gateway...${NC}"

# Generate server private key
openssl genrsa -out server.key 4096

# Generate server CSR
openssl req -new -key server.key -out server.csr \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=Gateway/CN=otel-gateway"

# Sign server certificate with CA
openssl x509 -req -days $DAYS_VALID -in server.csr \
    -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt

echo -e "${GREEN}✓ Server certificate created${NC}"
echo ""

# ============================================
# Generate Client Certificate (Alloy)
# ============================================
echo -e "${YELLOW}Generating client certificate for Alloy...${NC}"

# Generate client private key
openssl genrsa -out client.key 4096

# Generate client CSR
openssl req -new -key client.key -out client.csr \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=Alloy/CN=mdso-alloy-client"

# Sign client certificate with CA
openssl x509 -req -days $DAYS_VALID -in client.csr \
    -CA ca.crt -CAkey ca.key -set_serial 02 -out client.crt

echo -e "${GREEN}✓ Client certificate created${NC}"
echo ""

# ============================================
# Cleanup CSR files
# ============================================
rm -f server.csr client.csr

# ============================================
# Verify Certificates
# ============================================
echo -e "${YELLOW}Verifying certificates...${NC}"

echo "CA Certificate:"
openssl x509 -in ca.crt -noout -subject -dates

echo ""
echo "Server Certificate:"
openssl x509 -in server.crt -noout -subject -dates
openssl verify -CAfile ca.crt server.crt

echo ""
echo "Client Certificate:"
openssl x509 -in client.crt -noout -subject -dates
openssl verify -CAfile ca.crt client.crt

echo ""

# ============================================
# Summary
# ============================================
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Certificate Generation Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Generated files in ${CERTS_DIR}/:"
ls -lh

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Copy certificates to Gateway:"
echo "   cp ca.crt server.crt server.key ../gateway/"
echo ""
echo "2. Copy certificates to MDSO Dev (for Alloy):"
echo "   scp ca.crt client.crt client.key user@159.56.4.37:/etc/alloy/certs/"
echo ""
echo "3. Update Gateway config (gateway/otel-config.yaml):"
echo "   Add TLS configuration to receivers.otlp:"
echo ""
echo "   receivers:"
echo "     otlp:"
echo "       protocols:"
echo "         http:"
echo "           tls:"
echo "             cert_file: /certs/server.crt"
echo "             key_file: /certs/server.key"
echo "             client_ca_file: /certs/ca.crt"
echo "             require_client_auth: true"
echo ""
echo "4. Update Alloy config (mdso-alloy/config.alloy):"
echo "   Add TLS configuration to exporter:"
echo ""
echo "   otelcol.exporter.otlphttp \"server124\" {"
echo "     client {"
echo "       endpoint = \"https://159.56.4.94:4318\""
echo "       tls {"
echo "         ca_file   = \"/etc/alloy/certs/ca.crt\""
echo "         cert_file = \"/etc/alloy/certs/client.crt\""
echo "         key_file  = \"/etc/alloy/certs/client.key\""
echo "       }"
echo "     }"
echo "   }"
echo ""
echo "5. Restart services:"
echo "   docker-compose restart otel-gateway"
echo "   sudo systemctl restart alloy  # On MDSO Dev"
echo ""
echo -e "${GREEN}Certificates valid for ${DAYS_VALID} days${NC}"
echo ""