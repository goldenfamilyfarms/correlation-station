import sys

req_list = sys.path[0].split("/")
length = len(req_list)
req_list.pop(length - 1)
req_list.pop(length - 2)
req_path = "/".join(req_list) + "/model-definitions"
sys.path.append(req_path)
