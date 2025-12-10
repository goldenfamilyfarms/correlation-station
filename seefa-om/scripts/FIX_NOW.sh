#!/bin/bash
# Quick fix for correlation-engine

cd /opt/seefa-om

echo "Checking correlation-engine logs..."
sudo docker logs --tail 20 correlation-engine

echo ""
echo "The issue is likely missing Python dependencies (pandas, selenium, openpyxl)"
echo ""
echo "Option 1: Rebuild with dependencies installed"
echo "==========================================="
sudo docker compose down correlation-engine
sudo docker compose build --no-cache correlation-engine
sudo docker compose up -d correlation-engine

echo ""
echo "Waiting 10 seconds..."
sleep 10

echo ""
echo "Checking status..."
sudo docker ps | grep correlation-engine

echo ""
echo "If still failing, check logs:"
echo "sudo docker logs correlation-engine"
