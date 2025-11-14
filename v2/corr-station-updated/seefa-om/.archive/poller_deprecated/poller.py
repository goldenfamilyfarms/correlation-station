#!/usr/bin/env python3
"""
MDSO Syslog Poller
Polls MDSO Syslog API, extracts ZIP, normalizes to NDJSON with trace correlation fields
"""
import os
import json
import time
import zipfile
import io
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
MDSO_AUTH_ENDPOINT = "https://47.43.111.79/tron/api/v1/tokens"
# MDSO_SYSLOG_ENDPOINT = os.getenv('MDSO_SYSLOG_ENDPOINT')
MDSO_SYSLOG_ENDPOINT = "http://159.56.4.37/logarchive/api/v1/logs "
MDSO_USERNAME = os.getenv('MDSO_USERNAME')
MDSO_PASSWORD = os.getenv('MDSO_PASSWORD')
POLL_INTERVAL = int(os.getenv('MDSO_POLL_INTERVAL', '180'))
LOG_DIR = Path(os.getenv('POLLER_LOG_DIR', '/var/log/mdso'))
DEFAULT_PRODUCT_UUID = os.getenv('DEFAULT_PRODUCT_UUID', 'poc-server-124')
DEFAULT_SERVICE = os.getenv('DEFAULT_SERVICE_NAME', 'mdso-syslog')
DEFAULT_ENV = os.getenv('DEFAULT_ENVIRONMENT', 'dev')
BATCH_SIZE = int(os.getenv('POLLER_BATCH_SIZE', '1000'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/mdso-poller.log')
    ]
)
logger = logging.getLogger(__name__)

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)


class MDSOClient:
    """Client for MDSO API authentication and syslog retrieval"""

    def __init__(self):
        self.token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self.session = requests.Session()

    def authenticate(self) -> bool:
        """Authenticate with MDSO and get bearer token"""
        try:
            response = self.session.post(
                MDSO_AUTH_ENDPOINT,
                json={
                    'username': MDSO_USERNAME,
                    'password': MDSO_PASSWORD
                },
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            self.token = data.get('access_token') or data.get('token')
            # Token typically valid for 1 hour; refresh after 50 minutes
            self.token_expires = datetime.now() + timedelta(minutes=50)

            logger.info("✓ Authenticated with MDSO")
            return True

        except Exception as e:
            logger.error(f"✗ Authentication failed: {e}")
            return False

    def ensure_authenticated(self) -> bool:
        """Ensure we have a valid token"""
        if not self.token or not self.token_expires or datetime.now() >= self.token_expires:
            return self.authenticate()
        return True

    def fetch_syslogs(self, start_time: Optional[datetime] = None) -> Optional[bytes]:
        """
        Fetch syslog ZIP archive from MDSO
        Returns ZIP bytes or None on error
        """
        if not self.ensure_authenticated():
            return None

        # Default: last 5 minutes
        if not start_time:
            start_time = datetime.now() - timedelta(minutes=5)

        params = {
            'start_time': start_time.isoformat(),
            'format': 'zip'
        }

        try:
            response = self.session.get(
                MDSO_SYSLOG_ENDPOINT,
                headers={'Authorization': f'Bearer {self.token}'},
                params=params,
                timeout=30
            )
            response.raise_for_status()

            if response.headers.get('Content-Type', '').startswith('application/zip'):
                logger.info(f"✓ Fetched {len(response.content)} bytes (ZIP)")
                return response.content
            else:
                logger.warning(f"Unexpected content type: {response.headers.get('Content-Type')}")
                return None

        except Exception as e:
            logger.error(f"✗ Syslog fetch failed: {e}")
            return None


def synthesize_trace_id(log_line: str) -> str:
    """
    Generate deterministic trace_id from log content
    Useful for grouping related logs when no trace context exists
    """
    # Use first 32 chars of SHA256 hash (standard trace ID length)
    return hashlib.sha256(log_line.encode()).hexdigest()[:32]


def extract_trace_id(log_line: str) -> Optional[str]:
    """
    Attempt to extract trace_id from log line
    Looks for common patterns: trace_id=..., traceId:..., etc.
    """
    import re
    patterns = [
        r'trace_id[=:]([a-f0-9]{16,32})',
        r'traceId[=:]([a-f0-9]{16,32})',
        r'trace[=:]([a-f0-9]{16,32})',
    ]

    for pattern in patterns:
        match = re.search(pattern, log_line, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def normalize_log_line(raw_line: str, product_uuid: str, mdso_request_id: str) -> Dict:
    """
    Normalize syslog line to structured JSON with correlation fields
    """
    # Extract or synthesize trace_id
    trace_id = extract_trace_id(raw_line)
    if not trace_id:
        trace_id = synthesize_trace_id(raw_line)

    # Build structured log record
    return {
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'message': raw_line.strip(),
        'service': DEFAULT_SERVICE,
        'env': DEFAULT_ENV,
        'product_uuid': product_uuid,
        'mdso_request_id': mdso_request_id,
        'trace_id': trace_id,
        'source': 'mdso-syslog-api',
        'level': 'INFO',  # Default; could parse from syslog severity
    }


def process_zip_archive(zip_bytes: bytes) -> int:
    """
    Extract ZIP, normalize logs, write NDJSON
    Returns count of logs processed
    """
    today = datetime.now().strftime('%Y-%m-%d')
    output_file = LOG_DIR / f'syslog-{today}.ndjson'

    # Generate request ID for this batch
    mdso_request_id = f"mdso-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            log_count = 0

            with open(output_file, 'a', encoding='utf-8') as out:
                for filename in zf.namelist():
                    if not filename.endswith('.log') and not filename.endswith('.txt'):
                        continue

                    with zf.open(filename) as log_file:
                        for line in log_file:
                            try:
                                line_str = line.decode('utf-8', errors='ignore').strip()
                                if not line_str:
                                    continue

                                # Normalize to structured JSON
                                log_record = normalize_log_line(
                                    line_str,
                                    DEFAULT_PRODUCT_UUID,
                                    mdso_request_id
                                )

                                # Write NDJSON
                                out.write(json.dumps(log_record) + '\n')
                                log_count += 1

                            except Exception as e:
                                logger.warning(f"Failed to parse line: {e}")
                                continue

            logger.info(f"✓ Processed {log_count} logs → {output_file}")
            return log_count

    except Exception as e:
        logger.error(f"✗ ZIP processing failed: {e}")
        return 0


def main_loop():
    """Main polling loop"""
    client = MDSOClient()
    last_fetch_time = datetime.now() - timedelta(minutes=5)

    logger.info("=== MDSO Syslog Poller Started ===")
    logger.info(f"Polling interval: {POLL_INTERVAL}s")
    logger.info(f"Output directory: {LOG_DIR}")

    while True:
        try:
            # Fetch logs since last successful fetch
            zip_bytes = client.fetch_syslogs(start_time=last_fetch_time)

            if zip_bytes:
                count = process_zip_archive(zip_bytes)
                if count > 0:
                    last_fetch_time = datetime.now()
                    logger.info(f"✓ Batch complete: {count} logs ingested")
            else:
                logger.warning("No data received from MDSO")

        except KeyboardInterrupt:
            logger.info("Poller stopped by user")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main_loop()