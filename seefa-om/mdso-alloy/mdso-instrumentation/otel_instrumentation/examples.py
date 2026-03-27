"""
Example usage patterns for MDSOInstrumentation class

This file demonstrates how to use the MDSOInstrumentation class
across different MDSO products and use cases.
"""

from mdso_instrumentation import MDSOInstrumentation, create_instrumentation


# ============================================================================
# Example 1: Basic Scriptplan with Common Plan Pattern
# ============================================================================

class CommonPlan:
    """
    Base class for MDSO scriptplans demonstrating instrumentation pattern
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.instrumentation = None

    def run(self, circuit_id: str, resource_id: str, **kwargs):
        """
        Main run method that all scriptplans should implement

        This pattern initializes instrumentation, injects context,
        and wraps the main logic in a traced span.
        """
        # Initialize instrumentation
        self.instrumentation = MDSOInstrumentation(
            service_name=self.service_name,
            environment="prod",
            version="1.0.0"
        )
        self.instrumentation.setup()

        # Inject correlation context at the start
        self.instrumentation.inject_context(
            circuit_id=circuit_id,
            resource_id=resource_id,
            product_id=kwargs.get("product_id")
        )

        # Main operation wrapped in span
        with self.instrumentation.span(
            f"{self.service_name}.run",
            circuit_id=circuit_id
        ) as span:
            self.instrumentation.log(
                "Starting scriptplan execution",
                "STARTED",
                circuit_id=circuit_id,
                resource_id=resource_id
            )

            try:
                # Execute main logic
                result = self._execute(circuit_id, resource_id, **kwargs)

                self.instrumentation.log(
                    "Scriptplan execution complete",
                    "COMPLETED",
                    circuit_id=circuit_id
                )

                return result

            except Exception as e:
                # Add error attributes to span
                self.instrumentation.add_error_attrs(
                    span,
                    error_message=str(e),
                    error_category=self._categorize_error(e)
                )

                self.instrumentation.log(
                    "Scriptplan execution failed",
                    "FAILED",
                    circuit_id=circuit_id,
                    error=str(e)
                )
                raise

    def _execute(self, circuit_id: str, resource_id: str, **kwargs):
        """Override this in subclasses with actual logic"""
        raise NotImplementedError("Subclasses must implement _execute")

    def _categorize_error(self, error: Exception) -> str:
        """Categorize error using instrumentation utilities"""
        if self.instrumentation:
            category = self.instrumentation.categorize_error(str(error))
            return category.get("category", "UNKNOWN_ERROR")
        return "UNKNOWN_ERROR"


# ============================================================================
# Example 2: Circuit Provisioning Scriptplan
# ============================================================================

class CircuitProvisionerPlan(CommonPlan):
    """
    Example: Circuit provisioning scriptplan with topology and device operations
    """

    def __init__(self):
        super().__init__(service_name="circuit-provisioner")

    def _execute(self, circuit_id: str, resource_id: str, **kwargs):
        """
        Provision a circuit with full instrumentation
        """
        # Fetch topology from Beorn
        topology = self._fetch_topology(circuit_id)

        # Configure each device
        results = []
        for device in topology.get("devices", []):
            result = self._configure_device(device, circuit_id)
            results.append(result)

        return {"status": "success", "devices_configured": len(results)}

    def _fetch_topology(self, circuit_id: str):
        """
        Fetch topology from Beorn with tracing
        """
        with self.instrumentation.span(
            "beorn.topology.fetch",
            circuit_id=circuit_id
        ) as span:
            self.instrumentation.log(
                "Fetching topology from Beorn",
                "STARTED",
                circuit_id=circuit_id
            )

            # Simulate fetching topology
            topology = {
                "circuit_id": circuit_id,
                "service_type": "FIA",
                "devices": [
                    {
                        "tid": "ABCD123456W",
                        "fqdn": "device1.example.com",
                        "vendor": "juniper",
                        "role": "PE",
                        "ip": "10.0.0.1"
                    },
                    {
                        "tid": "EFGH789012W",
                        "fqdn": "device2.example.com",
                        "vendor": "cisco",
                        "role": "CPE",
                        "ip": "10.0.0.2"
                    }
                ]
            }

            # Add topology attributes to span
            self.instrumentation.add_topology_attrs(
                span,
                service_type=topology["service_type"],
                vendor=topology["devices"][0]["vendor"] if topology["devices"] else None,
                topology_node_count=len(topology["devices"]),
                validation_status=True
            )

            self.instrumentation.log(
                "Topology fetched successfully",
                "COMPLETED",
                circuit_id=circuit_id,
                device_count=len(topology["devices"])
            )

            return topology

    def _configure_device(self, device: dict, circuit_id: str):
        """
        Configure a single device with tracing
        """
        with self.instrumentation.span(
            "device.configure",
            tid=device["tid"],
            fqdn=device["fqdn"]
        ) as span:
            # Add network function attributes
            self.instrumentation.add_network_function_attrs(
                span,
                vendor=device["vendor"],
                ip_address=device["ip"],
                device_role=device["role"],
                communication_state="reachable"
            )

            self.instrumentation.log(
                f"Configuring device {device['tid']}",
                "STARTED",
                tid=device["tid"],
                fqdn=device["fqdn"]
            )

            try:
                # Simulate device configuration
                # In real implementation, this would call device APIs
                config_result = {
                    "tid": device["tid"],
                    "status": "configured",
                    "commands_sent": 15
                }

                self.instrumentation.log(
                    f"Device {device['tid']} configured",
                    "COMPLETED",
                    tid=device["tid"]
                )

                return config_result

            except Exception as e:
                # Categorize and add error attributes
                error_category = self.instrumentation.categorize_error(str(e))

                self.instrumentation.add_error_attrs(
                    span,
                    error_message=str(e),
                    error_category=error_category.get("category"),
                    is_new_error=True
                )

                self.instrumentation.log(
                    f"Device {device['tid']} configuration failed",
                    "FAILED",
                    tid=device["tid"],
                    error=str(e)
                )
                raise


# ============================================================================
# Example 3: Simple Standalone Script
# ============================================================================

def device_audit_script():
    """
    Example: Standalone device audit script
    """
    # Create and setup instrumentation
    instr = create_instrumentation(
        service_name="device-audit",
        environment="dev"
    )

    # Main operation
    with instr.span("audit.devices") as span:
        instr.log("Starting device audit", "STARTED")

        # Simulate getting devices
        devices = [
            {"tid": "DEVICE001W", "ip": "10.0.0.1"},
            {"tid": "DEVICE002W", "ip": "10.0.0.2"},
            {"tid": "DEVICE003W", "ip": "10.0.0.3"},
        ]

        instr.log(f"Found {len(devices)} devices to audit", device_count=len(devices))

        # Audit each device
        for device in devices:
            with instr.span("audit.device", tid=device["tid"]) as device_span:
                instr.add_network_function_attrs(
                    device_span,
                    ip_address=device["ip"],
                    communication_state="reachable"
                )
                # Perform audit
                instr.log(f"Auditing device {device['tid']}", tid=device["tid"])

        instr.log("Audit complete", "COMPLETED")


# ============================================================================
# Example 4: Error Handling and Pattern Matching
# ============================================================================

def error_handling_example():
    """
    Example: Comprehensive error handling with pattern matching
    """
    instr = create_instrumentation("error-handler")

    with instr.span("process.with.errors") as span:
        try:
            # Simulate an error
            error_msg = "IP 10.0.0.1 already exists on device DEVICE001W"
            raise ValueError(error_msg)

        except Exception as e:
            # Extract identifiers from error message
            identifiers = instr.extract_identifiers(str(e))
            print(f"Extracted identifiers: {identifiers}")

            # Categorize the error
            category = instr.categorize_error(str(e))
            print(f"Error category: {category}")

            # Add error attributes to span
            instr.add_error_attrs(
                span,
                error_message=str(e),
                error_category=category["category"],
                error_code=category.get("type"),
                is_new_error=True
            )

            # Log the error
            instr.log(
                "Error occurred during processing",
                "FAILED",
                error_category=category["category"],
                **identifiers
            )


# ============================================================================
# Example 5: SENSE App Integration (Flask)
# ============================================================================

def flask_app_example():
    """
    Example: Using MDSOInstrumentation in a Flask app
    """
    from flask import Flask, jsonify, request

    app = Flask(__name__)

    # Initialize instrumentation once at app startup
    instrumentation = MDSOInstrumentation(
        service_name="beorn",
        environment="prod",
        version="2.0.0"
    )
    instrumentation.setup()

    @app.route("/topology/<circuit_id>")
    def get_topology(circuit_id):
        """Endpoint to fetch topology with full tracing"""

        # Extract correlation context from headers
        product_id = request.headers.get("X-Product-Id")
        resource_id = request.headers.get("X-Resource-Id")

        # Inject context
        instrumentation.inject_context(
            circuit_id=circuit_id,
            product_id=product_id,
            resource_id=resource_id
        )

        with instrumentation.span(
            "beorn.api.get_topology",
            circuit_id=circuit_id
        ) as span:
            try:
                # Fetch topology (simplified)
                topology = {
                    "circuit_id": circuit_id,
                    "nodes": ["node1", "node2", "node3"]
                }

                # Add attributes
                instrumentation.add_topology_attrs(
                    span,
                    topology_node_count=len(topology["nodes"]),
                    validation_status=True
                )

                return jsonify(topology)

            except Exception as e:
                instrumentation.add_error_attrs(
                    span,
                    error_message=str(e)
                )
                return jsonify({"error": str(e)}), 500

    return app


# ============================================================================
# Example 6: Context Propagation Across Functions
# ============================================================================

def context_propagation_example():
    """
    Example: Context propagation across multiple function calls
    """
    instr = create_instrumentation("context-demo")

    # Top-level span with context injection
    with instr.span("main.operation") as main_span:
        circuit_id = "22.ABCD.123456.."
        resource_id = "550e8400-e29b-41d4-a716-446655440000"

        # Inject context
        instr.inject_context(
            circuit_id=circuit_id,
            resource_id=resource_id
        )

        # Call other functions - context is automatically propagated
        step1_result = processing_step_1(instr)
        step2_result = processing_step_2(instr, step1_result)

        # Extract context in any function
        ctx = instr.extract_context()
        print(f"Current context: {ctx}")

        return step2_result


def processing_step_1(instr: MDSOInstrumentation):
    """Context is automatically available from parent span"""
    with instr.span("processing.step1") as span:
        instr.log("Executing step 1", "STARTED")

        # Context is available via baggage
        ctx = instr.extract_context()
        circuit_id = ctx.get("circuit_id")

        instr.log(
            "Step 1 complete",
            "COMPLETED",
            circuit_id=circuit_id
        )

        return {"step": 1, "result": "success"}


def processing_step_2(instr: MDSOInstrumentation, previous_result: dict):
    """Nested span with inherited context"""
    with instr.span("processing.step2") as span:
        instr.log("Executing step 2", "STARTED")

        # Do work
        result = {"step": 2, "previous": previous_result}

        instr.log("Step 2 complete", "COMPLETED")

        return result


# ============================================================================
# Example 7: Batch Configuration and Profiling
# ============================================================================

def advanced_configuration_example():
    """
    Example: Advanced configuration with custom batch settings and profiling
    """
    instr = MDSOInstrumentation(
        service_name="high-throughput-processor",
        environment="prod",
        version="3.0.0",
        batch_config={
            "max_queue_size": 4096,  # Larger queue for high throughput
            "max_export_batch_size": 1024,
            "schedule_delay_millis": 2000,  # Export more frequently
        }
    )
    instr.setup()

    # Enable continuous profiling
    profiling_enabled = instr.setup_pyroscope(
        tags={
            "team": "network-ops",
            "region": "us-east-1"
        }
    )

    if profiling_enabled:
        print("Continuous profiling enabled")

    # Use instrumentation
    with instr.span("high.throughput.operation") as span:
        # Process large volumes
        for i in range(1000):
            # Each iteration creates minimal overhead
            with instr.span("process.item", item_id=i):
                pass  # Process item


# ============================================================================
# Main: Run examples
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("MDSOInstrumentation Examples")
    print("=" * 80)

    print("\n1. Circuit Provisioner Example:")
    print("-" * 80)
    plan = CircuitProvisionerPlan()
    plan.run(
        circuit_id="22.ABCD.123456..",
        resource_id="550e8400-e29b-41d4-a716-446655440000"
    )

    print("\n2. Device Audit Script:")
    print("-" * 80)
    device_audit_script()

    print("\n3. Error Handling Example:")
    print("-" * 80)
    try:
        error_handling_example()
    except ValueError:
        pass  # Expected

    print("\n4. Context Propagation Example:")
    print("-" * 80)
    context_propagation_example()

    print("\n5. Advanced Configuration Example:")
    print("-" * 80)
    advanced_configuration_example()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)
