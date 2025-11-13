#!/bin/bash
# Sample Loki query script

LOKI_URL="${LOKI_URL:-http://localhost:3100}"

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -s SERVICE    Filter by service name"
    echo "  -t TRACE_ID   Filter by trace_id"
    echo "  -l LIMIT      Limit results (default: 100)"
    echo "  -h            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 -s beorn"
    echo "  $0 -t abc123def456"
    echo "  $0 -s palantir -l 50"
}

SERVICE=""
TRACE_ID=""
LIMIT=100

while getopts "s:t:l:h" opt; do
    case $opt in
        s) SERVICE="$OPTARG" ;;
        t) TRACE_ID="$OPTARG" ;;
        l) LIMIT="$OPTARG" ;;
        h) usage; exit 0 ;;
        *) usage; exit 1 ;;
    esac
done

# Build LogQL query
QUERY="{}"

if [ -n "$SERVICE" ]; then
    QUERY="{service=\"$SERVICE\"}"
fi

if [ -n "$TRACE_ID" ]; then
    if [ "$QUERY" = "{}" ]; then
        QUERY="{trace_id=\"$TRACE_ID\"}"
    else
        QUERY="${QUERY:0:-1}, trace_id=\"$TRACE_ID\"}"
    fi
fi

echo "Querying Loki..."
echo "Query: $QUERY"
echo "Limit: $LIMIT"
echo ""

# Query Loki
START=$(date -u -d '1 hour ago' +%s)000000000
END=$(date -u +%s)000000000

curl -s -G "$LOKI_URL/loki/api/v1/query_range" \
    --data-urlencode "query=$QUERY" \
    --data-urlencode "limit=$LIMIT" \
    --data-urlencode "start=$START" \
    --data-urlencode "end=$END" \
    | jq -r '.data.result[] | .values[] | .[1]' \
    | while read -r line; do
        echo "$line" | jq -C '.' 2>/dev/null || echo "$line"
    done

echo ""
echo "Query complete. View in Grafana: http://159.56.4.94:3000"