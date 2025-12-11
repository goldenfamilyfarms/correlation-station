from flask import Flask, jsonify
import os, json, time
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

app = Flask(__name__)
OTEL_ENDPOINT = os.getenv("OTEL_COLLECTOR_OTLP_ENDPOINT", "http://otel-collector:4318/v1/traces")
resource = Resource.create({"service.name": "sense-disconnect"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'mock', 'data', 'msp_managed.json')
if not os.path.exists(DATA_FILE):
    DATA_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'mock', 'data', 'msp_managed.json')

@app.route('/trigger', methods=['POST'])
def trigger():
    with open(DATA_FILE) as f:
        data = json.load(f)
    with tracer.start_as_current_span("disconnect.workflow") as span:
        span.set_attribute("workflow", data.get('workflow'))
        span.set_attribute("cid", data.get('circuit', {}).get('cid'))
        for step in data.get('actions', []):
            span.add_event(f"disconnect:{step.get('step')}:{step.get('status')}")
            time.sleep(0.02)
    return jsonify({"status": "ok", "cid": data.get('circuit', {}).get('cid')})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)
