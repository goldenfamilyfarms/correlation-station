from flask import Flask, jsonify, request
import os
import json
import time
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

app = Flask(__name__)

# Configure OTLP exporter - default to in-cluster collector
OTEL_ENDPOINT = os.getenv("OTEL_COLLECTOR_OTLP_ENDPOINT", "http://otel-collector:4318/v1/traces")

resource = Resource.create({"service.name": "mdso-mock"})
provider = TracerProvider(resource=resource)
span_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
provider.add_span_processor(BatchSpanProcessor(span_exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'mock', 'data')
if not os.path.exists(DATA_DIR):
    # fall back to demo/mock/data
    DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'mock', 'data')


@app.route('/tron/api/v1/tokens', methods=['POST'])
def tokens():
    return jsonify({"token": "demo-token"})


@app.route('/trigger', methods=['POST'])
def trigger():
    """Trigger the mdso workflow: reads mdso JSON and emits a trace span"""
    payload = request.get_json(silent=True) or {}
    file = payload.get('file', 'msp_managed.json')
    filepath = os.path.join(DATA_DIR, file)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return jsonify({"error": f"cannot read {filepath}: {e}"}), 400

    with tracer.start_as_current_span("mdso.process_workflow") as span:
        span.set_attribute("workflow.type", data.get('workflow', 'unknown'))
        span.set_attribute("circuit.cid", data.get('circuit', {}).get('cid', 'unknown'))
        # simulate processing steps
        for step in data.get('actions', []):
            span.add_event(f"step:{step.get('step')}:{step.get('status')}")
            time.sleep(0.05)

    return jsonify({"status": "processed", "cid": data.get('circuit', {}).get('cid')}), 200


@app.route('/bpocore/market/api/v1/resources', methods=['GET'])
def resources():
    # simple demo resources response
    items = [
        {"id": "res-1", "type": "demo.resourceTypes.productA", "properties": {"name": "demo-item-1"}},
        {"id": "res-2", "type": "demo.resourceTypes.productB", "properties": {"name": "demo-item-2"}},
    ]
    return jsonify({"items": items})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
