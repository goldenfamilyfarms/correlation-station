from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# simple in-memory token and resources for demo
DEMO_TOKEN = "demo-token"
DEMO_RESOURCES = [
    {"id": "res-1", "type": "demo.resourceTypes.productA", "properties": {"name": "demo-item-1"}},
    {"id": "res-2", "type": "demo.resourceTypes.productB", "properties": {"name": "demo-item-2"}},
]

@app.route('/tron/api/v1/tokens', methods=['POST'])
def tokens():
    body = request.get_json(force=True)
    # very small demo auth: accept any username/password
    return jsonify({"token": DEMO_TOKEN})

@app.route('/tron/api/v1/tokens/<token>', methods=['DELETE'])
def delete_token(token):
    return ('', 204)

@app.route('/bpocore/market/api/v1/resources/count')
def resources_count():
    exact_type = request.args.get('exactTypeId')
    count = sum(1 for r in DEMO_RESOURCES if r['type'] == exact_type) if exact_type else len(DEMO_RESOURCES)
    return jsonify({"count": count})

@app.route('/bpocore/market/api/v1/resources')
def resources_list():
    resource_type = request.args.get('resourceTypeId')
    limit = int(request.args.get('limit', '100'))
    items = [r for r in DEMO_RESOURCES if r['type'] == resource_type] if resource_type else DEMO_RESOURCES
    return jsonify({"items": items[:limit]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
