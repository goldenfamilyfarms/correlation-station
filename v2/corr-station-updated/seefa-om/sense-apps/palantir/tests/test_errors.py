# import json
#
# from palantir.common.errors import InvalidUsage, ConnectionIssue


# def test_jsonify_InvalidUsage(client):
#     """Test we get an InvalidUsage error with expected response code"""
#
#     bad_req = """
#     [
#         {
#             "transactionID": "345",
#             "zSide":
#                 {
#                     "ip": "99.99.99.99",
#                     "vlan": "VLAN1199"
#                 },
#             "aSide":
#                 {
#                     "ip": null,
#                     "port": null,
#                     "vlan": null
#                 }
#         }
#     ]
#     """
#
#     json_payload = json.loads(bad_req)
#
#     resp = client.post('/', data=json.dumps(json_payload))
#     err_dict = InvalidUsage("Invalid usage!", status_code=400).to_dict()
#     assert err_dict['status_code'] == resp.status_code
#     assert b"Missing port in JSON. Transaction ID: 345" in resp.data
#
#
# def test_jsonify_ConnectionIssue(client):
#     """Test we can get a connection error (status code 503) when we can't
#     SSH into the router
#     """
#     bad_req = """
#     [
#         {
#             "transactionID": "345",
#             "zSide":
#                 {
#                     "ip": "99.99.99.99",
#                     "port": "ge-0/1/7",
#                     "vlan": "VLAN1199"
#                 },
#             "aSide":
#                 {
#                     "ip": null,
#                     "port": null,
#                     "vlan": null
#                 }
#         }
#     ]
#     """
#     # Load it into python
#     json_payload = json.loads(bad_req)
#
#     resp = client.post('/', data=json.dumps(json_payload))
#     err_dict = ConnectionIssue("Unable to contact device", status_code=503).to_dict()
#     assert err_dict['status_code'] == resp.status_code
#     assert b"Error connecting to the router. Transaction ID: 345" in resp.data
