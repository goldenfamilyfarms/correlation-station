"""
Environment Logger for Scriptplan

This module provides functionality to log detailed environment information
about where scriptplan is running, including:
- Python version and implementation
- System and platform information
- OpenTelemetry package versions
- Dependencies resolved via pip-compile based on Python version
"""

import sys
import os
import platform
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json


class EnvironmentLogger:
    """Logger for capturing and reporting scriptplan execution environment."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the environment logger.

        Args:
            logger: Optional logger instance. If not provided, creates one.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.env_info = {}

    def collect_environment_info(self) -> Dict:
        """
        Collect all environment information.

        Returns:
            Dictionary containing all environment information
        """
        self.env_info = {
            'python': self._get_python_info(),
            'system': self._get_system_info(),
            'paths': self._get_path_info(),
            'otel': self._get_otel_info(),
            'environment_vars': self._get_relevant_env_vars(),
        }

        return self.env_info

    def _get_python_info(self) -> Dict:
        """Get Python version and implementation details."""
        return {
            'version': sys.version,
            'version_info': {
                'major': sys.version_info.major,
                'minor': sys.version_info.minor,
                'micro': sys.version_info.micro,
                'releaselevel': sys.version_info.releaselevel,
                'serial': sys.version_info.serial,
            },
            'version_string': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'implementation': platform.python_implementation(),
            'compiler': platform.python_compiler(),
            'executable': sys.executable,
        }

    def _get_system_info(self) -> Dict:
        """Get system and platform information."""
        try:
            hostname = platform.node()
        except Exception:
            hostname = os.environ.get('HOSTNAME', 'unknown')

        return {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'hostname': hostname,
            'architecture': platform.architecture()[0],
        }

    def _get_path_info(self) -> Dict:
        """Get path and directory information."""
        return {
            'cwd': os.getcwd(),
            'script_dir': os.path.dirname(os.path.abspath(__file__)),
            'home_dir': os.path.expanduser('~'),
            'python_path': sys.path[:5],  # First 5 entries to avoid spam
        }

    def _get_otel_info(self) -> Dict:
        """Get OpenTelemetry package versions and configuration."""
        otel_info = {
            'enabled': os.environ.get('OTEL_ENABLED', 'true').lower() == 'true',
            'export_mode': os.environ.get('OTEL_EXPORT_MODE', 'auto'),
            'packages': {},
        }

        # Try to get installed OTel package versions
        otel_packages = [
            'opentelemetry-api',
            'opentelemetry-sdk',
            'opentelemetry-instrumentation',
            'opentelemetry-exporter-otlp',
            'opentelemetry-instrumentation-requests',
            'opentelemetry-instrumentation-urllib',
            'opentelemetry-instrumentation-urllib3',
            'opentelemetry-instrumentation-logging',
        ]

        for package in otel_packages:
            version = self._get_package_version(package)
            if version:
                otel_info['packages'][package] = version

        return otel_info

    def _get_package_version(self, package_name: str) -> Optional[str]:
        """
        Get the version of an installed package.

        Args:
            package_name: Name of the package

        Returns:
            Version string or None if not installed
        """
        try:
            import importlib.metadata
            return importlib.metadata.version(package_name)
        except Exception:
            # Fallback for older Python versions
            try:
                import pkg_resources
                return pkg_resources.get_distribution(package_name).version
            except Exception:
                return None

    def _get_relevant_env_vars(self) -> Dict:
        """Get relevant environment variables for scriptplan."""
        relevant_vars = [
            'OTEL_ENABLED',
            'OTEL_EXPORT_MODE',
            'OTEL_TRACE_LOG_DIR',
            'OTEL_EXPORTER_OTLP_ENDPOINT',
            'OTEL_USE_SUDO',
            'OTEL_SERVICE_NAME',
            'DEPLOYMENT_ENV',
            'ENVIRONMENT',
            'PATH',
        ]

        env_vars = {}
        for var in relevant_vars:
            value = os.environ.get(var)
            if value:
                # Truncate PATH to avoid spam
                if var == 'PATH':
                    paths = value.split(':')
                    value = f"{len(paths)} paths: {':'.join(paths[:3])}..." if len(paths) > 3 else value
                env_vars[var] = value

        return env_vars

    def get_pip_compiled_dependencies(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate pip-compiled dependencies for OpenTelemetry based on Python version.

        Returns:
            Tuple of (requirements_output, error_message)
        """
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        # Look for requirements file in otel directory
        script_dir = Path(__file__).parent
        otel_req_file = script_dir / 'otel' / 'requirements.txt'

        if not otel_req_file.exists():
            return None, f"Requirements file not found: {otel_req_file}"

        try:
            # Create a temporary output file name
            output_file = script_dir / 'otel' / f'requirements_compiled_py{python_version.replace(".", "")}.txt'

            # Run pip-compile
            result = subprocess.run(
                [
                    sys.executable, '-m', 'piptools', 'compile',
                    '--output-file', str(output_file),
                    '--verbose',
                    '--annotate',
                    str(otel_req_file)
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Read the compiled output
                with open(output_file, 'r') as f:
                    compiled_deps = f.read()
                return compiled_deps, None
            else:
                return None, f"pip-compile failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return None, "pip-compile timed out after 60 seconds"
        except FileNotFoundError:
            return None, "pip-tools not installed. Install with: pip install pip-tools"
        except Exception as e:
            return None, f"Error running pip-compile: {str(e)}"

    def log_environment(self, include_dependencies: bool = True, otel_span=None):
        """
        Log all collected environment information.

        Args:
            include_dependencies: Whether to run pip-compile and log dependencies
            otel_span: Optional OpenTelemetry span to add attributes to
        """
        # Collect environment info
        env_info = self.collect_environment_info()

        # Log separator
        self.logger.info("=" * 80)
        self.logger.info("SCRIPTPLAN ENVIRONMENT INFORMATION")
        self.logger.info("=" * 80)

        # Python Information
        py_info = env_info['python']
        self.logger.info(f"Python Version: {py_info['version_string']} ({py_info['implementation']})")
        self.logger.info(f"Python Executable: {py_info['executable']}")
        self.logger.info(f"Python Compiler: {py_info['compiler']}")

        # Add to OTel span if available
        if otel_span:
            otel_span.set_attribute('environment.python.version', py_info['version_string'])
            otel_span.set_attribute('environment.python.implementation', py_info['implementation'])
            otel_span.set_attribute('environment.python.executable', py_info['executable'])

        # System Information
        sys_info = env_info['system']
        self.logger.info(f"System: {sys_info['system']} {sys_info['release']}")
        self.logger.info(f"Platform: {sys_info['platform']}")
        self.logger.info(f"Hostname: {sys_info['hostname']}")
        self.logger.info(f"Architecture: {sys_info['architecture']}")
        self.logger.info(f"Machine: {sys_info['machine']}")

        if otel_span:
            otel_span.set_attribute('environment.system.platform', sys_info['platform'])
            otel_span.set_attribute('environment.system.hostname', sys_info['hostname'])
            otel_span.set_attribute('environment.system.architecture', sys_info['architecture'])

        # Path Information
        path_info = env_info['paths']
        self.logger.info(f"Current Working Directory: {path_info['cwd']}")
        self.logger.info(f"Script Directory: {path_info['script_dir']}")

        if otel_span:
            otel_span.set_attribute('environment.paths.cwd', path_info['cwd'])
            otel_span.set_attribute('environment.paths.script_dir', path_info['script_dir'])

        # OpenTelemetry Information
        otel_info = env_info['otel']
        self.logger.info(f"OpenTelemetry Enabled: {otel_info['enabled']}")
        self.logger.info(f"OpenTelemetry Export Mode: {otel_info['export_mode']}")

        if otel_info['packages']:
            self.logger.info("OpenTelemetry Packages:")
            for pkg, version in otel_info['packages'].items():
                self.logger.info(f"  - {pkg}: {version}")
                if otel_span:
                    # Use sanitized attribute name
                    attr_name = f"environment.otel.package.{pkg.replace('-', '_')}"
                    otel_span.set_attribute(attr_name, version)
        else:
            self.logger.info("OpenTelemetry Packages: None installed or not detected")

        if otel_span:
            otel_span.set_attribute('environment.otel.enabled', otel_info['enabled'])
            otel_span.set_attribute('environment.otel.export_mode', otel_info['export_mode'])

        # Environment Variables
        if env_info['environment_vars']:
            self.logger.info("Relevant Environment Variables:")
            for var, value in env_info['environment_vars'].items():
                self.logger.info(f"  - {var}: {value}")

        # Pip-compiled dependencies
        if include_dependencies:
            self.logger.info("-" * 80)
            self.logger.info(f"DEPENDENCIES (pip-compile for Python {py_info['version_string']})")
            self.logger.info("-" * 80)

            deps, error = self.get_pip_compiled_dependencies()
            if deps:
                self.logger.info("Successfully compiled OpenTelemetry dependencies:")
                # Log first 20 lines to avoid spam, but indicate there's more
                dep_lines = deps.split('\n')
                for line in dep_lines[:20]:
                    if line.strip():
                        self.logger.info(f"  {line}")
                if len(dep_lines) > 20:
                    self.logger.info(f"  ... ({len(dep_lines) - 20} more lines)")
                    self.logger.info(f"  Full output saved to requirements_compiled_py{py_info['version_string'].replace('.', '')}.txt")
            else:
                self.logger.warning(f"Could not compile dependencies: {error}")

        self.logger.info("=" * 80)

        return env_info


def log_scriptplan_environment(logger: Optional[logging.Logger] = None,
                               include_dependencies: bool = True,
                               otel_span=None) -> Dict:
    """
    Convenience function to log scriptplan environment information.

    Args:
        logger: Optional logger instance
        include_dependencies: Whether to run pip-compile and log dependencies
        otel_span: Optional OpenTelemetry span to add attributes to

    Returns:
        Dictionary containing environment information
    """
    env_logger = EnvironmentLogger(logger)
    return env_logger.log_environment(include_dependencies=include_dependencies, otel_span=otel_span)
