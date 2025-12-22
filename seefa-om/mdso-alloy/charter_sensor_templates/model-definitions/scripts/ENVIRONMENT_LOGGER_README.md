# Scriptplan Environment Logger

## Overview

The Environment Logger provides detailed information about where scriptplan is running on the MDSO server, including Python version, system information, OpenTelemetry package versions, and resolved dependencies using pip-compile.

## Features

- **Python Version Detection**: Reports Python version, implementation, and compiler details
- **System Information**: Captures hostname, platform, architecture, and OS details
- **Path Information**: Logs current working directory, script directory, and Python path
- **OpenTelemetry Package Versions**: Detects and reports installed OTel package versions
- **Dependency Resolution**: Uses pip-compile to generate resolved dependencies based on Python version
- **OpenTelemetry Integration**: Can attach environment data as span attributes for distributed tracing

## Usage

### Automatic Integration

The environment logger is automatically called when CommonPlan.run() executes. It logs environment information early in the execution lifecycle, right after OpenTelemetry initialization.

### Manual Usage

You can also use the environment logger manually in your scripts:

```python
from scripts.environment_logger import log_scriptplan_environment
import logging

logger = logging.getLogger(__name__)

# Basic usage - logs environment info
env_info = log_scriptplan_environment(logger=logger)

# Without pip-compile (faster startup)
env_info = log_scriptplan_environment(
    logger=logger,
    include_dependencies=False
)

# With OpenTelemetry span
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("my_operation") as span:
    env_info = log_scriptplan_environment(
        logger=logger,
        include_dependencies=True,
        otel_span=span
    )
```

### Using the EnvironmentLogger Class

For more control, use the `EnvironmentLogger` class directly:

```python
from scripts.environment_logger import EnvironmentLogger
import logging

logger = logging.getLogger(__name__)
env_logger = EnvironmentLogger(logger)

# Collect environment info without logging
env_info = env_logger.collect_environment_info()

# Get only pip-compiled dependencies
deps, error = env_logger.get_pip_compiled_dependencies()
if deps:
    print(deps)
else:
    print(f"Error: {error}")

# Log everything
env_logger.log_environment(include_dependencies=True)
```

## Environment Information Captured

### Python Information
- Version string (e.g., "3.9.18")
- Version details (major, minor, micro, releaselevel, serial)
- Implementation (CPython, PyPy, etc.)
- Compiler information
- Python executable path

### System Information
- Platform (OS and version)
- System type (Linux, Windows, etc.)
- Release and version
- Machine architecture (x86_64, arm64, etc.)
- Processor information
- Hostname

### Path Information
- Current working directory
- Script directory location
- Home directory
- Python path (first 5 entries)

### OpenTelemetry Information
- OTel enabled status
- Export mode (file, otlp, auto)
- Installed package versions:
  - opentelemetry-api
  - opentelemetry-sdk
  - opentelemetry-instrumentation
  - opentelemetry-exporter-otlp
  - opentelemetry-instrumentation-requests
  - opentelemetry-instrumentation-urllib
  - opentelemetry-instrumentation-urllib3
  - opentelemetry-instrumentation-logging

### Environment Variables
- OTEL_ENABLED
- OTEL_EXPORT_MODE
- OTEL_TRACE_LOG_DIR
- OTEL_EXPORTER_OTLP_ENDPOINT
- OTEL_USE_SUDO
- OTEL_SERVICE_NAME
- DEPLOYMENT_ENV
- ENVIRONMENT
- PATH (truncated)

### Dependencies (via pip-compile)
- Fully resolved dependency tree for OpenTelemetry packages
- Based on current Python version
- Includes all transitive dependencies with exact versions
- Output saved to `requirements_compiled_py<version>.txt`

## Requirements

### Base Requirements
- Python 3.6+
- Standard library modules (sys, os, platform, logging, subprocess)

### Optional Requirements
- `pip-tools` (for pip-compile functionality)
  - Install: `pip install pip-tools`
  - If not installed, dependency resolution will be skipped with a warning

### OpenTelemetry (Optional)
- If OpenTelemetry is installed, package versions will be detected
- If not installed, OTel section will report "None installed"

## Installation

1. Ensure `pip-tools` is installed:
   ```bash
   pip install -r seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts/otel/requirements.txt
   ```

2. The environment logger is automatically available when using CommonPlan

## Testing

Run the test suite to verify the environment logger:

```bash
cd seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts
python test_environment_logger.py
```

The test suite includes:
- Test 1: Basic environment logging (fast, no pip-compile)
- Test 2: Structured environment data collection
- Test 3: pip-compile dependencies only
- Test 4: Full logging with dependencies

## Configuration

### Disable Dependency Resolution

To skip pip-compile and improve startup time, set `include_dependencies=False`:

```python
# In common_plan.py, modify the log_scriptplan_environment call:
log_scriptplan_environment(
    logger=self.logger,
    include_dependencies=False,  # Faster startup
    otel_span=None
)
```

### Disable Environment Logging

Environment logging can be disabled by modifying the condition in `common_plan.py`:

```python
# Comment out or remove this block in CommonPlan.run()
if log_scriptplan_environment:
    try:
        log_scriptplan_environment(...)
    except Exception as e:
        ...
```

## Output Example

```
================================================================================
SCRIPTPLAN ENVIRONMENT INFORMATION
================================================================================
Python Version: 3.9.18 (CPython)
Python Executable: /usr/local/bin/python3
Python Compiler: GCC 9.4.0
System: Linux 5.15.0-58-generic
Platform: Linux-5.15.0-58-generic-x86_64-with-glibc2.31
Hostname: mdso-server-01
Architecture: 64bit
Machine: x86_64
Current Working Directory: /opt/ciena/bp2/mdso/scripts
Script Directory: /opt/ciena/bp2/mdso/scripts
OpenTelemetry Enabled: True
OpenTelemetry Export Mode: file
OpenTelemetry Packages:
  - opentelemetry-api: 1.20.0
  - opentelemetry-sdk: 1.20.0
  - opentelemetry-exporter-otlp: 1.20.0
  - opentelemetry-instrumentation-requests: 0.41b0
  - opentelemetry-instrumentation-urllib3: 0.41b0
Relevant Environment Variables:
  - OTEL_ENABLED: true
  - OTEL_EXPORT_MODE: file
  - OTEL_TRACE_LOG_DIR: /opt/ciena/bp2/alloy-collector
--------------------------------------------------------------------------------
DEPENDENCIES (pip-compile for Python 3.9.18)
--------------------------------------------------------------------------------
Successfully compiled OpenTelemetry dependencies:
  # This file is autogenerated by pip-compile
  opentelemetry-api==1.20.0
  opentelemetry-sdk==1.20.0
  opentelemetry-exporter-otlp-proto-http==1.20.0
  ... (20 more lines)
  Full output saved to requirements_compiled_py39.txt
================================================================================
```

## OpenTelemetry Span Attributes

When an OTel span is provided, the following attributes are added:

- `environment.python.version`
- `environment.python.implementation`
- `environment.python.executable`
- `environment.system.platform`
- `environment.system.hostname`
- `environment.system.architecture`
- `environment.paths.cwd`
- `environment.paths.script_dir`
- `environment.otel.enabled`
- `environment.otel.export_mode`
- `environment.otel.package.<package_name>` (for each installed OTel package)

## Troubleshooting

### pip-compile not found

**Error**: `pip-tools not installed. Install with: pip install pip-tools`

**Solution**: Install pip-tools:
```bash
pip install pip-tools
```

### pip-compile timeout

**Error**: `pip-compile timed out after 60 seconds`

**Solution**: This may occur with slow network or large dependency trees. Options:
1. Increase timeout in `environment_logger.py`
2. Disable dependency resolution: `include_dependencies=False`
3. Pre-compile dependencies offline

### Permission errors

**Error**: Permission denied when writing compiled requirements

**Solution**: Ensure the scripts directory is writable by the scriptplan user

### Import errors

**Error**: `Failed to import environment_logger`

**Solution**: Ensure the `scripts` directory is in the Python path:
```python
import sys
sys.path.append("model-definitions/scripts")
```

## Performance Considerations

- **Basic logging** (without dependencies): < 100ms
- **With pip-compile**: 30-60 seconds (first run only)
- Compiled dependencies are cached to disk for reuse

To minimize performance impact in production:
1. Set `include_dependencies=False` for faster startup
2. Pre-compile dependencies during deployment/build
3. Run pip-compile once per Python version and cache results

## Integration Points

The environment logger is integrated into:

1. **CommonPlan.run()** - Automatic logging after OTel initialization
2. **Test Suite** - `test_environment_logger.py`
3. **Requirements** - `otel/requirements.txt` includes pip-tools

## File Locations

- **Module**: `scripts/environment_logger.py`
- **Test**: `scripts/test_environment_logger.py`
- **Documentation**: `scripts/ENVIRONMENT_LOGGER_README.md`
- **Integration**: `scripts/common_plan.py` (lines 480-493)
- **Requirements**: `scripts/otel/requirements.txt`

## Version History

- **v1.0** (2025-12-22): Initial implementation
  - Python version detection
  - System information collection
  - OpenTelemetry package detection
  - pip-compile dependency resolution
  - OpenTelemetry span integration
  - Automatic CommonPlan integration
