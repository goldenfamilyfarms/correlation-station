from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/palantir/v1/hvt/ctbh')
def ctbh():
    # A tiny demo response mimicking the real endpoint
    return jsonify({"status": "ok", "message": "demo-response"})

@app.route('/palantir/v1/hvt/eece')
def eece():
    # if query contains a circuit_id that starts with 31 -> simulate error
    circuit = request.args.get('circuit_id', '')
    if circuit.startswith('31'):
        return jsonify({"error": "demo-error"})
    return jsonify({"status": "ok", "data": {"cid": circuit}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
