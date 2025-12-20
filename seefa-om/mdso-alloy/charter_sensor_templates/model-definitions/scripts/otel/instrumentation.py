"""
instrumentation.py - Utility functions for OTel instrumentation

Provides standalone functions for products that don't inherit from OTelPlan
"""

import os
import json
import logging
import subprocess
import tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

# Try importing OpenTelemetry - gracefully degrade if not available
try:
    from opentelemetry import trace, baggage, context
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
    from opentelemetry.sdk.trace import ReadableSpan
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = baggage = context = None
    SpanExporter = object

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None


logger = logging.getLogger(__name__)

if not OTEL_AVAILABLE:
    logger.warning("OpenTelemetry not available - instrumentation will be disabled")

# Try importing Pyroscope
try:
    import pyroscope
    PYROSCOPE_AVAILABLE = True
except ImportError:
    PYROSCOPE_AVAILABLE = False
    logger.warning("Pyroscope not available")

# Default directory for file-based trace export (for isolated containers)
DEFAULT_TRACE_LOG_DIR = "/opt/ciena/bp2/alloy-collector"
DEFAULT_TRACE_LOG_FILE = "traces.ndjson"


def _get_otel_config(key: str, default_value=None, instance=None):
    """
    Get OTel configuration value from CommonPlan constants or environment variable.
    
    Priority:
    1. CommonPlan class constant (if instance is provided and has the attribute)
    2. Environment variable
    3. Default value
    
    Args:
        key: Configuration key name (e.g., "OTEL_EXPORT_MODE")
        default_value: Default value if not found
        instance: Optional instance of CommonPlan (or class with OTel constants)
    
    Returns:
        Configuration value
    """
    # Try to get from instance/class constants first
    if instance is not None:
        # Check if instance has the constant
        if hasattr(instance, key):
            value = getattr(instance, key)
            if value is not None:
                return value
        # Also check the class
        if hasattr(instance.__class__, key):
            value = getattr(instance.__class__, key)
            if value is not None:
                return value
    
    # Fall back to environment variable
    env_value = os.getenv(key, None)
    if env_value is not None:
        return env_value
    
    # Return default
    return default_value


if OTEL_AVAILABLE:
    class FileSpanExporter(SpanExporter):
        """
        File-based span exporter for isolated containers that can't reach Alloy agent.
    
        Writes OTLP traces as JSON lines (NDJSON) to a file that Alloy can tail.
        This is necessary when MDSO scripts run in isolated Docker networks managed
        by BluePlanet's solution manager.
        """
    
        def __init__(self, file_path: str, use_sudo: bool = None, instance=None):
            """
            Initialize file-based span exporter.
        
            Args:
                file_path: Path to the trace log file (e.g., /opt/ciena/bp2/alloy-collector/traces.ndjson)
                use_sudo: Whether to use sudo for file operations. If None, auto-detects based on permissions.
                instance: Optional CommonPlan instance to get constants from
            """
            self.file_path = Path(file_path)
            logger.info(f"FileSpanExporter: Initializing with file path: {self.file_path}")
            
            # Determine if sudo is needed
            if use_sudo is None:
                # Check CommonPlan constant or environment variable
                sudo_config = _get_otel_config("OTEL_USE_SUDO", None, instance)
                if sudo_config is not None:
                    if isinstance(sudo_config, bool):
                        use_sudo = sudo_config
                    elif isinstance(sudo_config, str):
                        use_sudo = sudo_config.lower() in ("true", "1", "yes")
                    else:
                        use_sudo = bool(sudo_config)
                else:
                    # Auto-detect: check if we can write to the directory
                    parent_dir = self.file_path.parent
                    if parent_dir.exists():
                        use_sudo = not os.access(parent_dir, os.W_OK)
                    else:
                        # Try to create directory first, if that fails we'll need sudo
                        try:
                            parent_dir.mkdir(parents=True, exist_ok=True)
                            use_sudo = False
                        except PermissionError:
                            use_sudo = True
                        except Exception:
                            use_sudo = True
            
            self.use_sudo = use_sudo
            logger.info(f"FileSpanExporter: Using sudo for file operations: {self.use_sudo}")
            
            # Check if parent directory exists and log its status
            parent_dir = self.file_path.parent
            if parent_dir.exists():
                logger.info(f"FileSpanExporter: Parent directory exists: {parent_dir}")
                # Check permissions
                if os.access(parent_dir, os.W_OK):
                    logger.info(f"FileSpanExporter: Parent directory is writable: {parent_dir}")
                else:
                    logger.warning(f"FileSpanExporter: Parent directory exists but is NOT writable: {parent_dir}")
                    if self.use_sudo:
                        logger.info(f"FileSpanExporter: Will use sudo to write to directory")
            else:
                logger.info(f"FileSpanExporter: Parent directory does not exist, creating: {parent_dir}")
            
            # Create directory if needed
            if self.use_sudo:
                try:
                    self._create_directory_with_sudo(parent_dir)
                    logger.info(f"FileSpanExporter: Directory created/verified with sudo: {self.file_path.parent}")
                except Exception as e:
                    logger.error(f"FileSpanExporter: Failed to create directory with sudo {self.file_path.parent}: {e}")
                    raise
            else:
                try:
                    self.file_path.parent.mkdir(parents=True, exist_ok=True)
                    logger.info(f"FileSpanExporter: Directory created/verified: {self.file_path.parent}")
                except Exception as e:
                    logger.error(f"FileSpanExporter: Failed to create directory {self.file_path.parent}: {e}")
                    # Try with sudo as fallback
                    logger.info(f"FileSpanExporter: Attempting to create directory with sudo as fallback")
                    try:
                        self._create_directory_with_sudo(parent_dir)
                        self.use_sudo = True
                        logger.info(f"FileSpanExporter: Directory created with sudo, enabling sudo mode")
                    except Exception as sudo_error:
                        logger.error(f"FileSpanExporter: Failed to create directory with sudo: {sudo_error}")
                        raise
            
            # Check directory permissions after creation
            if parent_dir.exists():
                stat_info = os.stat(parent_dir)
                logger.info(f"FileSpanExporter: Directory permissions - mode: {oct(stat_info.st_mode)}, uid: {stat_info.st_uid}, gid: {stat_info.st_gid}")
            
            self.file_handle = None
            self._pending_writes = []  # Buffer for sudo writes
            if not self.use_sudo:
                self._open_file()
            else:
                logger.info(f"FileSpanExporter: Skipping direct file open, will use sudo for writes")
    
        def _create_directory_with_sudo(self, directory: Path):
            """Create directory using sudo"""
            try:
                cmd = ["sudo", "mkdir", "-p", str(directory)]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    raise Exception(f"sudo mkdir failed: {result.stderr}")
                logger.info(f"FileSpanExporter: Created directory with sudo: {directory}")
            except subprocess.TimeoutExpired:
                raise Exception("sudo mkdir timed out")
            except FileNotFoundError:
                raise Exception("sudo command not found")
            except Exception as e:
                raise Exception(f"Failed to create directory with sudo: {e}")
        
        def _open_file(self):
            """Open file in append mode"""
            try:
                # Check if file exists before opening
                file_exists = self.file_path.exists()
                if file_exists:
                    file_size = self.file_path.stat().st_size
                    logger.info(f"FileSpanExporter: Opening existing file: {self.file_path} (size: {file_size} bytes)")
                else:
                    logger.info(f"FileSpanExporter: Creating new file: {self.file_path}")
                
                self.file_handle = open(self.file_path, "a", encoding="utf-8")
                logger.info(f"FileSpanExporter: Successfully opened file handle: {self.file_path}")
                
                # Log file permissions
                if self.file_path.exists():
                    stat_info = self.file_path.stat()
                    logger.info(f"FileSpanExporter: File permissions - mode: {oct(stat_info.st_mode)}, uid: {stat_info.st_uid}, gid: {stat_info.st_gid}, size: {stat_info.st_size} bytes")
                
            except PermissionError as e:
                logger.error(f"FileSpanExporter: Permission denied opening file {self.file_path}: {e}")
                logger.error(f"FileSpanExporter: Current user: {os.getuid()}, Current group: {os.getgid()}")
                raise
            except Exception as e:
                logger.error(f"FileSpanExporter: Failed to open trace log file {self.file_path}: {e}", exc_info=True)
                raise
        
        def _write_with_sudo(self, content: str):
            """Write content to file using sudo tee"""
            try:
                # Use sudo tee -a to append to file
                cmd = ["sudo", "tee", "-a", str(self.file_path)]
                result = subprocess.run(
                    cmd,
                    input=content,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    logger.error(f"FileSpanExporter: sudo tee failed: {result.stderr}")
                    return False
                return True
            except subprocess.TimeoutExpired:
                logger.error(f"FileSpanExporter: sudo tee timed out")
                return False
            except FileNotFoundError:
                logger.error(f"FileSpanExporter: sudo command not found")
                return False
            except Exception as e:
                logger.error(f"FileSpanExporter: Failed to write with sudo: {e}")
                return False
    
        def export(self, spans) -> SpanExportResult:
            """
            Export spans to file as JSON lines.
        
            Each span is written as a single JSON line (NDJSON format).
            Uses sudo if configured or if permission denied.
            """
            if not spans:
                logger.debug(f"FileSpanExporter: export() called with empty spans list")
                return SpanExportResult.SUCCESS
        
            num_spans = len(spans)
            logger.info(f"FileSpanExporter: Exporting {num_spans} span(s) to {self.file_path} (sudo={self.use_sudo})")
            
            # Get file size before write
            try:
                file_size_before = self.file_path.stat().st_size if self.file_path.exists() else 0
            except Exception:
                file_size_before = 0
            
            try:
                if self.use_sudo:
                    # Use sudo for writing
                    return self._export_with_sudo(spans, num_spans, file_size_before)
                else:
                    # Use direct file writing
                    if self.file_handle is None or self.file_handle.closed:
                        logger.warning(f"FileSpanExporter: File handle is None or closed, reopening file: {self.file_path}")
                        try:
                            self._open_file()
                        except PermissionError:
                            logger.warning(f"FileSpanExporter: Permission denied, falling back to sudo")
                            self.use_sudo = True
                            return self._export_with_sudo(spans, num_spans, file_size_before)
                    
                    bytes_written = 0
                    for idx, span in enumerate(spans):
                        # Convert span to OTLP-compatible JSON format
                        span_data = self._span_to_dict(span)
                        json_line = json.dumps(span_data, default=str)
                        line_bytes = self.file_handle.write(json_line + "\n")
                        bytes_written += line_bytes
                        logger.debug(f"FileSpanExporter: Wrote span {idx+1}/{num_spans} ({span.name}) - {line_bytes} bytes")
                
                    # Flush to ensure data is written
                    self.file_handle.flush()
                    
                    # Get file size after write
                    try:
                        file_size_after = self.file_path.stat().st_size if self.file_path.exists() else 0
                        bytes_added = file_size_after - file_size_before
                    except Exception:
                        file_size_after = file_size_before
                        bytes_added = 0
                    
                    logger.info(f"FileSpanExporter: Successfully exported {num_spans} span(s) - wrote {bytes_written} bytes, file size: {file_size_before} -> {file_size_after} bytes (+{bytes_added})")
                    return SpanExportResult.SUCCESS
            except PermissionError as e:
                logger.warning(f"FileSpanExporter: Permission denied, falling back to sudo: {e}")
                self.use_sudo = True
                return self._export_with_sudo(spans, num_spans, file_size_before)
            except Exception as e:
                logger.error(f"FileSpanExporter: Failed to export {num_spans} span(s) to file {self.file_path}: {e}", exc_info=True)
                return SpanExportResult.FAILURE
        
        def _export_with_sudo(self, spans, num_spans, file_size_before) -> SpanExportResult:
            """Export spans using sudo"""
            try:
                # Build all lines to write
                lines_to_write = []
                for idx, span in enumerate(spans):
                    span_data = self._span_to_dict(span)
                    json_line = json.dumps(span_data, default=str)
                    lines_to_write.append(json_line)
                    logger.debug(f"FileSpanExporter: Prepared span {idx+1}/{num_spans} ({span.name}) for sudo write")
                
                # Combine all lines
                content = "\n".join(lines_to_write) + "\n"
                bytes_to_write = len(content.encode('utf-8'))
                
                # Write using sudo
                logger.info(f"FileSpanExporter: Writing {num_spans} span(s) using sudo ({bytes_to_write} bytes)")
                if self._write_with_sudo(content):
                    # Get file size after write
                    try:
                        file_size_after = self.file_path.stat().st_size if self.file_path.exists() else 0
                        bytes_added = file_size_after - file_size_before
                    except Exception:
                        file_size_after = file_size_before
                        bytes_added = bytes_to_write
                    
                    logger.info(f"FileSpanExporter: Successfully exported {num_spans} span(s) with sudo - wrote {bytes_to_write} bytes, file size: {file_size_before} -> {file_size_after} bytes (+{bytes_added})")
                    return SpanExportResult.SUCCESS
                else:
                    logger.error(f"FileSpanExporter: Failed to write {num_spans} span(s) with sudo")
                    return SpanExportResult.FAILURE
            except Exception as e:
                logger.error(f"FileSpanExporter: Error in _export_with_sudo: {e}", exc_info=True)
                return SpanExportResult.FAILURE
    
        def _span_to_dict(self, span: ReadableSpan) -> Dict[str, Any]:
            """
            Convert OpenTelemetry span to OTLP-compatible dictionary.
        
            Format matches what Alloy's filelog receiver expects for OTLP traces.
            """
            # Get trace context
            trace_id = format(span.context.trace_id, "032x")
            span_id = format(span.context.span_id, "016x")
        
            # Convert attributes
            attributes = {}
            for key, value in span.attributes.items():
                if isinstance(value, (str, int, float, bool)):
                    attributes[key] = value
                else:
                    attributes[key] = str(value)
        
            # Get resource attributes
            resource_attributes = {}
            if span.resource:
                for key, value in span.resource.attributes.items():
                    if isinstance(value, (str, int, float, bool)):
                        resource_attributes[key] = value
                    else:
                        resource_attributes[key] = str(value)
        
            # Build OTLP-compatible structure
            span_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
                "span_id": span_id,
                "name": span.name,
                "kind": span.kind.name if hasattr(span.kind, "name") else str(span.kind),
                "start_time": span.start_time,
                "end_time": span.end_time if span.end_time else None,
                "duration_ns": (span.end_time - span.start_time) if span.end_time else None,
                "status": {
                    "code": span.status.status_code.name if hasattr(span.status.status_code, "name") else str(span.status.status_code),
                    "message": span.status.description if span.status.description else None,
                },
                "attributes": attributes,
                "resource": resource_attributes,
                "events": [
                    {
                        "name": event.name,
                        "timestamp": event.timestamp,
                        "attributes": dict(event.attributes) if hasattr(event, "attributes") else {},
                    }
                    for event in span.events
                ],
            }
        
            return span_data
    
        def shutdown(self):
            """Close file handle"""
            if self.file_handle:
                try:
                    self.file_handle.close()
                except Exception as e:
                    logger.error(f"Error closing trace log file: {e}")
    
        def force_flush(self, timeout_millis: int = 30000) -> bool:
            """Flush file buffer"""
            try:
                if self.use_sudo:
                    # For sudo mode, writes are immediate, nothing to flush
                    logger.debug(f"FileSpanExporter: force_flush called in sudo mode (no-op)")
                    return True
                elif self.file_handle:
                    self.file_handle.flush()
                    return True
                return True
            except Exception as e:
                logger.error(f"Error flushing trace log file: {e}")
                return False


else:
    class FileSpanExporter:
        def __init__(self, *args, **kwargs): pass
        def export(self, *args, **kwargs): return None
        def shutdown(self): pass
        def force_flush(self, *args, **kwargs): return True

def setup_otel(
    service_name: str = "mdso-scriptplan",
    endpoint: str = None,
    environment: str = "dev",
    version: str = "1.0.0",
    use_file_export: Optional[bool] = None,
    trace_log_dir: str = None,
    instance: Optional[Any] = None
) -> Optional[Any]:  # Returns trace.Tracer when OTEL available
    """
    Setup OpenTelemetry tracer for MDSO scriptplan

    Architecture (Two Modes):
    
    Mode 1: Direct OTLP (when containers can reach Alloy agent)
        MDSO Scripts → Alloy Agent (localhost:4318) → Meta Server (159.56.4.94:55681)
        
    Mode 2: File-based (for isolated containers in BluePlanet solution manager)
        MDSO Scripts → Write to /opt/ciena/bp2/alloy-collector/traces.ndjson
        Alloy Agent → Tails file → Meta Server (159.56.4.94:55681)
        
    The function auto-detects the mode based on:
    - OTEL_EXPORT_MODE env var: "file" or "otlp" (default: auto-detect)
    - Network connectivity to Alloy agent (if auto-detect)
    - use_file_export parameter (explicit override)

    Args:
        service_name: Service name for resource attributes
        endpoint: OTLP exporter endpoint (only used in OTLP mode)
        environment: Deployment environment (dev/staging/prod)
        version: Service version
        use_file_export: Force file-based export (True) or OTLP (False). None = auto-detect
        trace_log_dir: Directory for trace log files (default: /opt/ciena/bp2/alloy-collector)
        instance: Optional CommonPlan instance to get constants from

    Returns:
        Configured tracer instance

    Example:
        >>> tracer = setup_otel("mdso-scriptplan", environment="dev")
        >>> with tracer.start_as_current_span("my_operation") as span:
        ...     span.set_attribute("circuit_id", "123-456")
        ...     # ... do work ...
    """
    if not OTEL_AVAILABLE:
        return None
    
    # Determine export mode from CommonPlan constant or environment variable
    export_mode_config = _get_otel_config("OTEL_EXPORT_MODE", "", instance)
    export_mode = export_mode_config.lower() if export_mode_config else ""
    logger.info(f"setup_otel: Export mode detection - OTEL_EXPORT_MODE: '{export_mode_config or 'not set'}', use_file_export parameter: {use_file_export}")
    
    if use_file_export is None:
        # Auto-detect: prefer file mode if explicitly set, or if in isolated container
        if export_mode == "file":
            use_file_export = True
            logger.info("setup_otel: Export mode explicitly set to 'file' via OTEL_EXPORT_MODE environment variable")
        elif export_mode == "otlp":
            use_file_export = False
            logger.info("setup_otel: Export mode explicitly set to 'otlp' via OTEL_EXPORT_MODE environment variable")
        else:
            # Auto-detect: try to connect to Alloy agent
            # If we're in an isolated container, localhost:4318 won't be reachable
            # Default to file mode for safety (works in all scenarios)
            use_file_export = True  # Default to file mode for isolated containers
            logger.info("setup_otel: Auto-detecting export mode: defaulting to file-based (safe for isolated containers)")
            logger.info("setup_otel: No OTEL_EXPORT_MODE set, and use_file_export=None, so defaulting to file mode")
    else:
        logger.info(f"setup_otel: Export mode explicitly set via use_file_export parameter: {use_file_export}")
    
    # Create resource with service metadata
    resource = Resource.create({
        "service.name": service_name,
        "service.version": version,
        "deployment.environment": environment,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
        "telemetry.sdk.version": "1.20.0",
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    if use_file_export:
        # File-based export for isolated containers
        trace_log_dir = trace_log_dir or _get_otel_config(
            "OTEL_TRACE_LOG_DIR", 
            DEFAULT_TRACE_LOG_DIR,
            instance
        )
        trace_log_file = os.path.join(trace_log_dir, DEFAULT_TRACE_LOG_FILE)
        
        logger.info(f"setup_otel: Using file-based trace export mode")
        logger.info(f"setup_otel: Trace log directory: {trace_log_dir}")
        logger.info(f"setup_otel: Trace log file: {trace_log_file}")
        trace_log_dir_config = _get_otel_config("OTEL_TRACE_LOG_DIR", "not set", instance)
        logger.info(f"setup_otel: OTEL_TRACE_LOG_DIR config: {trace_log_dir_config}")
        logger.info("setup_otel: This mode is required for isolated containers that cannot reach Alloy agent")
        
        # Verify directory exists and is writable before creating exporter
        trace_log_dir_path = Path(trace_log_dir)
        if trace_log_dir_path.exists():
            logger.info(f"setup_otel: Trace log directory exists: {trace_log_dir_path}")
            if os.access(trace_log_dir_path, os.W_OK):
                logger.info(f"setup_otel: Trace log directory is writable: {trace_log_dir_path}")
            else:
                logger.warning(f"setup_otel: Trace log directory exists but is NOT writable: {trace_log_dir_path}")
        else:
            logger.info(f"setup_otel: Trace log directory does not exist, will be created: {trace_log_dir_path}")
        
        # Check if sudo should be used from CommonPlan constant or environment variable
        use_sudo_config = _get_otel_config("OTEL_USE_SUDO", None, instance)
        use_sudo = None
        if use_sudo_config is not None:
            if isinstance(use_sudo_config, bool):
                use_sudo = use_sudo_config
            elif isinstance(use_sudo_config, str):
                use_sudo = use_sudo_config.lower() in ("true", "1", "yes")
            else:
                use_sudo = bool(use_sudo_config)
        if use_sudo:
            logger.info(f"setup_otel: OTEL_USE_SUDO is set, will use sudo for file operations")
        
        logger.info(f"setup_otel: Creating FileSpanExporter instance for: {trace_log_file}")
        file_exporter = FileSpanExporter(trace_log_file, use_sudo=use_sudo, instance=instance)
        logger.info(f"setup_otel: FileSpanExporter created successfully (sudo={file_exporter.use_sudo})")
        
        logger.info(f"setup_otel: Creating BatchSpanProcessor with max_queue_size=2048, max_export_batch_size=512, schedule_delay_millis=5000")
        processor = BatchSpanProcessor(
            file_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
        logger.info(f"setup_otel: BatchSpanProcessor created successfully")
        export_info = f"file:{trace_log_file}"
    else:
        # Direct OTLP export to Alloy agent
        endpoint = endpoint or _get_otel_config(
            "OTEL_EXPORTER_OTLP_ENDPOINT", 
            "http://localhost:4318",  # Alloy OTLP HTTP receiver
            instance
        )
        
        logger.info(f"setup_otel: Using direct OTLP export mode")
        logger.info(f"setup_otel: OTLP endpoint: {endpoint}")
        otlp_endpoint_config = _get_otel_config("OTEL_EXPORTER_OTLP_ENDPOINT", "not set", instance)
        logger.info(f"setup_otel: OTEL_EXPORTER_OTLP_ENDPOINT config: {otlp_endpoint_config}")
        logger.warning(f"setup_otel: WARNING - Using OTLP mode instead of file mode. If scripts are in isolated containers, this may fail!")
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=f"{endpoint}/v1/traces",
            timeout=30,
        )
        logger.info(f"setup_otel: OTLPSpanExporter created for endpoint: {endpoint}/v1/traces")
        
        processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
        logger.info(f"setup_otel: BatchSpanProcessor created successfully for OTLP export")
        export_info = f"otlp:{endpoint}"

    # Add processor to provider
    logger.info(f"setup_otel: Adding span processor to TracerProvider")
    provider.add_span_processor(processor)
    logger.info(f"setup_otel: Span processor added successfully")

    # Set global tracer provider
    logger.info(f"setup_otel: Setting global tracer provider")
    trace.set_tracer_provider(provider)
    logger.info(f"setup_otel: Global tracer provider set successfully")

    logger.info(f"setup_otel: OTel initialization complete - service={service_name}, export={export_info}, env={environment}")
    
    # If using file export, verify the file is writable
    if use_file_export:
        trace_log_file = os.path.join(
            trace_log_dir or _get_otel_config("OTEL_TRACE_LOG_DIR", DEFAULT_TRACE_LOG_DIR, instance),
            DEFAULT_TRACE_LOG_FILE
        )
        trace_log_path = Path(trace_log_file)
        if trace_log_path.exists():
            try:
                # Try to write a test byte to verify writability
                with open(trace_log_path, "a") as test_file:
                    test_file.write("")
                logger.info(f"setup_otel: Verified trace log file is writable: {trace_log_file}")
            except Exception as e:
                logger.error(f"setup_otel: WARNING - Trace log file exists but is NOT writable: {trace_log_file}, error: {e}")

    return trace.get_tracer(__name__)


def test_file_export(trace_log_dir: str = None, instance: Optional[Any] = None) -> Dict[str, Any]:
    """
    Diagnostic function to test file-based trace export.
    
    Creates a test span and verifies it can be written to the trace log file.
    Useful for debugging why logs aren't appearing in /opt/ciena/bp2/alloy-collector.
    
    Args:
        trace_log_dir: Directory for trace log files (default: /opt/ciena/bp2/alloy-collector)
        instance: Optional CommonPlan instance to get constants from
    
    Returns:
        Dictionary with test results including success status, file path, and any errors
    
    Example:
        >>> result = test_file_export()
        >>> print(result)
        {'success': True, 'file_path': '/opt/ciena/bp2/alloy-collector/traces.ndjson', ...}
    """
    result = {
        "success": False,
        "file_path": None,
        "error": None,
        "file_exists": False,
        "file_writable": False,
        "file_size": 0,
        "test_span_written": False
    }
    
    if not OTEL_AVAILABLE:
        result["error"] = "OpenTelemetry not available"
        logger.error(f"test_file_export: {result['error']}")
        return result
    
    try:
        # Determine file path from CommonPlan constant or environment variable
        trace_log_dir = trace_log_dir or _get_otel_config("OTEL_TRACE_LOG_DIR", DEFAULT_TRACE_LOG_DIR, instance)
        trace_log_file = os.path.join(trace_log_dir, DEFAULT_TRACE_LOG_FILE)
        result["file_path"] = trace_log_file
        
        logger.info(f"test_file_export: Testing file export to: {trace_log_file}")
        
        # Check directory
        trace_log_path = Path(trace_log_file)
        parent_dir = trace_log_path.parent
        
        if not parent_dir.exists():
            logger.warning(f"test_file_export: Parent directory does not exist: {parent_dir}")
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"test_file_export: Created parent directory: {parent_dir}")
            except Exception as e:
                result["error"] = f"Failed to create directory: {e}"
                logger.error(f"test_file_export: {result['error']}")
                return result
        
        # Check if file exists
        result["file_exists"] = trace_log_path.exists()
        if result["file_exists"]:
            result["file_size"] = trace_log_path.stat().st_size
            logger.info(f"test_file_export: File exists, current size: {result['file_size']} bytes")
        else:
            logger.info(f"test_file_export: File does not exist, will be created")
        
        # Test file writability
        try:
            with open(trace_log_path, "a") as test_file:
                test_file.write("")
            result["file_writable"] = True
            logger.info(f"test_file_export: File is writable")
        except Exception as e:
            result["error"] = f"File is not writable: {e}"
            logger.error(f"test_file_export: {result['error']}")
            return result
        
        # Create a test span using the tracer
        logger.info(f"test_file_export: Setting up test tracer with file export")
        test_tracer = setup_otel(
            service_name="test-file-export",
            environment="test",
            use_file_export=True,
            trace_log_dir=trace_log_dir,
            instance=instance
        )
        
        if test_tracer is None:
            result["error"] = "Failed to create test tracer"
            logger.error(f"test_file_export: {result['error']}")
            return result
        
        # Create and export a test span
        logger.info(f"test_file_export: Creating test span")
        with test_tracer.start_as_current_span("test_file_export_span") as span:
            span.set_attribute("test", True)
            span.set_attribute("timestamp", datetime.now(timezone.utc).isoformat())
            span.set_status(trace.Status(trace.StatusCode.OK))
            logger.info(f"test_file_export: Test span created: {span.name}, trace_id: {format(span.get_span_context().trace_id, '032x')}")
        
        # Force flush the span processor
        logger.info(f"test_file_export: Flushing span processor to ensure spans are written")
        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            try:
                provider.force_flush(timeout_millis=5000)
                logger.info(f"test_file_export: Span processor flushed successfully")
            except Exception as e:
                logger.warning(f"test_file_export: Failed to flush span processor: {e}")
        
        # Also try to get the processor and flush it directly
        if hasattr(provider, "_span_processors"):
            for processor in provider._span_processors:
                if hasattr(processor, "force_flush"):
                    try:
                        processor.force_flush(timeout_millis=5000)
                        logger.info(f"test_file_export: Flushed individual span processor")
                    except Exception as e:
                        logger.warning(f"test_file_export: Failed to flush individual processor: {e}")
        
        # Check if file was written to
        if trace_log_path.exists():
            new_file_size = trace_log_path.stat().st_size
            if new_file_size > result["file_size"]:
                result["test_span_written"] = True
                result["file_size"] = new_file_size
                logger.info(f"test_file_export: Test span written successfully, file size: {result['file_size']} bytes")
            else:
                logger.warning(f"test_file_export: File size did not increase after writing test span")
        
        result["success"] = True
        logger.info(f"test_file_export: Test completed successfully")
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"test_file_export: Test failed with error: {e}", exc_info=True)
    
    return result


def get_otel_logger(service_name: str = "mdso-scriptplan") -> Optional[Any]:  # Returns structlog.BoundLogger when available
    """
    Get structured logger for OTel-compatible logging

    Automatically includes trace context (trace_id, span_id) and baggage
    (circuit_id, resource_id, etc.) in all log entries.

    Args:
        service_name: Service name to bind to logger

    Returns:
        Structured logger instance

    Example:
        >>> logger = get_otel_logger("mdso-scriptplan")
        >>> logger.info("Processing started", circuit_id="123", resource_id="456")
    """
    if not OTEL_AVAILABLE:
        return None
    
    # Configure structlog with trace context enhancement
    def add_trace_context(logger, method_name, event_dict):
        """Add trace_id, span_id, and baggage to logs automatically"""
        # Add trace context from current span
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
            event_dict["trace_flags"] = format(ctx.trace_flags, "02x")

        # Add baggage (correlation keys) to logs
        correlation_keys = ["circuit_id", "product_id", "resource_id", "resource_type_id"]
        for key in correlation_keys:
            value = baggage.get_baggage(key)
            if value:
                event_dict[key] = value

        return event_dict

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Merge contextvars (if set)
            add_trace_context,  # Add trace context and baggage
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create bound logger with service context
    return structlog.get_logger(service_name)


def otel_enter_exit_log(
    message: str,
    state: str = "STARTED",
    tracer = None,
    **context: Any
):
    """
    Standalone enter_exit_log function for products that don't inherit OTelPlan

    Emits structured log and optional span event.

    Args:
        message: Log message
        state: Process state (STARTED, COMPLETED, FAILED)
        tracer: Optional tracer instance (will use global if not provided)
        **context: Additional context fields (circuit_id, resource_id, etc.)

    Example:
        >>> otel_enter_exit_log("Starting provisioning", "STARTED",
        ...                     circuit_id="123", resource_id="456")
        >>> # ... do work ...
        >>> otel_enter_exit_log("Provisioning complete", "COMPLETED",
        ...                     circuit_id="123", resource_id="456")
    """
    if not OTEL_AVAILABLE:
        return
    
    logger = get_otel_logger()

    # Determine log level
    if state == "FAILED":
        log_level = "error"
    elif state == "COMPLETED":
        log_level = "info"
    else:
        log_level = "debug"

    # Emit structured log
    getattr(logger, log_level)(message, state=state, **context)

    # Add span event if we have a current span
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(
            name=f"process.{state.lower()}",
            attributes={
                "message": message,
                "state": state,
                **context
            }
        )


def inject_correlation_context(
    circuit_id: Optional[str] = None,
    product_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type_id: Optional[str] = None,
) -> Dict[str, str]:
    """
    Inject correlation keys into current trace context

    Sets:
    1. Span attributes (for trace correlation)
    2. Baggage (for cross-service propagation)
    3. Structlog contextvars (for automatic log inclusion)

    Args:
        circuit_id: Circuit identifier
        product_id: Product identifier
        resource_id: Resource identifier
        resource_type_id: Resource type identifier

    Returns:
        Dictionary of injected context

    Example:
        >>> inject_correlation_context(
        ...     circuit_id="550e8400-e29b-41d4-a716-446655440000",
        ...     resource_id="7c9e6679-7425-40de-944b-e07fc1f90ae7"
        ... )
    """
    if not OTEL_AVAILABLE:
        return {}
    
    # Get current span
    span = trace.get_current_span()

    # Collect context to inject
    correlation_context = {}

    # Set span attributes
    if span and span.is_recording():
        if circuit_id:
            span.set_attribute("circuit_id", circuit_id)
            correlation_context["circuit_id"] = circuit_id
        if product_id:
            span.set_attribute("product_id", product_id)
            correlation_context["product_id"] = product_id
        if resource_id:
            span.set_attribute("resource_id", resource_id)
            correlation_context["resource_id"] = resource_id
        if resource_type_id:
            span.set_attribute("resource_type_id", resource_type_id)
            correlation_context["resource_type_id"] = resource_type_id

    # Set baggage for propagation
    ctx = context.get_current()
    if circuit_id:
        ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
    if product_id:
        ctx = baggage.set_baggage("product_id", product_id, context=ctx)
    if resource_id:
        ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)
    if resource_type_id:
        ctx = baggage.set_baggage("resource_type_id", resource_type_id, context=ctx)

    context.attach(ctx)

    # Set structlog contextvars (for automatic inclusion in logs)
    # These will be merged by merge_contextvars processor
    if circuit_id:
        structlog.contextvars.bind_contextvars(circuit_id=circuit_id)
    if product_id:
        structlog.contextvars.bind_contextvars(product_id=product_id)
    if resource_id:
        structlog.contextvars.bind_contextvars(resource_id=resource_id)
    if resource_type_id:
        structlog.contextvars.bind_contextvars(resource_type_id=resource_type_id)

    return correlation_context


def extract_correlation_context() -> Dict[str, Optional[str]]:
    """
    Extract correlation keys from current baggage and contextvars

    Returns:
        Dictionary with correlation keys (may contain None values)

    Example:
        >>> context = extract_correlation_context()
        >>> print(context["circuit_id"])
        550e8400-e29b-41d4-a716-446655440000
    """
    if not OTEL_AVAILABLE:
        return {}
    
    # Extract from baggage (OTel propagation)
    baggage_context = {}
    for key in ["circuit_id", "product_id", "resource_id", "resource_type_id"]:
        value = baggage.get_baggage(key)
        # Only include non-None values
        if value is not None:
            baggage_context[key] = value
    
    # Also check structlog contextvars (local context) - fills in missing values
    try:
        contextvars_dict = structlog.contextvars.get_contextvars()
        for key in ["circuit_id", "product_id", "resource_id", "resource_type_id"]:
            # Only use contextvar if baggage doesn't have it (baggage takes precedence)
            if key not in baggage_context and key in contextvars_dict:
                value = contextvars_dict[key]
                if value is not None:
                    baggage_context[key] = value
    except Exception:
        pass  # Contextvars may not be available
    
    return baggage_context


def clear_correlation_context():
    """
    Clear all correlation context (baggage and contextvars)
    
    Useful when starting a new operation that shouldn't inherit context.
    
    Example:
        >>> clear_correlation_context()
        >>> # Start fresh operation
    """
    if not OTEL_AVAILABLE:
        return
    
    from opentelemetry import context
    
    # Clear baggage
    ctx = context.get_current()
    for key in ["circuit_id", "product_id", "resource_id", "resource_type_id"]:
        ctx = baggage.set_baggage(key, None, context=ctx)
    context.attach(ctx)
    
    # Clear structlog contextvars
    structlog.contextvars.clear_contextvars()


def create_mdso_span(
    name: str,
    kind = None,  # trace.SpanKind.INTERNAL when OTEL available
    attributes: Optional[Dict[str, Any]] = None,
    tracer: Optional[Any] = None
) -> Optional[Any]:  # Returns trace.Span when OTEL available
    """
    Create a span with MDSO-specific attributes

    Args:
        name: Span name (e.g., "mdso.product.CircuitDetailsCollector")
        kind: Span kind (INTERNAL, CLIENT, SERVER, etc.)
        attributes: Additional attributes
        tracer: Optional tracer (uses global if not provided)

    Returns:
        Started span (remember to call .end()!)

    Example:
        >>> span = create_mdso_span(
        ...     "mdso.product.ServiceProvisioner",
        ...     attributes={"circuit_id": "123", "vendor": "JUNIPER"}
        ... )
        >>> try:
        ...     # ... do work ...
        ...     span.set_status(trace.Status(trace.StatusCode.OK))
        ... except Exception as e:
        ...     span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        ...     raise
        ... finally:
        ...     span.end()
    """
    if not OTEL_AVAILABLE:
        return None
    
    if tracer is None:
        tracer = trace.get_tracer(__name__)

    # Merge with default MDSO attributes
    span_attributes = {
        "mdso.component": "scriptplan",
        **(attributes or {})
    }

    return tracer.start_span(
        name=name,
        kind=kind,
        attributes=span_attributes
    )


# Context manager for easier span usage
class mdso_span:
    """
    Context manager for MDSO spans

    Example:
        >>> with mdso_span("mdso.product.DeviceOnboarder", circuit_id="123") as span:
        ...     # ... do work ...
        ...     span.set_attribute("device_count", 5)
    """

    def __init__(
        self,
        name: str,
        kind = None,  # trace.SpanKind.INTERNAL when OTEL available
        **attributes: Any
    ):
        self.name = name
        self.kind = kind
        self.attributes = attributes
        self.span = None

    def __enter__(self) -> Optional[Any]:  # Returns trace.Span when OTEL available
        self.span = create_mdso_span(
            name=self.name,
            kind=self.kind,
            attributes=self.attributes
        )
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_type is not None:
                if OTEL_AVAILABLE and self.span:
                    self.span.set_status(
                        trace.Status(trace.StatusCode.ERROR, str(exc_val))
                    )
            else:
                if OTEL_AVAILABLE and self.span:
                    self.span.set_status(trace.Status(trace.StatusCode.OK))
            self.span.end()
        return False  # Don't suppress exceptions


# ========================================
# MDSO-Specific Helper Functions (using otel_mdso_utils)
# ========================================

def create_topology_span(
    circuit_id: str,
    operation: str = "fetch",
    tracer: Optional[Any] = None
) -> Optional[Any]:  # Returns trace.Span when OTEL available
    """
    Create a span for Beorn topology operations using MDSOSpanHelper
    
    Args:
        circuit_id: Circuit identifier
        operation: Operation type (fetch, parse, validate)
        tracer: Optional tracer (uses global if not provided)
    
    Returns:
        Active span (remember to call .end()!)
    
    Example:
        >>> from otel.instrumentation import create_topology_span
        >>> span = create_topology_span("123-456", "fetch")
        >>> try:
        ...     # ... fetch topology ...
        ...     span.set_status(trace.Status(trace.StatusCode.OK))
        ... finally:
        ...     span.end()
    """
    from otel.otel_mdso_utils import MDSOSpanHelper
    
    if tracer is None:
        tracer = trace.get_tracer(__name__)
    
    return MDSOSpanHelper.create_topology_span(tracer, circuit_id, operation)


def create_network_function_span(
    tid: str,
    fqdn: Optional[str] = None,
    operation: str = "check",
    tracer: Optional[Any] = None
) -> Optional[Any]:  # Returns trace.Span when OTEL available
    """
    Create a span for network function operations using MDSOSpanHelper
    
    Args:
        tid: Device TID
        fqdn: Device FQDN (optional)
        operation: Operation type (check, query, validate)
        tracer: Optional tracer (uses global if not provided)
    
    Returns:
        Active span (remember to call .end()!)
    
    Example:
        >>> from otel.instrumentation import create_network_function_span
        >>> span = create_network_function_span("TID123", "device.example.com", "check")
        >>> try:
        ...     # ... check device ...
        ...     span.set_status(trace.Status(trace.StatusCode.OK))
        ... finally:
        ...     span.end()
    """
    from otel.otel_mdso_utils import MDSOSpanHelper
    
    if tracer is None:
        tracer = trace.get_tracer(__name__)
    
    return MDSOSpanHelper.create_network_function_span(tracer, tid, fqdn, operation)


def add_topology_attributes(
    span,
    service_type: Optional[str] = None,
    vendor: Optional[str] = None,
    fqdn: Optional[str] = None,
    topology_node_count: Optional[int] = None,
    validation_status: Optional[bool] = None,
):
    """
    Add Beorn topology-specific attributes to a span using MDSOSpanHelper
    
    Args:
        span: Active OTEL span
        service_type: Service type (FIA, ELAN, ELINE, etc.)
        vendor: Device vendor (adva, juniper, cisco, rad)
        fqdn: Device FQDN
        topology_node_count: Number of nodes in topology
        validation_status: Whether topology validation passed
    
    Example:
        >>> from opentelemetry import trace
        >>> span = trace.get_current_span()
        >>> add_topology_attributes(
        ...     span,
        ...     service_type="FIA",
        ...     vendor="juniper",
        ...     topology_node_count=5,
        ...     validation_status=True
        ... )
    """
    from otel.otel_mdso_utils import MDSOSpanHelper
    
    MDSOSpanHelper.add_topology_attributes(
        span=span,
        service_type=service_type,
        vendor=vendor,
        fqdn=fqdn,
        topology_node_count=topology_node_count,
        validation_status=validation_status
    )


def add_network_function_attributes(
    span,
    communication_state: Optional[str] = None,
    ip_address: Optional[str] = None,
    vendor: Optional[str] = None,
    device_role: Optional[str] = None,
    provider_resource_id: Optional[str] = None,
):
    """
    Add network function-specific attributes to a span using MDSOSpanHelper
    
    Args:
        span: Active OTEL span
        communication_state: Device communication state
        ip_address: Device IP address
        vendor: Device vendor
        device_role: Device role (CPE, PE)
        provider_resource_id: MDSO provider resource ID
    
    Example:
        >>> from opentelemetry import trace
        >>> span = trace.get_current_span()
        >>> add_network_function_attributes(
        ...     span,
        ...     communication_state="reachable",
        ...     ip_address="10.0.0.1",
        ...     vendor="adva",
        ...     device_role="CPE"
        ... )
    """
    from otel.otel_mdso_utils import MDSOSpanHelper
    
    MDSOSpanHelper.add_network_function_attributes(
        span=span,
        communication_state=communication_state,
        ip_address=ip_address,
        vendor=vendor,
        device_role=device_role,
        provider_resource_id=provider_resource_id
    )


def add_error_attributes(
    span,
    error_code: Optional[str] = None,
    error_category: Optional[str] = None,
    error_message: Optional[str] = None,
    is_new_error: Optional[bool] = None,
):
    """
    Add error-tracking attributes to a span using MDSOSpanHelper
    
    Args:
        span: Active OTEL span
        error_code: Error code (e.g., DE-1000)
        error_category: Categorized error type
        error_message: Raw error message (truncated to 500 chars)
        is_new_error: Whether this is a newly discovered error
    
    Example:
        >>> from opentelemetry import trace
        >>> span = trace.get_current_span()
        >>> add_error_attributes(
        ...     span,
        ...     error_code="DE-1000",
        ...     error_category="CONNECTIVITY_ERROR",
        ...     error_message="Unable to connect to device",
        ...     is_new_error=True
        ... )
    """
    from otel.otel_mdso_utils import MDSOSpanHelper
    
    MDSOSpanHelper.add_error_attributes(
        span=span,
        error_code=error_code,
        error_category=error_category,
        error_message=error_message,
        is_new_error=is_new_error
    )


def set_correlation_baggage(
    circuit_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    tid: Optional[str] = None,
    fqdn: Optional[str] = None,
    provider_resource_id: Optional[str] = None,
):
    """
    Set correlation keys as baggage for cross-service tracing using MDSOSpanHelper
    
    Implements the correlation chain:
    circuit_id → fqdn → provider_resource_id
    
    Args:
        circuit_id: Circuit identifier
        resource_id: MDSO resource ID
        tid: Device TID
        fqdn: Device FQDN
        provider_resource_id: MDSO provider resource ID
    
    Example:
        >>> set_correlation_baggage(
        ...     circuit_id="123-456",
        ...     fqdn="device.example.com",
        ...     provider_resource_id="uuid-123"
        ... )
    """
    from otel.otel_mdso_utils import MDSOSpanHelper
    
    MDSOSpanHelper.set_correlation_baggage(
        circuit_id=circuit_id,
        resource_id=resource_id,
        tid=tid,
        fqdn=fqdn,
        provider_resource_id=provider_resource_id
    )


def record_span_event(
    span,
    event_name: str,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Record a span event with attributes using MDSOSpanHelper
    
    Args:
        span: Active OTEL span
        event_name: Name of the event
        attributes: Event attributes
    
    Example:
        >>> from opentelemetry import trace
        >>> span = trace.get_current_span()
        >>> record_span_event(
        ...     span,
        ...     "device.provisioning.started",
        ...     {"device_id": "123", "vendor": "juniper"}
        ... )
    """
    from otel.otel_mdso_utils import MDSOSpanHelper
    
    MDSOSpanHelper.record_span_event(span, event_name, attributes)


def extract_error_identifiers(error_message: str) -> Dict[str, Any]:
    """
    Extract all identifiers from an error message using ErrorPatternMatcher
    
    Args:
        error_message: Raw error text
    
    Returns:
        Dictionary of extracted identifiers (circuit_id, tid, resource_id, fqdn, ipv4)
    
    Example:
        >>> identifiers = extract_error_identifiers(
        ...     "Error processing circuit 123-456 for device TID789"
        ... )
        >>> print(identifiers.get("circuit_id"))
        123-456
    """
    from otel.otel_mdso_utils import ErrorPatternMatcher
    
    matcher = ErrorPatternMatcher()
    return matcher.extract_all_identifiers(error_message)


def categorize_error(error_message: str) -> Dict[str, str]:
    """
    Categorize an error message using ErrorPatternMatcher
    
    Args:
        error_message: Raw error text
    
    Returns:
        Dictionary with category and type
    
    Example:
        >>> result = categorize_error("IP 10.0.0.1 already exists on device")
        >>> print(result["category"])
        IP_CONFLICT_ERROR
    """
    from otel.otel_mdso_utils import ErrorPatternMatcher
    
    matcher = ErrorPatternMatcher()
    return matcher.categorize_error(error_message)


def extract_vendor_from_node_name(node_name_list: List[Dict]) -> Optional[str]:
    """
    Extract vendor from Beorn node name array
    
    Args:
        node_name_list: Node name array from Beorn topology
    
    Returns:
        Vendor name (lowercase) or None
    
    Example:
        >>> node_name = [{"name": "Site"}, {"name": "Device"}, {"value": "JUNIPER"}]
        >>> vendor = extract_vendor_from_node_name(node_name)
        >>> print(vendor)
        juniper
    """
    from otel.otel_mdso_utils import extract_vendor_from_node_name as _extract_vendor
    
    return _extract_vendor(node_name_list)


def extract_fqdn_from_node_name(node_name_list: List[Dict]) -> Optional[str]:
    """
    Extract FQDN from Beorn node name array
    
    Args:
        node_name_list: Node name array from Beorn topology
    
    Returns:
        FQDN or None
    
    Example:
        >>> node_name = [{"name": "Site"}, ..., {"value": "device.example.com"}]
        >>> fqdn = extract_fqdn_from_node_name(node_name)
        >>> print(fqdn)
        device.example.com
    """
    from otel.otel_mdso_utils import extract_fqdn_from_node_name as _extract_fqdn
    
    return _extract_fqdn(node_name_list)


def validate_beorn_response(data: Dict) -> bool:
    """
    Validate Beorn response has minimum required elements
    
    Args:
        data: Beorn API response
    
    Returns:
        True if valid (>= 8 elements), False otherwise
    
    Example:
        >>> response = {"element1": "value1", ...}  # 8+ elements
        >>> is_valid = validate_beorn_response(response)
        >>> print(is_valid)
        True
    """
    from otel.otel_mdso_utils import validate_beorn_response as _validate
    
    return _validate(data)


def setup_pyroscope(
    service_name: str = "mdso-scriptplan",
    server_address: str = None,
    environment: str = "dev",
    version: str = "1.0.0",
    tags: Optional[Dict[str, str]] = None
) -> bool:
    """
    Setup Pyroscope continuous profiling for MDSO scripts

    Args:
        service_name: Application name for profiling
        server_address: Pyroscope server URL (defaults to env var or local instance)
        environment: Deployment environment (dev/staging/prod)
        version: Service version
        tags: Additional tags for profiling data

    Returns:
        True if Pyroscope was successfully configured, False otherwise

    Example:
        >>> from instrumentation import setup_pyroscope
        >>> setup_pyroscope("mdso-circuit-provisioner", environment="prod", tags={"team": "network-ops"})
        >>> # Script execution will now be profiled
    """
    if not PYROSCOPE_AVAILABLE:
        logger.warning("Pyroscope not available - install with: pip install pyroscope-io")
        return False

    # Get Pyroscope server address from CommonPlan constant or environment variable
    # Note: instance parameter would need to be added to this function signature if needed
    server_address = server_address or os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040")

    # Merge default tags with provided tags
    profiling_tags = {
        "environment": environment,
        "version": version,
        **(tags or {})
    }

    try:
        pyroscope.configure(
            application_name=service_name,
            server_address=server_address,
            tags=profiling_tags
        )
        logger.info(f"Pyroscope profiling enabled: service={service_name}, server={server_address}, env={environment}")
        return True
    except Exception as e:
        logger.error(f"Failed to configure Pyroscope: {e}")
        return False
