import os

if not os.path.exists("logs"):
    os.mkdir("logs")
log_path = "/beorn/logs"
if not os.path.exists(log_path):
    os.makedirs(log_path)

bind = "0.0.0.0:5002"
workers = 16
threads = 16
worker_class = "gthread"
errorlog = f"{log_path}/gunicorn/error.log"
worker_tmp_dir = "/dev/shm"
accesslog = f"{log_path}/gunicorn/gunicorn.log"
loglevel = "info"
max_requests_jitter = 200
timeout = 0
limit_request_line = 10000
