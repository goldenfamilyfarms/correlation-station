# Diagnostic Guide: Troubleshooting Missing Logs in alloy-collector

## Problem

Trace logs are not appearing in `/opt/ciena/bp2/alloy-collector/traces.ndjson` even though:
- The directory exists on the host machine
- BluePlanet solution manager is running the scripts
- Scripts are using the instrumentation code

## Enhanced Logging

The instrumentation code has been enhanced with comprehensive diagnostic logging to help identify the issue.

### What's Been Added

1. **FileSpanExporter Logging**
   - Logs when directory is created/verified
   - Logs file permissions and ownership
   - Logs when file is opened successfully
   - Logs each span export with byte counts
   - Logs file size before and after writes

2. **setup_otel() Logging**
   - Logs export mode detection process
   - Logs which mode is selected (file vs OTLP)
   - Logs full file path being used
   - Logs when FileSpanExporter is instantiated
   - Verifies file writability after setup

3. **OTelMixin Logging**
   - Logs when OTel is initialized
   - Logs export mode environment variable
   - Logs when root spans are created
   - Logs correlation context injection

## Diagnostic Steps

### Step 1: Check Application Logs

When scripts run, you should now see detailed logging:

```
setup_otel: Export mode detection - OTEL_EXPORT_MODE env var: 'not set', use_file_export parameter: None
setup_otel: Auto-detecting export mode: defaulting to file-based (safe for isolated containers)
setup_otel: Using file-based trace export mode
setup_otel: Trace log directory: /opt/ciena/bp2/alloy-collector
setup_otel: Trace log file: /opt/ciena/bp2/alloy-collector/traces.ndjson
FileSpanExporter: Initializing with file path: /opt/ciena/bp2/alloy-collector/traces.ndjson
FileSpanExporter: Parent directory exists: /opt/ciena/bp2/alloy-collector
FileSpanExporter: Successfully opened file handle
FileSpanExporter: Exporting 1 span(s) to /opt/ciena/bp2/alloy-collector/traces.ndjson
FileSpanExporter: Successfully exported 1 span(s) - wrote 1234 bytes
```

**If you don't see these logs:**
- Scripts may not be calling `setup_otel()` or `__init_otel__()`
- OTel may not be initialized
- Check if feature flags are disabling OTel

**If you see OTLP mode instead of file mode:**
- Check `OTEL_EXPORT_MODE` environment variable
- It should be unset or set to "file"
- If set to "otlp", change it to "file" or unset it

### Step 2: Run Diagnostic Test Script

Use the provided test script to verify file export:

```bash
# From the MDSO script environment
python otel/test_file_export.py

# Or with custom directory
python otel/test_file_export.py --trace-log-dir /opt/ciena/bp2/alloy-collector

# With verbose logging
python otel/test_file_export.py --verbose
```

The script will:
1. Check if directory exists and is writable
2. Create a test span
3. Verify the span is written to the file
4. Report success/failure with detailed information

### Step 3: Check Environment Variables

Verify these environment variables in the BluePlanet solution manager:

```bash
# Should be unset or "file" for file-based export
echo $OTEL_EXPORT_MODE

# Should point to the trace log directory (optional)
echo $OTEL_TRACE_LOG_DIR

# Should be set to enable OTel (if using feature flags)
echo $OTEL_ENABLED

# Enable sudo for file operations if needed (optional, auto-detected if not set)
echo $OTEL_USE_SUDO
```

**Sudo Support:**
The FileSpanExporter now supports using `sudo` to write logs when direct file access is not permitted. This is useful when scripts run under BluePlanet solution manager without write permissions to `/opt/ciena/bp2/alloy-collector`.

- **Auto-detection**: If `OTEL_USE_SUDO` is not set, the exporter will automatically detect if sudo is needed based on directory permissions
- **Manual override**: Set `OTEL_USE_SUDO=true` to force sudo usage, or `OTEL_USE_SUDO=false` to disable it
- **Fallback**: If direct write fails with permission error, the exporter will automatically fall back to sudo

### Step 4: Verify File Permissions

Check that the directory and file are writable:

```bash
# Check directory permissions
ls -ld /opt/ciena/bp2/alloy-collector

# Check file permissions (if file exists)
ls -l /opt/ciena/bp2/alloy-collector/traces.ndjson

# Test write access
touch /opt/ciena/bp2/alloy-collector/test_write && rm /opt/ciena/bp2/alloy-collector/test_write
```

### Step 5: Check for Errors in Logs

Look for error messages in application logs:

- `FileSpanExporter: Failed to open trace log file` - Permission issue
- `FileSpanExporter: Failed to create directory` - Directory creation failed
- `setup_otel: WARNING - Using OTLP mode instead of file mode` - Wrong export mode
- `OTelMixin.__init_otel__: setup_otel() returned None` - OTel not available

## Common Issues and Solutions

### Issue: Export Mode is OTLP Instead of File

**Symptoms:**
- Logs show "Using direct OTLP export to: http://localhost:4318"
- No file is created

**Solution:**
- Set `OTEL_EXPORT_MODE=file` in BluePlanet solution manager environment
- Or unset the variable to use default (file mode)

### Issue: Permission Denied

**Symptoms:**
- Logs show "Permission denied opening file"
- File exists but can't be written to
- Logs show "Falling back to sudo"

**Solution:**
The exporter will automatically detect permission issues and fall back to sudo. However, you can also:

1. **Enable sudo explicitly:**
   ```bash
   export OTEL_USE_SUDO=true
   ```

2. **Fix permissions (if sudo is not desired):**
   - Check file/directory ownership: `ls -l /opt/ciena/bp2/alloy-collector`
   - Ensure the user running scripts has write access
   - May need to change ownership: `chown -R <user>:<group> /opt/ciena/bp2/alloy-collector`
   - Or add user to appropriate group: `usermod -a -G <group> <user>`

3. **Verify sudo access:**
   - Ensure the user running scripts has sudo privileges
   - Test manually: `sudo touch /opt/ciena/bp2/alloy-collector/test && sudo rm /opt/ciena/bp2/alloy-collector/test`

### Issue: Directory Doesn't Exist

**Symptoms:**
- Logs show "Parent directory does not exist"
- File creation fails

**Solution:**
- The code should create it automatically, but if it fails:
  - Create manually: `mkdir -p /opt/ciena/bp2/alloy-collector`
  - Set permissions: `chmod 755 /opt/ciena/bp2/alloy-collector`

### Issue: No Logs Appear at All

**Symptoms:**
- No OTel initialization logs
- No FileSpanExporter logs

**Possible Causes:**
1. Scripts not using OTelMixin or calling setup_otel()
2. Feature flag disabling OTel
3. OpenTelemetry packages not installed
4. Logging level too high (check logger configuration)

**Solution:**
- Verify scripts inherit from OTelMixin
- Check `OTEL_ENABLED` environment variable
- Verify OpenTelemetry is installed: `pip list | grep opentelemetry`
- Check logging configuration

## Using the Diagnostic Function Programmatically

You can also call the diagnostic function from your code:

```python
from otel.instrumentation import test_file_export

result = test_file_export()
if result['success']:
    print(f"File export working: {result['file_path']}")
else:
    print(f"File export failed: {result['error']}")
```

## Next Steps

If diagnostics show everything is working but logs still don't appear:

1. **Check Alloy Configuration**
   - Verify Alloy is configured to tail `/opt/ciena/bp2/alloy-collector/traces.ndjson`
   - Check Alloy logs for errors

2. **Check File Content**
   - Manually inspect the file: `tail -f /opt/ciena/bp2/alloy-collector/traces.ndjson`
   - Verify it contains JSON lines

3. **Check BatchSpanProcessor**
   - Spans may be queued but not flushed
   - Check if spans are actually being created
   - Verify spans are ending (not left open)

4. **Check BluePlanet Container Environment**
   - Verify scripts are running in the expected environment
   - Check if there are multiple containers/processes
   - Verify file paths are correct in container context

